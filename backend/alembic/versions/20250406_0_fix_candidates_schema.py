"""Fix candidates table schema - add missing columns

Revision ID: 20250406_001
Revises: 4402afc8b225
Create Date: 2025-04-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250406_001'
down_revision: Union[str, None] = '4402afc8b225'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add missing columns to candidates table
    # Check if columns exist before adding
    with op.batch_operations.batch_alter_table('candidates', schema=None) as batch_op:
        # Add full_name if not exists
        try:
            batch_op.add_column(sa.Column('full_name', sa.String(), nullable=True))
        except:
            pass  # Column already exists
        
        # Add email if not exists
        try:
            batch_op.add_column(sa.Column('email', sa.String(), nullable=True))
        except:
            pass  # Column already exists
        
        # Add phone if not exists
        try:
            batch_op.add_column(sa.Column('phone', sa.String(), nullable=True))
        except:
            pass  # Column already exists
        
        # Add linkedin_url if not exists
        try:
            batch_op.add_column(sa.Column('linkedin_url', sa.String(), nullable=True))
        except:
            pass  # Column already exists
        
        # Add github_url if not exists
        try:
            batch_op.add_column(sa.Column('github_url', sa.String(), nullable=True))
        except:
            pass  # Column already exists
        
        # Add cv_path if not exists
        try:
            batch_op.add_column(sa.Column('cv_path', sa.String(), nullable=True))
        except:
            pass  # Column already exists
        
        # Create unique index on email if not exists
        try:
            batch_op.create_index(op.f('ix_candidates_email'), ['email'], unique=True)
        except:
            pass  # Index already exists


def downgrade() -> None:
    # Remove the added columns
    with op.batch_operations.batch_alter_table('candidates', schema=None) as batch_op:
        try:
            batch_op.drop_column('cv_path')
        except:
            pass
        try:
            batch_op.drop_column('github_url')
        except:
            pass
        try:
            batch_op.drop_column('linkedin_url')
        except:
            pass
        try:
            batch_op.drop_column('phone')
        except:
            pass
        try:
            batch_op.drop_column('email')
        except:
            pass
        try:
            batch_op.drop_column('full_name')
        except:
            pass
        try:
            batch_op.drop_index(op.f('ix_candidates_email'))
        except:
            pass
