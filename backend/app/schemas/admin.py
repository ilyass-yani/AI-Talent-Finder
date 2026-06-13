"""Pydantic schemas for the admin module.

Covers the Administrateur use cases:
- Gérer les utilisateurs (CRUD)
- Consulter les statistiques globales
- Superviser les logs et performances
- Configurer les paramètres du pipeline IA
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, List
from datetime import datetime

from app.schemas.user import UserRole


# ---------------------------------------------------------------------------
# Gérer les utilisateurs (CRUD)
# ---------------------------------------------------------------------------

class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    role: UserRole = UserRole.recruiter


class AdminUserUpdate(BaseModel):
    """All fields optional; only provided fields are updated."""
    full_name: Optional[str] = Field(None, min_length=2)
    role: Optional[UserRole] = None
    password: Optional[str] = Field(None, min_length=6)


class AdminUserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Consulter les statistiques globales
# ---------------------------------------------------------------------------

class GlobalStatsResponse(BaseModel):
    total_users: int
    users_by_role: Dict[str, int]
    total_candidates: int
    total_jobs: int
    total_match_results: int
    total_feedback: int
    total_skills: int
    average_match_score: Optional[float] = None
    recent_signups: int  # users created in the last 7 days


# ---------------------------------------------------------------------------
# Superviser les logs et performances
# ---------------------------------------------------------------------------

class ActivityLogResponse(BaseModel):
    id: int
    timestamp: datetime
    level: str
    action: str
    user_id: Optional[int] = None
    detail: Optional[str] = None

    class Config:
        from_attributes = True


class SystemHealthResponse(BaseModel):
    status: str
    database_connected: bool
    capabilities: Dict[str, object]
    counts: Dict[str, int]
    log_levels: Dict[str, int]  # number of log entries by level


# ---------------------------------------------------------------------------
# Configurer les paramètres du pipeline IA
# ---------------------------------------------------------------------------

class PipelineConfigResponse(BaseModel):
    skill_weight: float
    semantic_weight: float
    experience_weight: float
    education_weight: float
    perfect_match_bonus: float
    accept_threshold: float
    review_threshold: float
    defaults: Dict[str, float]


class PipelineConfigUpdate(BaseModel):
    """Partial update; only provided fields change. Each value in [0, 1]."""
    skill_weight: Optional[float] = Field(None, ge=0, le=1)
    semantic_weight: Optional[float] = Field(None, ge=0, le=1)
    experience_weight: Optional[float] = Field(None, ge=0, le=1)
    education_weight: Optional[float] = Field(None, ge=0, le=1)
    perfect_match_bonus: Optional[float] = Field(None, ge=0, le=1)
    accept_threshold: Optional[float] = Field(None, ge=0, le=1)
    review_threshold: Optional[float] = Field(None, ge=0, le=1)
