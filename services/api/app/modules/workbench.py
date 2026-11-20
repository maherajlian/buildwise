from uuid import UUID

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.discovery.schemas import STEPS, completed_steps
from app.modules.operations import generator as operations
from app.modules.operations import service as operations_service
from app.modules.planning import service as planning
from app.modules.planning.models import PlanTask
from app.modules.projects.access import (
    OptionalOwnerToken,
    OwnerToken,
    get_project,
    owner_hash,
)
from app.modules.projects.models import Discovery, Project, Requirement
from app.modules.recommendations.engine import recommend
from app.modules.recommendations.router import effective
from app.modules.specifications import generator as specs
from app.modules.specifications.models import Artefact
from app.telemetry.operations import observed

router = APIRouter(prefix="/api/v1", tags=["workbench"])


class RecentProject(BaseModel):
    id: UUID
    name: str
    stage: str
    outstanding_requirements: int
    open_tasks: int
    recent_artefacts: list[str]


@router.get("/dashboard", response_model=list[RecentProject])
def dashboard(
    request: Request, response: Response, x_project_token: OwnerToken
) -> list[RecentProject]:
    response.headers["Cache-Control"] = "private, no-store"
    with Session(request.app.state.engine) as session:
        projects = session.scalars(
            select(Project)
            .where(Project.owner_hash == owner_hash(x_project_token))
            .order_by(Project.updated_at.desc(), Project.id)
            .limit(3)
        )
        result = []
        for project in projects.all():
            discovery = session.get(Discovery, project.id)
            requirements = session.scalar(
                select(func.count())
                .select_from(Requirement)
                .where(
                    Requirement.project_id == project.id,
                    Requirement.status == "proposed",
                )
            )
            task_count, open_tasks = session.execute(
                select(
                    func.count(), func.count().filter(PlanTask.status != "done")
                ).where(PlanTask.project_id == project.id)
            ).one()
            titles = list(
                session.scalars(
                    select(Artefact.title)
                    .where(Artefact.project_id == project.id)
                    .order_by(Artefact.updated_at.desc(), Artefact.id)
                    .limit(3)
                )
            )
            stage = "Discovery"
            if project.status == "archived":
                stage = "Archived"
            elif task_count:
                stage = "Build plan"
            elif titles:
                stage = "Specifications"
            elif discovery and len(completed_steps(discovery.answers)) == len(STEPS):
                stage = "Architecture"
            result.append(
                RecentProject(
                    id=project.id,
                    name=project.name,
                    stage=stage,
                    outstanding_requirements=requirements or 0,
                    open_tasks=open_tasks,
                    recent_artefacts=titles,
                )
            )
        return result


def brief(discovery: Discovery | None) -> str:
    lines = ["## Project brief"]
    answers = discovery.answers if discovery else {}
    for step in STEPS:
        lines.append(f"### {step.title}")
        for field in step.fields:
            value = answers.get(field)
            label = field.replace("_", " ").capitalize()
            body = specs.bullets(value) if isinstance(value, list) else value
            lines.extend([f"**{label}**", body or "Not answered yet."])
    return "\n\n".join(lines)


def recommendations(request: Request, session: Session, project_id: UUID) -> str:
    _, signals, notes = effective(session, project_id)
    result = recommend(signals, request.app.state.catalogue)
    lines = [
        "## Technology recommendations",
        f"Catalogue: {result.catalogue_version} · Rules: {result.rules_version}",
        result.disclaimer,
        *notes,
    ]
    for item in result.recommendations:
        label = item.category.replace("_", " ").capitalize()
        if not item.recommendation:
            lines.extend([f"### {label}", item.explanation])
            continue
        selected = item.recommendation
        lines.extend(
            [
                f"### {label}: {selected.name}",
                item.reason,
                f"Cost ({selected.cost_category}): {selected.cost_note}",
                f"Complexity: {selected.operational_complexity}",
                f"Operational burden: {selected.operational_burden}",
                "Trade-offs: " + "; ".join(selected.trade_offs),
                "Revisit if: " + "; ".join(selected.change_conditions),
                "Alternatives: "
                + (", ".join(a.name for a in item.alternatives) or "None"),
            ]
        )
        for match in selected.matched_rules:
            inputs = ", ".join(
                f"{signal.label}={signal.value}" for signal in match.signals
            )
            lines.append(f"- {match.reason} ({inputs}; {match.weight:+d})")
    return "\n\n".join(lines)


class MarkdownResponse(Response):
    media_type = "text/markdown"


@router.get("/projects/{project_id}/export/markdown", response_class=MarkdownResponse)
@observed("exports")
def export_project_pack(
    project_id: UUID, request: Request, x_project_token: OptionalOwnerToken = None
) -> MarkdownResponse:
    with Session(request.app.state.engine) as session:
        project = get_project(session, project_id, x_project_token)
        documents = specs.ordered(session, project_id)
        return MarkdownResponse(
            "\n\n".join(
                [
                    f"# {project.name} — Project pack",
                    project.description,
                    brief(session.get(Discovery, project_id)),
                    recommendations(request, session, project_id),
                    "## Specifications",
                    "\n\n".join(specs.markdown(doc, level=3) for doc in documents)
                    or "TODO: generate artefacts.",
                    planning.markdown(
                        project, planning.read(session, project_id), level=2
                    ),
                    operations.markdown(
                        operations_service.read(session, project_id), level=2
                    ),
                ]
            ),
            headers={
                "Cache-Control": "private, no-store",
                "Content-Disposition": (
                    'attachment; filename="buildwise-project-pack.md"'
                ),
            },
        )
