"""FastAPI router for LLM-specific endpoints.

Exposes:
  * ``POST /llm/score``     — direct LLM scoring of a CV ↔ Job pair
  * ``POST /llm/explain``   — LLM-generated natural-language rationale
  * ``GET  /llm/status``    — adapter / base-model availability
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..config import LLMConfig
from ..llm.inference import MatchingLLM

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class LLMScoreRequest(BaseModel):
    cv_text: str = Field(..., min_length=10)
    job_text: str = Field(..., min_length=10)
    max_new_tokens: int = 512
    temperature: float = 0.0


class LLMScoreResponse(BaseModel):
    score: float
    decision: str
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    strengths: List[str] = []
    weaknesses: List[str] = []
    rationale: str = ""


# --------------------------------------------------------------------------- #
# DI
# --------------------------------------------------------------------------- #
_LLM: Optional[MatchingLLM] = None


def get_llm() -> MatchingLLM:
    global _LLM
    if _LLM is None:
        # Will lazy-load only on first .score() call
        _LLM = MatchingLLM(config=LLMConfig())
    return _LLM


def set_llm(llm: MatchingLLM) -> None:
    global _LLM
    _LLM = llm


# --------------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------------- #
router = APIRouter(prefix="/llm", tags=["llm"])


@router.post("/score", response_model=LLMScoreResponse)
def llm_score(
    payload: LLMScoreRequest,
    llm: MatchingLLM = Depends(get_llm),
) -> LLMScoreResponse:
    try:
        res = llm.score(
            cv_text=payload.cv_text,
            job_text=payload.job_text,
            max_new_tokens=payload.max_new_tokens,
            temperature=payload.temperature,
        )
        return LLMScoreResponse(**res.to_dict())
    except Exception as exc:
        logger.exception("LLM scoring failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/status")
def llm_status(llm: MatchingLLM = Depends(get_llm)) -> Dict[str, Any]:
    return {
        "base_model": llm.config.base_model,
        "adapter_path": llm.adapter_path,
        "load_in_4bit": llm.load_in_4bit,
        "loaded": llm._model is not None,
    }
