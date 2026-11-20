"""Persist editable specifications and implementation plans."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "artefacts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("sections", postgresql.JSONB(), nullable=False),
        sa.Column("edited", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("context", postgresql.JSONB(), nullable=False),
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
        sa.CheckConstraint(
            "kind IN ('prd', 'technical_design', 'architecture', 'adr', 'data_model', "
            "'api_contract', 'user_stories', 'acceptance_criteria', "
            "'non_functional_requirements', 'security', 'test_strategy', "
            "'deployment', 'observability')",
            name="artefact_kind",
        ),
    )
    op.create_index("ix_artefacts_project_id", "artefacts", ["project_id"])
    op.create_index(
        "uq_artefacts_project_kind",
        "artefacts",
        ["project_id", "kind"],
        unique=True,
        postgresql_where=sa.text("kind <> 'adr'"),
    )
    op.create_table(
        "epics",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_epics_project_id", "epics", ["project_id"])
    op.create_table(
        "plan_tasks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("epic_id", sa.Uuid(), sa.ForeignKey("epics.id", ondelete="SET NULL")),
        sa.Column("key", sa.String(20), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("priority", sa.String(2), nullable=False, server_default="P1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="backlog"),
        sa.Column("implementation_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "acceptance_criteria",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("skill", sa.String(200), nullable=False, server_default=""),
        sa.Column("workflow", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "depends_on", postgresql.JSONB(), nullable=False, server_default="[]"
        ),
        sa.Column(
            "requirement_id",
            sa.Uuid(),
            sa.ForeignKey("requirements.id", ondelete="SET NULL"),
        ),
        sa.UniqueConstraint("project_id", "key", name="uq_plan_task_key"),
        sa.CheckConstraint("priority IN ('P0', 'P1', 'P2')", name="plan_task_priority"),
        sa.CheckConstraint(
            "status IN ('backlog', 'ready', 'in_progress', 'review', 'done')",
            name="plan_task_status",
        ),
    )
    op.create_index("ix_plan_tasks_project_id", "plan_tasks", ["project_id"])


def downgrade() -> None:
    op.drop_table("plan_tasks")
    op.drop_table("epics")
    op.drop_table("artefacts")
