import re
from collections.abc import Sequence
from typing import Any, Literal

from app.modules.recommendations.schemas import Evidence, Overrides, Signal

DEFAULTS: dict[str, str | list[str]] = {
    "budget": "low",
    "scale": "small",
    "data_shape": "relational",
    "background_jobs": "no",
    "realtime": "no",
    "auth_needs": "basic",
    "ops_capability": "low",
    "integrations": [],
    "ai_layer": "not_needed",
}
PATTERNS: dict[str, dict[str, str]] = {
    "budget": {
        "zero": r"zero budget|no budget|free only",
        "low": r"small team|low budget|MVP",
        "flexible": r"flexible budget|unlimited budget",
    },
    "scale": {
        "large": r"millions of users|global scale|large scale",
        "medium": r"thousands of users|medium scale",
    },
    "data_shape": {
        "mixed": r"mixed data|relational and document",
        "document": r"document database|unstructured documents",
        "relational": r"booking|bookings|relational|transactions|tenant",
    },
    "background_jobs": {
        "yes": r"reminder|reminders|background jobs|scheduled|queue|queues"
    },
    "realtime": {"yes": r"real.time|live updates|websocket|chat"},
    "auth_needs": {
        "enterprise_sso": r"enterprise SSO|SAML|single sign.on",
        "none": r"no authentication|public only",
    },
    "ops_capability": {
        "high": r"dedicated platform team|high ops|SRE team",
        "medium": r"medium ops|experienced operators",
    },
    "integrations": {
        "payments": r"payment|payments|stripe|deposit|deposits",
        "email": r"email",
        "sms": r"SMS|text messages",
        "calendar": r"calendar",
        "maps": r"maps|geocoding",
        "generic_api": r"external API|third.party API|webhook|webhooks",
    },
}
AI_PATTERN = r"AI|machine learning|language model|LLM|generative"


def derive_signals(
    answers: dict[str, Any],
    requirements: Sequence[dict[str, Any]],
    overrides: Overrides,
) -> tuple[list[Signal], list[str]]:
    texts: list[tuple[str, str]] = []
    for field, value in sorted(answers.items()):
        if isinstance(value, str):
            texts.append((f"discovery.{field}", value))
        elif isinstance(value, list):
            texts.extend(
                (f"discovery.{field}[{i}]", str(v)) for i, v in enumerate(value)
            )
    for req in sorted(requirements, key=lambda r: str(r["title"])):
        for field in ("title", "description", "acceptance_criteria"):
            value = req.get(field, "")
            values = value if isinstance(value, list) else [value]
            texts.extend(
                (f'requirement "{req["title"]}".{field}[{i}]', str(v))
                for i, v in enumerate(values)
            )
    explicit = overrides.model_dump(exclude_unset=True)
    signals = []
    for key, default in sorted(DEFAULTS.items()):
        source: Literal["explicit", "detected", "default"]
        evidence = []
        detected = []
        for value, pattern in PATTERNS.get(key, {}).items():
            matches = []
            for field, text in texts:
                match = re.search(r"\b(?:" + pattern + r")\b", text, re.I)
                if match:
                    start = max(0, match.start() - 80)
                    matches.append(
                        Evidence(field=field, excerpt=text[start : start + 240])
                    )
            if matches:
                detected.append(value)
                evidence.extend(matches)
        if key in explicit:
            value = explicit[key]
            if isinstance(value, list):
                value = sorted(set(value))
            source = "explicit"
            evidence = [Evidence(field=f"overrides.{key}", excerpt=str(value))]
        elif detected:
            value = sorted(detected) if isinstance(default, list) else detected[0]
            source = "detected"
        else:
            value = default
            source = "default"
        signals.append(
            Signal(
                id=key,
                label=key.replace("_", " ").capitalize(),
                value=value,
                source=source,
                evidence=evidence,
            )
        )
    notes = []
    if any(re.search(r"\b(?:" + AI_PATTERN + r")\b", t, re.I) for _, t in texts):
        notes.append(
            "AI-related text detected. Set ai_layer explicitly to required to "
            "evaluate optional, cost-dependent AI candidates; "
            "a mention does not enable AI."
        )
    return signals, notes
