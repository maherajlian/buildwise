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
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Artefact(Base):
    __tablename__ = "artefacts"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('prd', 'technical_design', 'architecture', 'adr', 'data_model', "
            "'api_contract', 'user_stories', 'acceptance_criteria', "
            "'non_functional_requirements', 'security', 'test_strategy', "
            "'deployment', 'observability')",
            name="artefact_kind",
        ),
        Index(
            "uq_artefacts_project_kind",
            "project_id",
            "kind",
            unique=True,
            postgresql_where=text("kind <> 'adr'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(200))
    sections: Mapped[list[dict[str, str]]] = mapped_column(JSONB)
    edited: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    context: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
