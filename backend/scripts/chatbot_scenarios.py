#!/usr/bin/env python3
"""
Run chatbot scenarios against deployed or local API for QA.
Usage:
  API_BASE_URL=https://... RECRUITER_EMAIL=... RECRUITER_PASSWORD=... \
    PYTHONPATH=. python3 backend/scripts/chatbot_scenarios.py
"""
import json
import os
import requests

BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
EMAIL = os.getenv("RECRUITER_EMAIL")
PASSWORD = os.getenv("RECRUITER_PASSWORD")
HEADERS = {"Content-Type": "application/json"}


def _url(path: str) -> str:
    return BASE.rstrip("/") + path


def _print_response(resp: requests.Response) -> None:
    print("Status:", resp.status_code)
    try:
        print("Response:", json.dumps(resp.json(), indent=2, ensure_ascii=False)[:2000])
    except Exception:
        print("Response text:", resp.text[:2000])


def _login() -> dict:
    if not (EMAIL and PASSWORD):
        return dict(HEADERS)

    resp = requests.post(
        _url("/api/auth/login"),
        headers=HEADERS,
        json={"email": EMAIL, "password": PASSWORD},
        timeout=15,
    )
    if resp.status_code != 200:
        print("Login failed:", resp.status_code, resp.text[:300])
        return dict(HEADERS)

    token = resp.json().get("access_token")
    if not token:
        return dict(HEADERS)
    headers = dict(HEADERS)
    headers["Authorization"] = f"Bearer {token}"
    return headers


def _maybe_create_criteria(headers: dict) -> int | None:
    if "Authorization" not in headers:
        return None

    payload = {
        "title": "Senior Python Developer",
        "description": "Looking for backend engineer with FastAPI and ML experience.",
        "required_skills": [
            {"name": "Python", "weight": 90},
            {"name": "FastAPI", "weight": 80},
            {"name": "PostgreSQL", "weight": 70},
            {"name": "Docker", "weight": 70},
            {"name": "Machine Learning", "weight": 60},
        ],
    }
    resp = requests.post(
        _url("/api/matching/criteria"),
        headers=headers,
        json=payload,
        timeout=30,
    )
    if resp.status_code not in {200, 201}:
        print("Criteria creation failed:", resp.status_code, resp.text[:300])
        return None

    criteria_id = resp.json().get("id")
    if criteria_id:
        requests.post(
            _url(f"/api/matching/{criteria_id}/results"),
            headers=headers,
            timeout=60,
        )
    return criteria_id


def main() -> None:
    print(f"Running chatbot scenarios against {BASE}")
    auth_headers = _login()
    criteria_id = _maybe_create_criteria(auth_headers)
    context = {"current_criteria_id": criteria_id} if criteria_id else {}

    scenarios = [
        {
            "name": "Chat - explanation",
            "endpoint": "/api/chat",
            "method": "post",
            "payload": {
                "message": "Pourquoi le meilleur candidat a ce score ?",
                "context": context,
            },
        },
        {
            "name": "Chat - comparison",
            "endpoint": "/api/chat",
            "method": "post",
            "payload": {
                "message": "Compare les deux meilleurs candidats.",
                "context": context,
            },
        },
        {
            "name": "Chat - exploration",
            "endpoint": "/api/chat",
            "method": "post",
            "payload": {
                "message": "Montre les candidats avec Python.",
                "context": context,
            },
        },
        {
            "name": "Chat - ideal profile",
            "endpoint": "/api/chat/ideal-profile",
            "method": "post",
            "payload": {
                "job_title": "Senior Python Developer",
                "job_description": "FastAPI, ML, Docker, and PostgreSQL focus.",
                "required_skills": ["Python", "FastAPI", "Docker"],
            },
        },
    ]

    for scenario in scenarios:
        print("\n---")
        print("Scenario:", scenario["name"])
        try:
            url = _url(scenario["endpoint"])
            if scenario["method"].lower() == "post":
                resp = requests.post(url, headers=HEADERS, json=scenario["payload"], timeout=30)
            else:
                resp = requests.get(url, headers=HEADERS, timeout=30)
            _print_response(resp)
        except Exception as exc:
            print("Error calling endpoint:", exc)

    if "Authorization" in auth_headers:
        print("\n---")
        print("Scenario: Matching - generate-and-match")
        try:
            resp = requests.post(
                _url("/api/matching/generate-and-match"),
                headers=auth_headers,
                json={
                    "job_title": "Senior Python Developer",
                    "description": "FastAPI, ML, Docker, PostgreSQL, and cloud experience.",
                },
                timeout=60,
            )
            _print_response(resp)
        except Exception as exc:
            print("Error calling endpoint:", exc)

    print("\nDone.")


if __name__ == "__main__":
    main()
