"""
Matching API routes - Recruteur workflow
MODES:
  1️⃣ Mode recherche: Chercher dans candidats existants
  2️⃣ Mode génération profil idéal: Décrire le besoin, l'IA génère le profil
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Tuple
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

from app.core.dependencies import get_db
from app.models.models import (
    JobCriteria, 
    MatchResult, 
    Candidate, 
    User,
    CriteriaSkill,
    Skill,
    CandidateSkill,
    SkillCategory,
)
from ai_module.nlp.profile_generator import ProfileGenerator
from ai_module.matching.semantic_matcher import SemanticSkillMatcher


router = APIRouter(prefix="/api/matching", tags=["matching"])


# ============================================================================
# SCHEMAS
# ============================================================================

class MatchingMode(str, Enum):
    search = "search"  # Mode 1: Chercher dans la base
    generate = "generate"  # Mode 2: Générer profil idéal


class JobCriteriaCreate(BaseModel):
    """Create job criteria for matching"""
    title: str  # e.g., "Senior Python Developer"
    description: str  # Job description
    mode: MatchingMode = MatchingMode.search
    required_skills: List[dict] = Field(default_factory=list)  # [{"name": "Python", "weight": 100}, ...]


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


# ============================================================================
# HELPERS
# ============================================================================

def calculate_match_score(
    candidate: Candidate, 
    criteria_skills: List[dict],
    use_semantic_matching: bool = True
) -> Tuple[float, Dict]:
    """
    Calculate match score between candidate and job criteria.
    
    Uses semantic matching with all-MiniLM-L6-v2 embeddings to intelligently
    match skills even when names don't match exactly.
    
    Args:
        candidate: Candidate object
        criteria_skills: List of required skills [{"name": "Python", "weight": 100}, ...]
        use_semantic_matching: Use semantic embeddings for matching (default: True)
    
    Returns:
        Tuple of (score: float 0-100, details: dict with matching info)
    """
    if not criteria_skills:
        return 50.0, {"details": "No criteria skills"}  # Default score if no criteria
    
    # Get candidate's skills
    candidate_skill_names = [skill.skill.name for skill in candidate.candidate_skills]
    
    # Use semantic matching if enabled
    if use_semantic_matching:
        match_result = SemanticSkillMatcher.match_candidate_skills(
            candidate_skills=candidate_skill_names,
            criteria_skills=criteria_skills,
            threshold=0.6  # 60% similarity threshold
        )
        
        return float(match_result["score"]), {
            "matched_skills": match_result["matched_skills"],
            "total_matches": match_result["total_matches"],
            "total_criteria": match_result["total_criteria"],
            "details": match_result["details"],
            "method": "semantic"
        }
    
    # Fallback to exact matching
    matched_skills = 0
    total_weight = sum(s.get("weight", 50) for s in criteria_skills)
    candidate_skills_lower = {s.lower() for s in candidate_skill_names}
    
    for criteria_skill in criteria_skills:
        skill_name = criteria_skill.get("name", "").lower()
        weight = criteria_skill.get("weight", 50)
        
        if skill_name in candidate_skills_lower:
            matched_skills += weight
    
    score = (matched_skills / total_weight * 100) if total_weight > 0 else 50.0
    
    return min(100.0, max(0.0, score)), {
        "method": "exact_match",
        "details": f"Matched {matched_skills}/{total_weight} weight"
    }


# ============================================================================
# MODE 1: RECHERCHE - Search existing candidates
# ============================================================================

@router.post("/criteria", response_model=JobCriteriaResponse)
async def create_job_criteria(
    criteria: JobCriteriaCreate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Create job criteria for matching
    
    🅰️ MODE 1 (Search): Décrire les besoins, le système cherche dans les candidats
    """
    # Simplified - in real app, decode token to get recruiter_id
    recruiter_id = 1
    
    # Create criteria
    db_criteria = JobCriteria(
        recruiter_id=recruiter_id,
        title=criteria.title,
        description=criteria.description
    )
    db.add(db_criteria)
    db.flush()

    # Persist required skills for downstream matching.
    persisted_required_skills: List[dict] = []
    for raw_skill in criteria.required_skills:
        skill_name = (raw_skill.get("name") or "").strip()
        if not skill_name:
            continue

        raw_weight = raw_skill.get("weight", 50)
        try:
            weight = int(raw_weight)
        except (TypeError, ValueError):
            weight = 50
        weight = max(0, min(100, weight))

        skill = (
            db.query(Skill)
            .filter(func.lower(Skill.name) == skill_name.lower())
            .first()
        )
        if not skill:
            skill = Skill(name=skill_name, category=SkillCategory.TECHNICAL)
            db.add(skill)
            db.flush()

        db.add(
            CriteriaSkill(
                criteria_id=db_criteria.id,
                skill_id=skill.id,
                weight=weight,
            )
        )

        persisted_required_skills.append({"name": skill.name, "weight": weight})
    
    db.commit()
    db.refresh(db_criteria)
    
    return JobCriteriaResponse(
        id=db_criteria.id,
        recruiter_id=db_criteria.recruiter_id,
        title=db_criteria.title,
        description=db_criteria.description,
        created_at=db_criteria.created_at,
        required_skills=persisted_required_skills
    )


@router.post("/search/{criteria_id}")
async def search_candidates(
    criteria_id: int,
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
    
    # Get all candidates
    candidates = db.query(Candidate).all()

    # Load criteria skills once.
    criteria_skills = db.query(CriteriaSkill).filter(
        CriteriaSkill.criteria_id == criteria_id
    ).all()
    criteria_skills_dict = [
        {"name": cs.skill.name, "weight": cs.weight}
        for cs in criteria_skills
    ]
    
    # Calculate match scores
    matches = []
    for candidate in candidates:
        # Now returns tuple (score, details)
        score, details = calculate_match_score(candidate, criteria_skills_dict)
        
        matches.append(CandidateMatchResponse(
            candidate_id=candidate.id,
            full_name=candidate.full_name or f"Candidate #{candidate.id}",
            email=candidate.email or "",
            match_score=score,
            explanation=details.get("details", "")
        ))
    
    # Sort by score DESC
    matches.sort(key=lambda x: x.match_score, reverse=True)
    
    return matches


# ============================================================================
# MODE 2: GÉNÉRATION - Generate ideal profile and match
# ============================================================================

@router.post("/generate-profile")
async def generate_ideal_profile(
    job_title: str,
    description: str,
    db: Session = Depends(get_db)
) -> dict:
    """
    🅱️ MODE 2 - Generate ideal candidate profile from job description
    
    Utilise un générateur de profil local basé sur des règles simples.
    """
    ideal_profile = ProfileGenerator.generate_from_text(description)
    ideal_profile["title"] = job_title
    ideal_profile["description"] = description
    return ideal_profile


@router.post("/generate-and-match")
async def generate_and_match(
    job_title: str,
    description: str,
    db: Session = Depends(get_db)
) -> dict:
    """
    🅱️ MODE 2 - Complete workflow:
    1. Generate ideal profile from description
    2. Match against all candidates with semantic matching
    3. Return ranked results
    """
    # Step 1: Generate ideal profile
    ideal_profile = await generate_ideal_profile(job_title, description, db)
    
    # Step 2: Match all candidates against ideal profile
    candidates = db.query(Candidate).all()
    matches = []
    
    for candidate in candidates:
        score, details = calculate_match_score(
            candidate, 
            ideal_profile.get("ideal_skills", [])
        )
        
        matches.append({
            "candidate_id": candidate.id,
            "full_name": candidate.full_name,
            "email": candidate.email,
            "match_score": score,
            "matching_details": details,
            "gap_analysis": f"Missing: Docker, Additional: {len(candidate.experiences)} years experience"
        })
    
    # Sort by score
    matches.sort(key=lambda x: x["match_score"], reverse=True)
    
    return {
        "ideal_profile": ideal_profile,
        "matches": matches[:10]  # Top 10
    }


# ============================================================================
# GET endpoints
# ============================================================================

@router.get("/results", response_model=List[MatchResultResponse])
async def get_match_results(
    criteria_id: int = None,
    candidate_id: int = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all match results"""
    query = db.query(MatchResult)
    
    if criteria_id:
        query = query.filter(MatchResult.criteria_id == criteria_id)
    if candidate_id:
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

    required_skills = [
        {"name": cs.skill.name, "weight": cs.weight}
        for cs in criteria.criteria_skills
    ]
    
    return JobCriteriaResponse(
        id=criteria.id,
        recruiter_id=criteria.recruiter_id,
        title=criteria.title,
        description=criteria.description,
        created_at=criteria.created_at,
        required_skills=required_skills,
    )
