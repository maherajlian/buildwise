import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint("length(trim(name)) BETWEEN 1 AND 200", name="project_name"),
        CheckConstraint("length(description) <= 10000", name="project_description"),
        CheckConstraint(
            "status IN ('draft', 'active', 'archived')", name="project_status"
        ),
        CheckConstraint(
            "is_sample OR owner_hash IS NOT NULL", name="project_owner_required"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    is_sample: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    status: Mapped[str] = mapped_column(
        String(20), default="draft", server_default="draft"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        index=True,
    )


class Discovery(Base):
    __tablename__ = "discoveries"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    answers: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )
    current_step: Mapped[str] = mapped_column(
        String(40), default="problem", server_default="problem"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Requirement(Base):
    __tablename__ = "requirements"
    __table_args__ = (
        CheckConstraint(
            "type IN ('functional', 'non_functional')", name="requirement_type"
        ),
        CheckConstraint("priority IN ('P0', 'P1', 'P2')", name="requirement_priority"),
        CheckConstraint(
            "status IN ('proposed', 'confirmed', 'deferred')",
            name="requirement_status",
        ),
        CheckConstraint(
            "length(trim(title)) BETWEEN 1 AND 200", name="requirement_title"
        ),
        CheckConstraint("length(description) <= 5000", name="requirement_description"),
        Index("ix_requirements_project_id_id", "project_id", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE")
    )
    type: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    priority: Mapped[str] = mapped_column(String(2), default="P1", server_default="P1")
    status: Mapped[str] = mapped_column(
        String(20), default="proposed", server_default="proposed"
    )
    acceptance_criteria: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
