"""Pytest configuration and shared fixtures."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make backend/ importable so `import ai_pipeline` works
# (conftest is at backend/ai_pipeline_tests/conftest.py, so go up 1 level)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def sample_cv() -> str:
    return (
        "Nom : Test Candidate\n"
        "Email : test@example.com\n"
        "Formation : Master en Informatique (2022)\n"
        "Expérience (3 ans):\n"
        "- Développeur Python, FastAPI, PostgreSQL\n"
        "Compétences : Python, FastAPI, PostgreSQL, Docker, Git\n"
        "Langues : Français Natif, Anglais C1"
    )


@pytest.fixture
def sample_job() -> str:
    return (
        "Poste : Backend Python Engineer\n"
        "Compétences requises : Python, FastAPI, PostgreSQL, Docker\n"
        "Expérience : 2+ ans\n"
        "Formation : Master en informatique"
    )
