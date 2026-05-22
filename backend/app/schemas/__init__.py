"""Pydantic schema exports used across the backend and legacy scripts."""

from app.schemas.candidate import (
    CandidateBase,
    CandidateCreate,
    CandidateUpdate,
    CandidateResponse,
)
from app.schemas.job_criteria import (
    JobCriteriaBase,
    JobCriteriaCreate,
    JobCriteriaUpdate,
    JobCriteriaResponse,
)

CandidateProfile = CandidateResponse

__all__ = [
    "CandidateBase",
    "CandidateCreate",
    "CandidateUpdate",
    "CandidateResponse",
    "CandidateProfile",
    "JobCriteriaBase",
    "JobCriteriaCreate",
    "JobCriteriaUpdate",
    "JobCriteriaResponse",
]
