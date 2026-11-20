"""Reject known model SDK dependencies and source imports without third-party tools."""

import argparse
import ast
import os
import re
from pathlib import Path

BLOCKED = re.compile(
    r"(?<![a-z0-9_-])(?:openai|anthropic|google[-_.]generativeai|"
    r"google[-_.]genai|litellm|langchain[a-z0-9_.-]*|@ai-sdk/[a-z0-9_.-]+|"
    r"@google/(?:generative-ai|genai)|cohere(?:-ai)?|mistralai|groq|replicate)"
    r"(?![a-z0-9_-])",
    re.IGNORECASE,
)
JS_IMPORT = re.compile(
    r"\b(?:import|export)\s+(?:[^;]*?\s+from\s*)?[\"']([^\"']+)[\"']"
    r"|\b(?:import|require)\s*\(\s*[\"']([^\"']+)[\"']",
)
MANIFESTS = {"pyproject.toml", "uv.lock", "package.json", "pnpm-lock.yaml"}
SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
EXCLUDED = {
    ".git",
    ".venv",
    "node_modules",
    ".next",
    "out",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "test-results",
    "playwright-report",
}


def source_imports(path: Path, content: str) -> list[str]:
    if path.suffix != ".py":
        return [first or second for first, second in JS_IMPORT.findall(content)]
    imports = []
    for node in ast.walk(ast.parse(content, filename=str(path))):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and not node.level:
            imports.extend(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Call) and node.args:
            dynamic = (
                isinstance(node.func, ast.Name) and node.func.id == "__import__"
            ) or (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "import_module"
            )
            if dynamic and isinstance(node.args[0], ast.Constant):
                if isinstance(node.args[0].value, str):
                    imports.append(node.args[0].value)
    return imports


def scan(root: Path) -> tuple[list[str], int]:
    violations = []
    checked = 0
    for directory, folders, files in os.walk(root):
        folders[:] = sorted(folder for folder in folders if folder not in EXCLUDED)
        for filename in sorted(files):
            path = Path(directory) / filename
            if path.name not in MANIFESTS and path.suffix not in SOURCE_SUFFIXES:
                continue
            checked += 1
            relative = path.relative_to(root)
            try:
                content = path.read_text(encoding="utf-8")
                candidates = (
                    [content]
                    if path.name in MANIFESTS
                    else source_imports(path, content)
                )
                for candidate in candidates:
                    for match in BLOCKED.finditer(candidate):
                        violations.append(f"{relative}: forbidden SDK {match.group()}")
            except (OSError, UnicodeError, SyntaxError) as error:
                violations.append(f"{relative}: cannot scan ({type(error).__name__})")
    return violations, checked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    violations, checked = scan(parser.parse_args().root.resolve())
    if violations:
        print("No-paid-AI guard: FAIL")
        for violation in violations:
            print(violation)
        return 1
    print(f"No-paid-AI guard: PASS ({checked} manifests/source files checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
