from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.core.dependencies import get_db, require_admin
from app.models.models import User, ModerationStatus
from app.schemas.admin import (
    PaginatedUsersResponse,
    AdminUserResponse,
    UserStatusUpdate,
    PaginatedJobsResponse,
    AdminJobResponse,
    JobModerationUpdate,
    AdminStatsResponse,
)
from app.services import admin_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get("/users", response_model=PaginatedUsersResponse)
def list_users(
    skip: int = 0,
    limit: int = 50,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Liste paginée de tous les utilisateurs, filtrable par rôle/statut."""
    return admin_service.list_users(db, skip=skip, limit=limit, role=role, is_active=is_active)


@router.patch("/users/{user_id}/status", response_model=AdminUserResponse)
def update_user_status(
    user_id: int,
    body: UserStatusUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Activer ou désactiver un compte utilisateur."""
    user = admin_service.set_user_status(db, user_id=user_id, is_active=body.is_active)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Supprimer définitivement un compte utilisateur."""
    deleted = admin_service.delete_user(db, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


# ── Jobs ──────────────────────────────────────────────────────────────────────

@router.get("/jobs", response_model=PaginatedJobsResponse)
def list_jobs(
    skip: int = 0,
    limit: int = 50,
    moderation_status: Optional[str] = None,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Liste de toutes les offres avec leur statut de modération."""
    return admin_service.list_jobs(db, skip=skip, limit=limit, moderation_status=moderation_status)


@router.patch("/jobs/{job_id}/moderate", response_model=AdminJobResponse)
def moderate_job(
    job_id: int,
    body: JobModerationUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Valider ou rejeter une offre d'emploi."""
    job = admin_service.moderate_job(db, job_id=job_id, moderation_status=ModerationStatus(body.moderation_status.value))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Supprimer définitivement une offre d'emploi."""
    deleted = admin_service.delete_job(db, job_id=job_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=AdminStatsResponse)
def get_stats(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Dashboard : stats globales (candidats, recruteurs, offres actives, matchings)."""
    return admin_service.get_stats(db)
