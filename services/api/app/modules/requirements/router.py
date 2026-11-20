from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.projects.access import OptionalOwnerToken, OwnerToken, get_project
from app.modules.projects.models import Requirement

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/requirements", tags=["requirements"]
)
MAX_REQUIREMENTS = 200
RequirementType = Literal["functional", "non_functional"]
Priority = Literal["P0", "P1", "P2"]
RequirementStatus = Literal["proposed", "confirmed", "deferred"]
Title = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
Criterion = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
]
Criteria = Annotated[list[Criterion], Field(max_length=20)]


class RequirementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: RequirementType
    title: Title
    description: str = Field(default="", max_length=5000)
    priority: Priority = "P1"
    status: RequirementStatus = "proposed"
    acceptance_criteria: Criteria = []


class RequirementUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: RequirementType | None = None
    title: Title | None = None
    description: str | None = Field(default=None, max_length=5000)
    priority: Priority | None = None
    status: RequirementStatus | None = None
    acceptance_criteria: Criteria | None = None


class RequirementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    type: RequirementType
    title: str
    description: str
    priority: Priority
    status: RequirementStatus
    acceptance_criteria: list[str]
    created_at: datetime
    updated_at: datetime


def owned_requirement(
    session: Session, project_id: UUID, requirement_id: UUID
) -> Requirement:
    requirement = session.get(Requirement, requirement_id)
    if requirement is None or requirement.project_id != project_id:
        raise HTTPException(404, "Requirement not found")
    return requirement


@router.get("", response_model=list[RequirementRead])
def list_requirements(
    project_id: UUID, request: Request, x_project_token: OptionalOwnerToken = None
) -> list[Requirement]:
    with Session(request.app.state.engine) as session:
        get_project(session, project_id, x_project_token)
        return list(
            session.scalars(
                select(Requirement)
                .where(Requirement.project_id == project_id)
                .order_by(Requirement.priority, Requirement.created_at, Requirement.id)
            )
        )


@router.post("", response_model=RequirementRead, status_code=201)
def create_requirement(
    project_id: UUID,
    body: RequirementCreate,
    request: Request,
    x_project_token: OwnerToken,
) -> Requirement:
    with Session(request.app.state.engine) as session:
        project = get_project(session, project_id, x_project_token, write=True)
        total = session.scalar(
            select(func.count()).where(Requirement.project_id == project_id)
        )
        if (total or 0) >= MAX_REQUIREMENTS:
            raise HTTPException(
                400, f"A project can have at most {MAX_REQUIREMENTS} requirements"
            )
        requirement = Requirement(project_id=project_id, **body.model_dump())
        project.updated_at = func.now()
        session.add(requirement)
        session.commit()
        session.refresh(requirement)
        return requirement


@router.patch("/{requirement_id}", response_model=RequirementRead)
def update_requirement(
    project_id: UUID,
    requirement_id: UUID,
    body: RequirementUpdate,
    request: Request,
    x_project_token: OwnerToken,
) -> Requirement:
    with Session(request.app.state.engine) as session:
        project = get_project(session, project_id, x_project_token, write=True)
        requirement = owned_requirement(session, project_id, requirement_id)
        changes = body.model_dump(exclude_unset=True)
        if any(value is None for value in changes.values()):
            raise HTTPException(422, "Fields cannot be null")
        for key, value in changes.items():
            setattr(requirement, key, value)
        requirement.updated_at = func.now()
        project.updated_at = func.now()
        session.commit()
        session.refresh(requirement)
        return requirement


@router.delete("/{requirement_id}", status_code=204)
def delete_requirement(
    project_id: UUID,
    requirement_id: UUID,
    request: Request,
    x_project_token: OwnerToken,
) -> Response:
    with Session(request.app.state.engine) as session:
        project = get_project(session, project_id, x_project_token, write=True)
        session.delete(owned_requirement(session, project_id, requirement_id))
        project.updated_at = func.now()
        session.commit()
        return Response(status_code=204)
