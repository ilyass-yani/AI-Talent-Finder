"""Job Criteria API routes - ÉTAPE 2 COMPLÉTION"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.dependencies import get_db, get_current_user
from app.models.models import JobCriteria, CriteriaSkill, Skill, User, UserRole
from app.schemas.job_criteria import (
    JobCriteriaResponse, 
    JobCriteriaCreate, 
    JobCriteriaUpdate,
    CriteriaSkillResponse,
    CriteriaSkillCreate
)

router = APIRouter(prefix="/api/jobs", tags=["job-criteria"])


@router.get("/", response_model=List[JobCriteriaResponse])
def list_job_criteria(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all job criteria for current recruiter"""
    # Recruiter sees only their own criteria
    if current_user.role == UserRole.admin:
        # Admin sees all
        criteria = db.query(JobCriteria).offset(skip).limit(limit).all()
    else:
        # Others see only their own
        criteria = db.query(JobCriteria).filter(
            JobCriteria.recruiter_id == current_user.id
        ).offset(skip).limit(limit).all()
    
    return criteria


@router.get("/{criteria_id}", response_model=JobCriteriaResponse)
def get_job_criteria(
    criteria_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific job criteria by ID"""
    criteria = db.query(JobCriteria).filter(JobCriteria.id == criteria_id).first()
    
    if not criteria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job criteria not found"
        )
    
    # Check authorization
    if criteria.recruiter_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this criteria"
        )
    
    return criteria


@router.post("/", response_model=JobCriteriaResponse, status_code=status.HTTP_201_CREATED)
def create_job_criteria(
    job_criteria: JobCriteriaCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new job criteria (recruiter only)"""
    # Only recruiters can create criteria
    if current_user.role not in [UserRole.recruiter, UserRole.admin]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only recruiters can create criteria"
        )
    
    # Create criteria
    db_criteria = JobCriteria(
        recruiter_id=current_user.id,
        title=job_criteria.title,
        description=job_criteria.description
    )
    db.add(db_criteria)
    db.flush()  # Flush to get the ID before adding skills
    
    # Add criteria skills if provided
    for skill_data in job_criteria.criteria_skills:
        # Verify skill exists
        skill = db.query(Skill).filter(Skill.id == skill_data.skill_id).first()
        if not skill:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skill {skill_data.skill_id} not found"
            )
        
        db_criteria_skill = CriteriaSkill(
            criteria_id=db_criteria.id,
            skill_id=skill_data.skill_id,
            weight=skill_data.weight
        )
        db.add(db_criteria_skill)
    
    db.commit()
    db.refresh(db_criteria)
    return db_criteria


@router.put("/{criteria_id}", response_model=JobCriteriaResponse)
def update_job_criteria(
    criteria_id: int,
    job_criteria: JobCriteriaUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a job criteria"""
    db_criteria = db.query(JobCriteria).filter(JobCriteria.id == criteria_id).first()
    
    if not db_criteria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job criteria not found"
        )
    
    # Check authorization
    if db_criteria.recruiter_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this criteria"
        )
    
    # Update only provided fields
    update_data = job_criteria.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_criteria, key, value)
    
    db.commit()
    db.refresh(db_criteria)
    return db_criteria


@router.delete("/{criteria_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job_criteria(
    criteria_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a job criteria"""
    db_criteria = db.query(JobCriteria).filter(JobCriteria.id == criteria_id).first()
    
    if not db_criteria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job criteria not found"
        )
    
    # Check authorization
    if db_criteria.recruiter_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this criteria"
        )
    
    db.delete(db_criteria)
    db.commit()


# ============================================================================
# CRITERIA SKILLS ENDPOINTS
# ============================================================================

@router.post("/{criteria_id}/skills", response_model=CriteriaSkillResponse, status_code=status.HTTP_201_CREATED)
def add_criteria_skill(
    criteria_id: int,
    criteria_skill: CriteriaSkillCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a skill to a job criteria"""
    db_criteria = db.query(JobCriteria).filter(JobCriteria.id == criteria_id).first()
    
    if not db_criteria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job criteria not found"
        )
    
    # Check authorization
    if db_criteria.recruiter_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    # Verify skill exists
    skill = db.query(Skill).filter(Skill.id == criteria_skill.skill_id).first()
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found"
        )
    
    # Check if already exists
    existing = db.query(CriteriaSkill).filter(
        CriteriaSkill.criteria_id == criteria_id,
        CriteriaSkill.skill_id == criteria_skill.skill_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Skill already added to criteria"
        )
    
    db_criteria_skill = CriteriaSkill(
        criteria_id=criteria_id,
        skill_id=criteria_skill.skill_id,
        weight=criteria_skill.weight
    )
    db.add(db_criteria_skill)
    db.commit()
    db.refresh(db_criteria_skill)
    return db_criteria_skill


@router.delete("/{criteria_id}/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_criteria_skill(
    criteria_id: int,
    skill_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a skill from a job criteria"""
    db_criteria = db.query(JobCriteria).filter(JobCriteria.id == criteria_id).first()
    
    if not db_criteria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job criteria not found"
        )
    
    # Check authorization
    if db_criteria.recruiter_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    db_criteria_skill = db.query(CriteriaSkill).filter(
        CriteriaSkill.criteria_id == criteria_id,
        CriteriaSkill.skill_id == skill_id
    ).first()
    
    if not db_criteria_skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found in criteria"
        )
    
    db.delete(db_criteria_skill)
    db.commit()
