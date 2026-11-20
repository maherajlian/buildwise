import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from no_paid_ai import scan


class NoPaidAiTests(unittest.TestCase):
    def check_content(self, filename: str, content: str) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / filename).write_text(content)
            violations, checked = scan(root)
            self.assertEqual(checked, 1)
            return violations

    def test_all_denied_dependencies_in_each_manifest(self):
        for filename in ["pyproject.toml", "uv.lock", "package.json", "pnpm-lock.yaml"]:
            for name in [
                "openai",
                "anthropic",
                "google-generativeai",
                "google-genai",
                "litellm",
                "langchain",
                "langchain-core",
                "langchain_openai",
                "@ai-sdk/openai",
                "@ai-sdk/provider",
                "cohere",
                "mistralai",
                "groq",
                "replicate",
                "@google/genai",
                "@google/generative-ai",
                "cohere-ai",
            ]:
                with self.subTest(filename=filename, name=name):
                    self.assertTrue(self.check_content(filename, f'"{name}": "1.0"'))

    def test_python_imports(self):
        for content in [
            "import openai as client",
            "from anthropic import Client",
            "from google import genai",
            "import google.generativeai",
            "from langchain_core.messages import HumanMessage",
            '__import__("groq")',
            'importlib.import_module("replicate")',
        ]:
            with self.subTest(content=content):
                self.assertTrue(self.check_content("module.py", content))

    def test_javascript_imports(self):
        for content in [
            'import Client from "openai";',
            'import "@ai-sdk/provider";',
            'export { generate } from "langchain/core";',
            'const sdk = require("cohere");',
            'await import("mistralai");',
            'import {\n Client,\n} from "anthropic";',
        ]:
            with self.subTest(content=content):
                self.assertTrue(self.check_content("client.ts", content))

    def test_empty_and_allowed_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(scan(Path(directory)), ([], 0))
        for filename, content in [
            ("pyproject.toml", 'dependencies = ["fastapi", "opentelemetry-sdk"]'),
            ("package.json", '{"dependencies":{"openapi-fetch":"1"}}'),
            ("module.py", '# import openai\nmessage = "import anthropic"'),
            ("client.ts", 'import { api } from "./api";'),
        ]:
            self.assertEqual(self.check_content(filename, content), [])

    def test_ignores_installed_dependencies_and_generated_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ["node_modules", ".venv", ".next", "out"]:
                (root / name).mkdir()
                (root / name / "package.json").write_text('{"name":"openai"}')
            self.assertEqual(scan(root), ([], 0))

    def test_invalid_python_fails_closed(self):
        self.assertIn("cannot scan", self.check_content("broken.py", "import (")[0])

    def test_cli_exit_codes(self):
        script = Path(__file__).with_name("no_paid_ai.py")
        with tempfile.TemporaryDirectory() as directory:
            command = [sys.executable, str(script), "--root", directory]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            Path(directory, "uv.lock").write_text('name = "openai"')
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("No-paid-AI guard: FAIL", result.stdout)


if __name__ == "__main__":
    unittest.main()
