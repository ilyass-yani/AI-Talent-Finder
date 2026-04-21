"""Tests for the NLP layer: skill dictionary, skill extractor, NER fallbacks."""

from __future__ import annotations

import pytest

from ai_module.nlp.cv_cleaner import CVCleaner
from ai_module.nlp.skill_extractor import SkillExtractor


# --------------------------------------------------------------- Cleaner


def test_cv_cleaner_collapses_whitespace_and_strips_urls():
    cleaned = CVCleaner.clean_text("Visit  https://example.com   for details")
    assert "https" not in cleaned
    assert "example.com" not in cleaned
    assert "Visit" in cleaned and "for details" in cleaned


def test_cv_cleaner_strips_emails_and_phones():
    cleaned = CVCleaner.clean_text("Call 555-123-4567 or write john@example.com")
    assert "@" not in cleaned
    assert "555-123-4567" not in cleaned


def test_cv_cleaner_returns_empty_for_empty_input():
    assert CVCleaner.clean_text("") == ""


# --------------------------------------------------------------- Skill extractor


@pytest.fixture(scope="module")
def extractor() -> SkillExtractor:
    return SkillExtractor()


def test_dictionary_has_expected_categories(extractor):
    assert set(extractor.skills_dict.keys()) >= {"tech", "soft", "language"}
    assert len(extractor.all_skills) >= 200


def test_extractor_finds_exact_skill_matches(extractor):
    text = "I am a Python developer with strong experience in Docker and Kubernetes."
    found = {item["name"].lower() for item in extractor.extract_skills(text, threshold=85)}
    assert "python" in found
    assert "docker" in found
    assert "kubernetes" in found


def test_extractor_returns_method_and_confidence_metadata(extractor):
    found = extractor.extract_skills("Skilled in Python and FastAPI", threshold=90)
    by_name = {item["name"].lower(): item for item in found}
    python_match = by_name["python"]
    assert python_match["method"] == "exact"
    assert python_match["confidence"] == 100
    assert python_match["category"] == "tech"


def test_extractor_skips_unrelated_words(extractor):
    text = "I love hiking and cooking on weekends."
    found = {item["name"].lower() for item in extractor.extract_skills(text, threshold=95)}
    # None of those hobbies should map to a real tech/soft skill at 95% threshold.
    assert "python" not in found
    assert "kubernetes" not in found


def test_extractor_returns_empty_for_empty_text(extractor):
    assert extractor.extract_skills("") == []


def test_proficiency_detects_seniority_keywords(extractor):
    text = "Senior Python architect with 10 years experience"
    assert extractor.extract_proficiency(text, "Python") in {"expert", "advanced"}


def test_proficiency_defaults_to_beginner_when_skill_absent(extractor):
    assert extractor.extract_proficiency("This text does not mention it", "Python") == "beginner"
