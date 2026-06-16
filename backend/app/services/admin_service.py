from typing import Optional
from sqlalchemy.orm import Session

from app.models.models import User, UserRole, JobCriteria, MatchResult, ModerationStatus
from app.schemas.admin import (
    AdminUserResponse,
    PaginatedUsersResponse,
    AdminJobResponse,
    PaginatedJobsResponse,
    AdminStatsResponse,
)


def list_users(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> PaginatedUsersResponse:
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()

    items = [
        AdminUserResponse(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role.value,
            is_active=u.is_active,
            created_at=u.created_at.isoformat(),
        )
        for u in users
    ]
    return PaginatedUsersResponse(total=total, items=items)


def set_user_status(db: Session, user_id: int, is_active: bool) -> AdminUserResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


def delete_user(db: Session, user_id: int) -> bool:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    db.delete(user)
    db.commit()
    return True


def list_jobs(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    moderation_status: Optional[str] = None,
) -> PaginatedJobsResponse:
    query = db.query(JobCriteria)
    if moderation_status:
        query = query.filter(JobCriteria.moderation_status == moderation_status)

    total = query.count()
    jobs = query.order_by(JobCriteria.created_at.desc()).offset(skip).limit(limit).all()

    items = [
        AdminJobResponse(
            id=j.id,
            title=j.title,
            description=j.description,
            moderation_status=j.moderation_status.value,
            recruiter_id=j.recruiter_id,
            recruiter_email=j.recruiter.email if j.recruiter else None,
            created_at=j.created_at.isoformat(),
        )
        for j in jobs
    ]
    return PaginatedJobsResponse(total=total, items=items)


def moderate_job(
    db: Session, job_id: int, moderation_status: ModerationStatus
) -> AdminJobResponse:
    job = db.query(JobCriteria).filter(JobCriteria.id == job_id).first()
    if not job:
        return None
    job.moderation_status = moderation_status
    db.commit()
    db.refresh(job)
    return AdminJobResponse(
        id=job.id,
        title=job.title,
        description=job.description,
        moderation_status=job.moderation_status.value,
        recruiter_id=job.recruiter_id,
        recruiter_email=job.recruiter.email if job.recruiter else None,
        created_at=job.created_at.isoformat(),
    )


def delete_job(db: Session, job_id: int) -> bool:
    job = db.query(JobCriteria).filter(JobCriteria.id == job_id).first()
    if not job:
        return False
    db.delete(job)
    db.commit()
    return True


def get_stats(db: Session) -> AdminStatsResponse:
    total_candidates = db.query(User).filter(User.role == UserRole.candidate).count()
    total_recruiters = db.query(User).filter(User.role == UserRole.recruiter).count()
    total_active_jobs = (
        db.query(JobCriteria)
        .filter(JobCriteria.moderation_status == ModerationStatus.approved)
        .count()
    )
    total_matchings = db.query(MatchResult).count()

    return AdminStatsResponse(
        total_candidates=total_candidates,
        total_recruiters=total_recruiters,
        total_active_jobs=total_active_jobs,
        total_matchings=total_matchings,
    )
