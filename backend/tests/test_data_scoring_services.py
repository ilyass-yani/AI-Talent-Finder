"""Unit tests for data normalization, scoring and deduplication."""

import pytest
from app.services.data_normalization import (
    normalize_skill,
    normalize_skills_list,
    parse_experience_years,
    clean_candidate,
)
from app.services.scoring import (
    compute_match_score,
    decide_match,
    MatchDecision,
    apply_business_rules,
)
from app.services.deduplication import (
    compute_fingerprint,
    deduplicate_candidates,
)
from app.services.synthetic_data import (
    generate_synthetic_candidate,
    generate_synthetic_job,
    generate_synthetic_dataset,
)


class TestDataNormalization:
    """Test data normalization functions."""

    def test_normalize_skill_basic(self):
        assert normalize_skill("Python") == "Python"
        assert normalize_skill("python") == "Python"

    def test_normalize_skill_mapping(self):
        assert normalize_skill("ml") == "Machine Learning"
        assert normalize_skill("ML") == "Machine Learning"
        assert normalize_skill("js") == "JavaScript"
        assert normalize_skill("nodejs") == "Node.js"

    def test_normalize_skills_list(self):
        skills = ["React.js", "python", "ml", "AWS"]
        normalized = normalize_skills_list(skills)
        assert "React" in normalized
        assert "Python" in normalized
        assert "Machine Learning" in normalized
        assert "AWS" in normalized

    def test_parse_experience_years(self):
        assert parse_experience_years("5+ years") == 5
        assert parse_experience_years("5+ years of experience") == 5
        assert parse_experience_years("10 ans") == 10
        assert parse_experience_years("") == 0

    def test_clean_candidate(self):
        cand = {
            "skills": "React, python, ml, AWS",
            "experience": "5+ years in web dev",
            "education": "Bachelor",
        }
        cleaned = clean_candidate(cand)
        assert "normalized_skills" in cleaned
        assert len(cleaned["normalized_skills"]) == 4
        assert cleaned["experience_years"] == 5


class TestScoring:
    """Test scoring logic."""

    def test_compute_match_score_perfect_match(self):
        score = compute_match_score(
            cv_skills=["React", "Python", "AWS"],
            job_skills=["React", "Python", "AWS"],
            cv_years=5,
            job_years=3,
        )
        # Score should be high for perfect skill match + enough experience
        assert score >= 0.80

    def test_compute_match_score_no_skills(self):
        score = compute_match_score(
            cv_skills=[],
            job_skills=["React"],
            cv_years=5,
        )
        assert score < 0.5

    def test_decide_match_accepted(self):
        decision = decide_match(0.85)
        assert decision == MatchDecision.ACCEPTED

    def test_decide_match_review(self):
        decision = decide_match(0.65)
        assert decision == MatchDecision.REVIEW

    def test_decide_match_rejected(self):
        decision = decide_match(0.40)
        assert decision == MatchDecision.REJECTED

    def test_apply_business_rules(self):
        result = apply_business_rules({
            "score": 0.75,
            "cv_skills": ["React", "Python"],
            "job_skills": ["React", "Node"],
            "cv_years": 5,
            "job_years": 3,
        })
        assert result["decision"] == "to_review"
        assert result["score"] == 0.75
        # missing_skills are lowercased during comparison
        assert any("node" in str(skill).lower() for skill in result["missing_skills"])


class TestDeduplication:
    """Test deduplication logic."""

    def test_compute_fingerprint(self):
        cand = {
            "email": "test@example.com",
            "phone": "123456",
            "full_name": "John Doe",
            "normalized_skills": ["Python", "React"],
        }
        fp = compute_fingerprint(cand)
        assert isinstance(fp, str)
        assert len(fp) == 32  # MD5 hash

    def test_deduplicate_candidates(self):
        cand1 = {
            "email": "test@example.com",
            "phone": "123456",
            "full_name": "John",
            "normalized_skills": ["Python"],
        }
        cand2 = {
            "email": "test@example.com",
            "phone": "123456",
            "full_name": "John",
            "normalized_skills": ["Python"],
        }
        cand3 = {
            "email": "other@example.com",
            "phone": "999999",
            "full_name": "Jane",
            "normalized_skills": ["React"],
        }
        candidates = [cand1, cand2, cand3]
        deduped = deduplicate_candidates(candidates)
        assert len(deduped) == 2  # cand2 is duplicate of cand1


class TestSyntheticData:
    """Test synthetic data generation."""

    def test_generate_synthetic_candidate(self):
        cand = generate_synthetic_candidate(user_id=100)
        assert cand["id"] == 100
        assert cand["full_name"] == "Candidate 100"
        assert len(cand["normalized_skills"]) > 0
        assert cand["experience_years"] >= 0
        assert len(cand["languages"]) > 0

    def test_generate_synthetic_job(self):
        job = generate_synthetic_job(job_id=50)
        assert job["id"] == 50
        assert len(job["required_skills"]) > 0
        assert job["required_years"] >= 0

    def test_generate_synthetic_dataset(self):
        dataset = generate_synthetic_dataset(n_candidates=3, n_jobs=2, seed=42)
        assert len(dataset["candidates"]) == 3
        assert len(dataset["jobs"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
