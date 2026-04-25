from pydantic import BaseModel, ConfigDict
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
    model_config = ConfigDict(from_attributes=True)
