"""Favorites API routes - ÉTAPE 2 COMPLÉTION"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.dependencies import get_db, get_current_user
from app.models.models import Favorite, User, Candidate
from app.schemas.favorite import FavoriteResponse, FavoriteCreate

router = APIRouter(prefix="/api/favorites", tags=["favorites"])


@router.post("/{candidate_id}", response_model=FavoriteResponse, status_code=status.HTTP_201_CREATED)
def add_favorite(
    candidate_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a candidate to favorites (recruiter only)"""
    # Verify candidate exists
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    # Check if already in favorites
    existing = db.query(Favorite).filter(
        Favorite.recruiter_id == current_user.id,
        Favorite.candidate_id == candidate_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Candidate already in favorites"
        )
    
    db_favorite = Favorite(
        recruiter_id=current_user.id,
        candidate_id=candidate_id
    )
    db.add(db_favorite)
    db.commit()
    db.refresh(db_favorite)
    return db_favorite


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(
    candidate_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a candidate from favorites"""
    favorite = db.query(Favorite).filter(
        Favorite.recruiter_id == current_user.id,
        Favorite.candidate_id == candidate_id
    ).first()
    
    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favorite not found"
        )
    
    db.delete(favorite)
    db.commit()


@router.get("/", response_model=List[FavoriteResponse])
def list_favorites(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all favorites for current recruiter"""
    favorites = db.query(Favorite).filter(
        Favorite.recruiter_id == current_user.id
    ).offset(skip).limit(limit).all()
    return favorites
