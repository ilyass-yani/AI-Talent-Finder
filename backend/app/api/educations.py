"""Educations API routes - ÉTAPE 2 COMPLÉTION"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.dependencies import get_db, get_current_user
from app.models.models import Education, Candidate, User
from app.schemas.education import EducationResponse, EducationCreate, EducationUpdate

router = APIRouter(prefix="/api/candidates/{candidate_id}/educations", tags=["educations"])


@router.get("/", response_model=List[EducationResponse])
def list_educations(
    candidate_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all educations for a candidate"""
    # Verify candidate exists
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    educations = db.query(Education).filter(
        Education.candidate_id == candidate_id
    ).offset(skip).limit(limit).all()
    return educations


@router.get("/{education_id}", response_model=EducationResponse)
def get_education(
    candidate_id: int,
    education_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific education"""
    education = db.query(Education).filter(
        Education.id == education_id,
        Education.candidate_id == candidate_id
    ).first()
    
    if not education:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Education not found"
        )
    return education


@router.post("/", response_model=EducationResponse, status_code=status.HTTP_201_CREATED)
def create_education(
    candidate_id: int,
    education: EducationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new education for a candidate"""
    # Verify candidate exists
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    db_education = Education(
        candidate_id=candidate_id,
        degree=education.degree,
        institution=education.institution,
        field=education.field,
        year=education.year
    )
    db.add(db_education)
    db.commit()
    db.refresh(db_education)
    return db_education


@router.put("/{education_id}", response_model=EducationResponse)
def update_education(
    candidate_id: int,
    education_id: int,
    education: EducationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an education"""
    db_education = db.query(Education).filter(
        Education.id == education_id,
        Education.candidate_id == candidate_id
    ).first()
    
    if not db_education:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Education not found"
        )
    
    # Update only provided fields
    update_data = education.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_education, key, value)
    
    db.commit()
    db.refresh(db_education)
    return db_education


@router.delete("/{education_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_education(
    candidate_id: int,
    education_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an education"""
    db_education = db.query(Education).filter(
        Education.id == education_id,
        Education.candidate_id == candidate_id
    ).first()
    
    if not db_education:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Education not found"
        )
    
    db.delete(db_education)
    db.commit()
