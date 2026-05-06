"""
Matching API routes - Recruteur workflow
MODES:
  1️⃣ Mode recherche: Chercher dans candidats existants
  2️⃣ Mode génération profil idéal: Décrire le besoin, l'IA génère le profil
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Tuple, cast
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import os

from app.core.dependencies import get_db, get_current_user
from app.models.models import (
    JobCriteria, 
    MatchResult, 
    Candidate, 
    User,
    CriteriaSkill,
    Skill,
    CandidateSkill
)
from app.services.matching_engine import build_skill_universe, build_explanation_payload, score_candidate_against_criteria
from app.services.feature_engineering import build_pair_features, PairFeatureMeta
from app.services.normalization import normalize_skill_name, normalize_text
from app.services.explainability_engine import generate_explanation, generate_shortlist_summary

# Optional imports with fallback
try:
    from ai_module.nlp.profile_generator import ProfileGenerator
    PROFILE_GENERATOR_AVAILABLE = True
except Exception as e:
    print(f"⚠️ ProfileGenerator not available: {e}")
    PROFILE_GENERATOR_AVAILABLE = False

try:
    from ai_module.matching.semantic_matcher import SemanticSkillMatcher
    SEMANTIC_MATCHER_AVAILABLE = True
except Exception as e:
    print(f"⚠️ SemanticSkillMatcher not available: {e}")
    SEMANTIC_MATCHER_AVAILABLE = False

try:
    from ai_module.nlp.skill_extractor import SkillExtractor
    SKILL_EXTRACTOR_AVAILABLE = True
except Exception as e:
    print(f"⚠️ SkillExtractor not available: {e}")
    SKILL_EXTRACTOR_AVAILABLE = False


router = APIRouter(
    prefix="/api/matching",
    tags=["matching"],
    dependencies=[Depends(get_current_user)]
)

import json
import joblib
from pathlib import Path
import numpy as np

# Lazy-loaded baseline model cache
_BASELINE_MODEL: dict | None = None
_SIAMESE_MODEL = None
_SIAMESE_MODEL_PATH: str | None = None
_MATCH_THRESHOLDS: dict[str, float] | None = None


def _load_baseline_model() -> dict | None:
    global _BASELINE_MODEL
    if _BASELINE_MODEL is not None:
        return _BASELINE_MODEL

    model_root = Path(__file__).resolve().parents[3] / "models"
    candidates = [
        model_root / "final_match_model.joblib",
        model_root / "baseline_model.joblib",
    ]
    model_path = next((path for path in candidates if path.exists()), None)
    if model_path is None:
        return None

    try:
        _BASELINE_MODEL = joblib.load(model_path)
        thresholds = _BASELINE_MODEL.get("thresholds") if isinstance(_BASELINE_MODEL, dict) else None
        if isinstance(thresholds, dict):
            global _MATCH_THRESHOLDS
            _MATCH_THRESHOLDS = {
                "accept_pct": float(thresholds.get("accept_pct", 94.78)),
                "review_pct": float(thresholds.get("review_pct", 89.78)),
            }
        return _BASELINE_MODEL
    except Exception:
        return None


def _load_siamese_model() -> tuple[object, str] | tuple[None, None]:
    global _SIAMESE_MODEL, _SIAMESE_MODEL_PATH

    if _SIAMESE_MODEL is not None and _SIAMESE_MODEL_PATH is not None:
        return _SIAMESE_MODEL, _SIAMESE_MODEL_PATH

    model_root = Path(__file__).resolve().parents[3] / "models"
    candidates = [
        model_root / "siamese_model_phase2_full",
        model_root / "siamese_model_phase2",
        model_root / "siamese_model",
    ]

    existing = [path for path in candidates if path.exists()]
    if not existing:
        return None, None

    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        return None, None

    for model_path in existing:
        try:
            _SIAMESE_MODEL = SentenceTransformer(str(model_path))
            _SIAMESE_MODEL_PATH = str(model_path)
            return _SIAMESE_MODEL, _SIAMESE_MODEL_PATH
        except Exception:
            continue

    return None, None


def _score_with_siamese(model: object, candidate_text: str, job_text: str) -> float:
    embeddings = model.encode(
        [candidate_text, job_text],
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    similarity = float(np.dot(embeddings[0], embeddings[1]))
    return float(np.clip(similarity, 0.0, 1.0) * 100.0)


def _decision_from_score(score_pct: float) -> str:
    global _MATCH_THRESHOLDS
    if _MATCH_THRESHOLDS is None:
        _load_baseline_model()

    accept_threshold = float(
        os.getenv(
            "MATCH_ACCEPT_THRESHOLD",
            str((_MATCH_THRESHOLDS or {}).get("accept_pct", 94.78)),
        )
    )
    review_threshold = float(
        os.getenv(
            "MATCH_REVIEW_THRESHOLD",
            str((_MATCH_THRESHOLDS or {}).get("review_pct", 89.78)),
        )
    )

    # Keep ordering sane even if env vars are misconfigured.
    if review_threshold > accept_threshold:
        review_threshold = accept_threshold

    if score_pct >= accept_threshold:
        return "accepted"
    if score_pct >= review_threshold:
        return "review"
    return "rejected"


def _build_pair_features_single(candidate_text: str, job_text: str, meta: dict) -> np.ndarray:
    if isinstance(meta, PairFeatureMeta):
        feature_meta = meta
    else:
        feature_meta = PairFeatureMeta(tfidf=meta.get('tf'), svd=meta.get('svd'))

    return build_pair_features(candidate_text, job_text, feature_meta)



# ============================================================================
# SCHEMAS
# ============================================================================

class MatchingMode(str, Enum):
    search = "search"  # Mode 1: Chercher dans la base
    generate = "generate"  # Mode 2: Générer profil idéal


class RequiredSkillInput(BaseModel):
    name: str
    weight: int = 50


class JobCriteriaCreate(BaseModel):
    """Create job criteria for matching"""
    title: str  # e.g., "Senior Python Developer"
    description: str  # Job description
    mode: MatchingMode = MatchingMode.search
    required_skills: List[RequiredSkillInput] = Field(default_factory=list)


class JobCriteriaUpdate(BaseModel):
    """Update an existing criteria"""
    title: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[List[RequiredSkillInput]] = None


class MatchResultResponse(BaseModel):
    """Match result between criteria and candidate"""
    id: int
    criteria_id: int
    candidate_id: int
    score: float  # 0-100
    explanation: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class JobCriteriaResponse(BaseModel):
    """Job criteria response"""
    id: int
    recruiter_id: int
    title: str
    description: str
    created_at: datetime
    required_skills: List[dict] = Field(default_factory=list)

    class Config:
        from_attributes = True


class CandidateMatchResponse(BaseModel):
    """Candidate with match score"""
    candidate_id: int
    full_name: str
    email: str
    match_score: float
    explanation: Optional[str] = None


class GenerateProfileRequest(BaseModel):
    job_title: str
    description: str


class SkillBreakdownResponse(BaseModel):
    skill: str
    weight: int
    present: bool
    score: float
    contribution: float


class CriteriaMatchResultResponse(BaseModel):
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


class PredictSkillBreakdownResponse(BaseModel):
    skill: str
    present: bool
    weight: int
    matched: bool


class PredictCandidateResponse(BaseModel):
    candidate_id: int
    full_name: str
    email: str
    predicted_score: float
    decision: str
    coverage: float
    matched_skills: List[str]
    missing_skills: List[str]
    skill_breakdown: List[PredictSkillBreakdownResponse]
    summary: str


class PredictCriteriaResponse(BaseModel):
    criteria_id: int
    model: str
    top_k: int
    results: List[PredictCandidateResponse]


# ============================================================================
# HELPERS
# ============================================================================

def _normalize_weight(weight: int) -> int:
    return max(0, min(100, int(weight)))


def _get_or_create_skill(db: Session, skill_name: str) -> Skill:
    normalized_name = normalize_skill_name(skill_name)
    if not normalized_name:
        raise HTTPException(status_code=400, detail="Skill name cannot be empty")

    existing_skill = db.query(Skill).filter(Skill.name.ilike(normalized_name)).first()
    if existing_skill:
        return existing_skill

    created_skill = Skill(name=normalized_name, category="tech")
    db.add(created_skill)
    db.flush()
    return created_skill


def _replace_criteria_skills(db: Session, criteria_id: int, required_skills: List[RequiredSkillInput]) -> None:
    db.query(CriteriaSkill).filter(CriteriaSkill.criteria_id == criteria_id).delete()

    for req_skill in required_skills:
        if not normalize_skill_name(req_skill.name):
            continue
        skill = _get_or_create_skill(db, req_skill.name)
        db.add(CriteriaSkill(
            criteria_id=criteria_id,
            skill_id=skill.id,
            weight=_normalize_weight(req_skill.weight)
        ))


def _build_criteria_response(criteria: JobCriteria, db: Session) -> JobCriteriaResponse:
    criteria_skills = db.query(CriteriaSkill).filter(CriteriaSkill.criteria_id == criteria.id).all()
    required_skills = [
        {"name": cs.skill.name, "weight": cs.weight}
        for cs in criteria_skills
    ]

    return JobCriteriaResponse(
        id=criteria.id,
        recruiter_id=criteria.recruiter_id,
        title=normalize_text(criteria.title),
        description=normalize_text(criteria.description),
        created_at=criteria.created_at,
        required_skills=required_skills
    )


def _load_criteria_skills(criteria_id: int, db: Session) -> List[Dict[str, int]]:
    rows = db.query(CriteriaSkill).filter(CriteriaSkill.criteria_id == criteria_id).order_by(CriteriaSkill.weight.desc(), CriteriaSkill.id.asc()).all()
    return [{"name": row.skill.name, "weight": row.weight} for row in rows]


def _serialize_match_result(candidate: Candidate, criteria_id: int, score: float, details: Dict[str, object], stored_id: int = 0) -> CriteriaMatchResultResponse:
    explanation_payload = build_explanation_payload(score, details)
    return CriteriaMatchResultResponse(
        match_result_id=stored_id,
        criteria_id=criteria_id,
        candidate_id=cast(int, candidate.id),
        candidate_name=cast(str, candidate.full_name),
        candidate_email=cast(str, candidate.email),
        score=score,
        coverage=float(details.get("coverage", 0)),
        matched_skills=list(details.get("matched_skills", [])),
        missing_skills=list(details.get("missing_skills", [])),
        skill_breakdown=[SkillBreakdownResponse(**item) for item in details.get("skill_breakdown", [])],
        summary=str(explanation_payload.get("summary", "")),
        created_at=datetime.utcnow(),
    )


def _score_all_candidates(criteria: JobCriteria, db: Session) -> List[CriteriaMatchResultResponse]:
    criteria_skills = _load_criteria_skills(criteria.id, db)
    skill_universe = build_skill_universe(db)
    # Only match fully extracted candidates with valid names and uploaded CV text
    candidates = db.query(Candidate).filter(
        ((Candidate.is_fully_extracted == True) | (Candidate.extraction_quality_score >= 80)),
        Candidate.full_name.isnot(None),
        Candidate.full_name != "Unknown",
        Candidate.full_name != "",
        Candidate.raw_text.isnot(None)
    ).order_by(Candidate.created_at.desc()).all()

    results: List[CriteriaMatchResultResponse] = []
    for candidate in candidates:
        score, details = score_candidate_against_criteria(candidate, criteria_skills, skill_universe)
        results.append(_serialize_match_result(candidate, criteria.id, score, details))

    results.sort(key=lambda item: item.score, reverse=True)
    return results


def _persist_match_results(db: Session, criteria_id: int, results: List[CriteriaMatchResultResponse]) -> List[MatchResult]:
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


def _format_stored_result(result: MatchResult) -> CriteriaMatchResultResponse:
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

    return CriteriaMatchResultResponse(
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


def _build_prediction_explainability(candidate: Candidate, criteria: JobCriteria, criteria_skills: List[Dict[str, int]]) -> Dict[str, object]:
    candidate_skill_names: List[str] = []
    for candidate_skill in getattr(candidate, "candidate_skills", []) or []:
        skill = getattr(candidate_skill, "skill", None)
        if skill and getattr(skill, "name", None):
            candidate_skill_names.append(str(skill.name))

    criteria_skill_names = [str(skill.get("name", "")) for skill in criteria_skills if skill.get("name")]
    candidate_skill_lookup = {item.lower() for item in candidate_skill_names}
    matched_skills = [skill for skill in criteria_skill_names if skill.lower() in candidate_skill_lookup]
    missing_skills = [skill for skill in criteria_skill_names if skill.lower() not in candidate_skill_lookup]

    total = len(criteria_skill_names) or 1
    coverage = round((len(matched_skills) / total) * 100, 1)

    skill_breakdown: List[Dict[str, object]] = []
    for skill in criteria_skills:
        skill_name = str(skill.get("name", ""))
        is_present = skill_name.lower() in candidate_skill_lookup
        skill_breakdown.append({
            "skill": skill_name,
            "present": is_present,
            "weight": int(skill.get("weight", 50)),
            "matched": is_present,
        })

    if matched_skills:
        summary = f"{candidate.full_name} couvre {len(matched_skills)}/{len(criteria_skill_names)} compétences clés ({coverage:.0f}%)."
    else:
        summary = f"{candidate.full_name} ne couvre pas encore les compétences prioritaires du poste."

    return {
        "coverage": coverage,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "skill_breakdown": skill_breakdown,
        "summary": summary,
    }


def _compute_candidate_matches(criteria: JobCriteria, db: Session) -> List[CandidateMatchResponse]:
    from ai_module.matching import CosineScorer

    # Build criteria skills dict from DB
    criteria_skills_db = db.query(CriteriaSkill).filter(CriteriaSkill.criteria_id == criteria.id).all()
    criteria_skills_dict = {cs.skill.name: _normalize_weight(cs.weight) for cs in criteria_skills_db}

    # Build global skill dictionary (all known skills)
    all_skills_objs = db.query(Skill).all()
    all_skills = [s.name for s in all_skills_objs]

    results: List[CandidateMatchResponse] = []

    # Iterate candidates and score them (only fully extracted with valid names)
    candidates = db.query(Candidate).filter(
        ((Candidate.is_fully_extracted == True) | (Candidate.extraction_quality_score >= 80)),
        Candidate.full_name.isnot(None),
        Candidate.full_name != "Unknown",
        Candidate.full_name != "",
        Candidate.raw_text.isnot(None)
    ).all()
    for cand in candidates:
        cand_skills = [cs.skill.name for cs in getattr(cand, "candidate_skills", [])]
        details = CosineScorer.calculate_match_score(cand_skills, criteria_skills_dict, all_skills)
        score = details.get("score", 0.0)

        results.append(CandidateMatchResponse(
            candidate_id=cast(int, cand.id),
            full_name=cast(str, cand.full_name),
            email=cast(str, cand.email),
            match_score=score,
            explanation=str(details.get("skill_breakdown", {}))
        ))

    # Sort descending by score
    results.sort(key=lambda r: r.match_score, reverse=True)
    return results


def calculate_match_score(candidate: Candidate, criteria_skills: List[dict] | Dict[str, int], criteria_job_title: str = "", criteria_companies: Optional[List[str]] = None) -> Tuple[float, Dict]:
    """Wrapper that adapts candidate/criteria structures to the internal scorer."""
    from ai_module.matching import CosineScorer

    # Normalize criteria to dict
    criteria_dict: Dict[str, int] = {}
    if isinstance(criteria_skills, dict):
        criteria_dict = {k: _normalize_weight(v) for k, v in criteria_skills.items()}
    else:
        for item in (criteria_skills or []):
            if isinstance(item, dict):
                name = item.get("name") or item.get("skill")
                weight = item.get("weight", 50)
                if name:
                    criteria_dict[name] = _normalize_weight(weight)

    # Candidate skills extraction
    candidate_skills = []
    try:
        candidate_skills = [cs.skill.name for cs in getattr(candidate, "candidate_skills", [])]
    except Exception:
        if isinstance(candidate, dict):
            candidate_skills = candidate.get("skills", []) or []

    # Build a minimal all_skills list (union of both sets)
    all_skills = list({*candidate_skills, *list(criteria_dict.keys())})

    details = CosineScorer.calculate_match_score(candidate_skills, criteria_dict, all_skills)
    return details.get("score", 0.0), details


def _generate_profile_payload(request: GenerateProfileRequest) -> dict:
    """Generate the ideal profile payload shared by both IA routes."""
    generated_profile: dict = {}

    if PROFILE_GENERATOR_AVAILABLE:
        try:
            generated_profile = ProfileGenerator.generate_from_text(request.description)
        except Exception:
            generated_profile = {}

    if not isinstance(generated_profile, dict):
        generated_profile = {}

    generated_skills = generated_profile.get("ideal_skills") or []
    if not generated_skills and SKILL_EXTRACTOR_AVAILABLE:
        extractor = SkillExtractor()
        extracted = extractor.extract_skills(request.description, threshold=85)
        generated_skills = [{"name": item["name"], "weight": 90, "level": "Advanced"} for item in extracted[:8]]

    if not generated_skills:
        generated_skills = [
            {"name": "Communication", "weight": 80, "level": "Advanced"},
            {"name": "Problem Solving", "weight": 80, "level": "Advanced"},
            {"name": "Team Work", "weight": 70, "level": "Intermediate"},
        ]

    return {
        "title": request.job_title,
        "description": request.description,
        "ideal_skills": generated_skills,
        "ideal_experience_years": generated_profile.get("ideal_experience_years", 5),
        "ideal_education": generated_profile.get("ideal_education", "Bachelor's degree or equivalent"),
        "ideal_languages": generated_profile.get("ideal_languages", []),
        "industries": generated_profile.get("industries", []),
    }



# ============================================================================
# MODE 1: RECHERCHE - Search existing candidates
# ============================================================================

@router.post("/criteria", response_model=JobCriteriaResponse)
async def create_job_criteria(
    criteria: JobCriteriaCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create job criteria for matching
    
    🅰️ MODE 1 (Search): Décrire les besoins, le système cherche dans les candidats
    """
    # Simplified recruiter fallback for MVP
    recruiter_id = 1
    
    # Create criteria
    db_criteria = JobCriteria(
        recruiter_id=recruiter_id,
        title=criteria.title,
        description=criteria.description
    )
    db.add(db_criteria)
    db.flush()
    
    # Persist criteria skills with weights
    _replace_criteria_skills(db, db_criteria.id, criteria.required_skills)
    
    db.commit()
    db.refresh(db_criteria)
    
    return JobCriteriaResponse(
        id=cast(int, db_criteria.id),
        recruiter_id=cast(int, db_criteria.recruiter_id),
        title=cast(str, db_criteria.title),
        description=cast(str, db_criteria.description),
        created_at=cast(datetime, db_criteria.created_at),
        required_skills=criteria.required_skills
    )

 


@router.post("/search/{criteria_id}")
async def search_candidates(
    criteria_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[CandidateMatchResponse]:
    """
    🅰️ MODE 1 - Search candidates matching criteria
    
    Utilise semantic matching pour matcher intelligemment les compétences
    même si les noms ne correspondent pas exactement.
    
    Algorithme:
    1. Récupère tous les candidats
    2. Calcule score de match pour chacun avec embeddings sémantiques
    3. Retourne triés par score (DESC)
    """
    # Get criteria
    criteria = db.query(JobCriteria).filter(JobCriteria.id == criteria_id).first()
    if not criteria:
        raise HTTPException(status_code=404, detail="Criteria not found")
    
    return _compute_candidate_matches(criteria, db)





@router.get("/candidate/{candidate_id}/analysis")
async def get_candidate_match_analysis(
    candidate_id: int,
    criteria_id: int = None,
    db: Session = Depends(get_db)
) -> dict:
    """
    🔄 ÉTAPE 7 - Get detailed match analysis for candidate
    
    Shows:
    - NER-extracted data (companies, job titles, skills)
    - Component scores (skills, experience, companies)
    - Data quality metrics
    - Matching recommendations
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # Get criteria if provided
    criteria_skills_dict = []
    criteria_title = ""
    
    if criteria_id:
        criteria_skills = db.query(CriteriaSkill).filter(
            CriteriaSkill.criteria_id == criteria_id
        ).all()
        criteria_skills_dict = [
            {"name": cs.skill.name, "weight": cs.weight}
            for cs in criteria_skills
        ]
    
    # Calculate match score with enhanced metrics
    score, details = calculate_match_score(
        candidate,
        criteria_skills_dict,
        criteria_job_title=criteria_title
    )
    
    # Build comprehensive response
    import json
    return {
        "candidate": {
            "id": candidate.id,
            "name": candidate.full_name,
            "email": candidate.email,
        },
        "extraction_quality": {
            "overall_score": candidate.extraction_quality_score or 0,
            "fully_extracted": candidate.is_fully_extracted,
            "data_completeness": f"{(candidate.extraction_quality_score or 0):.0f}%"
        },
        "ner_extracted_data": {
            "name": candidate.extracted_name,
            "emails": json.loads(candidate.extracted_emails or "[]"),
            "phones": json.loads(candidate.extracted_phones or "[]"),
            "job_titles": json.loads(candidate.extracted_job_titles or "[]"),
            "companies": json.loads(candidate.extracted_companies or "[]"),
            "education": json.loads(candidate.extracted_education or "[]")
        },
        "matching_analysis": {
            "overall_score": min(100, max(0, score)),
            "component_scores": details.get("component_scores", {}),
            "method": details.get("method", "standard"),
            "data_sources": details.get("data_sources", {}),
            "matched_skills_count": details.get("matched_skills", 0),
            "total_criteria_skills": details.get("total_skills", 0)
        },
        "recommendations": {
            "strengths": _get_strengths(candidate, details),
            "gaps": _get_gaps(candidate, details),
            "priority_match": score >= 75
        }
    }


def _get_strengths(candidate: Candidate, details: Dict) -> List[str]:
    """Extract match strengths"""
    strengths = []
    
    if details.get("component_scores", {}).get("skills", 0) >= 70:
        strengths.append("Strong skill match")
    
    if details.get("component_scores", {}).get("experience_level", 0) >= 80:
        strengths.append("High experience level")
    
    if candidate.extraction_quality_score and candidate.extraction_quality_score >= 70:
        strengths.append("Complete data extraction")
    
    if len(candidate.candidate_skills) >= 15:
        strengths.append("Diverse skill portfolio")
    
    return strengths or ["Potential candidate"]


def _get_gaps(candidate: Candidate, details: Dict) -> List[str]:
    """Extract match gaps"""
    gaps = []
    
    if details.get("component_scores", {}).get("skills", 0) < 50:
        gaps.append("Key skills missing - consider training")
    
    if details.get("component_scores", {}).get("experience_level", 0) < 50:
        gaps.append("Less experience than required")
    
    if not candidate.extracted_job_titles:
        gaps.append("Job title extraction unavailable")
    
    if not candidate.extracted_companies:
        gaps.append("Company background extraction unavailable")
    
    return gaps


@router.post("/calculate/{candidate_id}/{criteria_id}", response_model=MatchResultResponse)
async def calculate_match(
    candidate_id: int,
    criteria_id: int,
    db: Session = Depends(get_db)
):
    """Calculate match score for one candidate and one criteria."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    criteria = db.query(JobCriteria).filter(JobCriteria.id == criteria_id).first()
    if not criteria:
        raise HTTPException(status_code=404, detail="Criteria not found")

    criteria_skills = db.query(CriteriaSkill).filter(
        CriteriaSkill.criteria_id == criteria_id
    ).all()

    criteria_skills_dict = [
        {"name": cs.skill.name, "weight": cs.weight}
        for cs in criteria_skills
    ]

    score, details = calculate_match_score(candidate, criteria_skills_dict)
    explanation = details.get("details") or (
        f"Matched {len([s for s in criteria_skills_dict if s['name'] in [cs.skill.name for cs in candidate.candidate_skills]])} required skills"
        if criteria_skills_dict else "No skills defined for criteria"
    )

    match_result = MatchResult(
        criteria_id=criteria_id,
        candidate_id=candidate_id,
        score=score,
        explanation=explanation
    )
    db.add(match_result)
    db.commit()
    db.refresh(match_result)

    return match_result



# ============================================================================
# MODE 2: GÉNÉRATION - Generate ideal profile and match
# ============================================================================

@router.post("/generate-profile")
async def generate_ideal_profile(
    request: GenerateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    🅱️ MODE 2 - Generate ideal candidate profile from job description
    
    Utilise un générateur de profil local basé sur des règles simples.
    """
    return _generate_profile_payload(request)


class GenerateAndMatchRequest(BaseModel):
    """Request body for generate and match endpoint"""
    job_title: str
    description: str


@router.post("/generate-and-match")
async def generate_and_match(
    request: GenerateAndMatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    🅱️ MODE 2 - Complete workflow:
    1. Generate ideal profile from description
    2. Match against all candidates with semantic matching
    3. Return ranked results
    """
    # Step 1: Generate ideal profile
    generated_profile = _generate_profile_payload(
        GenerateProfileRequest(job_title=request.job_title, description=request.description)
    )

    ideal_skills = generated_profile.get("ideal_skills", [])
    candidates = db.query(Candidate).filter(
        ((Candidate.is_fully_extracted == True) | (Candidate.extraction_quality_score >= 80)),
        Candidate.full_name.isnot(None),
        Candidate.full_name != "Unknown",
        Candidate.full_name != "",
        Candidate.raw_text.isnot(None)
    ).all()

    # Step 2: Match all candidates against generated profile
    matches: List[CandidateMatchResponse] = []
    for candidate in candidates:
        score, details = calculate_match_score(
            candidate,
            ideal_skills,
            criteria_job_title=request.job_title,
            criteria_companies=[]
        )
        matches.append(CandidateMatchResponse(
            candidate_id=candidate.id,
            full_name=candidate.full_name,
            email=candidate.email,
            match_score=score,
            explanation=details.get("details", "")
        ))

    matches.sort(key=lambda m: m.match_score, reverse=True)

    return {
        "ideal_profile": generated_profile,
        "matches": [match.model_dump() for match in matches]
    }


@router.post("/{criteria_id}/results", response_model=List[CriteriaMatchResultResponse])
async def launch_matching_for_criteria(
    criteria_id: int,
    db: Session = Depends(get_db),
):
    criteria = db.query(JobCriteria).filter(JobCriteria.id == criteria_id).first()
    if not criteria:
        raise HTTPException(status_code=404, detail="Criteria not found")

    results = _score_all_candidates(criteria, db)
    stored_results = _persist_match_results(db, criteria_id, results)

    return [_format_stored_result(stored_result) for stored_result in sorted(stored_results, key=lambda item: item.score, reverse=True)]


@router.get("/{criteria_id}/results", response_model=List[CriteriaMatchResultResponse])
async def get_matching_results_for_criteria(
    criteria_id: int,
    db: Session = Depends(get_db),
):
    criteria = db.query(JobCriteria).filter(JobCriteria.id == criteria_id).first()
    if not criteria:
        raise HTTPException(status_code=404, detail="Criteria not found")

    stored_results = db.query(MatchResult).filter(MatchResult.criteria_id == criteria_id).order_by(MatchResult.score.desc(), MatchResult.id.asc()).all()
    if not stored_results:
        stored_results = _persist_match_results(db, criteria_id, _score_all_candidates(criteria, db))

    return [_format_stored_result(result) for result in stored_results]


# ============================================================================
# GET endpoints
# ============================================================================

@router.get("/results", response_model=List[MatchResultResponse])
async def get_match_results(
    criteria_id: Optional[int] = None,
    candidate_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all match results"""
    query = db.query(MatchResult)
    
    if criteria_id is not None:
        query = query.filter(MatchResult.criteria_id == criteria_id)
    if candidate_id is not None:
        query = query.filter(MatchResult.candidate_id == candidate_id)
    
    results = query.offset(skip).limit(limit).all()
    return results


@router.get("/criteria/{criteria_id}", response_model=JobCriteriaResponse)
async def get_criteria(
    criteria_id: int,
    db: Session = Depends(get_db)
):
    """Get criteria details"""
    criteria = db.query(JobCriteria).filter(JobCriteria.id == criteria_id).first()
    if not criteria:
        raise HTTPException(status_code=404, detail="Criteria not found")
    
    return JobCriteriaResponse(
        id=cast(int, criteria.id),
        recruiter_id=cast(int, criteria.recruiter_id),
        title=cast(str, criteria.title),
        description=cast(str, criteria.description),
        created_at=cast(datetime, criteria.created_at)
    )


@router.post("/{criteria_id}/predict", response_model=PredictCriteriaResponse)
async def predict_for_criteria(
    criteria_id: int,
    top_k: int = 20,
    model_type: str = "baseline",
    db: Session = Depends(get_db)
):
    """
    Predict match probabilities for all candidates for a given criteria.
    model_type can be 'baseline' or 'siamese'.
    Returns top_k candidates with predicted score (0-100).
    """
    selected_model_type = model_type.strip().lower()
    if selected_model_type not in {"baseline", "siamese"}:
        raise HTTPException(status_code=400, detail="model_type must be 'baseline' or 'siamese'")

    model = None
    meta: dict = {}

    if selected_model_type == "baseline":
        model_bundle = _load_baseline_model()
        if not model_bundle:
            raise HTTPException(status_code=404, detail="Baseline model not available")
        model = model_bundle.get('model')
        meta = model_bundle.get('meta') or {}
    else:
        model, model_path = _load_siamese_model()
        if model is None:
            raise HTTPException(status_code=404, detail="Siamese model not available")

    criteria = db.query(JobCriteria).filter(JobCriteria.id == criteria_id).first()
    if not criteria:
        raise HTTPException(status_code=404, detail="Criteria not found")

    # Build job_text from criteria
    criteria_skills = db.query(CriteriaSkill).filter(CriteriaSkill.criteria_id == criteria.id).all()
    skill_names = [cs.skill.name for cs in criteria_skills]
    job_text = f"{criteria.title} \n {criteria.description} \n Skills: {'; '.join(skill_names)}"

    candidates = db.query(Candidate).filter(
        ((Candidate.is_fully_extracted == True) | (Candidate.extraction_quality_score >= 80)),
        Candidate.full_name.isnot(None),
        Candidate.full_name != "Unknown",
        Candidate.full_name != "",
        Candidate.raw_text.isnot(None)
    ).all()
    scored: List[Tuple[Candidate, float, Dict[str, object]]] = []

    for cand in candidates:
        # Build candidate text
        try:
            skills = [cs.skill.name for cs in getattr(cand, 'candidate_skills', [])]
        except Exception:
            skills = []

        extracted = []
        try:
            extracted.extend(json.loads(cand.extracted_job_titles or '[]'))
        except Exception:
            pass
        try:
            extracted.extend(json.loads(cand.extracted_companies or '[]'))
        except Exception:
            pass

        candidate_text = f"{cand.full_name or ''} \n {'; '.join(skills)} \n {'; '.join(extracted)}"

        explainability = _build_prediction_explainability(cand, criteria, criteria_skills)

        try:
            if selected_model_type == "baseline":
                X = _build_pair_features_single(candidate_text, job_text, meta)
                prob = None
                try:
                    prob = model.predict_proba(X)[:,1][0]
                except Exception:
                    try:
                        prob = model.decision_function(X)[0]
                        prob = 1 / (1 + np.exp(-prob))
                    except Exception:
                        prob = float(model.predict(X)[0])
                score_pct = float(np.clip(prob * 100, 0, 100))
            else:
                score_pct = _score_with_siamese(model, candidate_text, job_text)
        except Exception:
            score_pct = 0.0

        scored.append((cand, score_pct, explainability))

    scored.sort(key=lambda t: t[1], reverse=True)

    results = []
    for cand, score, explainability in scored[:top_k]:
        results.append({
            'candidate_id': cand.id,
            'full_name': cand.full_name,
            'email': cand.email,
            'predicted_score': score,
            'decision': _decision_from_score(score),
            'coverage': explainability.get('coverage', 0),
            'matched_skills': explainability.get('matched_skills', []),
            'missing_skills': explainability.get('missing_skills', []),
            'skill_breakdown': explainability.get('skill_breakdown', []),
            'summary': explainability.get('summary', ''),
        })

    return {'criteria_id': criteria_id, 'model': selected_model_type, 'top_k': top_k, 'results': results}


# ==================== EXPLICABILITÉ / PHASE 2 ====================

class ExplainabilityRequest(BaseModel):
    """Request for match explanation."""
    candidate_id: int
    job_criteria_id: int


class ExplainabilityResponse(BaseModel):
    """Response with human-readable match explanation."""
    candidate_name: str
    job_title: str
    overall_score: float
    interpretation: str  # 🟢 Strong / 🟡 Moderate / 🔴 Weak
    matching_skills: list[str]
    missing_skills: list[str]
    experience_alignment: str
    key_reason: str
    recommendations: list[str]


@router.post("/match-explanation", response_model=ExplainabilityResponse)
def get_match_explanation(
    request: ExplainabilityRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate human-readable explanation for why a candidate matches (or doesn't match) a job.
    
    Phase 2 Feature: LLM-style explicability for recruiter decision-making.
    """
    # Get candidate
    candidate = db.query(Candidate).filter(Candidate.id == request.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # Get job criteria
    criteria = db.query(JobCriteria).filter(JobCriteria.id == request.job_criteria_id).first()
    if not criteria:
        raise HTTPException(status_code=404, detail="Job criteria not found")
    
    # Score the match
    explainability = build_explanation_payload(candidate, criteria, db)
    match_score = {
        "match_score": explainability.get("score", 0.0) / 100.0,
        "text_similarity": explainability.get("text_similarity", 0.0),
        "skills_match": explainability.get("skills_match_score", 0.0),
    }
    
    matching_skills = explainability.get("matched_skills", [])
    missing_skills = explainability.get("missing_skills", [])
    
    # Generate explanation
    explanation = generate_explanation(
        candidate_name=candidate.full_name,
        job_title=criteria.title,
        match_score=match_score,
        matching_skills=matching_skills,
        missing_skills=missing_skills,
        candidate_years_exp=float(candidate.years_of_experience or 0),
        required_years_exp=float(criteria.years_of_experience_required or 0),
    )
    
    return ExplainabilityResponse(
        candidate_name=explanation.candidate_name,
        job_title=explanation.job_title,
        overall_score=explanation.overall_score,
        interpretation=explanation.interpretation,
        matching_skills=explanation.matching_skills,
        missing_skills=explanation.missing_skills,
        experience_alignment=explanation.experience_alignment,
        key_reason=explanation.key_reason,
        recommendations=explanation.recommendations,
    )


class ShortlistSummaryRequest(BaseModel):
    """Request for shortlist summary."""
    job_criteria_id: int


class ShortlistSummaryResponse(BaseModel):
    """Summary of candidate shortlist."""
    total_candidates_screened: int
    strong_matches: int
    moderate_matches: int
    top_skills_in_pool: list[str]
    recommendations: list[str]


@router.post("/shortlist-summary", response_model=ShortlistSummaryResponse)
def get_shortlist_summary(
    request: ShortlistSummaryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate summary insights for a job's candidate shortlist.
    
    Phase 2 Feature: Strategic recommendations for recruitment workflow.
    """
    # Get job criteria
    criteria = db.query(JobCriteria).filter(JobCriteria.id == request.job_criteria_id).first()
    if not criteria:
        raise HTTPException(status_code=404, detail="Job criteria not found")
    
    # Get all match results for this criteria
    match_results = db.query(MatchResult).filter(MatchResult.criteria_id == request.job_criteria_id).all()
    
    # Build match list
    matches = []
    for result in match_results:
        candidate = db.query(Candidate).filter(Candidate.id == result.candidate_id).first()
        if candidate:
            matches.append({
                "candidate_id": candidate.id,
                "full_name": candidate.full_name,
                "score": result.score / 100.0,
                "matching_skills": result.matched_skills or [],
            })
    
    # Generate summary
    summary = generate_shortlist_summary(matches, criteria.title, top_n=5)
    
    return ShortlistSummaryResponse(
        total_candidates_screened=summary["total_candidates_screened"],
        strong_matches=summary["strong_matches"],
        moderate_matches=summary["moderate_matches"],
        top_skills_in_pool=summary["top_skills_in_pool"],
        recommendations=summary["recommendations"],
    )
