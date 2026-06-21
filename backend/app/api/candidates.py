"""Candidates API routes"""
import json
import os
import tempfile
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional, cast
from pathlib import Path

from app.core.dependencies import get_db, get_current_user
from app.models.models import Candidate, User, UserRole, CandidateSkill, Skill
from app.schemas.candidate import CandidateResponse, CandidateCreate, CandidateUpdate

router = APIRouter(
    prefix="/api/candidates",
    tags=["candidates"],
    dependencies=[Depends(get_current_user)],
)


# ---------------------------------------------------------------------------
# Permission helper — single source of truth
# ---------------------------------------------------------------------------

def _can_access_profile(profile: Candidate, requesting_user: User) -> bool:
    """Return True when requesting_user is allowed to read this profile.

    Rules:
    - Owner always has access.
    - An authenticated recruiter can read a candidate-deposited profile that
      has is_visible = True.
    - Everything else is denied (return False → caller raises 404).
    """
    if profile.user_id == requesting_user.id:
        return True
    effective_role = profile.owner_role or "candidate"
    if (
        requesting_user.role == UserRole.recruiter
        and effective_role == "candidate"
        and profile.is_visible
    ):
        return True
    return False


def _is_displayable_candidate(candidate: Candidate) -> bool:
    has_profile_data = bool(
        candidate.raw_text
        or candidate.cv_path
        or candidate.extracted_job_titles
        or candidate.extracted_companies
        or candidate.extracted_education
    )
    return bool(
        has_profile_data
        and candidate.full_name
        and candidate.full_name != "Unknown"
    )


# ---------------------------------------------------------------------------
# GET /  — listing
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[CandidateResponse])
def get_candidates(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List candidates according to visibility rules.

    - Recruiter: own deposits + candidate profiles with is_visible=True.
    - Candidate: own profile only (redirected to /me/profile is cleaner, but
      this route still works for consistency).
    - Admin: all profiles.
    """
    if current_user.role == UserRole.admin:
        query = db.query(Candidate)
    elif current_user.role == UserRole.recruiter:
        query = db.query(Candidate).filter(
            or_(
                Candidate.recruiter_id == current_user.id,
                and_(
                    or_(
                        Candidate.owner_role == "candidate",
                        Candidate.owner_role.is_(None),
                    ),
                    Candidate.is_visible == True,
                ),
            )
        )
    else:
        # candidate: only their own profile
        query = db.query(Candidate).filter(Candidate.user_id == current_user.id)

    candidates = query.offset(skip).limit(limit).all()
    return [c for c in candidates if _is_displayable_candidate(c)]


# ---------------------------------------------------------------------------
# POST /  — create (manual, no file)
# ---------------------------------------------------------------------------

@router.post("/", response_model=CandidateResponse)
def create_candidate(
    candidate: CandidateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or update a candidate profile by email (upsert)."""
    existing = db.query(Candidate).filter(Candidate.email == candidate.email).first()
    if existing:
        for field, value in candidate.dict(exclude_unset=True).items():
            setattr(existing, field, value)
        db_candidate = existing
    else:
        db_candidate = Candidate(
            full_name=candidate.full_name,
            email=candidate.email,
            phone=candidate.phone,
            linkedin_url=candidate.linkedin_url,
            github_url=candidate.github_url,
            cv_path=candidate.cv_path,
            raw_text=candidate.raw_text,
            user_id=current_user.id,
            owner_role=current_user.role.value,
            is_visible=False,
        )
        db.add(db_candidate)
    db.commit()
    db.refresh(db_candidate)
    return db_candidate


# ---------------------------------------------------------------------------
# GET /me/profile  — candidate reads their own profile
# ---------------------------------------------------------------------------

@router.get("/me/profile", response_model=CandidateResponse)
def get_my_candidate_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the authenticated candidate's own profile."""
    if cast(UserRole, current_user.role) != UserRole.candidate:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only candidates can access this endpoint",
        )

    candidate = (
        db.query(Candidate)
        .filter(Candidate.user_id == current_user.id)
        .order_by(Candidate.created_at.desc())
        .first()
    )
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found. Please upload a CV first.",
        )

    # Opportunistic re-extraction if quality is low
    needs_refresh = bool(
        candidate.raw_text
        and (
            (candidate.extraction_quality_score or 0) < 80
            or candidate.full_name == "Unknown"
            or not candidate.linkedin_url
            or not candidate.extracted_job_titles
            or not candidate.extracted_companies
            or not candidate.extracted_education
            or not candidate.ner_extraction_data
            or '"languages"' not in (candidate.ner_extraction_data or "")
            or '"experiences"' not in (candidate.ner_extraction_data or "")
        )
    )

    if needs_refresh:
        try:
            from app.services.cv_extractor import CVExtractionService

            extraction_service = CVExtractionService()
            refreshed = extraction_service.extract_from_text(candidate.raw_text)
            refreshed_candidate = extraction_service.to_candidate_dict(refreshed)

            should_update = refreshed.quality_score > (candidate.extraction_quality_score or 0)
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


# ---------------------------------------------------------------------------
# POST /me/profile  — candidate creates / updates their profile manually
# ---------------------------------------------------------------------------

@router.post("/me/profile", response_model=CandidateResponse)
def create_or_update_my_profile(
    candidate_data: CandidateUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or update the authenticated candidate's profile (no file upload)."""
    if cast(UserRole, current_user.role) != UserRole.candidate:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only candidates can access this endpoint",
        )

    email = candidate_data.email or current_user.email
    candidate = db.query(Candidate).filter(Candidate.email == email).first()

    if candidate:
        candidate.user_id = current_user.id
        for key, value in candidate_data.dict(exclude_unset=True).items():
            setattr(candidate, key, value)
    else:
        candidate = Candidate(
            user_id=current_user.id,
            full_name=candidate_data.full_name or current_user.full_name,
            email=email,
            phone=candidate_data.phone,
            linkedin_url=candidate_data.linkedin_url,
            github_url=candidate_data.github_url,
            cv_path=candidate_data.cv_path,
            raw_text=candidate_data.raw_text,
            owner_role="candidate",
            is_visible=False,
        )
        db.add(candidate)

    db.commit()
    db.refresh(candidate)
    return candidate


# ---------------------------------------------------------------------------
# PATCH /me/visibility  — candidate toggles their profile visibility
# ---------------------------------------------------------------------------

@router.patch("/me/visibility", response_model=CandidateResponse)
def toggle_my_visibility(
    is_visible: bool,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Let the authenticated candidate set their profile visible or hidden.

    Visible = recruiters can find the profile in their search.
    Hidden  = only the candidate themselves can see it.
    """
    if cast(UserRole, current_user.role) != UserRole.candidate:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only candidates can change their profile visibility",
        )

    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No profile found. Please upload a CV first.",
        )

    # Only candidate-owned profiles support the visibility flag
    if candidate.owner_role not in (None, "candidate"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Visibility toggle is only available for candidate profiles",
        )

    candidate.is_visible = is_visible
    db.commit()
    db.refresh(candidate)
    return candidate


# ---------------------------------------------------------------------------
# POST /upload  — upload + parse CV (PDF/TXT)
# ---------------------------------------------------------------------------

@router.post("/upload")
async def upload_candidate_cv(
    file: UploadFile = File(...),
    full_name: str = "",
    email: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a CV, parse it with NER, persist the structured profile.

    The PDF is written to a temporary file and deleted after parsing —
    only the extracted text and structured data are kept in the database.
    """
    import uuid

    file_name = file.filename or ""
    file_content_type = file.content_type or ""

    if file_content_type not in {"application/pdf", "text/plain"} and not (
        file_name.lower().endswith(".pdf") or file_name.lower().endswith(".txt")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and text files are supported",
        )

    contents = await file.read()
    max_size_bytes = 5 * 1024 * 1024
    if len(contents) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 5 MB limit",
        )

    tmp_path: Optional[str] = None
    try:
        # Write to a temporary file — will be deleted after parsing
        suffix = ".pdf" if (file_content_type == "application/pdf" or file_name.lower().endswith(".pdf")) else ".txt"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
            tmp_file.write(contents)
            tmp_path = tmp_file.name

        # Extract text
        if suffix == ".pdf":
            from app.services.cv_extractor import extract_text_from_pdf
            extracted_text = extract_text_from_pdf(tmp_path)
        else:
            extracted_text = contents.decode("utf-8", errors="ignore")

        if not extracted_text or not extracted_text.strip():
            extracted_text = f"Uploaded CV file: {Path(file_name).name}"

        # NER extraction pipeline
        from app.services.cv_extractor import CVExtractionService

        extraction_service = CVExtractionService()
        extraction_result = extraction_service.extract_from_text(extracted_text)
        candidate_dict = extraction_service.to_candidate_dict(extraction_result)

        if not candidate_dict.get("raw_text") or not str(candidate_dict.get("raw_text")).strip():
            candidate_dict["raw_text"] = extracted_text

        # PDF is NOT persisted — set cv_path to None
        candidate_dict["cv_path"] = None

        # Determine identity: prefer form params, then extraction, then auth user
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

        # Visibility metadata
        depositor_role = cast(UserRole, current_user.role)
        candidate_dict["owner_role"] = depositor_role.value  # "candidate" or "recruiter"
        # Recruiter deposits are always private; candidate profiles start hidden
        candidate_dict["is_visible"] = False

        if depositor_role == UserRole.candidate:
            # Candidate owns their profile: link via user_id (unique per user)
            candidate_dict["user_id"] = current_user.id
            candidate_dict["recruiter_id"] = None
            existing_candidate = db.query(Candidate).filter(
                Candidate.user_id == current_user.id
            ).first()
            if not existing_candidate and candidate_dict.get("email"):
                existing_candidate = db.query(Candidate).filter(
                    Candidate.email == candidate_dict["email"]
                ).first()
        else:
            # Recruiter deposits: track recruiter via recruiter_id, NOT user_id.
            # This allows a recruiter to upload many CVs without constraint conflicts.
            candidate_dict["user_id"] = None
            candidate_dict["recruiter_id"] = current_user.id
            # Upsert only by email to avoid overwriting a different person's record
            existing_candidate = None
            if candidate_dict.get("email"):
                existing_candidate = db.query(Candidate).filter(
                    Candidate.email == candidate_dict["email"]
                ).first()

        if existing_candidate:
            for key, value in candidate_dict.items():
                setattr(existing_candidate, key, value)
            db_candidate = existing_candidate
        else:
            db_candidate = Candidate(**candidate_dict)
            db.add(db_candidate)

        db.flush()
        candidate_id = db_candidate.id

        # Persist extracted skills
        for skill_data in extraction_result.skills:
            skill_name = skill_data["name"]
            db_skill = db.query(Skill).filter(Skill.name.ilike(skill_name)).first()
            if not db_skill:
                db_skill = Skill(
                    name=skill_name,
                    category=skill_data.get("category", "tech"),
                    synonyms=None,
                )
                db.add(db_skill)
                db.flush()
            candidate_skill = CandidateSkill(
                candidate_id=candidate_id,
                skill_id=db_skill.id,
                proficiency_level="intermediate",
                source=skill_data.get("source", "extracted"),
            )
            db.add(candidate_skill)

        db.commit()

        return {
            "message": "CV uploaded and parsed successfully",
            "candidate_id": candidate_id,
            "candidate": {
                "id": candidate_id,
                "full_name": db_candidate.full_name,
                "email": db_candidate.email,
                "phone": db_candidate.phone,
                "owner_role": db_candidate.owner_role,
                "is_visible": db_candidate.is_visible,
                "companies": json.loads(candidate_dict.get("extracted_companies") or "[]"),
                "job_titles": json.loads(candidate_dict.get("extracted_job_titles") or "[]"),
                "skills_count": len(extraction_result.skills),
                "extraction_quality": extraction_result.quality_score,
                "fully_extracted": candidate_dict.get("is_fully_extracted", False),
            },
            "extraction": {
                "quality_score": extraction_result.quality_score,
                "entities_found": extraction_result.extraction_metadata.get("entities_found", 0),
                "skills_extracted": len(extraction_result.skills),
                "top_skills": [s["name"] for s in extraction_result.skills[:5]],
                "metadata": extraction_result.extraction_metadata,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing CV: {str(e)}",
        )
    finally:
        # Always delete the temporary file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# POST /upload-cv-with-ner  — alternative NER upload endpoint
# ---------------------------------------------------------------------------

@router.post("/upload-cv-with-ner")
async def upload_cv_with_ner(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload CV with NER extraction. PDF is not persisted."""
    import uuid

    try:
        from ai_module.nlp.resume_ner_extractor import ResumeNERExtractor
        import pdfplumber

        file_name = file.filename or ""
        contents = await file.read()

        if len(contents) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 5MB)")

        tmp_path: Optional[str] = None
        try:
            if file_name.lower().endswith(".pdf"):
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(contents)
                    tmp_path = tmp.name
                try:
                    with pdfplumber.open(tmp_path) as pdf:
                        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"PDF extraction failed: {str(e)}")
            elif file_name.lower().endswith(".txt"):
                text = contents.decode("utf-8", errors="ignore")
            else:
                raise HTTPException(status_code=400, detail="Only PDF and TXT files supported")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        if not text or len(text.strip()) < 10:
            raise HTTPException(status_code=400, detail="CV text is empty or too short")

        extractor = ResumeNERExtractor()
        profile = extractor.extract_structured_profile(text)

        candidate_email = profile.get("email") or current_user.email
        depositor_role = cast(UserRole, current_user.role)

        is_recruiter_upload = depositor_role == UserRole.recruiter
        candidate = db.query(Candidate).filter(Candidate.email == candidate_email).first()

        if candidate:
            if is_recruiter_upload:
                candidate.recruiter_id = current_user.id
            else:
                candidate.user_id = current_user.id
            candidate.full_name = profile.get("full_name") or current_user.full_name
            candidate.phone = profile.get("phone")
            candidate.raw_text = text[:5000]
            candidate.extracted_name = profile.get("full_name")
            candidate.extracted_emails = json.dumps([profile.get("email")] if profile.get("email") else [])
            candidate.extracted_phones = json.dumps([profile.get("phone")] if profile.get("phone") else [])
            candidate.extracted_job_titles = json.dumps(profile.get("job_titles", []))
            candidate.extracted_companies = json.dumps(profile.get("companies", []))
            candidate.extracted_education = json.dumps(profile.get("education", []))
            candidate.ner_extraction_data = json.dumps(profile)
            candidate.is_fully_extracted = True
            candidate.owner_role = depositor_role.value
            candidate.cv_path = None  # not persisted
        else:
            candidate = Candidate(
                user_id=None if is_recruiter_upload else current_user.id,
                recruiter_id=current_user.id if is_recruiter_upload else None,
                full_name=profile.get("full_name") or current_user.full_name,
                email=candidate_email,
                phone=profile.get("phone"),
                raw_text=text[:5000],
                extracted_name=profile.get("full_name"),
                extracted_emails=json.dumps([profile.get("email")] if profile.get("email") else []),
                extracted_phones=json.dumps([profile.get("phone")] if profile.get("phone") else []),
                extracted_job_titles=json.dumps(profile.get("job_titles", [])),
                extracted_companies=json.dumps(profile.get("companies", [])),
                extracted_education=json.dumps(profile.get("education", [])),
                ner_extraction_data=json.dumps(profile),
                is_fully_extracted=True,
                owner_role=depositor_role.value,
                is_visible=False,
                cv_path=None,
            )
            db.add(candidate)

        db.flush()
        db.commit()

        return {
            "success": True,
            "candidate_id": candidate.id,
            "extracted_data": profile,
            "message": "CV uploaded and NER extraction complete",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ---------------------------------------------------------------------------
# GET /{candidate_id}/cv  — download original PDF (may not exist)
# ---------------------------------------------------------------------------

@router.get("/{candidate_id}/cv")
def download_candidate_cv(
    candidate_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download the original CV PDF if it was kept on disk."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate or not _can_access_profile(candidate, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    cv_path = cast(Optional[str], candidate.cv_path)
    if not cv_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No CV file associated with this candidate",
        )

    file_path = Path(__file__).parent.parent.parent / cv_path
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV file not found on server")

    return FileResponse(path=str(file_path), media_type="application/pdf", filename=file_path.name)


# ---------------------------------------------------------------------------
# GET /{candidate_id}  — detail
# ---------------------------------------------------------------------------

@router.get("/{candidate_id}", response_model=CandidateResponse)
def get_candidate(
    candidate_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific candidate profile — returns 404 when access is denied."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    # Always 404 (not 403) to avoid leaking the existence of private profiles
    if not candidate or not _can_access_profile(candidate, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    if not _is_displayable_candidate(candidate):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return candidate


# ---------------------------------------------------------------------------
# PUT /{candidate_id}  — update
# ---------------------------------------------------------------------------

@router.put("/{candidate_id}", response_model=CandidateResponse)
def update_candidate(
    candidate_id: int,
    candidate: CandidateUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a candidate profile (owner or admin only)."""
    db_candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not db_candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    is_owner = (
        (db_candidate.user_id is not None and db_candidate.user_id == current_user.id)
        or (db_candidate.recruiter_id is not None and db_candidate.recruiter_id == current_user.id)
    )
    if not is_owner and current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    for key, value in candidate.dict(exclude_unset=True).items():
        setattr(db_candidate, key, value)

    db.commit()
    db.refresh(db_candidate)
    return db_candidate


# ---------------------------------------------------------------------------
# DELETE /{candidate_id}  — delete (RGPD right to erasure)
# ---------------------------------------------------------------------------

@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(
    candidate_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a candidate profile (owner or admin only — RGPD right to erasure)."""
    db_candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not db_candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    is_owner = (
        (db_candidate.user_id is not None and db_candidate.user_id == current_user.id)
        or (db_candidate.recruiter_id is not None and db_candidate.recruiter_id == current_user.id)
    )
    if not is_owner and current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    db.delete(db_candidate)
    db.commit()
    return None
