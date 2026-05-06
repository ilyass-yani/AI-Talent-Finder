from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class MatchResultBase(BaseModel):
    score: float  # 0.0-100.0
    explanation: Optional[str] = None


class MatchResultCreate(MatchResultBase):
    criteria_id: int
    candidate_id: int


class MatchResultUpdate(BaseModel):
    score: Optional[float] = None
    explanation: Optional[str] = None


class MatchResultResponse(MatchResultBase):
    id: int
    criteria_id: int
    candidate_id: int
    created_at: datetime

    class Config:
        from_attributes = True
