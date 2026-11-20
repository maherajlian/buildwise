import json
import socket
from pathlib import Path

import jsonschema
import pytest
from pydantic import ValidationError

from app.modules.projects.sample import ANSWERS, REQUIREMENTS
from app.modules.recommendations.catalogue_loader import load_catalogue
from app.modules.recommendations.engine import recommend
from app.modules.recommendations.schemas import CATEGORIES, Catalogue, Overrides, Result
from app.modules.recommendations.signals import derive_signals


def result(**overrides: object) -> Result:
    signals, _ = derive_signals({}, [], Overrides.model_validate(overrides))
    return recommend(signals, load_catalogue())


def test_catalogue_schema_and_references() -> None:
    directory = Path(__file__).parents[2] / "app/modules/recommendations/catalogue"
    schema = json.loads((directory / "catalogue.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(json.loads((directory / "catalogue.json").read_text()), schema)
    catalogue = load_catalogue()
    assert len(catalogue.entries) == 30
    assert all(e.last_reviewed == "2026-11-20" for e in catalogue.entries)
    broken = catalogue.model_dump()
    broken["entries"][0]["selection_rules"] = ["missing"]
    with pytest.raises(ValidationError):
        Catalogue.model_validate(broken)
    broken = catalogue.model_dump()
    broken["rules"][0]["when"] = {"budget": "unknown"}
    with pytest.raises(ValidationError):
        Catalogue.model_validate(broken)


def test_default_rules_every_category() -> None:
    output = result()
    assert [r.category for r in output.recommendations] == CATEGORIES
    selected = {r.category: r.recommendation for r in output.recommendations}
    assert {k: v.id for k, v in selected.items() if v} == {
        "frontend": "nextjs",
        "backend": "fastapi",
        "database": "postgresql",
        "cache_queue": "postgres-jobs",
        "auth": "session-library",
        "hosting": "render-free",
        "ci_cd": "github-actions",
        "observability": "grafana-cloud",
        "integrations": "email-sms-calendar",
    }
    for category in output.recommendations[:-1]:
        assert category.recommendation is not None
        assert len(category.alternatives) == 2
        assert all(
            "Ranked below" in a.reason and a.trade_offs for a in category.alternatives
        )
    assert "sleep" in " ".join(selected["hosting"].constraints).lower()


@pytest.mark.parametrize("scale", ["small", "medium", "large"])
@pytest.mark.parametrize("ops", ["low", "medium", "high"])
def test_kubernetes_requires_scale_and_operators(scale: str, ops: str) -> None:
    hosting = next(
        r
        for r in result(scale=scale, ops_capability=ops).recommendations
        if r.category == "hosting"
    )
    assert hosting.recommendation is not None
    assert (hosting.recommendation.id == "kubernetes") == (
        scale == "large" and ops == "high"
    )


def test_jobs_and_data_rules() -> None:
    selected = {
        r.category: r.recommendation
        for r in result(background_jobs="yes").recommendations
    }
    queue = selected["cache_queue"]
    assert queue and queue.id == "postgres-jobs"
    assert "jobs" in [m.rule_id for m in queue.positive_matches]
    document = next(
        r
        for r in result(data_shape="document").recommendations
        if r.category == "database"
    )
    assert document.recommendation and document.recommendation.id == "mongodb"
    enterprise = next(
        r
        for r in result(auth_needs="enterprise_sso").recommendations
        if r.category == "auth"
    )
    assert enterprise.recommendation and enterprise.recommendation.id == "auth0"


def test_sample_detection_and_evidence() -> None:
    requirements = [
        {"title": t, "description": d, "acceptance_criteria": c}
        for _, t, d, _, _, c in REQUIREMENTS
    ]
    signals, _ = derive_signals(ANSWERS.model_dump(), requirements, Overrides())
    values = {s.id: s for s in signals}
    assert values["budget"].value == "low"
    assert values["budget"].source == "detected"
    assert values["data_shape"].value == "relational"
    assert values["background_jobs"].value == "yes"
    assert {"email", "sms", "calendar"} <= set(values["integrations"].value)
    assert any(
        e.field.startswith("discovery.constraints[") for e in values["budget"].evidence
    )
    signals, _ = derive_signals(
        {"constraints": ["LOW BUDGET"]}, [], Overrides(budget="flexible")
    )
    budget = next(s for s in signals if s.id == "budget")
    assert (budget.value, budget.source) == ("flexible", "explicit")


def test_long_evidence_keeps_matched_phrase() -> None:
    signals, _ = derive_signals(
        {"constraints": ["Context " * 80 + "low budget"]}, [], Overrides()
    )
    budget = next(s for s in signals if s.id == "budget")
    assert "low budget" in budget.evidence[0].excerpt
    assert len(budget.evidence[0].excerpt) <= 240


def test_ai_is_only_explicit_and_word_boundaries() -> None:
    signals, notes = derive_signals({"goals": ["AI and LLM features"]}, [], Overrides())
    ai = recommend(signals, load_catalogue()).recommendations[-1]
    assert notes and ai.status == "not_recommended" and ai.recommendation is None
    assert len(ai.candidates) == 3 and all(e.optional for e in ai.candidates)
    signals, _ = derive_signals({}, [], Overrides(ai_layer="required"))
    ai = recommend(signals, load_catalogue()).recommendations[-1]
    assert ai.recommendation and ai.recommendation.optional
    assert ai.explanation.lower() == "optional, may incur cost."
    signals, notes = derive_signals({"goals": ["chair retail detail"]}, [], Overrides())
    assert not notes
    signal = next(s for s in signals if s.id == "ai_layer")
    signal.value = "required"
    signal.source = "detected"
    assert (
        recommend(signals, load_catalogue()).recommendations[-1].status
        == "not_recommended"
    )


def test_reproducible_no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*args: object, **kwargs: object) -> None:
        raise AssertionError("Generation attempted network I/O")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    signals, _ = derive_signals({}, [], Overrides(integrations=["sms", "email", "sms"]))
    catalogue = load_catalogue()
    first = recommend(signals, catalogue)
    assert (
        first.model_dump_json()
        == recommend(list(reversed(signals)), catalogue).model_dump_json()
    )
    assert len(first.input_fingerprint) == 64
    catalogue.catalogue_version = "2026.11.2"
    changed = recommend(signals, catalogue)
    assert changed.catalogue_version != first.catalogue_version
    assert changed.input_fingerprint == first.input_fingerprint
    assert result(budget="flexible").input_fingerprint != result().input_fingerprint


@pytest.mark.parametrize(
    "overrides",
    [
        {"unknown": "yes"},
        {"scale": "huge"},
        {"budget": None},
        {"integrations": ["unknown"]},
    ],
)
def test_invalid_overrides(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Overrides.model_validate(overrides)


def test_catalogue_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.main import create_app

    def invalid() -> Catalogue:
        raise ValueError("Invalid catalogue")

    monkeypatch.setattr("app.main.load_catalogue", invalid)
    with pytest.raises(ValueError, match="Invalid catalogue"):
        create_app()
