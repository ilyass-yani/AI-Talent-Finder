"""Scoring and matching API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from app.services.scoring import compute_match_score, apply_business_rules
from app.services.data_normalization import normalize_skills_list, parse_experience_years
from app.services.synthetic_data import generate_synthetic_dataset
from app.services.deduplication import deduplicate_candidates


router = APIRouter(prefix="/api/matching", tags=["Matching"])


class CandidateMatchRequest(BaseModel):
    """Request to match a candidate against a job."""

    cv_skills: List[str] = Field(..., description="Candidate skills")
    job_skills: List[str] = Field(..., description="Job required skills")
    cv_years: int = Field(default=0, description="Candidate years of experience")
    job_years: int = Field(default=0, description="Job required years")
    cv_education: int = Field(default=2, description="Candidate education level (0-4)")
    job_education: int = Field(default=2, description="Job education requirement (0-4)")
    semantic_similarity: float = Field(default=0.0, description="Semantic similarity score (0-1)")


class MatchDecisionResponse(BaseModel):
    """Response with match decision and explanation."""

    decision: str = Field(..., description="accepted | to_review | rejected")
    score: float = Field(..., description="Match score (0-1)")
    skill_match_ratio: float = Field(..., description="Ratio of matched skills")
    experience_gap_years: int = Field(..., description="Years of experience gap")
    missing_skills: List[str] = Field(default_factory=list, description="Missing skills")
    explanation: str = Field(..., description="Human-readable explanation")


class TestDatasetResponse(BaseModel):
    """Response with synthetic test dataset."""

    n_candidates: int
    n_jobs: int
    candidates: List[Dict[str, Any]]
    jobs: List[Dict[str, Any]]


@router.post("/advanced-score", response_model=MatchDecisionResponse)
def compute_advanced_match_score(request: CandidateMatchRequest) -> MatchDecisionResponse:
    """Compute advanced match score with calibrated business rules.

    Returns:
    - decision: accepted (>=80%), to_review (50-80%), rejected (<50%)
    - score: computed match score
    - skill_match_ratio: % of required skills matched
    - experience_gap_years: gap between required and candidate years
    - missing_skills: list of required but missing skills
    - explanation: human-readable summary
    """
    # Normalize input skills
    cv_skills = normalize_skills_list(request.cv_skills)
    job_skills = normalize_skills_list(request.job_skills)

    # Compute score
    score = compute_match_score(
        cv_skills=cv_skills,
        job_skills=job_skills,
        cv_years=request.cv_years,
        job_years=request.job_years,
        cv_edu_level=request.cv_education,
        job_edu_level=request.job_education,
        similarity_score=request.semantic_similarity,
    )

    # Apply business rules
    decision_data = apply_business_rules({
        "score": score,
        "cv_skills": cv_skills,
        "job_skills": job_skills,
        "cv_years": request.cv_years,
        "job_years": request.job_years,
        "cv_edu": request.cv_education,
        "job_edu": request.job_education,
    })

    return MatchDecisionResponse(**decision_data)


@router.get("/test-dataset")
def get_test_dataset(
    n_candidates: int = 10,
    n_jobs: int = 5,
    seed: int = 42,
) -> TestDatasetResponse:
    """Generate and return a synthetic test dataset.

    Useful for testing matching algorithms locally without real data.

    Params:
    - n_candidates: number of synthetic CV candidates
    - n_jobs: number of synthetic job postings
    - seed: random seed for reproducibility
    """
    if n_candidates < 1 or n_candidates > 500:
        raise HTTPException(status_code=400, detail="n_candidates must be 1-500")
    if n_jobs < 1 or n_jobs > 100:
        raise HTTPException(status_code=400, detail="n_jobs must be 1-100")

    dataset = generate_synthetic_dataset(n_candidates, n_jobs, seed)

    # Deduplicate if needed
    candidates = deduplicate_candidates(dataset["candidates"])

    return TestDatasetResponse(
        n_candidates=len(candidates),
        n_jobs=len(dataset["jobs"]),
        candidates=candidates,
        jobs=dataset["jobs"],
    )


__all__ = ["router"]
