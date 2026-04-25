from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List


class CriteriaSkillBase(BaseModel):
    skill_id: int
    weight: int  # 0-100


class CriteriaSkillCreate(CriteriaSkillBase):
    pass


class CriteriaSkillResponse(CriteriaSkillBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class JobCriteriaBase(BaseModel):
    title: str
    description: Optional[str] = None


class JobCriteriaCreate(JobCriteriaBase):
    criteria_skills: List[CriteriaSkillCreate] = []


class JobCriteriaUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class JobCriteriaResponse(JobCriteriaBase):
    id: int
    recruiter_id: int
    created_at: datetime
    criteria_skills: List[CriteriaSkillResponse] = []
    model_config = ConfigDict(from_attributes=True)
