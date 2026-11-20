"""Persist manually tracked validation and operations plans."""

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def common() -> list[sa.Column]:  # type: ignore[type-arg]
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requirement_id",
            sa.Uuid(),
            sa.ForeignKey("requirements.id", ondelete="SET NULL"),
        ),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("generation_key", sa.String(64)),
        sa.Column("edited", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "test_cases",
        *common(),
        sa.UniqueConstraint(
            "project_id", "generation_key", name="uq_test_case_generation"
        ),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("result_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("executed_at", sa.DateTime(timezone=True)),
        sa.Column("executed_by", sa.String(200)),
        sa.CheckConstraint("source IN ('generated', 'user')", name="test_case_source"),
        sa.CheckConstraint(
            "category IN ('unit', 'integration', 'api_contract', 'e2e', "
            "'accessibility', 'security', 'performance', 'manual_acceptance', "
            "'model_evaluation', 'prompt_regression', 'tool_use_evaluation')",
            name="test_case_category",
        ),
        sa.CheckConstraint(
            "status IN ('proposed', 'planned', 'passed', 'failed', 'blocked')",
            name="test_case_status",
        ),
        sa.CheckConstraint(
            "status NOT IN ('passed', 'failed') OR "
            "(length(trim(result_notes)) > 0 AND executed_at IS NOT NULL)",
            name="test_case_execution",
        ),
    )
    op.create_table(
        "risks",
        *common(),
        sa.UniqueConstraint("project_id", "generation_key", name="uq_risk_generation"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("likelihood", sa.Integer(), nullable=False),
        sa.Column("impact", sa.Integer(), nullable=False),
        sa.Column("mitigation", sa.Text(), nullable=False, server_default=""),
        sa.Column("owner", sa.String(200), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False),
        sa.CheckConstraint("source IN ('generated', 'user')", name="risk_source"),
        sa.CheckConstraint(
            "category IN ('technical', 'security', 'operational', 'delivery', "
            "'compliance', 'cost')",
            name="risk_category",
        ),
        sa.CheckConstraint("likelihood BETWEEN 1 AND 5", name="risk_likelihood"),
        sa.CheckConstraint("impact BETWEEN 1 AND 5", name="risk_impact"),
        sa.CheckConstraint(
            "status IN ('open', 'mitigating', 'accepted', 'closed')", name="risk_status"
        ),
    )
    op.create_table(
        "slos",
        *common(),
        sa.UniqueConstraint("project_id", "generation_key", name="uq_slo_generation"),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("sli", sa.Text(), nullable=False),
        sa.Column("target", sa.String(500), nullable=False),
        sa.Column("window", sa.String(200), nullable=False),
        sa.Column("alert", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.CheckConstraint("source IN ('generated', 'user')", name="slo_source"),
        sa.CheckConstraint(
            "status IN ('suggested', 'adopted', 'rejected')", name="slo_status"
        ),
    )
    for table in ("test_cases", "risks", "slos"):
        op.create_index(f"ix_{table}_project_id", table, ["project_id"])


def downgrade() -> None:
    for table in ("slos", "risks", "test_cases"):
        op.drop_table(table)
