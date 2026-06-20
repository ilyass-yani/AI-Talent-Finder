import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.core.database import Base
from app.models.models import (
    User,
    Candidate,
    Skill,
    CandidateSkill,
    Experience,
    Education,
    JobCriteria,
    CriteriaSkill,
    MatchResult,
    Favorite,
)

target_metadata = Base.metadata

# Inject the real DATABASE_URL from environment, overriding the placeholder in alembic.ini.
# Without this, Alembic falls back to the hardcoded localhost URL in alembic.ini,
# fails to connect, and silently switches to offline mode (prints SQL instead of running it).
_db_url = os.environ.get("DATABASE_URL", "").strip()
if _db_url:
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    config.set_main_option("sqlalchemy.url", _db_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL to stdout, does NOT apply it).
    Only used when invoked explicitly with --sql flag or context.is_offline_mode()."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        as_sql=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (applies migrations directly to the database)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
