"""
SQLAlchemy ORM models.

Field additions (Lot 2) are nullable or have server defaults, so existing rows
keep working until backfilled. Run the new migration to apply them:

    alembic upgrade head
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB

# JSONB on Postgres, JSON on other dialects (SQLite in tests).
JSONBType = JSONB().with_variant(JSON(), "sqlite")
from sqlalchemy.orm import relationship

from app.core.database import Base


# ---------------------------------------------------------------- Enums

class UserRole(str, enum.Enum):
    admin = "admin"
    recruiter = "recruiter"
    candidate = "candidate"


class SkillCategory(str, enum.Enum):
    tech = "tech"
    soft = "soft"
    language = "language"


class ProficiencyLevel(str, enum.Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
    expert = "expert"


# ---------------------------------------------------------------- Users

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.recruiter, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="true", default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    job_criteria = relationship("JobCriteria", back_populates="recruiter")
    favorites = relationship("Favorite", back_populates="recruiter")
    candidate = relationship("Candidate", back_populates="user", uselist=False)


# ---------------------------------------------------------------- Candidates

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, unique=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    github_url = Column(String, nullable=True)
    cv_path = Column(String, nullable=True)
    raw_text = Column(Text, nullable=True)
    parsed_at = Column(DateTime, nullable=True)  # Set when NLP pipeline finishes
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # NER extraction results (populated by ai_module).
    extracted_name = Column(String, nullable=True)
    extracted_emails = Column(Text, nullable=True)         # JSON-encoded list
    extracted_phones = Column(Text, nullable=True)         # JSON-encoded list
    extracted_job_titles = Column(Text, nullable=True)     # JSON-encoded list
    extracted_companies = Column(Text, nullable=True)      # JSON-encoded list
    extracted_education = Column(Text, nullable=True)      # JSON-encoded list
    extraction_quality_score = Column(Float, default=0.0)
    ner_extraction_data = Column(Text, nullable=True)
    is_fully_extracted = Column(Boolean, default=False)

    user = relationship("User", back_populates="candidate", foreign_keys=[user_id])
    candidate_skills = relationship("CandidateSkill", back_populates="candidate", cascade="all, delete-orphan")
    experiences = relationship("Experience", back_populates="candidate", cascade="all, delete-orphan")
    educations = relationship("Education", back_populates="candidate", cascade="all, delete-orphan")
    match_results = relationship("MatchResult", back_populates="candidate", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="candidate", cascade="all, delete-orphan")


# ---------------------------------------------------------------- Skills

class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    # Lower-cased, accent-stripped form for fast matching. Backfilled at upsert time.
    normalized_name = Column(String, index=True, nullable=True)
    category = Column(Enum(SkillCategory), nullable=False)
    # Comma-separated for backwards compat with existing data.
    synonyms = Column(Text, nullable=True)

    candidate_skills = relationship("CandidateSkill", back_populates="skill")
    criteria_skills = relationship("CriteriaSkill", back_populates="skill")

    @property
    def synonyms_list(self) -> list[str]:
        if not self.synonyms:
            return []
        return [s.strip() for s in self.synonyms.split(",") if s.strip()]


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"
    __table_args__ = (
        UniqueConstraint("candidate_id", "skill_id", name="uq_candidate_skill"),
    )

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    proficiency_level = Column(Enum(ProficiencyLevel), nullable=False)
    source = Column(String, nullable=True)
    # 0.0 - 1.0, how confident the extractor is that this skill applies.
    confidence_score = Column(Float, nullable=True)

    candidate = relationship("Candidate", back_populates="candidate_skills")
    skill = relationship("Skill", back_populates="candidate_skills")


# ---------------------------------------------------------------- Experience / Education

class Experience(Base):
    __tablename__ = "experiences"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    duration_months = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    candidate = relationship("Candidate", back_populates="experiences")


class Education(Base):
    __tablename__ = "educations"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    degree = Column(String, nullable=False)
    institution = Column(String, nullable=False)
    field = Column(String, nullable=False)
    year = Column(Integer, nullable=True)
    # e.g. "bac", "licence", "master", "doctorat".
    level = Column(String, nullable=True)

    candidate = relationship("Candidate", back_populates="educations")


# ---------------------------------------------------------------- Job criteria

class JobCriteria(Base):
    __tablename__ = "job_criteria"

    id = Column(Integer, primary_key=True, index=True)
    recruiter_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    recruiter = relationship("User", back_populates="job_criteria")
    criteria_skills = relationship("CriteriaSkill", back_populates="criteria", cascade="all, delete-orphan")
    match_results = relationship("MatchResult", back_populates="criteria", cascade="all, delete-orphan")


class CriteriaSkill(Base):
    __tablename__ = "criteria_skills"
    __table_args__ = (
        UniqueConstraint("criteria_id", "skill_id", name="uq_criteria_skill"),
    )

    id = Column(Integer, primary_key=True, index=True)
    criteria_id = Column(Integer, ForeignKey("job_criteria.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    weight = Column(Integer, nullable=False)  # 0-100

    criteria = relationship("JobCriteria", back_populates="criteria_skills")
    skill = relationship("Skill", back_populates="criteria_skills")


# ---------------------------------------------------------------- Match results

class MatchResult(Base):
    __tablename__ = "match_results"
    __table_args__ = (
        UniqueConstraint("criteria_id", "candidate_id", name="uq_match_result"),
    )

    id = Column(Integer, primary_key=True, index=True)
    criteria_id = Column(Integer, ForeignKey("job_criteria.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Float, nullable=False)  # 0.0 - 1.0
    # Per-skill breakdown: {"python": {"weight": 40, "candidate_has": true, "score": 1.0}, ...}
    score_breakdown = Column(JSONBType, nullable=True)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, server_default=func.now())

    criteria = relationship("JobCriteria", back_populates="match_results")
    candidate = relationship("Candidate", back_populates="match_results")


# ---------------------------------------------------------------- Favorites

class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("recruiter_id", "candidate_id", name="uq_favorite"),
    )

    id = Column(Integer, primary_key=True, index=True)
    recruiter_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    recruiter = relationship("User", back_populates="favorites")
    candidate = relationship("Candidate", back_populates="favorites")
