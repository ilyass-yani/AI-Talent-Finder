"""Add recruiter_id to candidates to track who uploaded each CV

Revision ID: 20260620_add_recruiter_id
Revises: 20260617_add_profile_visibility
Create Date: 2026-06-20 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260620_add_recruiter_id"
down_revision: Union[str, None] = "20260617_add_profile_visibility"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "candidates",
        sa.Column(
            "recruiter_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_candidates_recruiter_id", "candidates", ["recruiter_id"])
    # Backfill: existing recruiter-deposited profiles have owner_role='recruiter'
    # and their user_id was incorrectly set to the recruiter's id.
    # Move that value to recruiter_id and clear user_id so the unique constraint
    # no longer blocks future uploads by the same recruiter.
    op.execute("""
        UPDATE candidates
        SET recruiter_id = user_id, user_id = NULL
        WHERE owner_role = 'recruiter' AND user_id IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_index("ix_candidates_recruiter_id", table_name="candidates")
    op.drop_column("candidates", "recruiter_id")
