from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.discovery.schemas import (
    STEPS,
    DiscoveryAnswers,
    StepId,
    completed_steps,
)
from app.modules.projects.access import OptionalOwnerToken, OwnerToken, get_project
from app.modules.projects.models import Discovery, Project

router = APIRouter(prefix="/api/v1/projects/{project_id}/discovery", tags=["discovery"])


class DiscoveryStep(BaseModel):
    id: str
    title: str
    fields: list[str]


class DiscoveryWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answers: DiscoveryAnswers
    current_step: StepId = "problem"


class DiscoveryRead(BaseModel):
    answers: DiscoveryAnswers
    current_step: StepId
    steps: list[DiscoveryStep]
    completed_steps: list[str]
    updated_at: datetime | None


def read_model(discovery: Discovery | None) -> DiscoveryRead:
    answers = DiscoveryAnswers.model_validate(discovery.answers if discovery else {})
    return DiscoveryRead(
        answers=answers,
        current_step=discovery.current_step if discovery else "problem",  # type: ignore[arg-type]
        steps=[
            DiscoveryStep(id=s.id, title=s.title, fields=list(s.fields)) for s in STEPS
        ],
        completed_steps=completed_steps(answers.model_dump()),
        updated_at=discovery.updated_at if discovery else None,
    )


@router.get("", response_model=DiscoveryRead)
def read_discovery(
    project_id: UUID, request: Request, x_project_token: OptionalOwnerToken = None
) -> DiscoveryRead:
    with Session(request.app.state.engine) as session:
        get_project(session, project_id, x_project_token)
        return read_model(session.get(Discovery, project_id))


@router.put("", response_model=DiscoveryRead)
def save_discovery(
    project_id: UUID,
    body: DiscoveryWrite,
    request: Request,
    x_project_token: OwnerToken,
) -> DiscoveryRead:
    with Session(request.app.state.engine) as session:
        project: Project = get_project(session, project_id, x_project_token, write=True)
        discovery = session.get(Discovery, project_id) or Discovery(
            project_id=project_id
        )
        discovery.answers = body.answers.model_dump()
        discovery.current_step = body.current_step
        discovery.updated_at = func.now()
        project.updated_at = func.now()
        session.add(discovery)
        session.commit()
        session.refresh(discovery)
        return read_model(discovery)
