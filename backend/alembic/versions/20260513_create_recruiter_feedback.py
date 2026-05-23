"""Create recruiter feedback table

Revision ID: 20260513_create_recruiter_feedback
Revises: 000001_create_all_tables
Create Date: 2026-05-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260513_create_recruiter_feedback"
down_revision: Union[str, None] = "add_ner_extraction"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recruiter_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("criteria_id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("recruiter_id", sa.Integer(), nullable=False),
        sa.Column("model_predicted_score", sa.Float(), nullable=False),
        sa.Column("model_predicted_decision", sa.String(), nullable=False),
        sa.Column("recruiter_decision", sa.String(), nullable=False),
        sa.Column("recruiter_score_override", sa.Float(), nullable=True),
        sa.Column("feedback_reason", sa.Text(), nullable=True),
        sa.Column("is_override", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("hire_outcome", sa.String(), nullable=True),
        sa.Column("hire_date", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["criteria_id"], ["job_criteria.id"]),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"]),
        sa.ForeignKeyConstraint(["recruiter_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recruiter_feedback_id"), "recruiter_feedback", ["id"], unique=False)
    op.create_index(op.f("ix_recruiter_feedback_criteria_id"), "recruiter_feedback", ["criteria_id"], unique=False)
    op.create_index(op.f("ix_recruiter_feedback_candidate_id"), "recruiter_feedback", ["candidate_id"], unique=False)
    op.create_index(op.f("ix_recruiter_feedback_recruiter_id"), "recruiter_feedback", ["recruiter_id"], unique=False)
    op.create_index(op.f("ix_recruiter_feedback_is_override"), "recruiter_feedback", ["is_override"], unique=False)
    op.create_index(op.f("ix_recruiter_feedback_created_at"), "recruiter_feedback", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_recruiter_feedback_created_at"), table_name="recruiter_feedback")
    op.drop_index(op.f("ix_recruiter_feedback_is_override"), table_name="recruiter_feedback")
    op.drop_index(op.f("ix_recruiter_feedback_recruiter_id"), table_name="recruiter_feedback")
    op.drop_index(op.f("ix_recruiter_feedback_candidate_id"), table_name="recruiter_feedback")
    op.drop_index(op.f("ix_recruiter_feedback_criteria_id"), table_name="recruiter_feedback")
    op.drop_index(op.f("ix_recruiter_feedback_id"), table_name="recruiter_feedback")
    op.drop_table("recruiter_feedback")