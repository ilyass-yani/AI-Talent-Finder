"""
Shared pytest fixtures.

Tests use an in-memory SQLite database created from `Base.metadata` (Alembic
migrations are PostgreSQL-specific). The `JSONB` column on `MatchResult` is
silently mapped to SQLite's `JSON` type by SQLAlchemy when needed — no
adjustment required.
"""

from __future__ import annotations

import os
from typing import Iterator

import pytest


# Force a deterministic config BEFORE app modules import settings.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-characters-long")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("LLM_API_KEY", "")  # disable LLM calls in tests


from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
# Import models so all tables are registered with Base.metadata.
from app.models import models  # noqa: F401,E402


@pytest.fixture(scope="session")
def engine():
    """One engine for the whole test session — StaticPool keeps the in-memory DB alive."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db_session(engine) -> Iterator:
    """A fresh session per test, wrapped in a rollback so tests don't leak rows."""
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        # Truncate every table so the next test starts clean. Using DELETE keeps
        # the schema intact (DROP would force recreation on every test).
        with engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(table.delete())


@pytest.fixture()
def client(db_session) -> Iterator[TestClient]:
    """TestClient with `get_db` overridden to use the test session."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass  # session lifecycle is managed by db_session fixture

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def recruiter_token(client) -> str:
    """Register a recruiter and return their access token."""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "recruiter@example.com",
            "password": "TestPass123!",
            "full_name": "Test Recruiter",
            "role": "recruiter",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


@pytest.fixture()
def candidate_user_token(client) -> str:
    """Register a candidate-role user and return their access token."""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "candidate@example.com",
            "password": "TestPass123!",
            "full_name": "Test Candidate",
            "role": "candidate",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


@pytest.fixture()
def auth_headers(recruiter_token):
    return {"Authorization": f"Bearer {recruiter_token}"}
