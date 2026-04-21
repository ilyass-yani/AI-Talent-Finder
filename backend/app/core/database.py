"""
SQLAlchemy engine, session factory, and FastAPI DB dependency.
"""

from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


# `pool_pre_ping=True` recycles dead connections (e.g. after DB restart).
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped DB session and closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
