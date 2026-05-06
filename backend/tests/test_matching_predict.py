import json
import os
import asyncio
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime
from unittest.mock import patch

import numpy as np


TEST_DB_PATH = Path(__file__).resolve().parent / "test_matching_predict.sqlite3"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DB_PATH}")

from app.main import app
from app.core.dependencies import get_current_user, get_db
from app.api import matching as matching_module
from app.models.models import JobCriteria, CriteriaSkill, Candidate


class FakeQuery:
    def __init__(self, rows):
        self.rows = list(rows)

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return list(self.rows)

    def first(self):
        return self.rows[0] if self.rows else None


class FakeSession:
    def __init__(self):
        self.criteria = SimpleNamespace(
            id=1,
            recruiter_id=1,
            title="Senior Python Developer",
            description="Build APIs with FastAPI and SQL",
            created_at=datetime.utcnow(),
        )
        self.criteria_skills = [
            SimpleNamespace(id=1, criteria_id=1, weight=90, skill=SimpleNamespace(name="Python")),
            SimpleNamespace(id=2, criteria_id=1, weight=80, skill=SimpleNamespace(name="SQL")),
        ]

        self.candidate = SimpleNamespace(
            id=10,
            full_name="Jean Dupont",
            email="jean@example.com",
            created_at=datetime.utcnow(),
            extracted_job_titles=json.dumps(["Backend Developer"]),
            extracted_companies=json.dumps(["ACME"]),
            candidate_skills=[
                SimpleNamespace(skill=SimpleNamespace(name="Python")),
                SimpleNamespace(skill=SimpleNamespace(name="SQL")),
            ],
        )

    def query(self, model):
        if model is JobCriteria:
            return FakeQuery([self.criteria])
        if model is CriteriaSkill:
            return FakeQuery(self.criteria_skills)
        if model is Candidate:
            return FakeQuery([self.candidate])
        return FakeQuery([])


class FakeModel:
    def predict_proba(self, X):
        return np.array([[0.12, 0.88]])


class FakeMeta:
    def __init__(self):
        self.tf = SimpleNamespace(transform=lambda texts: texts)
        self.svd = SimpleNamespace(transform=lambda x: x)


def test_predict_for_criteria_returns_ranked_candidates():
    fake_session = FakeSession()

    with patch("app.api.matching._load_baseline_model", return_value={"model": FakeModel(), "meta": {"tf": FakeMeta().tf, "svd": FakeMeta().svd}}):
        with patch("app.api.matching._build_pair_features_single", return_value=np.array([[1.0]])):
            data = asyncio.run(matching_module.predict_for_criteria(1, top_k=5, db=fake_session))

    assert data["criteria_id"] == 1
    assert data["model"] == "baseline"
    assert data["top_k"] == 5
    assert len(data["results"]) == 1
    assert data["results"][0]["candidate_id"] == 10
    assert data["results"][0]["predicted_score"] == 88.0
