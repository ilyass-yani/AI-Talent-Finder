"""add password reset columns to users

Revision ID: add_password_reset
Revises: add_ner_extraction
Create Date: 2026-06-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'add_password_reset'
down_revision: Union[str, None] = 'add_ner_extraction'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('reset_password_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('reset_password_token_expires', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_users_reset_password_token'), 'users', ['reset_password_token'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_reset_password_token'), table_name='users')
    op.drop_column('users', 'reset_password_token_expires')
    op.drop_column('users', 'reset_password_token')
