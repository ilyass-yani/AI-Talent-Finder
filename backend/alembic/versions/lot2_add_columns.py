"""Lot 2: add missing columns to align schema with the development guide.

Revision ID: lot2_add_columns
Revises: add_ner_extraction
Create Date: 2026-04-21
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "lot2_add_columns"
down_revision: Union[str, None] = "add_ner_extraction"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users.is_active
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    # candidates.parsed_at
    op.add_column("candidates", sa.Column("parsed_at", sa.DateTime(), nullable=True))

    # skills.normalized_name (+ index)
    op.add_column("skills", sa.Column("normalized_name", sa.String(), nullable=True))
    op.create_index("ix_skills_normalized_name", "skills", ["normalized_name"], unique=False)

    # candidate_skills.confidence_score (+ uq + index already implied by FK)
    op.add_column("candidate_skills", sa.Column("confidence_score", sa.Float(), nullable=True))
    op.create_unique_constraint(
        "uq_candidate_skill", "candidate_skills", ["candidate_id", "skill_id"]
    )

    # experiences: start_date, end_date
    op.add_column("experiences", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("experiences", sa.Column("end_date", sa.Date(), nullable=True))

    # educations.level
    op.add_column("educations", sa.Column("level", sa.String(), nullable=True))

    # job_criteria.updated_at — backfill to created_at then enforce NOT NULL.
    op.add_column(
        "job_criteria",
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.execute("UPDATE job_criteria SET updated_at = created_at WHERE updated_at IS NULL")
    op.alter_column("job_criteria", "updated_at", nullable=False, server_default=sa.func.now())

    # criteria_skills: enforce uniqueness (criteria_id, skill_id).
    op.create_unique_constraint(
        "uq_criteria_skill", "criteria_skills", ["criteria_id", "skill_id"]
    )

    # match_results.score_breakdown + uniqueness.
    op.add_column("match_results", sa.Column("score_breakdown", JSONB(), nullable=True))
    op.create_unique_constraint(
        "uq_match_result", "match_results", ["criteria_id", "candidate_id"]
    )

    # favorites: prevent duplicate (recruiter, candidate).
    op.create_unique_constraint(
        "uq_favorite", "favorites", ["recruiter_id", "candidate_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_favorite", "favorites", type_="unique")

    op.drop_constraint("uq_match_result", "match_results", type_="unique")
    op.drop_column("match_results", "score_breakdown")

    op.drop_constraint("uq_criteria_skill", "criteria_skills", type_="unique")

    op.drop_column("job_criteria", "updated_at")

    op.drop_column("educations", "level")

    op.drop_column("experiences", "end_date")
    op.drop_column("experiences", "start_date")

    op.drop_constraint("uq_candidate_skill", "candidate_skills", type_="unique")
    op.drop_column("candidate_skills", "confidence_score")

    op.drop_index("ix_skills_normalized_name", table_name="skills")
    op.drop_column("skills", "normalized_name")

    op.drop_column("candidates", "parsed_at")

    op.drop_column("users", "is_active")
