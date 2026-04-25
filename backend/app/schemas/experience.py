from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class ExperienceBase(BaseModel):
    title: str
    company: str
    duration_months: int
    description: Optional[str] = None


class ExperienceCreate(ExperienceBase):
    candidate_id: int


class ExperienceUpdate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    duration_months: Optional[int] = None
    description: Optional[str] = None


class ExperienceResponse(ExperienceBase):
    id: int
    candidate_id: int
    model_config = ConfigDict(from_attributes=True)
