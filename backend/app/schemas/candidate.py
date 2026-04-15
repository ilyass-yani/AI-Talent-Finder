from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any

class CandidateBase(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
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
    cv_path: Optional[str] = None
    raw_text: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class Entity(BaseModel):
    """Represents a parsed entity from CV"""
    value: str
    confidence: float


class ParsedEntityResponse(BaseModel):
    """Response for parsed CV entities"""
    candidate_id: int
    file: str
    metadata: Dict[str, Any]
    extraction: Dict[str, Any]
    parsed_entities: Dict[str, List[Entity]]
    timestamp: Optional[str] = None