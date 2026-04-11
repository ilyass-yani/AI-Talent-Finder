from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base


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


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.recruiter, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    job_criteria = relationship("JobCriteria", back_populates="recruiter")
    favorites = relationship("Favorite", back_populates="recruiter")
    candidate = relationship("Candidate", back_populates="user", uselist=False)


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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="candidate", foreign_keys=[user_id])
    candidate_skills = relationship("CandidateSkill", back_populates="candidate")
    experiences = relationship("Experience", back_populates="candidate")
    educations = relationship("Education", back_populates="candidate")
    match_results = relationship("MatchResult", back_populates="candidate")
    favorites = relationship("Favorite", back_populates="candidate")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    category = Column(Enum(SkillCategory), nullable=False)
    synonyms = Column(Text, nullable=True)  # Stored as comma-separated values

    # Relationships
    candidate_skills = relationship("CandidateSkill", back_populates="skill")
    criteria_skills = relationship("CriteriaSkill", back_populates="skill")


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False)
    proficiency_level = Column(Enum(ProficiencyLevel), nullable=False)
    source = Column(String, nullable=True)  # e.g., "CV", "LinkedIn", "AI extraction"

    # Relationships
    candidate = relationship("Candidate", back_populates="candidate_skills")
    skill = relationship("Skill", back_populates="candidate_skills")


class Experience(Base):
    __tablename__ = "experiences"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    duration_months = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)

    # Relationships
    candidate = relationship("Candidate", back_populates="experiences")


class Education(Base):
    __tablename__ = "educations"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    degree = Column(String, nullable=False)
    institution = Column(String, nullable=False)
    field = Column(String, nullable=False)
    year = Column(Integer, nullable=True)

    # Relationships
    candidate = relationship("Candidate", back_populates="educations")


class JobCriteria(Base):
    __tablename__ = "job_criteria"

    id = Column(Integer, primary_key=True, index=True)
    recruiter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    recruiter = relationship("User", back_populates="job_criteria")
    criteria_skills = relationship("CriteriaSkill", back_populates="criteria")
    match_results = relationship("MatchResult", back_populates="criteria")


class CriteriaSkill(Base):
    __tablename__ = "criteria_skills"

    id = Column(Integer, primary_key=True, index=True)
    criteria_id = Column(Integer, ForeignKey("job_criteria.id"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False)
    weight = Column(Integer, nullable=False)  # 0-100

    # Relationships
    criteria = relationship("JobCriteria", back_populates="criteria_skills")
    skill = relationship("Skill", back_populates="criteria_skills")


class MatchResult(Base):
    __tablename__ = "match_results"

    id = Column(Integer, primary_key=True, index=True)
    criteria_id = Column(Integer, ForeignKey("job_criteria.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    score = Column(Float, nullable=False)  # 0.0-1.0
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    criteria = relationship("JobCriteria", back_populates="match_results")
    candidate = relationship("Candidate", back_populates="match_results")


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    recruiter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    recruiter = relationship("User", back_populates="favorites")
    candidate = relationship("Candidate", back_populates="favorites")
