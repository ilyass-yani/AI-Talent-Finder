"""Canonical criteria and matching endpoints for Étape 7."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.security import decode_token
from app.models.models import Candidate, CriteriaSkill, JobCriteria, MatchResult, User, UserRole
from app.services.matching_engine import (
    build_explanation_payload,
    build_skill_universe,
    clamp_weight,
    score_candidate_against_criteria,
)


criteria_router = APIRouter(prefix="/api/criteria", tags=["criteria"])
matching_router = APIRouter(prefix="/api/criteria-legacy-matching", tags=["matching"])


class CriteriaSkillInput(BaseModel):
    name: str
    weight: int = Field(ge=0, le=100)


class CriteriaCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    required_skills: List[CriteriaSkillInput] = Field(default_factory=list)


class CriteriaUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[List[CriteriaSkillInput]] = None


class CriteriaSkillResponse(BaseModel):
    name: str
    weight: int


class CriteriaResponse(BaseModel):
    id: int
    recruiter_id: int
    title: str
    description: Optional[str] = None
    created_at: datetime
    required_skills: List[CriteriaSkillResponse] = Field(default_factory=list)


class SkillBreakdownResponse(BaseModel):
    skill: str
    weight: int
    present: bool
    score: float
    contribution: float


class CandidateMatchResponse(BaseModel):
    match_result_id: int
    criteria_id: int
    candidate_id: int
    candidate_name: str
    candidate_email: str
    score: float
    coverage: float
    matched_skills: List[str]
    missing_skills: List[str]
    skill_breakdown: List[SkillBreakdownResponse]
    summary: str
    created_at: datetime


def _resolve_recruiter(db: Session, authorization: Optional[str]) -> User:
    """Resolve the recruiter performing the action.

    The UI can work without a bearer token during local development, so we keep
    a deterministic fallback to recruiter #1 or the first recruiter/admin.
    """
    if authorization:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")

        token = parts[1]
        try:
            token_data = decode_token(token)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

        user = db.query(User).filter(User.id == token_data.user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user

    fallback = db.query(User).filter(User.id == 1).first()
    if fallback:
        return fallback

    fallback = (
        db.query(User)
        .filter(User.role.in_([UserRole.recruiter, UserRole.admin]))
        .order_by(User.id.asc())
        .first()
    )
    if fallback:
        return fallback

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No recruiter account available")


def _require_access(criteria: JobCriteria, current_user: User) -> None:
    if criteria.recruiter_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this criteria")


def _get_or_create_skill_id(db: Session, skill_name: str) -> int:
    from app.models.models import Skill

    normalized = skill_name.strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Skill name cannot be empty")

    skill = db.query(Skill).filter(Skill.name.ilike(normalized)).first()
    if skill:
        return skill.id

    skill = Skill(name=normalized, category="tech")
    db.add(skill)
    db.flush()
    return skill.id


def _replace_criteria_skills(db: Session, criteria_id: int, required_skills: List[CriteriaSkillInput]) -> None:
    db.query(CriteriaSkill).filter(CriteriaSkill.criteria_id == criteria_id).delete()

    for item in required_skills:
        name = item.name.strip()
        if not name:
            continue
        db.add(CriteriaSkill(criteria_id=criteria_id, skill_id=_get_or_create_skill_id(db, name), weight=clamp_weight(item.weight)))


def _serialize_criteria(criteria: JobCriteria, db: Session) -> CriteriaResponse:
    skills = (
        db.query(CriteriaSkill)
        .filter(CriteriaSkill.criteria_id == criteria.id)
        .order_by(CriteriaSkill.weight.desc(), CriteriaSkill.id.asc())
        .all()
    )
    required_skills = [CriteriaSkillResponse(name=skill.skill.name, weight=skill.weight) for skill in skills]
    return CriteriaResponse(
        id=criteria.id,
        recruiter_id=criteria.recruiter_id,
        title=criteria.title,
        description=criteria.description,
        created_at=criteria.created_at,
        required_skills=required_skills,
    )


def _load_criteria_skills(criteria_id: int, db: Session) -> List[Dict[str, int]]:
    rows = (
        db.query(CriteriaSkill)
        .filter(CriteriaSkill.criteria_id == criteria_id)
        .order_by(CriteriaSkill.weight.desc(), CriteriaSkill.id.asc())
        .all()
    )
    return [{"name": row.skill.name, "weight": row.weight} for row in rows]


def _score_all_candidates(criteria: JobCriteria, db: Session) -> List[CandidateMatchResponse]:
    criteria_skills = _load_criteria_skills(criteria.id, db)
    skill_universe = build_skill_universe(db)
    candidates = db.query(Candidate).order_by(Candidate.created_at.desc()).all()

    results: List[CandidateMatchResponse] = []
    for candidate in candidates:
        score, details = score_candidate_against_criteria(candidate, criteria_skills, skill_universe)
        explanation_payload = build_explanation_payload(score, details)
        results.append(CandidateMatchResponse(
            match_result_id=0,
            criteria_id=criteria.id,
            candidate_id=candidate.id,
            candidate_name=candidate.full_name,
            candidate_email=candidate.email,
            score=score,
            coverage=float(details.get("coverage", 0)),
            matched_skills=list(details.get("matched_skills", [])),
            missing_skills=list(details.get("missing_skills", [])),
            skill_breakdown=[SkillBreakdownResponse(**item) for item in details.get("skill_breakdown", [])],
            summary=str(explanation_payload.get("summary", "")),
            created_at=datetime.utcnow(),
        ))

    results.sort(key=lambda item: item.score, reverse=True)
    return results


def _persist_match_results(db: Session, criteria_id: int, results: List[CandidateMatchResponse]) -> List[MatchResult]:
    db.query(MatchResult).filter(MatchResult.criteria_id == criteria_id).delete()
    db.flush()

    stored_results: List[MatchResult] = []
    for result in results:
        stored = MatchResult(
            criteria_id=criteria_id,
            candidate_id=result.candidate_id,
            score=result.score,
            explanation=json.dumps({
                "summary": result.summary,
                "coverage": result.coverage,
                "matched_skills": result.matched_skills,
                "missing_skills": result.missing_skills,
                "skill_breakdown": [item.model_dump() for item in result.skill_breakdown],
            }, ensure_ascii=False),
        )
        db.add(stored)
        stored_results.append(stored)

    db.commit()
    for stored in stored_results:
        db.refresh(stored)
    return stored_results


def _format_stored_result(result: MatchResult) -> CandidateMatchResponse:
    explanation: Dict[str, object] = {}
    if result.explanation:
        try:
            explanation = json.loads(result.explanation)
        except Exception:
            explanation = {"summary": result.explanation}

    candidate = result.candidate
    matched_skills = explanation.get("matched_skills", []) if isinstance(explanation, dict) else []
    missing_skills = explanation.get("missing_skills", []) if isinstance(explanation, dict) else []
    skill_breakdown_data = explanation.get("skill_breakdown", []) if isinstance(explanation, dict) else []

    return CandidateMatchResponse(
        match_result_id=result.id,
        criteria_id=result.criteria_id,
        candidate_id=result.candidate_id,
        candidate_name=candidate.full_name if candidate else "Unknown",
        candidate_email=candidate.email if candidate else "",
        score=result.score,
        coverage=float(explanation.get("coverage", 0) if isinstance(explanation, dict) else 0),
        matched_skills=[str(item) for item in matched_skills],
        missing_skills=[str(item) for item in missing_skills],
        skill_breakdown=[SkillBreakdownResponse(**item) for item in skill_breakdown_data if isinstance(item, dict)],
        summary=str(explanation.get("summary", "")) if isinstance(explanation, dict) else "",
        created_at=result.created_at,
    )


@criteria_router.post("", response_model=CriteriaResponse, status_code=status.HTTP_201_CREATED)
def create_criteria(
    payload: CriteriaCreateRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    current_user = _resolve_recruiter(db, authorization)
    if current_user.role not in [UserRole.recruiter, UserRole.admin]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only recruiters can create criteria")

    criteria = JobCriteria(
        recruiter_id=current_user.id,
        title=payload.title.strip(),
        description=payload.description.strip() if payload.description else None,
    )
    db.add(criteria)
    db.flush()

    _replace_criteria_skills(db, criteria.id, payload.required_skills)
    db.commit()
    db.refresh(criteria)
    return _serialize_criteria(criteria, db)


@criteria_router.get("", response_model=List[CriteriaResponse])
def list_criteria(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    current_user = _resolve_recruiter(db, authorization)
    query = db.query(JobCriteria)
    if current_user.role != UserRole.admin:
        query = query.filter(JobCriteria.recruiter_id == current_user.id)

    criteria = query.order_by(JobCriteria.created_at.desc()).all()
    return [_serialize_criteria(item, db) for item in criteria]


@criteria_router.get("/{criteria_id}", response_model=CriteriaResponse)
def get_criteria(
    criteria_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    current_user = _resolve_recruiter(db, authorization)
    criteria = db.query(JobCriteria).filter(JobCriteria.id == criteria_id).first()
    if not criteria:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Criteria not found")
    _require_access(criteria, current_user)
    return _serialize_criteria(criteria, db)


@criteria_router.put("/{criteria_id}", response_model=CriteriaResponse)
def update_criteria(
    criteria_id: int,
    payload: CriteriaUpdateRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    current_user = _resolve_recruiter(db, authorization)
    criteria = db.query(JobCriteria).filter(JobCriteria.id == criteria_id).first()
    if not criteria:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Criteria not found")
    _require_access(criteria, current_user)

    if payload.title is not None:
        criteria.title = payload.title.strip()
    if payload.description is not None:
        criteria.description = payload.description.strip() if payload.description else None
    if payload.required_skills is not None:
        _replace_criteria_skills(db, criteria.id, payload.required_skills)

    db.commit()
    db.refresh(criteria)
    return _serialize_criteria(criteria, db)


@criteria_router.delete("/{criteria_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_criteria(
    criteria_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    current_user = _resolve_recruiter(db, authorization)
    criteria = db.query(JobCriteria).filter(JobCriteria.id == criteria_id).first()
    if not criteria:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Criteria not found")
    _require_access(criteria, current_user)

    db.query(CriteriaSkill).filter(CriteriaSkill.criteria_id == criteria_id).delete()
    db.query(MatchResult).filter(MatchResult.criteria_id == criteria_id).delete()
    db.delete(criteria)
    db.commit()


@matching_router.post("/{criteria_id}", response_model=List[CandidateMatchResponse])
def launch_matching(
    criteria_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    current_user = _resolve_recruiter(db, authorization)
    criteria = db.query(JobCriteria).filter(JobCriteria.id == criteria_id).first()
    if not criteria:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Criteria not found")
    _require_access(criteria, current_user)

    results = _score_all_candidates(criteria, db)
    stored_results = _persist_match_results(db, criteria_id, results)

    formatted_results = [
        _format_stored_result(stored_result)
        for stored_result in sorted(stored_results, key=lambda item: item.score, reverse=True)
    ]
    return formatted_results


@matching_router.get("/{criteria_id}/results", response_model=List[CandidateMatchResponse])
def get_matching_results(
    criteria_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    current_user = _resolve_recruiter(db, authorization)
    criteria = db.query(JobCriteria).filter(JobCriteria.id == criteria_id).first()
    if not criteria:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Criteria not found")
    _require_access(criteria, current_user)

    stored_results = (
        db.query(MatchResult)
        .filter(MatchResult.criteria_id == criteria_id)
        .order_by(MatchResult.score.desc(), MatchResult.id.asc())
        .all()
    )

    if not stored_results:
        computed_results = _score_all_candidates(criteria, db)
        stored_results = _persist_match_results(db, criteria_id, computed_results)

    return [_format_stored_result(result) for result in stored_results]
