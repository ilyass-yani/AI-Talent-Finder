"""Tests for the cosine matching engine and weighted scoring."""

from __future__ import annotations

from types import SimpleNamespace

from app.services.matching_engine import (
    build_explanation_payload,
    clamp_weight,
    extract_candidate_skill_names,
    load_skill_dictionary_from_file,
    normalize_skill_name,
    score_candidate_against_criteria,
)


# --------------------------------------------------------------- Helpers


def _candidate_with_skills(*skill_names: str):
    """Build a fake Candidate-like object exposing `candidate_skills` only."""
    candidate_skills = [
        SimpleNamespace(skill=SimpleNamespace(name=name)) for name in skill_names
    ]
    return SimpleNamespace(
        candidate_skills=candidate_skills,
        ner_extraction_data=None,
    )


# --------------------------------------------------------------- Normalisation


def test_normalize_skill_name_lowercases_and_collapses_whitespace():
    assert normalize_skill_name("  Python  ") == "python"
    assert normalize_skill_name("Machine   Learning") == "machine learning"


def test_clamp_weight_handles_out_of_range_and_invalid():
    assert clamp_weight(50) == 50
    assert clamp_weight(150) == 100
    assert clamp_weight(-20) == 0
    assert clamp_weight("not-a-number") == 0  # type: ignore[arg-type]


def test_load_skill_dictionary_returns_unique_ordered_list():
    skills = load_skill_dictionary_from_file()
    assert len(skills) >= 200, "Dictionary should hold the expanded Lot 3 vocabulary"
    assert len(skills) == len({normalize_skill_name(s) for s in skills}), "no duplicates expected"


# --------------------------------------------------------------- Skill extraction


def test_extract_candidate_skill_names_dedupes_db_and_ner_sources():
    candidate = SimpleNamespace(
        candidate_skills=[
            SimpleNamespace(skill=SimpleNamespace(name="Python")),
            SimpleNamespace(skill=SimpleNamespace(name="Docker")),
        ],
        ner_extraction_data='{"skills": ["python", "Kubernetes"]}',
    )
    names = extract_candidate_skill_names(candidate)
    normalized = {normalize_skill_name(n) for n in names}
    assert normalized == {"python", "docker", "kubernetes"}


# --------------------------------------------------------------- Scoring


def test_score_returns_zero_when_criteria_empty():
    candidate = _candidate_with_skills("Python")
    score, details = score_candidate_against_criteria(candidate, [])
    assert score == 0.0
    assert details["summary"] == "Aucun critère défini"


def test_score_perfect_match_when_candidate_has_all_skills():
    candidate = _candidate_with_skills("Python", "FastAPI", "Docker")
    criteria = [
        {"name": "Python", "weight": 50},
        {"name": "FastAPI", "weight": 30},
        {"name": "Docker", "weight": 20},
    ]
    score, details = score_candidate_against_criteria(candidate, criteria)
    # Cosine similarity between a binary candidate vector and a weighted criteria
    # vector won't be exactly 100, but coverage should be perfect when the
    # candidate has every required skill.
    assert score >= 90.0
    assert details["coverage"] == 100.0
    assert details["missing_skills"] == []
    assert set(details["matched_skills"]) == {"Python", "FastAPI", "Docker"}


def test_score_zero_when_no_skill_overlap():
    candidate = _candidate_with_skills("Ruby", "Rails")
    criteria = [{"name": "Python", "weight": 80}, {"name": "Django", "weight": 20}]
    score, details = score_candidate_against_criteria(candidate, criteria)
    assert score == 0.0
    assert details["coverage"] == 0.0
    assert set(details["missing_skills"]) == {"Python", "Django"}


def test_score_partial_match_higher_when_higher_weight_skill_matches():
    candidate = _candidate_with_skills("Python")
    high_weight_match = score_candidate_against_criteria(
        candidate, [{"name": "Python", "weight": 80}, {"name": "Docker", "weight": 20}]
    )[0]
    low_weight_match = score_candidate_against_criteria(
        candidate, [{"name": "Python", "weight": 20}, {"name": "Docker", "weight": 80}]
    )[0]
    assert high_weight_match > low_weight_match


def test_score_breakdown_records_each_skill_contribution():
    candidate = _candidate_with_skills("Python")
    criteria = [
        {"name": "Python", "weight": 60},
        {"name": "Docker", "weight": 40},
    ]
    _, details = score_candidate_against_criteria(candidate, criteria)
    breakdown = {item["skill"]: item for item in details["skill_breakdown"]}
    assert breakdown["Python"]["present"] is True
    assert breakdown["Python"]["contribution"] == 60.0
    assert breakdown["Docker"]["present"] is False
    assert breakdown["Docker"]["contribution"] == 0.0


def test_score_is_case_insensitive_and_whitespace_tolerant():
    candidate = _candidate_with_skills("  python  ", "FAST API")
    criteria = [{"name": "Python", "weight": 50}, {"name": "fast api", "weight": 50}]
    score, details = score_candidate_against_criteria(candidate, criteria)
    # Case + whitespace normalisation should still recognise both skills as matched.
    assert details["coverage"] == 100.0
    assert score > 0


def test_score_clamps_weights_outside_legal_range():
    candidate = _candidate_with_skills("Python")
    criteria = [{"name": "Python", "weight": 9999}, {"name": "Docker", "weight": -50}]
    score, details = score_candidate_against_criteria(candidate, criteria)
    # 9999 clamps to 100, -50 clamps to 0. Weighted coverage only counts the
    # contributing weight: Python(100)/Python(100)+Docker(0) = 100%.
    assert details["coverage"] == 100.0
    breakdown = {item["skill"]: item for item in details["skill_breakdown"]}
    assert breakdown["Python"]["weight"] == 100
    assert breakdown["Docker"]["weight"] == 0
    assert score > 0


def test_build_explanation_payload_passes_through_required_fields():
    candidate = _candidate_with_skills("Python")
    score, details = score_candidate_against_criteria(
        candidate, [{"name": "Python", "weight": 100}]
    )
    payload = build_explanation_payload(score, details)
    assert payload["score"] == score
    assert payload["coverage"] == 100.0
    assert payload["matched_skills"] == ["Python"]
    assert payload["missing_skills"] == []
    assert isinstance(payload["skill_breakdown"], list)
