"""Create projects with anonymous ownership."""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_hash", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
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
        sa.CheckConstraint("length(trim(name)) BETWEEN 1 AND 200", name="project_name"),
        sa.CheckConstraint("length(description) <= 10000", name="project_description"),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'archived')", name="project_status"
        ),
    )
    op.create_index("ix_projects_owner_hash", "projects", ["owner_hash"])


def downgrade() -> None:
    op.drop_table("projects")
