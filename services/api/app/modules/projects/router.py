import logging
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.discovery.schemas import STEPS, completed_steps
from app.modules.projects.access import (
    SAMPLE_PROJECT_ID,
    OptionalOwnerToken,
    OwnerToken,
    get_project,
    owner_hash,
    purge_expired,
)
from app.modules.projects.models import Discovery, Project, Requirement
from app.telemetry.operations import observed

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])
logger = logging.getLogger("buildwise")
ProjectStatus = Literal["draft", "active", "archived"]


def clean_name(value: str) -> str:
    if not value.strip():
        raise ValueError("Name must not be blank")
    return value.strip()


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=10000)
    status: ProjectStatus = "draft"

    _name = field_validator("name")(clean_name)


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    status: ProjectStatus | None = None

    @field_validator("name")
    @classmethod
    def optional_name(cls, value: str | None) -> str | None:
        return None if value is None else clean_name(value)


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str
    status: ProjectStatus
    is_sample: bool
    created_at: datetime
    updated_at: datetime


class ProjectPage(BaseModel):
    items: list[ProjectRead]
    next_cursor: UUID | None


class RequirementCounts(BaseModel):
    total: int
    functional: int
    non_functional: int
    proposed: int
    confirmed: int
    deferred: int
    p0: int


class ProjectOverview(BaseModel):
    project: ProjectRead
    discovery_steps: list[str]
    discovery_completed: list[str]
    discovery_updated_at: datetime | None
    requirements: RequirementCounts
    open_questions: list[str]
    assumptions: list[str]
    missing: list[str]


@router.post("", response_model=ProjectRead, status_code=201)
@observed("projects.create")
def create_project(
    body: ProjectCreate, request: Request, x_project_token: OwnerToken
) -> Project:
    with Session(request.app.state.engine) as session:
        purged = purge_expired(session)
        if purged:
            logger.info("projects_purged")
        project = Project(**body.model_dump(), owner_hash=owner_hash(x_project_token))
        session.add(project)
        session.commit()
        session.refresh(project)
        return project


@router.get("", response_model=ProjectPage)
def list_projects(
    request: Request,
    x_project_token: OwnerToken,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: UUID | None = None,
) -> ProjectPage:
    owner = owner_hash(x_project_token)
    with Session(request.app.state.engine) as session:
        statement = select(Project).where(Project.owner_hash == owner)
        if cursor is not None:
            anchor = session.get(Project, cursor)
            if anchor is None or anchor.owner_hash != owner:
                raise HTTPException(400, "Invalid cursor")
            statement = statement.where(Project.id > cursor)
        rows = session.scalars(statement.order_by(Project.id).limit(limit + 1)).all()
        return ProjectPage(
            items=[ProjectRead.model_validate(row) for row in rows[:limit]],
            next_cursor=rows[limit - 1].id if len(rows) > limit else None,
        )


@router.get("/sample", response_model=ProjectRead)
def sample_project(request: Request) -> Project:
    with Session(request.app.state.engine) as session:
        project = session.get(Project, SAMPLE_PROJECT_ID)
        if project is None or not project.is_sample:
            raise HTTPException(404, "Sample project not found")
        return project


@router.get("/{project_id}", response_model=ProjectRead)
def read_project(
    project_id: UUID, request: Request, x_project_token: OptionalOwnerToken = None
) -> Project:
    with Session(request.app.state.engine) as session:
        return get_project(session, project_id, x_project_token)


@router.patch("/{project_id}", response_model=ProjectRead)
@observed("projects.update")
def update_project(
    project_id: UUID,
    body: ProjectUpdate,
    request: Request,
    x_project_token: OwnerToken,
) -> Project:
    with Session(request.app.state.engine) as session:
        project = get_project(session, project_id, x_project_token, write=True)
        changes = body.model_dump(exclude_unset=True)
        if any(value is None for value in changes.values()):
            raise HTTPException(422, "Fields cannot be null")
        for key, value in changes.items():
            setattr(project, key, value)
        project.updated_at = func.now()
        session.commit()
        session.refresh(project)
        return project


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: UUID, request: Request, x_project_token: OwnerToken
) -> Response:
    with Session(request.app.state.engine) as session:
        session.delete(get_project(session, project_id, x_project_token, write=True))
        session.commit()
        return Response(status_code=204)


@router.get("/{project_id}/overview", response_model=ProjectOverview)
def project_overview(
    project_id: UUID, request: Request, x_project_token: OptionalOwnerToken = None
) -> ProjectOverview:
    with Session(request.app.state.engine) as session:
        project = get_project(session, project_id, x_project_token)
        discovery = session.get(Discovery, project_id)
        answers = discovery.answers if discovery else {}
        rows = session.execute(
            select(
                Requirement.type, Requirement.status, Requirement.priority, func.count()
            )
            .where(Requirement.project_id == project_id)
            .group_by(Requirement.type, Requirement.status, Requirement.priority)
        ).all()

        fields = {"type": 0, "status": 1, "priority": 2}

        def count(**match: str) -> int:
            return sum(
                row[3]
                for row in rows
                if all(row[fields[key]] == value for key, value in match.items())
            )

        done = completed_steps(answers)
        counts = RequirementCounts(
            total=count(),
            functional=count(type="functional"),
            non_functional=count(type="non_functional"),
            proposed=count(status="proposed"),
            confirmed=count(status="confirmed"),
            deferred=count(status="deferred"),
            p0=count(priority="P0"),
        )
        missing = [f"Discovery: {step.title}" for step in STEPS if step.id not in done]
        if counts.functional == 0:
            missing.append("At least one functional requirement")
        if counts.non_functional == 0:
            missing.append("At least one non-functional requirement")
        return ProjectOverview(
            project=ProjectRead.model_validate(project),
            discovery_steps=[step.id for step in STEPS],
            discovery_completed=done,
            discovery_updated_at=discovery.updated_at if discovery else None,
            requirements=counts,
            open_questions=list(answers.get("open_questions", [])),
            assumptions=list(answers.get("assumptions", [])),
            missing=missing,
        )
