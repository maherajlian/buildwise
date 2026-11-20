from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.planning.models import Epic, PlanTask
from app.modules.planning.schemas import EpicRead, PlanRead, TaskRead, Validation
from app.modules.projects.models import Project
from app.modules.recommendations.schemas import Catalogue
from app.modules.specifications.generator import TITLES, ordered, snapshot
from app.modules.specifications.models import Artefact


def bounded_criteria(criteria: list[str]) -> list[str]:
    result = [item if len(item) <= 1000 else item[:999] + "…" for item in criteria[:20]]
    if len(criteria) > 20:
        result[19] = f"…and {len(criteria) - 19} more, see Acceptance criteria artefact"
    return result


def task_notes(
    artefacts: list[Artefact],
    technologies: dict[str, str],
    kinds: tuple[str, ...],
    categories: tuple[str, ...],
) -> str:
    titles = [
        next(
            (a.title for a in artefacts if a.kind == kind),
            f"TODO: review {TITLES[kind]}",
        )
        for kind in kinds
    ]
    return "\n".join(
        ["- See: " + ", ".join(titles)]
        + [
            f"- {category.capitalize()}: "
            f"{technologies.get(category) or 'TODO: select technology'}"
            for category in categories
        ]
    )


def validation_errors(tasks: list[PlanTask]) -> list[str]:
    by_id = {str(t.id): t for t in tasks}
    errors: list[str] = []
    for task in tasks:
        deps = task.depends_on
        if str(task.id) in deps:
            errors.append(f"{task.key}: self-dependency is not allowed")
        for dep in deps:
            if dep not in by_id:
                errors.append(f"{task.key}: unknown or other-project dependency {dep}")
            elif (
                task.status in {"in_progress", "review", "done"}
                and by_id[dep].status != "done"
            ):
                errors.append(
                    f"{task.key}: all dependencies must be done before {task.status}"
                )
    remaining = {
        tid: {d for d in t.depends_on if d in by_id} for tid, t in by_id.items()
    }
    while remaining:
        roots = {tid for tid, deps in remaining.items() if not deps}
        if not roots:
            errors.append("Dependency cycle detected")
            break
        remaining = {
            tid: deps - roots for tid, deps in remaining.items() if tid not in roots
        }
    return list(dict.fromkeys(errors))


def tasks_for(session: Session, project_id: UUID) -> list[PlanTask]:
    return list(
        session.scalars(
            select(PlanTask)
            .where(PlanTask.project_id == project_id)
            .order_by(PlanTask.key)
        )
    )


def validate(session: Session, project_id: UUID) -> None:
    errors = validation_errors(tasks_for(session, project_id))
    if errors:
        raise HTTPException(422, "; ".join(errors))


def read(session: Session, project_id: UUID) -> PlanRead:
    epics = session.scalars(
        select(Epic)
        .where(Epic.project_id == project_id)
        .order_by(Epic.position, Epic.title, Epic.id)
    ).all()
    tasks = tasks_for(session, project_id)
    errors = validation_errors(tasks)
    return PlanRead(
        epics=[EpicRead.model_validate(e) for e in epics],
        tasks=[TaskRead.model_validate(t) for t in tasks],
        validation=Validation(valid=not errors, errors=errors),
    )


def next_key(session: Session, project_id: UUID) -> str:
    numbers = [int(t.key[2:]) for t in tasks_for(session, project_id)]
    return f"T-{max(numbers, default=0) + 1:03d}"


def generate(
    session: Session, project: Project, catalogue: Catalogue, overwrite: bool = False
) -> PlanRead:
    if not overwrite and (
        tasks_for(session, project.id)
        or session.scalar(select(Epic.id).where(Epic.project_id == project.id).limit(1))
    ):
        return read(session, project.id)
    session.execute(delete(PlanTask).where(PlanTask.project_id == project.id))
    session.execute(delete(Epic).where(Epic.project_id == project.id))
    context = snapshot(session, project, catalogue)
    artefacts = ordered(session, project.id)
    counter = 0

    def epic(title: str, description: str, position: int) -> Epic:
        item = Epic(
            project_id=project.id,
            title=title[:200],
            description=description,
            position=position,
        )
        session.add(item)
        session.flush()
        return item

    def task(
        group: Epic,
        title: str,
        description: str,
        kinds: tuple[str, ...],
        categories: tuple[str, ...],
        deps: list[str],
        criteria: list[str],
        skill: str,
        priority: str = "P1",
        requirement_id: UUID | None = None,
    ) -> PlanTask:
        nonlocal counter
        counter += 1
        item = PlanTask(
            project_id=project.id,
            epic_id=group.id,
            key=f"T-{counter:03d}",
            title=title[:200],
            description=description,
            priority=priority,
            status="backlog" if deps else "ready",
            implementation_notes=task_notes(
                artefacts, context["technologies"], kinds, categories
            ),
            acceptance_criteria=bounded_criteria(criteria),
            skill=skill,
            workflow=(
                "pair: human confirms scope and reviews; agent implements "
                "deterministic changes and tests; human approves merge."
            ),
            depends_on=deps,
            requirement_id=requirement_id,
        )
        session.add(item)
        session.flush()
        return item

    foundation = epic(
        "Foundation", f"Establish the reviewed architecture for {project.name}.", 0
    )
    first = task(
        foundation,
        "Review design and establish project foundation",
        "Review the architecture and prepare the repository for implementation. "
        "Confirm local development checks pass.",
        ("architecture", "technical_design"),
        ("backend", "database"),
        [],
        [
            "Architecture and security decisions approved",
            "Local environment and checks run",
        ],
        "Architecture / repository tooling",
        "P0",
    )
    functional: list[str] = []
    for index, req in enumerate(context["requirements"], 1):
        if req["type"] != "functional":
            continue
        group = epic(req["title"], req["description"], index)
        item = task(
            group,
            req["title"],
            "Implement this requirement as a tested user-facing workflow. "
            "Verify its acceptance criteria before review.",
            ("user_stories", "api_contract"),
            ("frontend", "backend"),
            [str(first.id)],
            req["acceptance_criteria"]
            or ["TODO: agree measurable acceptance criteria"],
            "Full-stack engineering / selected stack",
            req["priority"],
            UUID(req["id"]),
        )
        functional.append(str(item.id))
    if not functional:
        group = epic("Product scope", "TODO: discover functional requirements.", 1)
        item = task(
            group,
            "TODO: define and implement the first user journey",
            "Define the first user journey with stakeholders, then implement it "
            "with acceptance tests.",
            ("prd", "user_stories"),
            ("frontend", "backend"),
            [str(first.id)],
            ["TODO: confirm the user journey with stakeholders"],
            "Product discovery / implementation",
        )
        functional.append(str(item.id))
    quality = epic(
        "Quality",
        "Validate acceptance, security and non-functional requirements.",
        1000,
    )
    nfr = [r for r in context["requirements"] if r["type"] == "non_functional"]
    checks = [f"{r['title']}: {c}" for r in nfr for c in r["acceptance_criteria"]]
    quality_task = task(
        quality,
        "Verify quality and security",
        "Run acceptance, security and performance checks. "
        "Resolve failures before preparing the release.",
        ("test_strategy", "security", "non_functional_requirements"),
        ("backend",),
        functional,
        checks or ["TODO: agree quality budgets and security checks"],
        "Testing / security / performance",
        "P0",
    )
    deployment = epic(
        "Deployment & observability", "Release safely and verify service health.", 1001
    )
    task(
        deployment,
        "Deploy and verify telemetry",
        "Deploy the application and verify service health. "
        "Check telemetry and rehearse rollback before release.",
        ("deployment", "observability"),
        ("hosting", "observability"),
        [str(quality_task.id)],
        [
            "Health and smoke checks pass",
            "Dashboards, alerts and rollback are verified",
        ],
        "Platform engineering / CI / telemetry",
    )
    return read(session, project.id)


def markdown(project: Project, plan: PlanRead, *, level: int = 1) -> str:
    lines = [
        f"{'#' * level} {project.name} — Build plan",
        project.description,
        f"{'#' * (level + 1)} Validation",
        "Valid" if plan.validation.valid else "; ".join(plan.validation.errors),
    ]
    by_id = {t.id: t.key for t in plan.tasks}
    for epic in [*plan.epics, None]:
        group = [t for t in plan.tasks if t.epic_id == (epic.id if epic else None)]
        if not epic and not group:
            continue
        lines.extend(
            [
                f"{'#' * (level + 1)} {epic.title if epic else 'Ungrouped tasks'}",
                epic.description if epic else "",
            ]
        )
        for task in group:
            fields: dict[str, Any] = task.model_dump()
            lines.extend(
                [
                    f"{'#' * (level + 2)} {task.key}: {task.title}",
                    task.description,
                    f"Priority: {task.priority} | Status: {task.status}",
                    "Dependencies: "
                    + (
                        ", ".join(by_id.get(d, str(d)) for d in task.depends_on)
                        or "None"
                    ),
                    f"Requirement: {task.requirement_id or 'None'}",
                    f"Skill/tool: {task.skill}",
                    f"Workflow: {task.workflow}",
                    f"{'#' * (level + 3)} Implementation notes",
                    task.implementation_notes,
                    f"{'#' * (level + 3)} Acceptance criteria",
                    "\n".join(f"- {c}" for c in fields["acceptance_criteria"])
                    or "TODO: define criteria",
                ]
            )
    if not plan.tasks:
        lines.append("TODO: generate a build plan.")
    return "\n\n".join(lines) + "\n"
