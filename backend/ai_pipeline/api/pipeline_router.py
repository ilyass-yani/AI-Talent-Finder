"""FastAPI router exposing the matching pipeline."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..pipeline.orchestrator import (
    MatchingOrchestrator,
    MatchingRequest,
    MatchingResponse,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Pydantic schemas
# --------------------------------------------------------------------------- #
class MatchRequestSchema(BaseModel):
    cv_text: str = Field(..., min_length=10, description="Texte brut du CV")
    job_text: str = Field(..., min_length=10, description="Texte brut de l'offre")
    required_skills: List[str] = Field(default_factory=list)
    nice_to_have_skills: List[str] = Field(default_factory=list)
    min_years: float = 0.0
    min_edu_level: int = 0
    required_languages: Dict[str, str] = Field(default_factory=dict)
    job_location: Optional[str] = None
    remote_ok: bool = True
    use_llm: bool = False


class BatchMatchRequestSchema(BaseModel):
    cv_text: str
    jobs: List[MatchRequestSchema]


class ScoreSummary(BaseModel):
    final_score: float
    decision: str
    label_fr: str


class MatchResponseSchema(BaseModel):
    decision: Dict[str, Any]
    explanation: Dict[str, Any]
    normalized_candidate: Optional[Dict[str, Any]] = None
    timings_ms: Dict[str, float] = Field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Dependency
# --------------------------------------------------------------------------- #
_ORCHESTRATOR: Optional[MatchingOrchestrator] = None


def get_orchestrator() -> MatchingOrchestrator:
    global _ORCHESTRATOR
    if _ORCHESTRATOR is None:
        _ORCHESTRATOR = MatchingOrchestrator()
    return _ORCHESTRATOR


def set_orchestrator(orch: MatchingOrchestrator) -> None:
    """Inject a pre-built orchestrator (used in tests and at startup)."""
    global _ORCHESTRATOR
    _ORCHESTRATOR = orch


# --------------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------------- #
router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post(
    "/match",
    response_model=MatchResponseSchema,
    summary="Match d'un CV contre une offre d'emploi",
    description=(
        "Exécute le pipeline complet : nettoyage → normalisation → "
        "feature engineering → matching → scoring → décision → explication."
    ),
)
def match(
    payload: MatchRequestSchema,
    orch: MatchingOrchestrator = Depends(get_orchestrator),
) -> MatchResponseSchema:
    try:
        req = MatchingRequest(
            cv_text=payload.cv_text,
            job_text=payload.job_text,
            job_required_skills=set(payload.required_skills),
            job_nice_to_have_skills=set(payload.nice_to_have_skills),
            job_min_years=payload.min_years,
            job_min_edu_level=payload.min_edu_level,
            job_required_languages=payload.required_languages,
            job_location=payload.job_location,
            remote_ok=payload.remote_ok,
            use_llm=payload.use_llm,
        )
        resp: MatchingResponse = orch.match(req)
        return MatchResponseSchema(**resp.to_dict())
    except Exception as exc:
        logger.exception("Match failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/batch-match",
    response_model=List[MatchResponseSchema],
    summary="Match d'un CV contre plusieurs offres",
)
def batch_match(
    payload: BatchMatchRequestSchema,
    orch: MatchingOrchestrator = Depends(get_orchestrator),
) -> List[MatchResponseSchema]:
    requests = [
        MatchingRequest(
            cv_text=payload.cv_text,
            job_text=j.job_text,
            job_required_skills=set(j.required_skills),
            job_nice_to_have_skills=set(j.nice_to_have_skills),
            job_min_years=j.min_years,
            job_min_edu_level=j.min_edu_level,
            job_required_languages=j.required_languages,
            job_location=j.job_location,
            remote_ok=j.remote_ok,
            use_llm=j.use_llm,
        )
        for j in payload.jobs
    ]
    return [MatchResponseSchema(**r.to_dict()) for r in orch.batch_match(requests)]


@router.get("/health", summary="Health check du pipeline")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "ai-talent-finder-pipeline"}
