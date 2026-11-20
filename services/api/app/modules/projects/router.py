import hashlib
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.projects.models import Project

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=10000)
    status: Literal["draft", "active", "archived"] = "draft"

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Name must not be blank")
        return value.strip()


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str
    status: Literal["draft", "active", "archived"]
    created_at: datetime
    updated_at: datetime


class ProjectPage(BaseModel):
    items: list[ProjectRead]
    next_cursor: UUID | None


OwnerToken = Annotated[
    str,
    Header(
        alias="X-Project-Token",
        min_length=43,
        max_length=128,
        pattern=r"^[A-Za-z0-9_-]+$",
    ),
]


@router.post("", response_model=ProjectRead, status_code=201)
def create_project(
    body: ProjectCreate, request: Request, x_project_token: OwnerToken
) -> Project:
    with Session(request.app.state.engine) as session:
        project = Project(
            **body.model_dump(),
            owner_hash=hashlib.sha256(x_project_token.encode()).hexdigest(),
        )
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
    owner = hashlib.sha256(x_project_token.encode()).hexdigest()
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
