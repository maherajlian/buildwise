from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from app.modules.operations.generator import generate, markdown
from app.modules.operations.generator import test_csv as export_csv
from app.modules.operations.schemas import OperationsRead
from app.modules.operations.schemas import TestRead as CaseRead


def context() -> dict[str, Any]:
    return {
        "discovery": {
            "risks": ["Provider outage"],
            "assumptions": ["Stable internet"],
            "constraints": ["GDPR compliance"],
            "integrations": ["Email provider"],
            "open_questions": ["Launch date?"],
            "target_users": ["Web users"],
        },
        "requirements": [
            {
                "title": "Book a table",
                "type": "functional",
                "priority": "P0",
                "acceptance_criteria": ["Booking confirmed"],
            },
            {
                "title": "Guest offers",
                "type": "functional",
                "priority": "P2",
                "acceptance_criteria": ["Opt in required"],
            },
            {
                "title": "Future feature",
                "type": "functional",
                "priority": "P1",
                "status": "deferred",
                "acceptance_criteria": ["Reviewed manually"],
            },
            {
                "title": "Latency and security",
                "type": "non_functional",
                "priority": "P1",
                "description": "Encrypt PII; p95 < 200 ms under 1000 users",
                "acceptance_criteria": ["Cross-owner access rejected"],
            },
            {"title": "WCAG accessibility", "type": "non_functional", "priority": "P1"},
        ],
        "technologies": {
            "frontend": "Next.js",
            "backend": "FastAPI",
            "hosting": "Render",
        },
    }


def test_requirement_rules_numbers_and_determinism() -> None:
    ctx = context()
    original = deepcopy(ctx)
    result = generate(ctx, {"auth_needs": "basic", "ops_capability": "low"})
    assert ctx == original
    assert result == generate(ctx, {"auth_needs": "basic", "ops_capability": "low"})
    reordered = deepcopy(ctx)
    reordered["requirements"].reverse()
    assert result == generate(
        reordered, {"auth_needs": "basic", "ops_capability": "low"}
    )
    cases = result["test_cases"]
    assert len([c for c in cases if c["category"] == "unit"]) == 3
    assert len([c for c in cases if c["category"] == "integration"]) == 3
    assert {
        c["description"] for c in cases if c["category"] == "manual_acceptance"
    } == {"Opt in required", "Reviewed manually"}
    assert any(
        c["category"] == "e2e" and c["description"] == "Booking confirmed"
        for c in cases
    )
    assert {"api_contract", "accessibility", "security", "performance"} <= {
        c["category"] for c in cases
    }
    performance = next(c for c in cases if c["category"] == "performance")
    assert (
        "200 ms" in performance["description"]
        and "1000 users" in performance["description"]
    )
    assert all(
        c["rationale"]
        and c["status"] == "proposed"
        and c["executed_at"] is None
        and c["result_notes"] == ""
        for c in cases
    )
    assert not any(
        c["category"]
        in {"model_evaluation", "prompt_regression", "tool_use_evaluation"}
        for c in cases
    )
    assert any("Assumption proves false" in r["title"] for r in result["risks"])
    assert any("Third-party dependency" in r["title"] for r in result["risks"])
    assert any(r["category"] == "compliance" for r in result["risks"])
    assert all(
        1 <= r["likelihood"] <= 5 and 1 <= r["impact"] <= 5 and r["rationale"]
        for r in result["risks"]
    )
    latency = next(s for s in result["slos"] if s["name"] == "Request latency")
    assert latency["target"] == "p95 < 200 ms"
    assert "Latency and security" in latency["rationale"]
    assert all(
        "multi-window" in s["alert"] and s["status"] == "suggested"
        for s in result["slos"]
    )


@pytest.mark.parametrize(
    "ai,enabled",
    [
        (None, False),
        ("not_needed", False),
        (False, False),
        ("required", True),
        (True, True),
    ],
)
def test_ai_categories_only_when_explicitly_required(ai: object, enabled: bool) -> None:
    result = generate({}, {"ai_layer": ai})
    categories = {case["category"] for case in result["test_cases"]}
    assert (
        {"model_evaluation", "prompt_regression", "tool_use_evaluation"} <= categories
    ) is enabled


def test_empty_inputs_defaults_and_conditional_slos() -> None:
    result = generate({}, {"auth_needs": "none", "ops_capability": "high"})
    assert result["test_cases"] == [] and result["risks"] == []
    assert (
        next(s for s in result["slos"] if s["name"] == "Request latency")["target"]
        == "p95 < 500 ms"
    )
    expanded = generate(
        {},
        {
            "scale": "large",
            "ops_capability": "high",
            "background_jobs": "yes",
            "realtime": "yes",
        },
    )
    assert expanded["slos"][0]["target"] == "99.9%"
    assert {"Background-job completion", "Data freshness"} <= {
        s["name"] for s in expanded["slos"]
    }


def test_empty_exports_do_not_claim_execution() -> None:
    data = OperationsRead(test_cases=[], risks=[], slos=[])
    text = markdown(data)
    assert "Generated deterministically from requirements" in text
    assert "Proposed (not yet run): 0" in text and "Executed: 0" in text
    assert "passed" not in text
    assert export_csv(data).startswith(
        "title,category,description,rationale,status,executed,"
    )


def test_integration_signals_and_unrecorded_export_safety() -> None:
    result = generate({}, {"integrations": ["payments"]})
    assert any(
        c["category"] == "security"
        and "integrations includes payments" in c["rationale"]
        for c in result["test_cases"]
    )
    now = datetime.now(UTC)
    case = CaseRead(
        id=uuid4(),
        project_id=uuid4(),
        title="=Untrusted title",
        category="unit",
        status="passed",
        result_notes="",
        executed=False,
        source="user",
        edited=False,
        created_at=now,
        updated_at=now,
    )
    data = OperationsRead(test_cases=[case], risks=[], slos=[])
    assert "Status: passed" not in markdown(data)
    assert "Executed: 0" in markdown(data)
    assert "'=Untrusted title" in export_csv(data)
    assert ",proposed,False," in export_csv(data)
