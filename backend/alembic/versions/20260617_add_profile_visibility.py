"""Add owner_role, is_visible, updated_at to candidates

Revision ID: 20260617_add_profile_visibility
Revises: 20260615_add_admin_fields
Create Date: 2026-06-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260617_add_profile_visibility"
down_revision: Union[str, None] = "20260615_add_admin_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "candidates",
        sa.Column("owner_role", sa.String(), nullable=True),
    )
    op.add_column(
        "candidates",
        sa.Column(
            "is_visible",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "candidates",
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    # Backfill existing rows: assume they were deposited by a candidate
    op.execute("UPDATE candidates SET owner_role = 'candidate' WHERE owner_role IS NULL")


def downgrade() -> None:
    op.drop_column("candidates", "updated_at")
    op.drop_column("candidates", "is_visible")
    op.drop_column("candidates", "owner_role")
