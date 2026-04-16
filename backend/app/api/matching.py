"""
Matching API routes - Recruteur workflow
MODES:
  1️⃣ Mode recherche: Chercher dans candidats existants
  2️⃣ Mode génération profil idéal: Décrire le besoin, l'IA génère le profil
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Tuple, cast
from pydantic import BaseModel
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
    CandidateSkill
)

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


router = APIRouter(prefix="/api/matching", tags=["matching"])


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


# ============================================================================
# HELPERS
# ============================================================================

def _normalize_weight(weight: int) -> int:
    return max(0, min(100, int(weight)))


def _get_or_create_skill(db: Session, skill_name: str) -> Skill:
    normalized_name = skill_name.strip()
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
        if not req_skill.name.strip():
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
        title=criteria.title,
        description=criteria.description,
        created_at=criteria.created_at,
        required_skills=required_skills
    )


def _compute_candidate_matches(criteria: JobCriteria, db: Session) -> List[CandidateMatchResponse]:
    candidates = db.query(Candidate).all()
    criteria_skills = db.query(CriteriaSkill).filter(
        CriteriaSkill.criteria_id == criteria.id
    ).all()

    criteria_skills_dict = [
        {"name": cs.skill.name, "weight": cs.weight}
        for cs in criteria_skills
    ]

    matches: List[CandidateMatchResponse] = []
    for candidate in candidates:
        score, details = calculate_match_score(
            candidate,
            criteria_skills_dict,
            criteria_job_title=criteria.title,
            criteria_companies=[]
        )
        matches.append(CandidateMatchResponse(
            candidate_id=candidate.id,
            full_name=candidate.full_name,
            email=candidate.email,
            match_score=score,
            explanation=details.get("details", "")
        ))

    matches.sort(key=lambda x: x.match_score, reverse=True)
    return matches

def calculate_match_score(
    candidate: Candidate, 
    criteria_skills: List[dict],
    use_semantic_matching: bool = True,
    criteria_job_title: str = "",
    criteria_companies: List[str] = None
) -> Tuple[float, Dict]:
    """
    🔄 ÉTAPE 7 OPTIMISÉE - Calculate match score using NER-extracted data
    
    Enhanced algorithm that considers:
    1. Skill matching (core requirement)
    2. Experience level (job titles extracted)
    3. Industry experience (companies extracted)
    4. Data quality (extraction_quality_score)
    
    Args:
        candidate: Candidate object with NER-extracted fields
        criteria_skills: Required skills with weights
        use_semantic_matching: Enable semantic matching
        criteria_job_title: Target job title  
        criteria_companies: Target industries/companies
    
    Returns:
        (score: 0-100, details: rich matching metrics)
    """
    if not criteria_skills:
        return 50.0, {"details": "No criteria skills", "method": "baseline"}
    
    # ===== COMPONENT 1: SKILL MATCHING =====
    candidate_skill_names = [skill.skill.name for skill in candidate.candidate_skills]
    
    skill_score = 0.0
    total_weight = sum(s.get("weight", 50) for s in criteria_skills)
    matched_skills_count = 0
    
    # Use semantic matching if available
    if use_semantic_matching and SEMANTIC_MATCHER_AVAILABLE:
        try:
            match_result = SemanticSkillMatcher.match_candidate_skills(
                candidate_skills=candidate_skill_names,
                criteria_skills=criteria_skills,
                threshold=0.6
            )
            skill_score = float(match_result["score"])
            matched_skills_count = match_result["total_matches"]
        except Exception:
            # Fall back to exact matching
            use_semantic_matching = False
    
    if not use_semantic_matching or skill_score == 0:
        # Exact matching fallback
        matched_weight = 0.0
        candidate_skills_lower = {s.lower() for s in candidate_skill_names}
        
        for criteria_skill in criteria_skills:
            skill_name = criteria_skill.get("name", "").lower()
            weight = criteria_skill.get("weight", 50)
            
            if skill_name in candidate_skills_lower:
                matched_weight += weight
                matched_skills_count += 1
        
        skill_score = (matched_weight / total_weight * 100) if total_weight > 0 else 50.0
    
    # ===== COMPONENT 2: EXPERIENCE LEVEL (from extracted_job_titles) =====
    experience_score = 50.0  # Default baseline
    
    if candidate.extracted_job_titles:
        import json
        try:
            job_titles = json.loads(candidate.extracted_job_titles)
            titles_lower = [str(t).lower() for t in job_titles] if isinstance(job_titles, list) else []
            
            # Look for seniority indicators
            seniority_keywords = {
                "senior": 90,
                "lead": 85,
                "principal": 95,
                "manager": 80,
                "architect": 90,
                "director": 85,
                "junior": 40,
                "intern": 20,
                "mid": 60,
                "mid-level": 65
            }
            
            for title in titles_lower:
                for keyword, score in seniority_keywords.items():
                    if keyword in title:
                        experience_score = max(experience_score, score)
                        break
        except (json.JSONDecodeError, TypeError):
            pass
    
    # ===== COMPONENT 3: INDUSTRY/COMPANY RELEVANCE =====
    company_relevance_score = 50.0  # Default baseline
    
    if criteria_companies and candidate.extracted_companies:
        import json
        try:
            candidate_companies = json.loads(candidate.extracted_companies)
            companies_lower = [str(c).lower() for c in candidate_companies] if isinstance(candidate_companies, list) else []
            criteria_companies_lower = [c.lower() for c in criteria_companies]
            
            # Check for industry overlap
            matching_companies = sum(1 for cc in companies_lower for sc in criteria_companies_lower if cc in sc or sc in cc)
            
            company_relevance_score = min(100, 50 + (matching_companies * 15))
        except (json.JSONDecodeError, TypeError):
            pass
    
    # ===== COMPONENT 4: DATA QUALITY BOOSTING =====
    quality_boost = 1.0
    if candidate.extraction_quality_score and candidate.extraction_quality_score > 0:
        # High quality extractions get a boost (up to 10%)
        quality_boost = 1.0 + (candidate.extraction_quality_score / 1000.0)
    
    # ===== FINAL SCORE CALCULATION =====
    # Weights: skills (50%), experience (25%), company (15%), data quality (10%)
    final_score = (
        skill_score * 0.50 +
        experience_score * 0.25 +
        company_relevance_score * 0.15
    ) * quality_boost
    
    final_score = min(100.0, max(0.0, final_score))
    
    return final_score, {
        "method": "ner_enhanced" if candidate.is_fully_extracted else "standard",
        "component_scores": {
            "skills": min(100, skill_score),
            "experience_level": experience_score,
            "company_relevance": company_relevance_score,
            "data_quality_boost": (quality_boost - 1.0) * 100
        },
        "matched_skills": matched_skills_count,
        "total_skills": len(criteria_skills),
        "extraction_quality": candidate.extraction_quality_score or 0,
        "fully_extracted": candidate.is_fully_extracted,
        "data_sources": {
            "skills_from": "database_linked" if candidate.candidate_skills else "none",
            "experience_from": "ner_extracted" if candidate.extracted_job_titles else "none",
            "companies_from": "ner_extracted" if candidate.extracted_companies else "none"
        }
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


@router.get("/{criteria_id}", response_model=JobCriteriaResponse)
async def get_criteria_canonical(
    criteria_id: int,
    db: Session = Depends(get_db)
):
    """Canonical Step 7 endpoint for criteria detail."""
    criteria = db.query(JobCriteria).filter(JobCriteria.id == criteria_id).first()
    if not criteria:
        raise HTTPException(status_code=404, detail="Criteria not found")
    return _build_criteria_response(criteria, db)


@router.post("/{criteria_id}/results", response_model=List[MatchResultResponse])
async def compute_and_store_match_results(
    criteria_id: int,
    db: Session = Depends(get_db)
):
    """Canonical Step 7 endpoint to compute and persist match results."""
    criteria = db.query(JobCriteria).filter(JobCriteria.id == criteria_id).first()
    if not criteria:
        raise HTTPException(status_code=404, detail="Criteria not found")

    matches = _compute_candidate_matches(criteria, db)

    db.query(MatchResult).filter(MatchResult.criteria_id == criteria_id).delete()
    for match in matches:
        db.add(MatchResult(
            criteria_id=criteria_id,
            candidate_id=match.candidate_id,
            score=match.match_score,
            explanation=match.explanation
        ))

    db.commit()

    stored_results = db.query(MatchResult).filter(
        MatchResult.criteria_id == criteria_id
    ).order_by(MatchResult.score.desc()).all()
    return stored_results


@router.get("/{criteria_id}/results", response_model=List[MatchResultResponse])
async def list_stored_results_for_criteria(
    criteria_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    criteria = db.query(JobCriteria).filter(JobCriteria.id == criteria_id).first()
    if not criteria:
        raise HTTPException(status_code=404, detail="Criteria not found")

    return db.query(MatchResult).filter(
        MatchResult.criteria_id == criteria_id
    ).order_by(MatchResult.score.desc()).offset(skip).limit(limit).all()


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
        
        # Now returns tuple (score, details)
        score, details = calculate_match_score(candidate, criteria_skills_dict)
        
        matches.append(CandidateMatchResponse(
            candidate_id=cast(int, candidate.id),
            full_name=cast(str, candidate.full_name),
            email=cast(str, candidate.email),
            match_score=score,
            explanation=details.get("details", "")
        ))
    
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

    score = calculate_match_score(candidate, criteria_skills_dict)
    explanation = (
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


@router.get("/{criteria_id}/results", response_model=List[MatchResultResponse])
async def get_criteria_results(
    criteria_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all match results for a specific criteria."""
    results = db.query(MatchResult).filter(
        MatchResult.criteria_id == criteria_id
    ).offset(skip).limit(limit).all()
    return results


# ============================================================================
# MODE 2: GÉNÉRATION - Generate ideal profile and match
# ============================================================================

@router.post("/generate-profile")
async def generate_ideal_profile(
    request: GenerateProfileRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    🅱️ MODE 2 - Generate ideal candidate profile from job description
    
    Utilise un générateur de profil local basé sur des règles simples.
    """
    # Return a simple profile structure without blocking calls
    generated_skills = []

    if SKILL_EXTRACTOR_AVAILABLE:
        extractor = SkillExtractor()
        extracted = extractor.extract_skills(request.description, threshold=85)
        generated_skills = [
            {"name": item["name"], "weight": 90, "level": "Advanced"}
            for item in extracted[:8]
        ]

    if not generated_skills:
        generated_skills = [
            {"name": "Communication", "weight": 80, "level": "Advanced"},
            {"name": "Problem Solving", "weight": 80, "level": "Advanced"},
            {"name": "Team Work", "weight": 70, "level": "Intermediate"}
        ]

    return {
        "title": request.job_title,
        "description": request.description,
        "ideal_skills": generated_skills,
        "ideal_experience_years": 5,
        "ideal_education": "Bachelor's degree or equivalent",
        "industries": []
    }


class GenerateAndMatchRequest(BaseModel):
    """Request body for generate and match endpoint"""
    job_title: str
    description: str


@router.post("/generate-and-match")
async def generate_and_match(
    request: GenerateAndMatchRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    🅱️ MODE 2 - Complete workflow:
    1. Generate ideal profile from description
    2. Match against all candidates with semantic matching
    3. Return ranked results
    """
    # Step 1: Generate ideal profile
    generated_profile = await generate_ideal_profile(
        GenerateProfileRequest(job_title=request.job_title, description=request.description),
        db
    )

    ideal_skills = generated_profile.get("ideal_skills", [])
    candidates = db.query(Candidate).all()

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
