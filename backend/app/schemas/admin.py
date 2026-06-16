from pydantic import BaseModel
from typing import List, Optional
from enum import Enum


class UserRoleFilter(str, Enum):
    admin = "admin"
    recruiter = "recruiter"
    candidate = "candidate"


class ModerationStatusEnum(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


# ── User admin schemas ────────────────────────────────────────────────────────

class AdminUserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


class PaginatedUsersResponse(BaseModel):
    total: int
    items: List[AdminUserResponse]


class UserStatusUpdate(BaseModel):
    is_active: bool


# ── Job admin schemas ─────────────────────────────────────────────────────────

class AdminJobResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    moderation_status: str
    recruiter_id: int
    recruiter_email: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class PaginatedJobsResponse(BaseModel):
    total: int
    items: List[AdminJobResponse]


class JobModerationUpdate(BaseModel):
    moderation_status: ModerationStatusEnum


# ── Stats schema ──────────────────────────────────────────────────────────────

class AdminStatsResponse(BaseModel):
    total_candidates: int
    total_recruiters: int
    total_active_jobs: int
    total_matchings: int
