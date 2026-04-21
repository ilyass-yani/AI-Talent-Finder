"""
Alembic environment.

Reads the DB URL from `app.core.config.settings.database_url` so a single
source of truth is used in code, tests, Docker, and migrations.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
# Import models so `Base.metadata` is populated before autogenerate runs.
from app.core.database import Base  # noqa: F401
from app.models.models import (  # noqa: F401
    Candidate,
    CandidateSkill,
    CriteriaSkill,
    Education,
    Experience,
    Favorite,
    JobCriteria,
    MatchResult,
    Skill,
    User,
)


config = context.config

# Inject the runtime DB URL into the alembic config so alembic.ini doesn't need
# the credentials hard-coded.
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate SQL without connecting to the DB."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Apply migrations against a live DB connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
