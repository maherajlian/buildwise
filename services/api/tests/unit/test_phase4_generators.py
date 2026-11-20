from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.operational_rules import generate_slos
from app.modules.operations.generator import generate as generate_operations
from app.modules.planning.models import PlanTask
from app.modules.planning.schemas import (
    EpicRead,
    PlanRead,
    TaskCreate,
    TaskEdit,
    TaskRead,
    Validation,
)
from app.modules.planning.service import bounded_criteria, task_notes, validation_errors
from app.modules.planning.service import markdown as plan_markdown
from app.modules.projects.models import Project
from app.modules.specifications.generator import TITLES, export, markdown, template
from app.modules.specifications.models import Artefact
from app.modules.specifications.schemas import KINDS, Edit, Generate, Section


def context() -> dict[str, Any]:
    return {
        "name": "Orbit",
        "description": "Coordinate launches",
        "discovery": {
            "problem_statement": "Launches are delayed",
            "target_users": ["Operators"],
            "goals": ["Launch on time"],
        },
        "requirements": [
            {
                "id": str(uuid4()),
                "title": "Schedule launch",
                "description": "Avoid collisions",
                "type": "functional",
                "acceptance_criteria": ["Conflict is rejected"],
            },
            {
                "id": str(uuid4()),
                "title": "Fast scheduling",
                "description": "Meet latency budget",
                "type": "non_functional",
                "acceptance_criteria": ["p95 below 200ms"],
            },
        ],
        "technologies": {"backend": "FastAPI", "database": "PostgreSQL"},
    }


def test_templates_deterministic_context_and_complete_markdown() -> None:
    ctx = context()
    items = []
    project = Project(id=uuid4(), name="Orbit", description="Coordinate launches")
    for kind in KINDS:
        sections = template(kind, ctx)
        assert sections == template(kind, ctx)
        assert len({s["key"] for s in sections}) == len(sections)
        for section in sections:
            Section.model_validate(section)
        item = Artefact(
            id=uuid4(),
            project_id=project.id,
            kind=kind,
            title=TITLES[kind],
            sections=sections,
            context=ctx,
        )
        text = markdown(item)
        for section in sections:
            assert section["heading"] in text
            assert section["body"] in text
        items.append(item)
    output = export(project, items)
    assert "Table of contents" in output
    for item in items:
        assert item.title in output
        assert markdown(item) in output
    for phrase in [
        "Orbit",
        "Launches are delayed",
        "Operators",
        "Launch on time",
        "Schedule launch",
        "Conflict is rejected",
        "Fast scheduling",
        "p95 below 200ms",
        "FastAPI",
        "PostgreSQL",
    ]:
        assert phrase in output
    for kind in ["technical_design", "adr", "deployment", "observability"]:
        assert "FastAPI" in str(template(kind, ctx))
    assert "Conflict is rejected" in str(template("user_stories", ctx))
    assert "p95 below 200ms" in str(template("non_functional_requirements", ctx))


def test_empty_templates_and_validation() -> None:
    for kind in KINDS:
        sections = template(kind, {"name": "Empty", "description": ""})
        assert sections
        assert "TODO" in str(sections)
    for bad in [{"kinds": ["invented"]}, {"kinds": []}, {"unknown": True}]:
        with pytest.raises(ValidationError):
            Generate.model_validate(bad)
    for bad in [
        {"title": None},
        {"sections": []},
        {
            "sections": [
                {"key": "x", "heading": "A", "body": ""},
                {"key": "x", "heading": "B", "body": ""},
            ]
        },
    ]:
        with pytest.raises(ValidationError):
            Edit.model_validate(bad)


def test_project_specific_release_and_observability_plans_share_slo_rules() -> None:
    ctx = context()
    ctx["technologies"].update(
        {
            "frontend": "Next.js static export",
            "hosting": "Render Free",
            "auth": "OIDC provider",
            "cache_queue": "Managed Redis",
            "ci_cd": "GitHub Actions",
        }
    )
    ctx["technology_details"] = {
        "hosting": {
            "constraints": ["Service sleeps after inactivity", "Ephemeral filesystem"],
            "operational_burden": "Review resource quotas.",
            "cost_category": "free-tier",
            "cost_note": "pricing/free-tier claims require verification",
        }
    }
    ctx["discovery"]["integrations"] = ["SMS provider", "Email provider"]
    ctx["signals"] = {
        "auth_needs": "enterprise_sso",
        "scale": "large",
        "ops_capability": "high",
        "background_jobs": "yes",
        "realtime": "yes",
    }
    original = str(ctx)
    deployment = {s["key"]: s["body"] for s in template("deployment", ctx)}
    obs = {s["key"]: s["body"] for s in template("observability", ctx)}
    assert {"target_stack", "release", "rollback"} <= deployment.keys()
    assert {"stack", "signals", "service_objectives", "response"} <= obs.keys()
    assert "Render Free" in deployment["hosting_target_and_limitations"]
    assert "Ephemeral filesystem" in deployment["hosting_target_and_limitations"]
    assert "keep-warm" in deployment["hosting_target_and_limitations"].lower()
    assert "upgrade path" in deployment["hosting_target_and_limitations"]
    assert all(
        value in deployment["environment_variables"]
        for value in (
            "DATABASE_URL",
            "AUTH_SECRET",
            "AUTH_CLIENT_SECRET",
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "INTEGRATION_SMS_PROVIDER_API_KEY",
            "INTEGRATION_EMAIL_PROVIDER_API_KEY",
            "QUEUE_URL",
        )
    )
    assert "NEXT_PUBLIC_*" in deployment["secret_management"]
    assert "rotate" in deployment["secret_management"]
    assert all(
        value in deployment["release"]
        for value in (
            "Lint",
            "unit",
            "Integration",
            "contract",
            "end-to-end",
            "Security scan",
            "Migrate",
            "Deploy",
            "/health + /ready",
            "Rollback",
            "GitHub Actions",
        )
    )
    assert "schema compatibility" in deployment["rollback"]
    assert "503" in deployment["health_and_readiness"]
    assert "PostgreSQL" in deployment["health_and_readiness"]
    assert "trace/span IDs" in obs["signals"] and "Redact" in obs["signals"]
    assert "Fast scheduling" in obs["metrics"] and "200ms" in obs["metrics"]
    assert "queue depth" in obs["metrics"] and "freshness" in obs["metrics"]
    assert (
        "FastAPI" in obs["distributed_tracing"]
        and "PostgreSQL" in obs["distributed_tracing"]
    )
    assert "Email provider" in obs["distributed_tracing"]
    assert "privacy budgets" in obs["distributed_tracing"]
    slos = generate_slos(ctx, ctx["signals"])
    assert slos == generate_operations(ctx, ctx["signals"])["slos"]
    for slo in slos:
        assert all(
            slo[key] in obs["slo_candidates"]
            for key in ("name", "sli", "target", "window", "alert", "rationale")
        )
    assert "99.9%" in obs["slo_candidates"] and "p95 < 200ms" in obs["slo_candidates"]
    assert all(
        value in obs["response"]
        for value in (
            "Render Free",
            "PostgreSQL",
            "Email provider",
            "SMS provider",
            "CORS",
            "lost browser token",
            "Managed Redis",
            "vendor status",
            "rollback",
        )
    )
    assert original == str(ctx)
    assert template("observability", ctx) == template("observability", ctx)


def test_plans_handle_static_no_auth_and_normalize_integration_variable_names() -> None:
    ctx: dict[str, Any] = {
        "name": "Static site",
        "technologies": {"frontend": "Static HTML", "hosting": "Paid CDN"},
        "signals": {"auth_needs": "none", "background_jobs": "no"},
        "discovery": {"integrations": ["a-b", "a b", "123"]},
    }
    sections = {s["key"]: s["body"] for s in template("deployment", ctx)}
    env = sections["environment_variables"]
    assert (
        "DATABASE_URL" not in env
        and "AUTH_SECRET" not in env
        and "QUEUE_URL" not in env
    )
    assert "INTEGRATION_A_B_API_KEY" in env and "INTEGRATION_A_B_2_API_KEY" in env
    assert "INTEGRATION_123_API_KEY" in env
    assert "No API is selected" in sections["health_and_readiness"]
    assert "do not assume" in sections["hosting_target_and_limitations"]
    assert "TODO" in str(template("observability", {"name": "Empty"}))
    reversed_ctx = {**ctx, "discovery": {"integrations": ["123", "a b", "a-b"]}}
    assert template("deployment", ctx) == template("deployment", reversed_ctx)


def task(key: str, **kwargs: Any) -> PlanTask:
    return PlanTask(id=uuid4(), key=key, status="backlog", depends_on=[], **kwargs)


def test_dependency_validation_empty_normal_and_error_cases() -> None:
    assert validation_errors([]) == []
    a, b = task("T-001"), task("T-002")
    b.depends_on = [str(a.id)]
    assert validation_errors([a, b]) == []
    a.depends_on = [str(b.id)]
    assert "Dependency cycle detected" in validation_errors([a, b])
    a.depends_on = [str(a.id)]
    assert any("self-dependency" in e for e in validation_errors([a]))
    a.depends_on = [str(uuid4())]
    assert any("unknown or other-project" in e for e in validation_errors([a]))
    a.depends_on = []
    for status in ["in_progress", "review", "done"]:
        b.status = status
        assert any("must be done" in e for e in validation_errors([a, b]))
        a.status = "done"
        assert validation_errors([a, b]) == []
        a.status = "backlog"
    for status in ["backlog", "ready"]:
        b.status = status
        assert validation_errors([a, b]) == []


def test_plan_markdown_complete() -> None:
    project = Project(id=uuid4(), name="Orbit", description="Coordinate launches")
    epic = EpicRead(
        id=uuid4(),
        project_id=project.id,
        title="Foundation",
        description="Setup",
        position=0,
    )
    tasks = [
        TaskRead(
            id=uuid4(),
            project_id=project.id,
            key=f"T-{i:03d}",
            epic_id=epic.id if i == 1 else None,
            title=f"Task {i}",
            description=f"Description {i}",
            implementation_notes=f"Notes {i}",
            skill=f"Tool {i}",
            workflow=f"pair: review {i}",
            acceptance_criteria=[f"Check {i}"],
        )
        for i in [1, 2]
    ]
    tasks[1].depends_on = [tasks[0].id]
    plan = PlanRead(
        epics=[epic], tasks=tasks, validation=Validation(valid=True, errors=[])
    )
    output = plan_markdown(project, plan)
    assert "Foundation" in output
    assert "Ungrouped tasks" in output
    for t in tasks:
        for value in [
            t.key,
            t.title,
            t.description,
            t.implementation_notes,
            t.skill,
            t.workflow,
            *t.acceptance_criteria,
            t.status,
            t.priority,
        ]:
            assert value in output
    plan.tasks = []
    assert "TODO" in plan_markdown(project, plan)


def test_task_notes_are_scoped_bullets_with_missing_context_placeholders() -> None:
    artefacts = [Artefact(kind=kind, title=TITLES[kind], sections=[]) for kind in KINDS]
    notes = task_notes(
        artefacts,
        {"hosting": "Render Free", "database": "PostgreSQL"},
        ("deployment", "observability"),
        ("hosting",),
    )
    assert notes == "- See: Deployment plan, Observability plan\n- Hosting: Render Free"
    assert "PostgreSQL" not in notes
    assert "Product requirements document" not in notes
    empty = task_notes([], {}, ("deployment", "observability"), ("hosting",))
    assert "TODO: review Deployment plan" in empty
    assert "TODO: select technology" in empty
    assert all(line.startswith("- ") for line in empty.splitlines())


@pytest.mark.parametrize("count", [0, 1, 20, 21, 40])
@pytest.mark.parametrize("length", [1, 1000, 1001])
def test_generated_criteria_fit_create_and_edit_limits(count: int, length: int) -> None:
    criteria = [str(i % 10) * length for i in range(count)]
    result = bounded_criteria(criteria)
    assert result == bounded_criteria(criteria)
    assert criteria == [str(i % 10) * length for i in range(count)]
    TaskCreate(title="Generated task", acceptance_criteria=result)
    TaskEdit(acceptance_criteria=result)
    assert len(result) == min(count, 20)
    if count > 20:
        assert result[-1] == (
            f"…and {count - 19} more, see Acceptance criteria artefact"
        )
    else:
        assert result == [
            item[:999] + "…" if length > 1000 else item for item in criteria
        ]
