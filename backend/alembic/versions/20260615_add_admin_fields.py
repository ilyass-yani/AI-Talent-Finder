"""Add is_active to users and moderation_status to job_criteria

Revision ID: 20260615_add_admin_fields
Revises: 20260513_create_recruiter_feedback
Create Date: 2026-06-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260615_add_admin_fields"
down_revision: Union[str, None] = "20260513_create_recruiter_feedback"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "job_criteria",
        sa.Column(
            "moderation_status",
            sa.Enum("pending", "approved", "rejected", name="moderationstatus"),
            nullable=False,
            server_default="pending",
        ),
    )


def downgrade() -> None:
    op.drop_column("job_criteria", "moderation_status")
    op.drop_column("users", "is_active")
    op.execute("DROP TYPE IF EXISTS moderationstatus")
