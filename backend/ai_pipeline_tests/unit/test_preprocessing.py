"""Unit tests for the preprocessing layer."""
from __future__ import annotations

import pytest

from ai_pipeline.preprocessing.cv_cleaner import CVCleaner
from ai_pipeline.preprocessing.data_normalizer import DataNormalizer
from ai_pipeline.preprocessing.skill_normalizer import SkillNormalizer


def test_skill_normalizer_canonical_lookup():
    n = SkillNormalizer()
    # The canonical names are capitalized (Python, JavaScript, React, ...)
    assert n.normalize("js").lower() == "javascript"
    assert n.normalize("Python3").lower() == "python"
    assert n.normalize("REACT.JS").lower() == "react"


def test_skill_normalizer_extracts_skills_from_text():
    n = SkillNormalizer()
    text = "I have experience with Python, FastAPI, PostgreSQL and Docker"
    skills = n.extract_skills(text)
    skills_lower = [s.lower() for s in skills]
    assert "python" in skills_lower
    assert "fastapi" in skills_lower
    assert "postgresql" in skills_lower
    assert "docker" in skills_lower


def test_cv_cleaner_strips_noise():
    cleaner = CVCleaner()
    raw = "John Doe\n\n\n\n   Email:  john@x.com   \n\nExperience:\n- dev\n"
    cleaned = cleaner.clean_text_only(raw)
    assert "john@x.com" in cleaned.lower()
    # Triple-newlines collapsed
    assert "\n\n\n" not in cleaned


def test_data_normalizer_extracts_years_experience():
    n = DataNormalizer()
    cand = n.normalize_from_text(
        "Développeur Python avec 5 ans d'expérience. "
        "Formation : Master en informatique."
    )
    assert cand.years_experience >= 5
    assert cand.education_level >= 3  # Master = 3
