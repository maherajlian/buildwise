import uuid

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Epic(Base):
    __tablename__ = "epics"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class PlanTask(Base):
    __tablename__ = "plan_tasks"
    __table_args__ = (
        UniqueConstraint("project_id", "key", name="uq_plan_task_key"),
        CheckConstraint("priority IN ('P0', 'P1', 'P2')", name="plan_task_priority"),
        CheckConstraint(
            "status IN ('backlog', 'ready', 'in_progress', 'review', 'done')",
            name="plan_task_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    epic_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("epics.id", ondelete="SET NULL"), nullable=True
    )
    key: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    priority: Mapped[str] = mapped_column(String(2), default="P1", server_default="P1")
    status: Mapped[str] = mapped_column(
        String(20), default="backlog", server_default="backlog"
    )
    implementation_notes: Mapped[str] = mapped_column(
        Text, default="", server_default=""
    )
    acceptance_criteria: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    skill: Mapped[str] = mapped_column(String(200), default="", server_default="")
    workflow: Mapped[str] = mapped_column(Text, default="", server_default="")
    depends_on: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    requirement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("requirements.id", ondelete="SET NULL"), nullable=True
    )
