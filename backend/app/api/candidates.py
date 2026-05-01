"""Candidates API routes - ÉTAPE 5 OPTIMIZED with NER"""
import uuid
import json
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, cast

from app.core.dependencies import get_db, get_current_user
from app.models.models import Candidate, User, UserRole, CandidateSkill, Skill
from app.schemas.candidate import CandidateResponse, CandidateCreate, CandidateUpdate
from app.services.cv_extractor import CVExtractionService, extract_text_from_pdf, save_text_as_txt
from ai_module.nlp.cv_cleaner import CVCleaner

from fastapi import Depends

router = APIRouter(
    prefix="/api/candidates",
    tags=["candidates"],
    dependencies=[Depends(get_current_user)]
)


# ===== GENERAL ROUTES (un-authenticated) =====

@router.get("/", response_model=List[CandidateResponse])
def get_candidates(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all candidates"""
    candidates = db.query(Candidate).offset(skip).limit(limit).all()
    return candidates


@router.post("/", response_model=CandidateResponse)
def create_candidate(
    candidate: CandidateCreate,
    current_user: User = Depends(get_current_user),
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


# ===== AUTHENTICATED ROUTES (specific paths MUST be before /{id}) =====

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
    
    # Return the latest profile for this user, even if extraction is partial.
    # This avoids false 404 responses right after upload when extraction metadata is incomplete.
    candidate = db.query(Candidate).filter(
        Candidate.user_id == current_user.id
    ).order_by(Candidate.created_at.desc()).first()
    
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found. Please upload a CV first."
        )

    needs_refresh = bool(
        candidate.raw_text and (
            (candidate.extraction_quality_score or 0) < 80
            or candidate.full_name == "Unknown"
            or not candidate.linkedin_url
            or not candidate.extracted_job_titles
            or not candidate.extracted_companies
            or not candidate.extracted_education
            or not candidate.ner_extraction_data
            or '"languages"' not in candidate.ner_extraction_data
            or '"experiences"' not in candidate.ner_extraction_data
            or '"projects"' not in candidate.ner_extraction_data
            or '"certifications"' not in candidate.ner_extraction_data
            or '"github_urls"' not in candidate.ner_extraction_data
            or '"portfolio_urls"' not in candidate.ner_extraction_data
        )
    )

    if needs_refresh:
        try:
            extraction_service = CVExtractionService()
            refreshed = extraction_service.extract_from_text(candidate.raw_text)
            refreshed_candidate = extraction_service.to_candidate_dict(refreshed)

            should_update = (
                refreshed.quality_score > (candidate.extraction_quality_score or 0)
                or candidate.full_name == "Unknown"
                or not candidate.linkedin_url
                or not candidate.extracted_job_titles
                or not candidate.extracted_companies
                or not candidate.extracted_education
                or not candidate.ner_extraction_data
                or '"languages"' not in candidate.ner_extraction_data
                or '"experiences"' not in candidate.ner_extraction_data
                or '"projects"' not in candidate.ner_extraction_data
                or '"certifications"' not in candidate.ner_extraction_data
                or '"github_urls"' not in candidate.ner_extraction_data
                or '"portfolio_urls"' not in candidate.ner_extraction_data
            )

            if should_update:
                refreshed_candidate["user_id"] = candidate.user_id
                refreshed_candidate["cv_path"] = candidate.cv_path
                refreshed_candidate["raw_text"] = candidate.raw_text
                refreshed_candidate["email"] = candidate.email or refreshed_candidate.get("email")
                refreshed_candidate["full_name"] = (
                    candidate.full_name
                    if candidate.full_name and candidate.full_name != "Unknown"
                    else refreshed_candidate.get("full_name")
                )

                for key, value in refreshed_candidate.items():
                    setattr(candidate, key, value)
                db.commit()
                db.refresh(candidate)
        except Exception:
            db.rollback()
    
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a candidate CV file with NER extraction (Étape 5 Optimized)
    
    Steps:
    1. Validate file (PDF/TXT, max 5 MB)
    2. Extract text from PDF
    3. Use NER to extract structured data (name, email, companies, jobs, skills)
    4. Create/update candidate with auto-filled fields
    5. Extract skills (hybrid NER + fuzzy matching)
    6. Store in database
    """
    file_name = file.filename or ""
    file_content_type = file.content_type or ""

    # Validate file type
    if file_content_type not in {"application/pdf", "text/plain"} and not (
        file_name.lower().endswith(".pdf") or file_name.lower().endswith(".txt")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and text files are supported"
        )

    # Validate file size
    contents = await file.read()
    max_size_bytes = 5 * 1024 * 1024
    if len(contents) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 5 MB limit"
        )

    try:
        # Setup directories
        uploads_root = Path(__file__).resolve().parents[2] / "uploads"
        pdf_dir = uploads_root / "cvs"
        txt_dir = uploads_root / "txt"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        txt_dir.mkdir(parents=True, exist_ok=True)

        # Save file with unique name
        safe_filename = f"{uuid.uuid4().hex}_{Path(file_name).name}"
        pdf_path = pdf_dir / safe_filename
        pdf_path.write_bytes(contents)

        # Extract text from PDF/TXT
        if file_content_type == "application/pdf" or file_name.lower().endswith('.pdf'):
            extracted_text = extract_text_from_pdf(str(pdf_path))
        else:
            extracted_text = contents.decode('utf-8')

        # ===== NER EXTRACTION PIPELINE (NEW) =====
        extraction_service = CVExtractionService()
        extraction_result = extraction_service.extract_from_text(extracted_text)
        
        # Get candidate data from extraction
        candidate_dict = extraction_service.to_candidate_dict(extraction_result)
        candidate_dict["cv_path"] = str(pdf_path.relative_to(Path(__file__).resolve().parents[2]))

        # Prioritize user-provided data, then extraction, then authenticated user defaults.
        candidate_dict["full_name"] = (
            full_name
            or candidate_dict.get("full_name")
            or current_user.full_name
            or "Unknown"
        )
        candidate_dict["email"] = (
            email
            or candidate_dict.get("email")
            or current_user.email
            or f"candidate-{uuid.uuid4().hex}@example.com"
        )

        # Link candidate to authenticated user
        candidate_dict["user_id"] = current_user.id

        # Check if user already has a candidate profile
        existing_candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
        
        if existing_candidate:
            # Update existing profile
            for key, value in candidate_dict.items():
                setattr(existing_candidate, key, value)
            existing_candidate.user_id = current_user.id  # Ensure user_id is set
            db_candidate = existing_candidate
        else:
            # Create new candidate in database
            db_candidate = Candidate(**candidate_dict)
            db_candidate.user_id = current_user.id  # Explicitly set user_id
            db.add(db_candidate)
        
        db.flush()  # Get the ID
        candidate_id = db_candidate.id

        # ===== ADD EXTRACTED SKILLS =====
        for skill_data in extraction_result.skills:
            skill_name = skill_data["name"]
            
            # Check if skill exists in DB
            db_skill = db.query(Skill).filter(
                Skill.name.ilike(skill_name)
            ).first()
            
            if not db_skill:
                # Create new skill
                db_skill = Skill(
                    name=skill_name,
                    category=skill_data.get("category", "tech"),
                    synonyms=None
                )
                db.add(db_skill)
                db.flush()
            
            # Link skill to candidate
            candidate_skill = CandidateSkill(
                candidate_id=candidate_id,
                skill_id=db_skill.id,
                proficiency_level="intermediate",  # Default
                source=skill_data.get("source", "extracted")  # NER or DICT-FUZZY
            )
            db.add(candidate_skill)

        db.commit()

        # ===== RETURN RESPONSE =====
        return {
            "message": "File uploaded and structured extraction successful",
            "candidate_id": candidate_id,
            "candidate": {
                "id": candidate_id,
                "full_name": db_candidate.full_name,
                "email": db_candidate.email,
                "phone": db_candidate.phone,
                "companies": json.loads(candidate_dict["extracted_companies"] or "[]"),
                "job_titles": json.loads(candidate_dict["extracted_job_titles"] or "[]"),
                "skills_count": len(extraction_result.skills),
                "extraction_quality": extraction_result.quality_score,
                "fully_extracted": candidate_dict["is_fully_extracted"]
            },
            "extraction": {
                "quality_score": extraction_result.quality_score,
                "entities_found": extraction_result.extraction_metadata.get("entities_found", 0),
                "skills_extracted": len(extraction_result.skills),
                "top_skills": [s["name"] for s in extraction_result.skills[:5]],
                "metadata": extraction_result.extraction_metadata
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing CV: {str(e)}"
        )


# ===== ID-BASED ROUTES (generic patterns, must be AFTER specific routes) =====

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


@router.post("/upload-cv-with-ner")
async def upload_cv_with_ner(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload CV with NER extraction (Anjali Resume NER BERT v2)
    Extracts: name, email, phone, skills, companies, job titles, education
    """
    try:
        from ai_module.nlp.resume_ner_extractor import ResumeNERExtractor
        import pdfplumber
        
        file_name = file.filename or ""
        contents = await file.read()
        
        # Validate file size (5 MB max)
        if len(contents) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 5MB)")
        
        # Extract text based on file type
        if file_name.lower().endswith('.pdf'):
            with open('/tmp/temp_cv.pdf', 'wb') as tmp:
                tmp.write(contents)
            try:
                with pdfplumber.open('/tmp/temp_cv.pdf') as pdf:
                    text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"PDF extraction failed: {str(e)}")
        elif file_name.lower().endswith('.txt'):
            text = contents.decode('utf-8', errors='ignore')
        else:
            raise HTTPException(status_code=400, detail="Only PDF and TXT files supported")
        
        if not text or len(text.strip()) < 10:
            raise HTTPException(status_code=400, detail="CV text is empty or too short")
        
        # Extract with NER
        extractor = ResumeNERExtractor()
        profile = extractor.extract_structured_profile(text)
        
        # Get or create candidate
        candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
        
        if not candidate:
            candidate = Candidate(
                user_id=current_user.id,
                full_name=profile.get('full_name') or current_user.full_name,
                email=profile.get('email') or current_user.email,
                phone=profile.get('phone'),
                raw_text=text[:5000],  # Store first 5000 chars
                # Save extracted data - convert to JSON strings
                extracted_name=profile.get('full_name'),
                extracted_emails=json.dumps([profile.get('email')] if profile.get('email') else []),
                extracted_phones=json.dumps([profile.get('phone')] if profile.get('phone') else []),
                extracted_job_titles=json.dumps(profile.get('job_titles', [])),
                extracted_companies=json.dumps(profile.get('companies', [])),
                extracted_education=json.dumps(profile.get('education', [])),
                ner_extraction_data=json.dumps(profile),  # Store full profile as JSON
                is_fully_extracted=True
            )
            db.add(candidate)
            db.flush()
        else:
            candidate.full_name = profile.get('full_name') or candidate.full_name
            candidate.email = profile.get('email') or candidate.email
            candidate.phone = profile.get('phone') or candidate.phone
            candidate.raw_text = text[:5000]
            # Update extracted data - convert to JSON strings
            candidate.extracted_name = profile.get('full_name')
            candidate.extracted_emails = json.dumps([profile.get('email')] if profile.get('email') else [])
            candidate.extracted_phones = json.dumps([profile.get('phone')] if profile.get('phone') else [])
            candidate.extracted_job_titles = json.dumps(profile.get('job_titles', []))
            candidate.extracted_companies = json.dumps(profile.get('companies', []))
            candidate.extracted_education = json.dumps(profile.get('education', []))
            candidate.ner_extraction_data = json.dumps(profile)
            candidate.is_fully_extracted = True
        
        db.commit()
        
        return {
            "success": True,
            "candidate_id": candidate.id,
            "extracted_data": profile,
            "message": "CV uploaded and NER extraction complete"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


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
