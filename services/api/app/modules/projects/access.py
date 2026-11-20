import hashlib
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import Header, HTTPException
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.modules.projects.models import Project

RETENTION = timedelta(days=30)
SAMPLE_PROJECT_ID = UUID("00000000-0000-4000-8000-000000000001")

TOKEN_HEADER = Header(
    alias="X-Project-Token",
    min_length=43,
    max_length=128,
    pattern=r"^[A-Za-z0-9_-]+$",
)
OwnerToken = Annotated[str, TOKEN_HEADER]
OptionalOwnerToken = Annotated[str | None, TOKEN_HEADER]


def owner_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def get_project(
    session: Session, project_id: UUID, token: str | None, *, write: bool = False
) -> Project:
    project = session.get(Project, project_id)
    owned = (
        project is not None
        and token is not None
        and project.owner_hash == owner_hash(token)
    )
    if project is None or not (owned or project.is_sample):
        raise HTTPException(404, "Project not found")
    if write and project.is_sample:
        raise HTTPException(
            403, "The sample project is read-only. Create your own project to edit."
        )
    return project


def func_now() -> datetime:
    return datetime.now(UTC)


def purge_expired(session: Session) -> int:
    result = session.execute(
        delete(Project).where(
            Project.is_sample.is_(False),
            Project.updated_at < func_now() - RETENTION,
        )
    )
    return int(getattr(result, "rowcount", 0) or 0)
