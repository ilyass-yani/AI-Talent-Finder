"""Experiences API routes - ÉTAPE 2 COMPLÉTION"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.dependencies import get_db, get_current_user
from app.models.models import Experience, Candidate, User
from app.schemas.experience import ExperienceResponse, ExperienceCreate, ExperienceUpdate

router = APIRouter(prefix="/api/candidates/{candidate_id}/experiences", tags=["experiences"])


@router.get("/", response_model=List[ExperienceResponse])
def list_experiences(
    candidate_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all experiences for a candidate"""
    # Verify candidate exists
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    experiences = db.query(Experience).filter(
        Experience.candidate_id == candidate_id
    ).offset(skip).limit(limit).all()
    return experiences


@router.get("/{experience_id}", response_model=ExperienceResponse)
def get_experience(
    candidate_id: int,
    experience_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific experience"""
    experience = db.query(Experience).filter(
        Experience.id == experience_id,
        Experience.candidate_id == candidate_id
    ).first()
    
    if not experience:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experience not found"
        )
    return experience


@router.post("/", response_model=ExperienceResponse, status_code=status.HTTP_201_CREATED)
def create_experience(
    candidate_id: int,
    experience: ExperienceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new experience for a candidate"""
    # Verify candidate exists
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    db_experience = Experience(
        candidate_id=candidate_id,
        title=experience.title,
        company=experience.company,
        duration_months=experience.duration_months,
        description=experience.description
    )
    db.add(db_experience)
    db.commit()
    db.refresh(db_experience)
    return db_experience


@router.put("/{experience_id}", response_model=ExperienceResponse)
def update_experience(
    candidate_id: int,
    experience_id: int,
    experience: ExperienceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an experience"""
    db_experience = db.query(Experience).filter(
        Experience.id == experience_id,
        Experience.candidate_id == candidate_id
    ).first()
    
    if not db_experience:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experience not found"
        )
    
    # Update only provided fields
    update_data = experience.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_experience, key, value)
    
    db.commit()
    db.refresh(db_experience)
    return db_experience


@router.delete("/{experience_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_experience(
    candidate_id: int,
    experience_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an experience"""
    db_experience = db.query(Experience).filter(
        Experience.id == experience_id,
        Experience.candidate_id == candidate_id
    ).first()
    
    if not db_experience:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experience not found"
        )
    
    db.delete(db_experience)
    db.commit()
