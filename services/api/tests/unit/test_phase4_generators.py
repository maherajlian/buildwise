from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.planning.models import PlanTask
from app.modules.planning.schemas import EpicRead, PlanRead, TaskRead, Validation
from app.modules.planning.service import markdown as plan_markdown
from app.modules.planning.service import task_notes, validation_errors
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
