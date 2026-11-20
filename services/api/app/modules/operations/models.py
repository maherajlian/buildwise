import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OperationFields:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    requirement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("requirements.id", ondelete="SET NULL")
    )
    source: Mapped[str] = mapped_column(String(20), default="user")
    generation_key: Mapped[str | None] = mapped_column(String(64))
    edited: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    rationale: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TestCase(OperationFields, Base):
    __tablename__ = "test_cases"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "generation_key", name="uq_test_case_generation"
        ),
        CheckConstraint("source IN ('generated', 'user')", name="test_case_source"),
        CheckConstraint(
            "category IN ('unit', 'integration', 'api_contract', 'e2e', "
            "'accessibility', 'security', 'performance', 'manual_acceptance', "
            "'model_evaluation', 'prompt_regression', 'tool_use_evaluation')",
            name="test_case_category",
        ),
        CheckConstraint(
            "status IN ('proposed', 'planned', 'passed', 'failed', 'blocked')",
            name="test_case_status",
        ),
        CheckConstraint(
            "status NOT IN ('passed', 'failed') OR "
            "(length(trim(result_notes)) > 0 AND executed_at IS NOT NULL)",
            name="test_case_execution",
        ),
    )
    category: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    status: Mapped[str] = mapped_column(String(20), default="proposed")
    result_notes: Mapped[str] = mapped_column(Text, default="", server_default="")
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_by: Mapped[str | None] = mapped_column(String(200))

    @property
    def executed(self) -> bool:
        return (
            self.status in ("passed", "failed")
            and bool(self.result_notes.strip())
            and self.executed_at is not None
        )


class Risk(OperationFields, Base):
    __tablename__ = "risks"
    __table_args__ = (
        UniqueConstraint("project_id", "generation_key", name="uq_risk_generation"),
        CheckConstraint("source IN ('generated', 'user')", name="risk_source"),
        CheckConstraint(
            "category IN ('technical', 'security', 'operational', 'delivery', "
            "'compliance', 'cost')",
            name="risk_category",
        ),
        CheckConstraint("likelihood BETWEEN 1 AND 5", name="risk_likelihood"),
        CheckConstraint("impact BETWEEN 1 AND 5", name="risk_impact"),
        CheckConstraint(
            "status IN ('open', 'mitigating', 'accepted', 'closed')", name="risk_status"
        ),
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    category: Mapped[str] = mapped_column(String(20))
    likelihood: Mapped[int]
    impact: Mapped[int]
    mitigation: Mapped[str] = mapped_column(Text, default="", server_default="")
    owner: Mapped[str] = mapped_column(String(200), default="", server_default="")
    status: Mapped[str] = mapped_column(String(20), default="open")

    @property
    def score(self) -> int:
        return self.likelihood * self.impact


class SLO(OperationFields, Base):
    __tablename__ = "slos"
    __table_args__ = (
        UniqueConstraint("project_id", "generation_key", name="uq_slo_generation"),
        CheckConstraint("source IN ('generated', 'user')", name="slo_source"),
        CheckConstraint(
            "status IN ('suggested', 'adopted', 'rejected')", name="slo_status"
        ),
    )
    name: Mapped[str] = mapped_column(String(200))
    sli: Mapped[str] = mapped_column(Text)
    target: Mapped[str] = mapped_column(String(500))
    window: Mapped[str] = mapped_column(String(200))
    alert: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="suggested")
