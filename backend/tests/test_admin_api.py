#!/usr/bin/env python3
"""
Unit tests for the admin API endpoints.
Follows the same pattern as test_api_unit.py.

NOTE: The app registers routers in on_startup(), so we must use TestClient
as a context manager to trigger startup before making requests.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

try:
    from app.main import app
except Exception:
    with patch.dict("sys.modules", {
        "ai_module": MagicMock(),
        "ai_module.nlp": MagicMock(),
        "ai_module.nlp.cv_cleaner": MagicMock(),
        "ai_module.nlp.skill_extractor": MagicMock(),
        "ai_module.nlp.profile_generator": MagicMock(),
    }):
        from app.main import app

from app.models.models import User, UserRole
from app.core.security import get_password_hash


# ---------------------------------------------------------------------------
# Client fixture  — triggers on_startup (which registers all routers)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register(client, email: str, role: str = "recruiter") -> dict:
    res = client.post(
        "/api/auth/register",
        json={"email": email, "password": "Password123!", "full_name": "Test User", "role": role},
    )
    return res.json()


def _login_token(client, email: str) -> str:
    res = client.post(
        "/api/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    assert res.status_code == 200, f"Login failed: {res.json()}"
    return res.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def admin_token(client):
    """Create an admin user directly in the DB and obtain a JWT."""
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == "admin_test@example.io").first()
        if not existing:
            admin = User(
                email="admin_test@example.io",
                hashed_password=get_password_hash("Admin1234!"),
                full_name="Admin Test",
                role=UserRole.admin,
                is_active=True,
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()

    res = client.post(
        "/api/auth/login",
        json={"email": "admin_test@example.io", "password": "Admin1234!"},
    )
    assert res.status_code == 200, f"Admin login failed: {res.json()}"
    return res.json()["access_token"]


# ---------------------------------------------------------------------------
# Tests: authorization guard
# ---------------------------------------------------------------------------

class TestAdminAuthGuard:
    """Non-admin users must get 403 on all /api/admin/* routes."""

    def test_recruiter_cannot_access_admin_users(self, client):
        _register(client, "recruiter_guard@example.io", role="recruiter")
        token = _login_token(client, "recruiter_guard@example.io")
        res = client.get("/api/admin/users/", headers=_auth(token))
        assert res.status_code == 403

    def test_candidate_cannot_access_admin_users(self, client):
        _register(client, "candidate_guard@example.io", role="candidate")
        token = _login_token(client, "candidate_guard@example.io")
        res = client.get("/api/admin/users/", headers=_auth(token))
        assert res.status_code == 403

    def test_unauthenticated_cannot_access_admin(self, client):
        res = client.get("/api/admin/users/")
        assert res.status_code == 401

    def test_recruiter_cannot_access_admin_stats(self, client):
        _register(client, "rec_stats@example.io", role="recruiter")
        token = _login_token(client, "rec_stats@example.io")
        res = client.get("/api/admin/stats/", headers=_auth(token))
        assert res.status_code == 403


# ---------------------------------------------------------------------------
# Tests: admin user endpoints
# ---------------------------------------------------------------------------

class TestAdminUsers:

    def test_list_users_returns_paginated(self, client, admin_token):
        res = client.get("/api/admin/users/", headers=_auth(admin_token))
        assert res.status_code == 200
        data = res.json()
        assert "total" in data
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_list_users_filter_by_role(self, client, admin_token):
        _register(client, "filter_candidate@example.io", role="candidate")
        res = client.get("/api/admin/users/?role=candidate", headers=_auth(admin_token))
        assert res.status_code == 200
        for item in res.json()["items"]:
            assert item["role"] == "candidate"

    def test_set_user_status_deactivate(self, client, admin_token):
        _register(client, "to_deactivate@example.io", role="recruiter")
        users = client.get(
            "/api/admin/users/?role=recruiter", headers=_auth(admin_token)
        ).json()["items"]
        target = next((u for u in users if u["email"] == "to_deactivate@example.io"), None)
        assert target is not None

        res = client.patch(
            f"/api/admin/users/{target['id']}/status/",
            json={"is_active": False},
            headers=_auth(admin_token),
        )
        assert res.status_code == 200
        assert res.json()["is_active"] is False

    def test_set_user_status_not_found(self, client, admin_token):
        res = client.patch(
            "/api/admin/users/999999/status/",
            json={"is_active": True},
            headers=_auth(admin_token),
        )
        assert res.status_code == 404

    def test_delete_user(self, client, admin_token):
        _register(client, "to_delete@example.io", role="candidate")
        users = client.get(
            "/api/admin/users/?role=candidate", headers=_auth(admin_token)
        ).json()["items"]
        target = next((u for u in users if u["email"] == "to_delete@example.io"), None)
        assert target is not None

        res = client.delete(f"/api/admin/users/{target['id']}/", headers=_auth(admin_token))
        assert res.status_code == 204

    def test_delete_user_not_found(self, client, admin_token):
        res = client.delete("/api/admin/users/999999/", headers=_auth(admin_token))
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# Tests: admin job endpoints
# ---------------------------------------------------------------------------

class TestAdminJobs:

    def _create_job(self, client, recruiter_token: str) -> dict:
        res = client.post(
            "/api/jobs/",
            json={"title": "Admin Test Job", "description": "Test", "criteria_skills": []},
            headers=_auth(recruiter_token),
        )
        assert res.status_code in (200, 201), f"Job creation failed: {res.json()}"
        return res.json()

    def test_list_jobs_returns_paginated(self, client, admin_token):
        res = client.get("/api/admin/jobs/", headers=_auth(admin_token))
        assert res.status_code == 200
        data = res.json()
        assert "total" in data
        assert "items" in data

    def test_moderate_job_approve(self, client, admin_token):
        _register(client, "rec_for_jobs@example.io", role="recruiter")
        rec_token = _login_token(client, "rec_for_jobs@example.io")
        job = self._create_job(client, rec_token)

        res = client.patch(
            f"/api/admin/jobs/{job['id']}/moderate/",
            json={"moderation_status": "approved"},
            headers=_auth(admin_token),
        )
        assert res.status_code == 200
        assert res.json()["moderation_status"] == "approved"

    def test_moderate_job_reject(self, client, admin_token):
        _register(client, "rec_for_reject@example.io", role="recruiter")
        rec_token = _login_token(client, "rec_for_reject@example.io")
        job = self._create_job(client, rec_token)

        res = client.patch(
            f"/api/admin/jobs/{job['id']}/moderate/",
            json={"moderation_status": "rejected"},
            headers=_auth(admin_token),
        )
        assert res.status_code == 200
        assert res.json()["moderation_status"] == "rejected"

    def test_moderate_job_not_found(self, client, admin_token):
        res = client.patch(
            "/api/admin/jobs/999999/moderate/",
            json={"moderation_status": "approved"},
            headers=_auth(admin_token),
        )
        assert res.status_code == 404

    def test_delete_job(self, client, admin_token):
        _register(client, "rec_for_delete@example.io", role="recruiter")
        rec_token = _login_token(client, "rec_for_delete@example.io")
        job = self._create_job(client, rec_token)

        res = client.delete(f"/api/admin/jobs/{job['id']}/", headers=_auth(admin_token))
        assert res.status_code == 204

    def test_delete_job_not_found(self, client, admin_token):
        res = client.delete("/api/admin/jobs/999999/", headers=_auth(admin_token))
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# Tests: admin stats endpoint
# ---------------------------------------------------------------------------

class TestAdminStats:

    def test_stats_returns_expected_fields(self, client, admin_token):
        res = client.get("/api/admin/stats/", headers=_auth(admin_token))
        assert res.status_code == 200
        data = res.json()
        for field in ["total_candidates", "total_recruiters", "total_active_jobs", "total_matchings"]:
            assert field in data

    def test_stats_values_are_non_negative(self, client, admin_token):
        res = client.get("/api/admin/stats/", headers=_auth(admin_token))
        assert res.status_code == 200
        data = res.json()
        for field in ["total_candidates", "total_recruiters", "total_active_jobs", "total_matchings"]:
            assert data[field] >= 0
