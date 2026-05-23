"""Integration test for the end-to-end orchestrator.

Heavy components (semantic extractor, LLM) are mocked so the test
runs in a few seconds without network or GPU.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from ai_pipeline.pipeline.orchestrator import MatchingOrchestrator, MatchingRequest


def _make_orchestrator():
    fake_sem = MagicMock()
    fake_sem.similarity.return_value = 0.85
    return MatchingOrchestrator(semantic_extractor=fake_sem)


def test_orchestrator_runs_end_to_end_with_strong_match():
    orch = _make_orchestrator()
    req = MatchingRequest(
        cv_text=(
            "Développeur Python avec 4 ans d'expérience. "
            "Python, FastAPI, PostgreSQL, Docker. Master en informatique."
        ),
        job_text="Backend Python Engineer. Required: Python, FastAPI, PostgreSQL, Docker.",
        job_required_skills={"python", "fastapi", "postgresql", "docker"},
        job_min_years=2,
        job_min_edu_level=3,
    )
    resp = orch.match(req)
    assert resp.decision.final_score > 0.6
    assert resp.decision.decision.value in ("accepted", "to_review")
    assert "python" in resp.explanation.matched_skills
    assert resp.timings_ms["normalize_ms"] >= 0


def test_orchestrator_rejects_weak_match():
    orch = _make_orchestrator()
    orch.semantic_extractor.similarity.return_value = 0.15

    req = MatchingRequest(
        cv_text="Comptable senior avec 10 ans en Excel et SAP.",
        job_text="Required: Python, Kubernetes, AWS, Terraform.",
        job_required_skills={"python", "kubernetes", "aws", "terraform"},
        job_min_years=3,
    )
    resp = orch.match(req)
    assert resp.decision.final_score < 0.5
    # Blocker on hard skills should be triggered
    assert any(r.is_blocker for r in resp.decision.rule_results)


def test_orchestrator_returns_explanation_with_summary():
    orch = _make_orchestrator()
    req = MatchingRequest(
        cv_text="Dev Python, FastAPI, 3 ans d'expérience.",
        job_text="Python Backend, FastAPI required.",
        job_required_skills={"python", "fastapi"},
    )
    resp = orch.match(req)
    assert resp.explanation.summary
    assert len(resp.explanation.summary) > 10
