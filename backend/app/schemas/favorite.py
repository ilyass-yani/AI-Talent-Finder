from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class FavoriteBase(BaseModel):
    candidate_id: int


class FavoriteCreate(FavoriteBase):
    pass


class FavoriteResponse(BaseModel):
    id: int
    recruiter_id: int
    candidate_id: int
    created_at: datetime

    class Config:
        from_attributes = True
