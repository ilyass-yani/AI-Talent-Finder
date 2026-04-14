"""Candidates API routes ETAPES 5"""
import os
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional, cast

from app.core.dependencies import get_db, get_current_user
from app.models.models import Candidate, User, UserRole
from app.schemas.candidate import CandidateResponse, CandidateCreate, CandidateUpdate
from app.services.cv_extractor import extract_text_from_pdf

router = APIRouter(prefix="/api/candidates", tags=["candidates"])



@router.get("/", response_model=List[CandidateResponse])
def get_candidates(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all candidates"""
    candidates = db.query(Candidate).offset(skip).limit(limit).all()
    return candidates


@router.get("/{candidate_id}", response_model=CandidateResponse)
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific candidate by ID"""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    return candidate


@router.post("/", response_model=CandidateResponse)
def create_candidate(
    candidate: CandidateCreate,
    db: Session = Depends(get_db)
):
    """Create a new candidate"""
    db_candidate = Candidate(
        full_name=candidate.full_name,
        email=candidate.email,
        phone=candidate.phone,
        linkedin_url=candidate.linkedin_url,
        github_url=candidate.github_url,
        cv_path=candidate.cv_path,
        raw_text=candidate.raw_text
    )
    db.add(db_candidate)
    db.commit()
    db.refresh(db_candidate)
    return db_candidate


@router.put("/{candidate_id}", response_model=CandidateResponse)
def update_candidate(
    candidate_id: int,
    candidate: CandidateUpdate,
    db: Session = Depends(get_db)
):
    """Update a candidate"""
    db_candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not db_candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    # Update only provided fields
    update_data = candidate.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_candidate, key, value)
    
    db.commit()
    db.refresh(db_candidate)
    return db_candidate


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(
    candidate_id: int,
    db: Session = Depends(get_db)
):
    """Delete a candidate"""
    db_candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not db_candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    db.delete(db_candidate)
    db.commit()
    return None


# ===== Endpoints for authenticated candidate users =====

@router.get("/me/profile", response_model=CandidateResponse)
def get_my_candidate_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get my candidate profile (authenticated candidate only)"""
    current_user_role = cast(UserRole, current_user.role)
    if current_user_role != UserRole.candidate:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only candidates can access this endpoint"
        )
    
    # Get or create candidate profile for this user
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found. Please create your profile first."
        )
    
    return candidate


@router.post("/me/profile", response_model=CandidateResponse)
def create_or_update_my_profile(
    candidate_data: CandidateUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create or update my candidate profile (authenticated candidate only)"""
    current_user_role = cast(UserRole, current_user.role)
    if current_user_role != UserRole.candidate:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only candidates can access this endpoint"
        )
    
    # Check if candidate already exists for this user
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    
    if candidate:
        # Update existing profile
        update_data = candidate_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(candidate, key, value)
    else:
        # Create new profile
        candidate = Candidate(
            user_id=current_user.id,
            full_name=candidate_data.full_name or current_user.full_name,
            email=candidate_data.email or current_user.email,
            phone=candidate_data.phone,
            linkedin_url=candidate_data.linkedin_url,
            github_url=candidate_data.github_url,
            cv_path=candidate_data.cv_path,
            raw_text=candidate_data.raw_text
        )
        db.add(candidate)
    
    db.commit()
    db.refresh(candidate)
    return candidate


@router.post("/upload")
async def upload_candidate_cv(
    file: UploadFile = File(...),
    full_name: str = "",
    email: str = "",
    db: Session = Depends(get_db)
):
    """Upload a candidate CV file"""
    file_content_type = file.content_type or ""
    file_name = file.filename or ""
    if file_content_type != "application/pdf" and not file_name.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported"
        )

    contents = await file.read()
    max_size_bytes = 5 * 1024 * 1024
    if len(contents) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 5 MB limit"
        )

    upload_dir = Path(__file__).parent.parent.parent / "uploads" / "cvs"
    upload_dir.mkdir(parents=True, exist_ok=True)

    unique_filename = f"{uuid.uuid4()}.pdf"
    file_path = upload_dir / unique_filename
    file_path.write_bytes(contents)

    try:
        raw_text = extract_text_from_pdf(str(file_path))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting text from PDF: {str(e)}"
        )

    db_candidate = Candidate(
        full_name=full_name or "Unknown",
        email=email or f"candidate-{unique_filename}@example.com",
        phone=None,
        linkedin_url=None,
        github_url=None,
        cv_path=str(file_path.relative_to(Path(__file__).parent.parent.parent)),
        raw_text=raw_text
    )
    db.add(db_candidate)
    db.commit()
    db.refresh(db_candidate)

    return {
        "message": "File uploaded successfully",
        "candidate_id": db_candidate.id,
        "filename": unique_filename,
        "cv_path": db_candidate.cv_path,
        "raw_text": raw_text
    }


@router.get("/{candidate_id}/cv")
def download_candidate_cv(
    candidate_id: int,
    db: Session = Depends(get_db)
):
    """Download the original CV PDF for a candidate"""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )

    cv_path = cast(Optional[str], candidate.cv_path)
    if not cv_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No CV file associated with this candidate"
        )

    file_path = Path(__file__).parent.parent.parent / cv_path
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV file not found on server"
        )

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=file_path.name
    )
