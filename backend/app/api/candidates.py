"""Candidates API routes ETAPES 5"""
import uuid
import logging
import re
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Any, Dict, List, Optional, cast

from app.core.dependencies import get_db, get_current_user
from app.models.models import Candidate, User, UserRole
from app.schemas.candidate import CandidateResponse, CandidateCreate, CandidateUpdate
from ai_module.nlp.cv_processing_service import get_cv_pipeline
from ai_module.nlp.cv_cleaner import CVCleaner
from app.services.skill_service import SkillService
from app.services.ner_extractor import NERExtractor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/candidates", tags=["candidates"])


def _fallback_required_value(
    column_name: str,
    data_type: Optional[str],
    relative_pdf_path: str,
    file_name: str,
    fallback_email: str,
    extracted_text: str,
    inferred_full_name: str,
) -> Optional[Any]:
    """Return a safe fallback for required columns when schema varies."""
    normalized = column_name.lower()

    # Known semantic columns
    if normalized in {"cv_path", "file_path"}:
        return relative_pdf_path
    if normalized in {"filename", "file_name"}:
        return file_name
    if normalized == "raw_text":
        return extracted_text
    if normalized == "full_name":
        return inferred_full_name
    if normalized == "email":
        return fallback_email
    if normalized in {"created_at", "updated_at"}:
        return datetime.utcnow()

    # Generic fallback by SQL type
    dt = (data_type or "").lower()
    if any(token in dt for token in ["char", "text", "uuid"]):
        return ""
    if "bool" in dt:
        return False
    if any(token in dt for token in ["int", "numeric", "decimal", "real", "double"]):
        return 0
    if any(token in dt for token in ["timestamp", "date", "time"]):
        return datetime.utcnow()

    return None


def _normalize_label(value: Optional[str], default: str) -> str:
    if not value:
        return default
    cleaned = str(value).strip()
    return cleaned or default


def _months_from_years(value: Optional[int], minimum: int = 1) -> int:
    if value is None:
        return minimum
    try:
        return max(minimum, int(value) * 12)
    except (TypeError, ValueError):
        return minimum


def _save_extracted_profile_data(db: Session, candidate_id: int, extracted_text: str) -> None:
    """Save generic extracted skills, experiences and educations for any CV layout."""
    structured = NERExtractor().extract_entities(extracted_text)

    # Save skills through the dedicated service
    skill_service = SkillService(db)
    skill_service.extract_and_save_skills(candidate_id, extracted_text)

    # Save experiences heuristically, while skipping duplicates on repeated uploads.
    existing_experiences = db.execute(
        text("SELECT LOWER(title), LOWER(company) FROM experiences WHERE candidate_id = :id"),
        {"id": candidate_id},
    ).fetchall()
    existing_experiences_set = {(cast(str, row[0]), cast(str, row[1])) for row in existing_experiences}

    for experience in structured.get("experiences", []):
        title = _normalize_label(experience.get("job_title") or experience.get("title"), "Position")
        company = _normalize_label(experience.get("company"), "Company")
        key = (title.lower(), company.lower())
        if key in existing_experiences_set:
            continue

        db.execute(
            text(
                """
                INSERT INTO experiences (candidate_id, title, company, duration_months, description)
                VALUES (:candidate_id, :title, :company, :duration_months, :description)
                """
            ),
            {
                "candidate_id": candidate_id,
                "title": title,
                "company": company,
                "duration_months": _months_from_years(experience.get("duration_months"), minimum=1),
                "description": experience.get("description") or title,
            },
        )

    # Save educations heuristically, while skipping duplicates on repeated uploads.
    existing_educations = db.execute(
        text("SELECT LOWER(degree), LOWER(institution) FROM educations WHERE candidate_id = :id"),
        {"id": candidate_id},
    ).fetchall()
    existing_educations_set = {(cast(str, row[0]), cast(str, row[1])) for row in existing_educations}

    for education in structured.get("educations", []):
        degree = _normalize_label(education.get("degree"), "Degree")
        institution = _normalize_label(education.get("institution"), "Institution")
        key = (degree.lower(), institution.lower())
        if key in existing_educations_set:
            continue

        db.execute(
            text(
                """
                INSERT INTO educations (candidate_id, degree, institution, field, year)
                VALUES (:candidate_id, :degree, :institution, :field, :year)
                """
            ),
            {
                "candidate_id": candidate_id,
                "degree": degree,
                "institution": institution,
                "field": _normalize_label(education.get("field_of_study") or education.get("field"), "Not specified"),
                "year": education.get("graduation_year") or education.get("year"),
            },
        )

    db.commit()


def _collapse_whitespace(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _normalize_lines(text: str) -> List[str]:
    lines: List[str] = []
    for raw_line in text.splitlines():
        line = _collapse_whitespace(raw_line)
        if not line:
            continue
        if line.startswith("--- PAGE"):
            continue
        lines.append(line)
    return lines


def _is_contact_line(line: str) -> bool:
    lowered = line.lower()
    return bool(
        re.search(r"@\w|https?://|linkedin|github|tel\b|phone|mobile|adresse|contact", lowered)
    )


def _is_noise_line(line: str) -> bool:
    lowered = line.lower().strip()
    if not lowered:
        return True
    if _is_contact_line(lowered):
        return True
    if lowered in {"experience", "expériences", "formations", "education", "skills", "competences", "compétences", "profil"}:
        return True
    return False


def _meaningful_lines(text: str) -> List[str]:
    return [line for line in _normalize_lines(text) if not _is_noise_line(line)]


def _extract_phone_number(text: str) -> Optional[str]:
    phone_label_pattern = re.compile(
        r"(?:t[ée]l[ée]?phone|phone|mobile|portable)\s*[:\-]?\s*(?P<number>(?:\+?\d[\d\s().-]{7,}\d))",
        re.IGNORECASE,
    )
    for match in phone_label_pattern.finditer(text):
        digits = re.sub(r"\D", "", match.group("number"))
        if 8 <= len(digits) <= 15:
            return digits

    general_pattern = re.compile(r"(?P<number>(?:\+?\d[\d\s().-]{7,}\d))")
    for match in general_pattern.finditer(text):
        candidate = match.group("number")
        digits = re.sub(r"\D", "", candidate)
        if 8 <= len(digits) <= 15:
            return digits

    return None


def _extract_name_from_text(text: str) -> Optional[str]:
    for line in _normalize_lines(text)[:6]:
        if _is_noise_line(line):
            continue
        if len(line) < 3:
            continue
        if re.search(r"@|\d", line):
            continue
        words = [word for word in re.split(r"\s+", line) if word]
        if 1 <= len(words) <= 4:
            return line[:80]
    return None


def _extract_skill_section(text: str, sections: dict) -> str:
    section = _collapse_whitespace(sections.get("skills", ""))
    if section:
        return section
    return text


def _infer_profile_title(text: str, sections: dict, structured: dict) -> str:
    summary_lines = _meaningful_lines(sections.get("summary", ""))
    if summary_lines:
        return summary_lines[0][:120]

    for experience in structured.get("experiences", []):
        title = _collapse_whitespace(experience.get("job_title") or experience.get("title"))
        if title:
            return title[:120]

    for line in _meaningful_lines(text)[:10]:
        if len(line) <= 120:
            return line

    return "Profil candidat"


def _infer_profile_summary(text: str, sections: dict) -> str:
    summary_lines = _meaningful_lines(sections.get("summary", ""))
    if summary_lines:
        return " ".join(summary_lines[:2])[:350]

    return " ".join(_meaningful_lines(text)[:2])[:350]


def _looks_like_fragment(value: Optional[str]) -> bool:
    cleaned = _collapse_whitespace(value)
    if not cleaned:
        return True
    if cleaned.startswith("##"):
        return True
    if len(cleaned) <= 2:
        return True
    if re.fullmatch(r"[A-Z]", cleaned):
        return True
    if not re.search(r"[A-Za-zÀ-ÿ]", cleaned):
        return True
    return False


def _dedupe_dict_items(items: List[Dict[str, Any]], primary_key: str) -> List[Dict[str, Any]]:
    seen = set()
    deduped = []
    for item in items:
        key = _collapse_whitespace(cast(Optional[str], item.get(primary_key))).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _build_adaptive_profile(raw_text: str, candidate_row: Any, skills: List[Dict[str, Any]], experiences: List[Dict[str, Any]], educations: List[Dict[str, Any]]) -> Dict[str, Any]:
    text = raw_text or ""
    sections = CVCleaner.extract_sections(text) if text else {"experience": "", "education": "", "skills": "", "summary": ""}
    structured = NERExtractor().extract_entities(text) if text else {
        "name": None,
        "email": None,
        "phone": None,
        "skills": [],
        "experiences": [],
        "educations": [],
    }

    if _looks_like_fragment(structured.get("name")):
        structured["name"] = _extract_name_from_text(text)

    contact_phone = _extract_phone_number(text) or structured.get("phone") or cast(Optional[str], candidate_row[4])
    contact_email = structured.get("email") or cast(Optional[str], candidate_row[3])

    adaptive_skills = skills[:]
    if not adaptive_skills:
        for index, skill_name in enumerate(structured.get("skills", []), start=1):
            cleaned_name = _collapse_whitespace(skill_name)
            if _looks_like_fragment(cleaned_name) or len(cleaned_name) < 3:
                continue
            adaptive_skills.append(
                {
                    "id": -index,
                    "name": cleaned_name,
                    "category": "Adaptive",
                    "proficiency_level": "intermediate",
                    "source": "heuristic",
                }
            )

    adaptive_experiences = experiences[:]
    if not adaptive_experiences:
        for index, experience in enumerate(structured.get("experiences", []), start=1):
            title = experience.get("job_title") or experience.get("title")
            company = experience.get("company")
            if _looks_like_fragment(title) and _looks_like_fragment(company):
                continue
            adaptive_experiences.append(
                {
                    "id": -index,
                    "title": title or "Position",
                    "job_title": title or "Position",
                    "company": company or "Company",
                    "duration_months": experience.get("duration_months") or 12,
                    "description": experience.get("description") or "",
                }
            )

    adaptive_educations = educations[:]
    if not adaptive_educations:
        for index, education in enumerate(structured.get("educations", []), start=1):
            degree = education.get("degree")
            institution = education.get("institution")
            if _looks_like_fragment(degree) or _looks_like_fragment(institution):
                continue
            adaptive_educations.append(
                {
                    "id": -index,
                    "degree": degree or "Degree",
                    "institution": institution or "Institution",
                    "field": education.get("field_of_study") or education.get("field") or "",
                    "field_of_study": education.get("field_of_study") or education.get("field") or "",
                    "year": education.get("graduation_year") or education.get("year"),
                    "graduation_year": education.get("graduation_year") or education.get("year"),
                }
            )

    full_name = (
        _extract_name_from_text(text)
        or structured.get("name")
        or cast(Optional[str], candidate_row[2])
        or _infer_profile_title(text, sections, structured)
    )
    email = contact_email
    phone = contact_phone

    return {
        "name": full_name,
        "headline": _infer_profile_title(text, sections, structured),
        "summary": _infer_profile_summary(text, sections),
        "contact": {
            "email": email,
            "phone": phone,
        },
        "sections_detected": [name for name, value in sections.items() if _collapse_whitespace(value)],
        "skills": _dedupe_dict_items(adaptive_skills, "name"),
        "experiences": _dedupe_dict_items(adaptive_experiences, "title"),
        "educations": _dedupe_dict_items(adaptive_educations, "degree"),
        "source": "adaptive",
    }


@router.get("/", response_model=List[CandidateResponse])
def get_candidates(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all candidates"""
    query = text("""
        SELECT id, full_name, email, phone, linkedin_url, github_url, cv_path, raw_text, created_at 
        FROM candidates 
        ORDER BY created_at DESC 
        LIMIT :limit OFFSET :skip
    """)
    result = db.execute(query, {"limit": limit, "skip": skip}).fetchall()
    candidates = [
        {
            "id": row[0],
            "full_name": row[1],
            "email": row[2],
            "phone": row[3],
            "linkedin_url": row[4],
            "github_url": row[5],
            "cv_path": row[6],
            "raw_text": row[7],
            "created_at": row[8]
        }
        for row in result
    ]
    return candidates


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

@router.post("/upload")
async def upload_candidate_cv(
    file: UploadFile = File(...),
    full_name: str = "",
    email: str = "",
    db: Session = Depends(get_db)
):
    """
    Upload candidate CV and extract all information using HuggingFace NER
    
    Returns:
        Candidate info + extracted entities (skills, languages, experiences, etc.)
    """
    file_name = file.filename or ""
    
    # Validate file type
    if not (file_name.lower().endswith(".pdf") or file_name.lower().endswith(".txt")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and TXT files are supported"
        )
    
    # Validate file size (max 5MB)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large (max 5MB)"
        )
    
    try:
        # Create uploads directory
        uploads_root = Path(__file__).resolve().parents[2] / "uploads"
        pdf_dir = uploads_root / "cvs"
        parsed_dir = uploads_root / "parsed"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        parsed_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file with UUID
        safe_filename = f"{uuid.uuid4().hex}_{Path(file_name).name}"
        pdf_path = pdf_dir / safe_filename
        pdf_path.write_bytes(contents)
        
        logger.info(f"[UPLOAD] File saved: {pdf_path}")
        
        # Get CV pipeline and process
        pipeline = get_cv_pipeline(output_dir=str(parsed_dir))
        extraction_result = pipeline.process(str(pdf_path))
        
        if not extraction_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Extraction failed: {extraction_result.get('error', 'Unknown error')}"
            )
        
        # Create candidate record
        fallback_email = email or f"candidate-{uuid.uuid4().hex}@example.com"
        relative_pdf_path = str(pdf_path.relative_to(Path(__file__).resolve().parents[2]))
        
        extracted_text = extraction_result.get("extracted_text", "")
        
        candidate_values = {
            "full_name": full_name or extraction_result.get("metadata", {}).get("author", "Unknown"),
            "email": fallback_email,
            "phone": None,
            "linkedin_url": None,
            "github_url": None,
            "cv_path": relative_pdf_path,
            "file_path": relative_pdf_path,
            "filename": file_name,
            "raw_text": extracted_text,
            "created_at": datetime.utcnow(),
        }
        
        # Read schema metadata to support schema drift across environments.
        columns_result = db.execute(
            text(
                """
                SELECT column_name, is_nullable, column_default, data_type
                FROM information_schema.columns
                WHERE table_name = 'candidates'
                """
            )
        )
        column_rows = columns_result.fetchall()
        columns_meta = {
            cast(str, row[0]): {
                "is_nullable": cast(str, row[1]),
                "column_default": row[2],
                "data_type": cast(str, row[3]),
            }
            for row in column_rows
        }

        # Start with known values for columns that actually exist.
        insert_values = {
            col: value
            for col, value in candidate_values.items()
            if col in columns_meta
        }

        # Fill required columns that were not explicitly provided.
        for col, meta in columns_meta.items():
            if col in insert_values:
                continue

            is_required = meta["is_nullable"] == "NO" and meta["column_default"] is None
            if not is_required:
                continue

            fallback = _fallback_required_value(
                column_name=col,
                data_type=cast(Optional[str], meta["data_type"]),
                relative_pdf_path=relative_pdf_path,
                file_name=file_name,
                fallback_email=fallback_email,
                extracted_text=extracted_text,
                inferred_full_name=cast(str, candidate_values["full_name"]),
            )

            if fallback is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Candidates schema requires unsupported column: {col}",
                )

            insert_values[col] = fallback

        insert_columns = list(insert_values.keys())
        placeholders = ", ".join(f":{col}" for col in insert_columns)
        columns_sql = ", ".join(insert_columns)
        
        insert_sql = text(
            f"INSERT INTO candidates ({columns_sql}) VALUES ({placeholders}) RETURNING id"
        )
        
        result = db.execute(insert_sql, insert_values)
        candidate_id = cast(int, result.scalar_one())
        db.commit()
        
        logger.info(f"[UPLOAD] Candidate created: {candidate_id}")

        # Best-effort structured extraction for arbitrary CV layouts.
        try:
            _save_extracted_profile_data(db, candidate_id, extracted_text)
        except Exception as structured_error:
            logger.warning(f"[UPLOAD] Structured enrichment skipped: {structured_error}")
        
        # Return comprehensive result
        return {
            "success": True,
            "message": "CV uploaded and parsed successfully",
            "candidate_id": candidate_id,
            "filename": file_name,
            "cv_path": relative_pdf_path,
            "extraction": {
                "pages": extraction_result.get("extraction", {}).get("pages", 0),
                "images_detected": extraction_result.get("extraction", {}).get("images_detected", 0),
                "text_length": extraction_result.get("extraction", {}).get("text_length", 0)
            },
            "parsed_entities": extraction_result.get("parsed_entities", {}),
            "timestamp": extraction_result.get("timestamp")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[UPLOAD] Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.get("/{candidate_id}", response_model=CandidateResponse)
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific candidate by ID"""
    try:
        result = db.execute(
            text("""
                SELECT id, full_name, email, phone, linkedin_url, github_url, cv_path, raw_text, created_at 
                FROM candidates 
                WHERE id = :candidate_id
            """),
            {"candidate_id": candidate_id}
        ).first()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found"
            )
        
        return {
            "id": result[0],
            "full_name": result[1],
            "email": result[2],
            "phone": result[3],
            "linkedin_url": result[4],
            "github_url": result[5],
            "cv_path": result[6],
            "raw_text": result[7],
            "created_at": result[8]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching candidate {candidate_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching candidate: {str(e)}"
        )


@router.get("/{candidate_id}/parsed-entities")
def get_candidate_parsed_entities(
    candidate_id: int,
    db: Session = Depends(get_db)
):
    """
    Get parsed CV entities for a candidate
    
    Returns:
        Extracted skills, languages, experiences, educations, contact info
    """
    try:
        # Get candidate
        candidate_result = db.execute(
            text("SELECT id, full_name, raw_text FROM candidates WHERE id = :id"),
            {"id": candidate_id}
        ).first()
        
        if not candidate_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found"
            )
        
        candidate_id_val = candidate_result[0]
        raw_text = candidate_result[2] or ""
        
        # Parse text with pipeline
        pipeline = get_cv_pipeline()
        
        # Extract languages using our language detector
        from ai_module.nlp.cv_processing_service import LanguageExtractor
        languages = LanguageExtractor.extract(raw_text)
        
        # Extract emails and phones
        import re
        emails = []
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for match in re.findall(email_pattern, raw_text):
            if match not in [e["value"] for e in emails]:
                emails.append({"value": match, "confidence": 1.0})
        
        phones = []
        phone_pattern = r'\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}'
        for match in re.findall(phone_pattern, raw_text):
            if match not in [p["value"] for p in phones]:
                phones.append({"value": match, "confidence": 0.8})
        
        # Compile results
        result = {
            "candidate_id": candidate_id_val,
            "entities": {
                "languages": languages,
                "emails": emails,
                "phones": phones
            }
        }
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching parsed entities for candidate {candidate_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching entities: {str(e)}"
        )


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
                "job_title": exp[1],
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
                "field_of_study": edu[3],
                "year": edu[4],
                "graduation_year": edu[4]
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
                SELECT id, filename, full_name, email, phone, raw_text
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
        
        candidate_id_db, filename, full_name, email, phone, raw_text = candidate
        
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

        adaptive_context = _build_adaptive_profile(
            raw_text or "",
            candidate,
            skills_list,
            [],
            [],
        )
        
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

        if not experiences_list and raw_text:
            experiences_list = adaptive_context["experiences"]
        
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

        if not educations_list and raw_text:
            educations_list = adaptive_context["educations"]

        if not skills_list and raw_text:
            skills_list = adaptive_context["skills"]
        
        return {
            "candidate_id": candidate_id_db,
            "filename": filename,
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "headline": adaptive_context["headline"],
            "summary": adaptive_context["summary"],
            "contact": adaptive_context["contact"],
            "sections_detected": adaptive_context["sections_detected"],
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
