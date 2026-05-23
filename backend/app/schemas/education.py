from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class EducationBase(BaseModel):
    degree: str
    institution: str
    field: str
    year: Optional[int] = None


class EducationCreate(EducationBase):
    candidate_id: int


class EducationUpdate(BaseModel):
    degree: Optional[str] = None
    institution: Optional[str] = None
    field: Optional[str] = None
    year: Optional[int] = None


class EducationResponse(EducationBase):
    id: int
    candidate_id: int

    class Config:
        from_attributes = True
