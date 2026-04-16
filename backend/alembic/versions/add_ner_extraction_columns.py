"""add_ner_extraction_columns

Revision ID: add_ner_extraction
Revises: 000001_create_all_tables
Create Date: 2026-04-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_ner_extraction'
down_revision = '000001_create_all_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add NER extraction columns to candidates table
    op.add_column('candidates', sa.Column('extracted_name', sa.String(), nullable=True))
    op.add_column('candidates', sa.Column('extracted_emails', sa.Text(), nullable=True))
    op.add_column('candidates', sa.Column('extracted_phones', sa.Text(), nullable=True))
    op.add_column('candidates', sa.Column('extracted_job_titles', sa.Text(), nullable=True))
    op.add_column('candidates', sa.Column('extracted_companies', sa.Text(), nullable=True))
    op.add_column('candidates', sa.Column('extracted_education', sa.Text(), nullable=True))
    op.add_column('candidates', sa.Column('extraction_quality_score', sa.Float(), nullable=True, server_default='0.0'))
    op.add_column('candidates', sa.Column('ner_extraction_data', sa.Text(), nullable=True))
    op.add_column('candidates', sa.Column('is_fully_extracted', sa.Boolean(), nullable=True, server_default='false'))


def downgrade() -> None:
    # Remove NER extraction columns
    op.drop_column('candidates', 'is_fully_extracted')
    op.drop_column('candidates', 'ner_extraction_data')
    op.drop_column('candidates', 'extraction_quality_score')
    op.drop_column('candidates', 'extracted_education')
    op.drop_column('candidates', 'extracted_companies')
    op.drop_column('candidates', 'extracted_job_titles')
    op.drop_column('candidates', 'extracted_phones')
    op.drop_column('candidates', 'extracted_emails')
    op.drop_column('candidates', 'extracted_name')
