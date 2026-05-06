from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict

class CandidateBase(BaseModel):
    full_name: str
    email: str
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None

class CandidateCreate(CandidateBase):
    cv_path: Optional[str] = None
    raw_text: Optional[str] = None

class CandidateUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    cv_path: Optional[str] = None
    raw_text: Optional[str] = None

class CandidateResponse(CandidateBase):
    id: int
    cv_path: Optional[str]
    raw_text: Optional[str]
    created_at: datetime
    
    # NER Extraction Fields (Étape 5-6 Optimization)
    extracted_name: Optional[str] = None
    extracted_emails: Optional[str] = None
    extracted_phones: Optional[str] = None
    extracted_job_titles: Optional[str] = None
    extracted_companies: Optional[str] = None
    extracted_education: Optional[str] = None
    extraction_quality_score: Optional[float] = 0.0
    ner_extraction_data: Optional[str] = None
    is_fully_extracted: Optional[bool] = False

    class Config:
        from_attributes = True