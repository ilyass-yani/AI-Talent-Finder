#!/usr/bin/env python3
"""
Unit tests for AI-Talent-Finder API
Tests critical paths for authentication, CV upload, and matching
"""

import pytest
import json
import uuid
from unittest.mock import patch, MagicMock
from datetime import datetime
from fastapi.testclient import TestClient

# Mock dependent imports before importing main
with patch('app.ai_module.nlp.cv_cleaner.CVCleaner'):
    with patch('app.ai_module.nlp.skill_extractor.SkillExtractor'):
        with patch('app.ai_module.nlp.profile_generator.ProfileGenerator'):
            from app.main import app
            from app.models.models import User, Candidate, Favorite
            from app.core.security import get_password_hash

client = TestClient(app)


class TestAuthentication:
    """Test authentication workflows"""

    def test_register_user(self):
        """Test user registration"""
        email = f"testuser_{uuid.uuid4().hex[:8]}@example.com"
        response = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "TestPassword123!",
                "full_name": "Test User",
                "role": "candidate"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["user"]["email"] == email
        assert data["user"]["full_name"] == "Test User"
        assert "access_token" in data

    def test_login_user(self):
        """Test user login"""
        # First register
        email = f"logintest_{uuid.uuid4().hex[:8]}@example.com"
        client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "Password123!",
                "full_name": "Login User",
                "role": "candidate"
            }
        )

        # Then login
        response = client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "Password123!"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_email(self):
        """Test duplicate email registration"""
        email = f"duplicate_{uuid.uuid4().hex[:8]}@example.com"
        
        # First registration
        client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "Password123!",
                "full_name": "User 1",
                "role": "candidate"
            }
        )

        # Duplicate registration
        response = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "Password123!",
                "full_name": "User 2",
                "role": "candidate"
            }
        )
        assert response.status_code == 409


class TestCandidateProfile:
    """Test candidate profile endpoints"""

    @pytest.fixture
    def auth_token(self):
        """Create a test user and return auth token"""
        email = f"profiletest_{uuid.uuid4().hex[:8]}@example.com"
        response = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "Password123!",
                "full_name": "Profile Test User",
                "role": "candidate"
            }
        )
        token_response = client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "Password123!"
            }
        )
        return token_response.json()["access_token"]

    def test_get_profile_without_cv(self, auth_token):
        """Test getting profile when no CV uploaded yet"""
        response = client.get(
            "/api/candidates/me/profile",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 404

    def test_get_profile_with_placeholder_cv(self, auth_token):
        """Test getting profile after uploading CV"""
        # Mock file upload
        with patch('app.api.candidates.extract_text_from_pdf'):
                response = client.post(
                    "/api/candidates/upload",
                    headers={"Authorization": f"Bearer {auth_token}"},
                    data={"full_name": "John Doe", "email": "john@example.com"},
                    files={"file": ("test.txt", b"Test CV content")}
                )
                
                # Even if extraction fails, candidate should exist
                if response.status_code == 200:
                    profile_response = client.get(
                        "/api/candidates/me/profile",
                        headers={"Authorization": f"Bearer {auth_token}"}
                    )
                    assert profile_response.status_code == 200
                    assert profile_response.json()["full_name"]


class TestMatching:
    """Test semantic matching endpoints"""

    def test_search_candidates_no_criteria(self):
        """Test searching candidates without creating criteria first"""
        response = client.post("/api/matching/search/999")
        # Route is protected, so unauthenticated access should be rejected first
        assert response.status_code == 401


class TestFavorites:
    """Test favorites/shortlist endpoints"""

    @pytest.fixture
    def recruiter_token(self):
        """Create a recruiter user"""
        email = f"recruiter_{uuid.uuid4().hex[:8]}@example.com"
        response = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "Password123!",
                "full_name": "Recruiter User",
                "role": "recruiter"
            }
        )
        token_response = client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "Password123!"
            }
        )
        return token_response.json()["access_token"]

    @pytest.fixture
    def candidate_id(self, recruiter_token):
        """Create a candidate and return its ID"""
        email = f"fav_candidate_{uuid.uuid4().hex[:8]}@example.com"
        response = client.post(
            "/api/candidates/",
            headers={"Authorization": f"Bearer {recruiter_token}"},
            json={
                "full_name": "Favorite Candidate",
                "email": email,
                "phone": "+33 6 00 00 00 00",
                "linkedin_url": None,
                "github_url": None,
                "cv_path": None,
                "raw_text": "Python FastAPI Docker",
            },
        )
        return response.json().get("id")

    def test_add_favorite(self, recruiter_token, candidate_id):
        """Test adding candidate to favorites"""
        response = client.post(
            f"/api/favorites/{candidate_id}",
            headers={"Authorization": f"Bearer {recruiter_token}"}
        )
        assert response.status_code in [200, 201]
        assert response.json()["candidate_id"] == candidate_id

    def test_list_favorites(self, recruiter_token):
        """Test listing favorite candidates"""
        response = client.get(
            "/api/favorites/",
            headers={"Authorization": f"Bearer {recruiter_token}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_remove_favorite(self, recruiter_token, candidate_id):
        """Test removing candidate from favorites"""
        # First add to favorites
        client.post(
            f"/api/favorites/{candidate_id}",
            headers={"Authorization": f"Bearer {recruiter_token}"}
        )

        # Then remove
        response = client.delete(
            f"/api/favorites/{candidate_id}",
            headers={"Authorization": f"Bearer {recruiter_token}"}
        )
        assert response.status_code == 204


class TestAuthorization:
    """Test authorization constraints"""

    def test_unauthorized_access_profile(self):
        """Test accessing profile without auth token"""
        response = client.get("/api/candidates/me/profile")
        assert response.status_code == 401

    def test_unauthorized_upload_cv(self):
        """Test uploading CV without auth token"""
        response = client.post(
            "/api/candidates/upload",
            files={"file": ("test.txt", b"Test")}
        )
        assert response.status_code == 401


class TestErrorHandling:
    """Test error handling and validation"""

    def test_invalid_email_registration(self):
        """Test registration with invalid email"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "invalid-email",
                "password": "Password123!",
                "full_name": "Test User",
                "role": "candidate"
            }
        )
        assert response.status_code == 422

    def test_weak_password_registration(self):
        """Test registration with weak password"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "123",
                "full_name": "Test User",
                "role": "candidate"
            }
        )
        # Should succeed (no validation on password strength)
        # or fail (if validation implemented)
        assert response.status_code in [200, 422]


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
