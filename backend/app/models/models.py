from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    recruiter = "recruiter"
    candidate = "candidate"


class ModerationStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


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
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reset_password_token = Column(String, nullable=True, index=True)
    reset_password_token_expires = Column(DateTime, nullable=True)

    # Relationships
    job_criteria = relationship("JobCriteria", back_populates="recruiter")
    favorites = relationship("Favorite", back_populates="recruiter")
    candidate = relationship("Candidate", back_populates="user", uselist=False, foreign_keys="Candidate.user_id")


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, unique=True)
    recruiter_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    github_url = Column(String, nullable=True)
    cv_path = Column(String, nullable=True)
    raw_text = Column(Text, nullable=True)
    # Visibility: who deposited ("candidate" | "recruiter") and whether recruiters can see it
    owner_role = Column(String, nullable=True)  # "candidate" or "recruiter"
    is_visible = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)
    
    # NER Extraction Fields (Étape 5-6 optimization)
    extracted_name = Column(String, nullable=True)  # From NER
    extracted_emails = Column(Text, nullable=True)  # JSON list: ["email1", "email2"]
    extracted_phones = Column(Text, nullable=True)  # JSON list: ["+33612345"]
    extracted_job_titles = Column(Text, nullable=True)  # JSON list with confidence
    extracted_companies = Column(Text, nullable=True)  # JSON list with confidence
    extracted_education = Column(Text, nullable=True)  # JSON list
    extraction_quality_score = Column(Float, default=0.0)  # 0-100 quality metric
    ner_extraction_data = Column(Text, nullable=True)  # Full JSON from NER
    is_fully_extracted = Column(Boolean, default=False)  # Flag: quality > 70%

    # Relationships
    user = relationship("User", back_populates="candidate", foreign_keys=[user_id])
    # cascade="all, delete-orphan" ensures child rows are deleted (not nullified) when
    # the candidate is deleted. Without this, SQLAlchemy tries SET candidate_id=NULL
    # which violates the NOT NULL constraint on every child table.
    candidate_skills = relationship("CandidateSkill", back_populates="candidate", cascade="all, delete-orphan")
    experiences = relationship("Experience", back_populates="candidate", cascade="all, delete-orphan")
    educations = relationship("Education", back_populates="candidate", cascade="all, delete-orphan")
    match_results = relationship("MatchResult", back_populates="candidate", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="candidate", cascade="all, delete-orphan")


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
    moderation_status = Column(Enum(ModerationStatus), default=ModerationStatus.pending, nullable=False)
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


class SystemSetting(Base):
    """Admin use case: 'Configurer les paramètres du pipeline IA'.

    Key/value store (value is JSON-encoded) for runtime configuration such as
    the matching pipeline weights and decision thresholds.
    """
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(Text, nullable=True)  # JSON-encoded payload
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class ActivityLog(Base):
    """Admin use case: 'Superviser les logs et performances'.

    Lightweight audit trail of meaningful actions (auth, user management,
    configuration changes) used to power the admin monitoring view.
    """
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    level = Column(String, default="INFO", nullable=False)  # INFO | WARNING | ERROR
    action = Column(String, nullable=False, index=True)  # e.g. "user.create", "auth.login"
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    detail = Column(Text, nullable=True)

    user = relationship("User", foreign_keys=[user_id])


class RecruiterFeedback(Base):
    """Phase 3: Capture recruiter decisions vs model predictions for continuous learning."""
    __tablename__ = "recruiter_feedback"

    id = Column(Integer, primary_key=True, index=True)
    criteria_id = Column(Integer, ForeignKey("job_criteria.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    recruiter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Model prediction at time of decision
    model_predicted_score = Column(Float, nullable=False)  # 0.0-100.0
    model_predicted_decision = Column(String, nullable=False)  # "accepted" | "review" | "rejected"
    
    # Recruiter decision (can override model)
    recruiter_decision = Column(String, nullable=False)  # "accepted" | "rejected" | "no_action"
    recruiter_score_override = Column(Float, nullable=True)  # If recruiter gave explicit score
    
    # Context/reason for decision
    feedback_reason = Column(Text, nullable=True)  # Why recruiter accepted/rejected
    is_override = Column(Boolean, default=False)  # True if recruiter decision != model prediction
    
    # Outcome tracking
    hire_outcome = Column(String, nullable=True)  # "hired" | "rejected_later" | "unknown"
    hire_date = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    criteria = relationship("JobCriteria", foreign_keys=[criteria_id])
    candidate = relationship("Candidate", foreign_keys=[candidate_id])
    recruiter = relationship("User", foreign_keys=[recruiter_id])
