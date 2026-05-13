from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.core.dependencies import get_current_user, get_db
from app.api import matching as matching_module
from app.models.models import Candidate, JobCriteria, User, UserRole


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
        self.recruiter = User(
            id=1,
            email="recruiter@example.com",
            hashed_password="x",
            full_name="Recruiter",
            role=UserRole.recruiter,
        )
        self.criteria = JobCriteria(
            id=1,
            recruiter_id=1,
            title="Senior Python Developer",
            description="Build APIs with FastAPI and SQL",
        )
        self.candidate = Candidate(
            id=10,
            full_name="Alice Smith",
            email="alice@example.com",
            raw_text="Python FastAPI Docker",
        )

    def query(self, model):
        if model is User:
            return FakeQuery([self.recruiter])
        if model is JobCriteria:
            return FakeQuery([self.criteria])
        if model is Candidate:
            return FakeQuery([self.candidate])
        return FakeQuery([])


class FakeUser(SimpleNamespace):
    pass


class TestMatchingGenerationRoutes:
    def setup_method(self):
        self.fake_session = FakeSession()
        app.dependency_overrides[get_db] = lambda: self.fake_session
        app.dependency_overrides[get_current_user] = lambda: FakeUser(id=1, role=UserRole.recruiter)

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_generate_and_match_route_returns_results(self):
        with patch.object(matching_module, "_generate_profile_payload", return_value={"ideal_skills": [{"name": "Python", "weight": 100}]}), \
             patch.object(matching_module, "calculate_match_score", return_value=(88.0, {"details": "Strong fit"})):
            with TestClient(app) as client:
                response = client.post(
                    "/api/matching/generate-and-match",
                    json={"job_title": "Senior Python Developer", "description": "Looking for Python and FastAPI"},
                )

        assert response.status_code == 200
        payload = response.json()
        assert payload["ideal_profile"]["ideal_skills"]
        assert len(payload["matches"]) == 1
        assert payload["matches"][0]["candidate_id"] == 10
        assert payload["matches"][0]["match_score"] == 88.0

    def test_matching_results_route_handles_numeric_ids(self):
        with patch.object(matching_module, "_score_all_candidates", return_value=[]), \
             patch.object(matching_module, "_persist_match_results", return_value=[]):
            with TestClient(app) as client:
                response = client.post("/api/matching/1/results")

        assert response.status_code == 200
        assert response.json() == []
