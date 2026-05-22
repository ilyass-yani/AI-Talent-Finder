from app.core.database import Base
from app.models.models import (
    User,
    Candidate,
    Skill,
    CandidateSkill,
    Experience,
    Education,
    JobCriteria,
    CriteriaSkill,
    MatchResult,
    Favorite,
    UserRole,
    SkillCategory,
    ProficiencyLevel,
)

# Backward compatibility for legacy tests/imports that still refer to `Job`.
Job = JobCriteria

__all__ = [
    "Base",
    "User",
    "Candidate",
    "Job",
    "Skill",
    "CandidateSkill",
    "Experience",
    "Education",
    "JobCriteria",
    "CriteriaSkill",
    "MatchResult",
    "Favorite",
    "UserRole",
    "SkillCategory",
    "ProficiencyLevel",
]