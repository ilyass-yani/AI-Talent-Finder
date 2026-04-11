"""Match Results API routes - ÉTAPE 2 COMPLÉTION"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.dependencies import get_db, get_current_user
from app.models.models import MatchResult, JobCriteria, User, UserRole
from app.schemas.match_result import MatchResultResponse, MatchResultCreate, MatchResultUpdate

router = APIRouter(prefix="/api/matching/{criteria_id}/results", tags=["match-results"])


@router.get("/", response_model=List[MatchResultResponse])
def list_match_results(
    criteria_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all match results for a criteria"""
    # Verify criteria exists and user has access
    criteria = db.query(JobCriteria).filter(JobCriteria.id == criteria_id).first()
    
    if not criteria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job criteria not found"
        )
    
    if criteria.recruiter_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view these results"
        )
    
    results = db.query(MatchResult).filter(
        MatchResult.criteria_id == criteria_id
    ).order_by(MatchResult.score.desc()).offset(skip).limit(limit).all()
    
    return results


@router.get("/{match_id}", response_model=MatchResultResponse)
def get_match_result(
    criteria_id: int,
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific match result"""
    # Verify criteria exists and user has access
    criteria = db.query(JobCriteria).filter(JobCriteria.id == criteria_id).first()
    
    if not criteria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job criteria not found"
        )
    
    if criteria.recruiter_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    result = db.query(MatchResult).filter(
        MatchResult.id == match_id,
        MatchResult.criteria_id == criteria_id
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match result not found"
        )
    
    return result


@router.post("/", response_model=MatchResultResponse, status_code=status.HTTP_201_CREATED)
def create_match_result(
    criteria_id: int,
    match_result: MatchResultCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create/store a match result"""
    # Verify criteria exists and user has access
    criteria = db.query(JobCriteria).filter(JobCriteria.id == criteria_id).first()
    
    if not criteria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job criteria not found"
        )
    
    if criteria.recruiter_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    # Check if result already exists
    existing = db.query(MatchResult).filter(
        MatchResult.criteria_id == criteria_id,
        MatchResult.candidate_id == match_result.candidate_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Match result already exists for this candidate"
        )
    
    db_result = MatchResult(
        criteria_id=criteria_id,
        candidate_id=match_result.candidate_id,
        score=match_result.score,
        explanation=match_result.explanation
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result


@router.put("/{match_id}", response_model=MatchResultResponse)
def update_match_result(
    criteria_id: int,
    match_id: int,
    match_result: MatchResultUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a match result"""
    # Verify criteria exists and user has access
    criteria = db.query(JobCriteria).filter(JobCriteria.id == criteria_id).first()
    
    if not criteria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job criteria not found"
        )
    
    if criteria.recruiter_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    db_result = db.query(MatchResult).filter(
        MatchResult.id == match_id,
        MatchResult.criteria_id == criteria_id
    ).first()
    
    if not db_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match result not found"
        )
    
    # Update only provided fields
    update_data = match_result.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_result, key, value)
    
    db.commit()
    db.refresh(db_result)
    return db_result


@router.delete("/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_match_result(
    criteria_id: int,
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a match result"""
    # Verify criteria exists and user has access
    criteria = db.query(JobCriteria).filter(JobCriteria.id == criteria_id).first()
    
    if not criteria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job criteria not found"
        )
    
    if criteria.recruiter_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    db_result = db.query(MatchResult).filter(
        MatchResult.id == match_id,
        MatchResult.criteria_id == criteria_id
    ).first()
    
    if not db_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match result not found"
        )
    
    db.delete(db_result)
    db.commit()
