"""Add discovery, requirements and the read-only sample project flag."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("is_sample", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.alter_column(
        "projects", "owner_hash", existing_type=sa.String(64), nullable=True
    )
    op.create_check_constraint(
        "project_owner_required", "projects", "is_sample OR owner_hash IS NOT NULL"
    )
    op.create_index("ix_projects_updated_at", "projects", ["updated_at"])
    op.create_table(
        "discoveries",
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("answers", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "current_step", sa.String(40), nullable=False, server_default="problem"
        ),
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
    )
    op.create_table(
        "requirements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("priority", sa.String(2), nullable=False, server_default="P1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="proposed"),
        sa.Column(
            "acceptance_criteria",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
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
            "type IN ('functional', 'non_functional')", name="requirement_type"
        ),
        sa.CheckConstraint(
            "priority IN ('P0', 'P1', 'P2')", name="requirement_priority"
        ),
        sa.CheckConstraint(
            "status IN ('proposed', 'confirmed', 'deferred')",
            name="requirement_status",
        ),
        sa.CheckConstraint(
            "length(trim(title)) BETWEEN 1 AND 200", name="requirement_title"
        ),
        sa.CheckConstraint(
            "length(description) <= 5000", name="requirement_description"
        ),
    )
    op.create_index(
        "ix_requirements_project_id_id", "requirements", ["project_id", "id"]
    )


def downgrade() -> None:
    op.drop_table("requirements")
    op.drop_table("discoveries")
    op.drop_index("ix_projects_updated_at", "projects")
    op.execute("DELETE FROM projects WHERE owner_hash IS NULL")
    op.drop_constraint("project_owner_required", "projects", type_="check")
    op.alter_column(
        "projects", "owner_hash", existing_type=sa.String(64), nullable=False
    )
    op.drop_column("projects", "is_sample")
