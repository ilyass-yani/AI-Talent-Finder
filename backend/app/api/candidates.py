"""Candidates API routes ETAPES 5"""
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, cast

from app.core.dependencies import get_db, get_current_user
from app.models.models import Candidate, User, UserRole
from app.schemas.candidate import CandidateResponse, CandidateCreate, CandidateUpdate
from app.services.cv_extractor import extract_text_from_pdf, save_text_as_txt
from app.services.skill_service import SkillService
from app.services.cv_extraction_service import CVExtractionService
from ai_module.nlp.cv_cleaner import CVCleaner

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
    """Upload a candidate CV file and extract text from PDF."""
    file_name = file.filename or ""
    file_content_type = file.content_type or ""

    if file_content_type not in {"application/pdf", "text/plain"} and not (
        file_name.lower().endswith(".pdf") or file_name.lower().endswith(".txt")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and text files are supported"
        )

    contents = await file.read()
    max_size_bytes = 5 * 1024 * 1024
    if len(contents) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 5 MB limit"
        )

    try:
        uploads_root = Path(__file__).resolve().parents[2] / "uploads"
        pdf_dir = uploads_root / "cvs"
        txt_dir = uploads_root / "txt"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        txt_dir.mkdir(parents=True, exist_ok=True)

        safe_filename = f"{uuid.uuid4().hex}_{Path(file_name).name}"
        pdf_path = pdf_dir / safe_filename
        pdf_path.write_bytes(contents)

        # Check if it's a PDF or text file
        if file_content_type == "application/pdf" or file_name.lower().endswith('.pdf'):
            extracted_text = extract_text_from_pdf(str(pdf_path))
        elif file_content_type == "text/plain" or file_name.lower().endswith('.txt'):
            extracted_text = contents.decode('utf-8')
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF and text files are supported"
            )
        cleaned_text = CVCleaner.clean_text(extracted_text)
        txt_path = save_text_as_txt(cleaned_text, str(txt_dir), safe_filename)
        fallback_email = email or f"candidate-{uuid.uuid4().hex}@example.com"

        relative_pdf_path = str(pdf_path.relative_to(Path(__file__).resolve().parents[2]))

        # Support both legacy and modern DB schemas for `candidates`.
        columns_result = db.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'candidates'
                """
            )
        )
        available_columns = {cast(str, row[0]) for row in columns_result.fetchall()}

        candidate_values = {
            "full_name": full_name or "Unknown",
            "email": fallback_email,
            "phone": None,
            "linkedin_url": None,
            "github_url": None,
            "cv_path": relative_pdf_path,
            "file_path": relative_pdf_path,
            "filename": file_name,
            "raw_text": cleaned_text,
            "created_at": datetime.utcnow(),
        }

        insert_columns = [
            col for col in [
                "full_name",
                "email",
                "phone",
                "linkedin_url",
                "github_url",
                "cv_path",
                "filename",
                "file_path",
                "raw_text",
                "created_at",
            ]
            if col in available_columns
        ]

        if not insert_columns:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Candidates table schema is incompatible with upload endpoint"
            )

        placeholders = ", ".join(f":{col}" for col in insert_columns)
        columns_sql = ", ".join(insert_columns)
        insert_sql = text(
            f"INSERT INTO candidates ({columns_sql}) VALUES ({placeholders}) RETURNING id"
        )

        result = db.execute(insert_sql, {col: candidate_values[col] for col in insert_columns})
        candidate_id = cast(int, result.scalar_one())
        db.commit()

        # ÉTAPE 6: Extract ALL information from CV (skills, experiences, educations, contact info)
        cv_extraction_service = CVExtractionService(db)
        extraction_result = cv_extraction_service.extract_all(
            candidate_id=candidate_id,
            cv_text=cleaned_text
        )

        return {
            "message": "File uploaded and all information extracted successfully",
            "candidate_id": candidate_id,
            "filename": file_name,
            "pdf_path": str(pdf_path.relative_to(Path(__file__).resolve().parents[2])),
            "txt_path": str(Path(txt_path).relative_to(Path(__file__).resolve().parents[2])),
            "extraction_result": {
                "success": extraction_result.get("success"),
                "contact_info": extraction_result.get("contact_info", {}),
                "skills_extracted": len(extraction_result.get("skills", [])),
                "experiences_extracted": len(extraction_result.get("experiences", [])),
                "educations_extracted": len(extraction_result.get("educations", [])),
                "errors": extraction_result.get("errors", [])
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting text from PDF: {str(e)}"
        )


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


@router.get("/{candidate_id}/skills")
def get_candidate_skills(
    candidate_id: int,
    db: Session = Depends(get_db)
):
    """Get all extracted skills for a candidate with their proficiency levels"""
    skill_service = SkillService(db)
    result = skill_service.get_candidate_skills(candidate_id)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"]
        )
    
    return result


@router.get("/{candidate_id}/experiences")
def get_candidate_experiences(
    candidate_id: int,
    db: Session = Depends(get_db)
):
    """Get all extracted work experiences for a candidate"""
    try:
        result = db.execute(
            text("SELECT id FROM candidates WHERE id = :id"),
            {"id": candidate_id}
        ).first()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate {candidate_id} not found"
            )
        
        # Get all experiences
        experiences = db.execute(
            text("""
                SELECT id, title, company, duration_months, description
                FROM experiences
                WHERE candidate_id = :candidate_id
                ORDER BY id DESC
            """),
            {"candidate_id": candidate_id}
        ).fetchall()
        
        experiences_list = [
            {
                "id": exp[0],
                "title": exp[1],
                "company": exp[2],
                "duration_months": exp[3],
                "description": exp[4]
            }
            for exp in experiences
        ]
        
        return {
            "candidate_id": candidate_id,
            "experiences_count": len(experiences_list),
            "experiences": experiences_list
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching experiences: {str(e)}"
        )


@router.get("/{candidate_id}/educations")
def get_candidate_educations(
    candidate_id: int,
    db: Session = Depends(get_db)
):
    """Get all extracted education records for a candidate"""
    try:
        result = db.execute(
            text("SELECT id FROM candidates WHERE id = :id"),
            {"id": candidate_id}
        ).first()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate {candidate_id} not found"
            )
        
        # Get all educations
        educations = db.execute(
            text("""
                SELECT id, degree, institution, field, year
                FROM educations
                WHERE candidate_id = :candidate_id
                ORDER BY year DESC, id DESC
            """),
            {"candidate_id": candidate_id}
        ).fetchall()
        
        educations_list = [
            {
                "id": edu[0],
                "degree": edu[1],
                "institution": edu[2],
                "field": edu[3],
                "year": edu[4]
            }
            for edu in educations
        ]
        
        return {
            "candidate_id": candidate_id,
            "educations_count": len(educations_list),
            "educations": educations_list
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching educations: {str(e)}"
        )


@router.get("/{candidate_id}/profile-complete")
def get_candidate_complete_profile(
    candidate_id: int,
    db: Session = Depends(get_db)
):
    """Get complete candidate profile with all extracted information"""
    try:
        # Get candidate basic info (use columns that actually exist)
        candidate = db.execute(
            text("""
                SELECT id, filename
                FROM candidates
                WHERE id = :id
            """),
            {"id": candidate_id}
        ).first()
        
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate {candidate_id} not found"
            )
        
        candidate_id_db, filename = candidate
        
        # Get skills
        skills = db.execute(
            text("""
                SELECT cs.id, s.name, s.category, cs.proficiency_level, cs.source
                FROM candidate_skills cs
                JOIN skills s ON cs.skill_id = s.id
                WHERE cs.candidate_id = :candidate_id
            """),
            {"candidate_id": candidate_id}
        ).fetchall()
        
        skills_list = [
            {
                "id": s[0],
                "name": s[1],
                "category": s[2],
                "proficiency_level": s[3],
                "source": s[4]
            }
            for s in skills
        ]
        
        # Get experiences
        experiences = db.execute(
            text("""
                SELECT id, title, company, duration_months, description
                FROM experiences
                WHERE candidate_id = :candidate_id
                ORDER BY id DESC
            """),
            {"candidate_id": candidate_id}
        ).fetchall()
        
        experiences_list = [
            {
                "id": exp[0],
                "title": exp[1],
                "company": exp[2],
                "duration_months": exp[3],
                "description": exp[4]
            }
            for exp in experiences
        ]
        
        # Get educations
        educations = db.execute(
            text("""
                SELECT id, degree, institution, field, year
                FROM educations
                WHERE candidate_id = :candidate_id
                ORDER BY year DESC, id DESC
            """),
            {"candidate_id": candidate_id}
        ).fetchall()
        
        educations_list = [
            {
                "id": edu[0],
                "degree": edu[1],
                "institution": edu[2],
                "field": edu[3],
                "year": edu[4]
            }
            for edu in educations
        ]
        
        return {
            "candidate_id": candidate_id_db,
            "filename": filename,
            "skills_count": len(skills_list),
            "skills": skills_list,
            "experiences_count": len(experiences_list),
            "experiences": experiences_list,
            "educations_count": len(educations_list),
            "educations": educations_list
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching complete profile: {str(e)}"
        )
