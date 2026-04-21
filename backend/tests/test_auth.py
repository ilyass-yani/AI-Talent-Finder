"""End-to-end tests for /api/auth (register, login, refresh, /me)."""

from __future__ import annotations


def test_register_returns_token_pair_and_user(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "new@example.com",
            "password": "Password123!",
            "full_name": "New User",
            "role": "recruiter",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["email"] == "new@example.com"
    assert body["user"]["role"] == "recruiter"


def test_register_rejects_duplicate_email(client):
    payload = {
        "email": "dup@example.com",
        "password": "Password123!",
        "full_name": "Dup",
        "role": "recruiter",
    }
    assert client.post("/api/auth/register", json=payload).status_code == 201
    second = client.post("/api/auth/register", json=payload)
    assert second.status_code == 409


def test_register_rejects_invalid_email(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "not-an-email",
            "password": "Password123!",
            "full_name": "Test",
            "role": "recruiter",
        },
    )
    assert response.status_code == 422


def test_register_rejects_short_password(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "short@example.com",
            "password": "12345",
            "full_name": "Test",
            "role": "recruiter",
        },
    )
    assert response.status_code == 422


def test_login_with_correct_password_returns_token(client):
    client.post(
        "/api/auth/register",
        json={
            "email": "login@example.com",
            "password": "Password123!",
            "full_name": "Login User",
            "role": "recruiter",
        },
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "Password123!"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]


def test_login_with_wrong_password_returns_401(client):
    client.post(
        "/api/auth/register",
        json={
            "email": "wrong@example.com",
            "password": "Password123!",
            "full_name": "Wrong",
            "role": "recruiter",
        },
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "wrong@example.com", "password": "BadPassword!"},
    )
    assert response.status_code == 401


def test_login_unknown_email_returns_401(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "ghost@example.com", "password": "Whatever123!"},
    )
    assert response.status_code == 401


def test_me_endpoint_returns_current_user(client, recruiter_token):
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "recruiter@example.com"
    assert body["role"] == "recruiter"


def test_me_endpoint_requires_token(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_endpoint_rejects_malformed_token(client):
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer not.a.real.jwt"},
    )
    assert response.status_code == 401


def test_refresh_endpoint_returns_new_access_token(client):
    register = client.post(
        "/api/auth/register",
        json={
            "email": "refresh@example.com",
            "password": "Password123!",
            "full_name": "Refresh",
            "role": "recruiter",
        },
    ).json()

    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": register["refresh_token"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    # The new token must decode to the same user (issuance time may collide
    # within the same second, so we don't assert string inequality).
    from jose import jwt  # type: ignore
    from app.core.config import settings
    new_payload = jwt.decode(body["access_token"], settings.secret_key, algorithms=[settings.algorithm])
    assert new_payload["sub"] == "refresh@example.com"
    assert new_payload.get("type") == "access"


def test_refresh_rejects_access_token(client, recruiter_token):
    """Access tokens must NOT be accepted at /refresh — they have type=access."""
    response = client.post("/api/auth/refresh", json={"refresh_token": recruiter_token})
    assert response.status_code == 401
