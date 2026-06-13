"""Admin API endpoints — implements the Administrateur use cases.

Use cases (from the PFA use-case diagram, package "Administrateur"):
  * Gérer les utilisateurs (CRUD)            -> /api/admin/users ...
  * Consulter les statistiques globales      -> /api/admin/stats
  * Superviser les logs et performances      -> /api/admin/health, /api/admin/logs
  * Configurer les paramètres du pipeline IA -> /api/admin/pipeline-config

All routes require an authenticated user with the ``admin`` role.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user, require_admin, log_activity
from app.core.security import get_password_hash
from app.models.models import (
    User,
    UserRole,
    Candidate,
    JobCriteria,
    MatchResult,
    RecruiterFeedback,
    Skill,
    ActivityLog,
)
from app.schemas.admin import (
    AdminUserCreate,
    AdminUserUpdate,
    AdminUserResponse,
    GlobalStatsResponse,
    ActivityLogResponse,
    SystemHealthResponse,
    PipelineConfigResponse,
    PipelineConfigUpdate,
)
from app.core import settings_store


router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


# ===========================================================================
# Gérer les utilisateurs (CRUD)
# ===========================================================================

@router.get("/users", response_model=List[AdminUserResponse])
def list_users(
    role: Optional[UserRole] = Query(None, description="Filtrer par rôle"),
    search: Optional[str] = Query(None, description="Recherche email / nom"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all users (optionally filtered by role or a search term)."""
    query = db.query(User)
    if role is not None:
        query = query.filter(User.role == role)
    if search:
        like = f"%{search.lower()}%"
        query = query.filter(
            func.lower(User.email).like(like) | func.lower(User.full_name).like(like)
        )
    return query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/users", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_user),
):
    """Create a new user with any role."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email déjà utilisé")

    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        role=UserRole(payload.role.value),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_activity(db, "user.create", user_id=admin.id, detail=f"Création de {user.email} ({user.role.value})")
    return user


@router.get("/users/{user_id}", response_model=AdminUserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    return user


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_user),
):
    """Update a user's name, role and/or password."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.role is not None:
        # Guard: prevent removing the last admin.
        if user.role == UserRole.admin and payload.role != UserRole.admin:
            _assert_not_last_admin(db, user.id)
        user.role = UserRole(payload.role.value)
    if payload.password is not None:
        user.hashed_password = get_password_hash(payload.password)

    db.commit()
    db.refresh(user)

    log_activity(db, "user.update", user_id=admin.id, detail=f"Mise à jour de {user.email}")
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_user),
):
    """Delete a user. An admin cannot delete themselves or the last admin."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    if user.id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vous ne pouvez pas supprimer votre propre compte")
    if user.role == UserRole.admin:
        _assert_not_last_admin(db, user.id)

    email = user.email
    db.delete(user)
    db.commit()

    log_activity(db, "user.delete", user_id=admin.id, detail=f"Suppression de {email}")
    return None


def _assert_not_last_admin(db: Session, excluded_user_id: int) -> None:
    remaining_admins = (
        db.query(func.count(User.id))
        .filter(User.role == UserRole.admin, User.id != excluded_user_id)
        .scalar()
    )
    if not remaining_admins:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible: au moins un administrateur doit subsister",
        )


# ===========================================================================
# Consulter les statistiques globales
# ===========================================================================

@router.get("/stats", response_model=GlobalStatsResponse)
def global_stats(db: Session = Depends(get_db)):
    """Aggregate platform-wide statistics for the admin dashboard."""
    role_rows = (
        db.query(User.role, func.count(User.id)).group_by(User.role).all()
    )
    users_by_role = {role.value if hasattr(role, "value") else str(role): count for role, count in role_rows}
    total_users = sum(users_by_role.values())

    avg_score = db.query(func.avg(MatchResult.score)).scalar()
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_signups = db.query(func.count(User.id)).filter(User.created_at >= week_ago).scalar() or 0

    return GlobalStatsResponse(
        total_users=total_users,
        users_by_role=users_by_role,
        total_candidates=db.query(func.count(Candidate.id)).scalar() or 0,
        total_jobs=db.query(func.count(JobCriteria.id)).scalar() or 0,
        total_match_results=db.query(func.count(MatchResult.id)).scalar() or 0,
        total_feedback=db.query(func.count(RecruiterFeedback.id)).scalar() or 0,
        total_skills=db.query(func.count(Skill.id)).scalar() or 0,
        average_match_score=round(float(avg_score), 4) if avg_score is not None else None,
        recent_signups=recent_signups,
    )


# ===========================================================================
# Superviser les logs et performances
# ===========================================================================

@router.get("/logs", response_model=List[ActivityLogResponse])
def list_logs(
    level: Optional[str] = Query(None, description="INFO | WARNING | ERROR"),
    action: Optional[str] = Query(None, description="Filtrer par préfixe d'action"),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    """Return the most recent activity-log entries."""
    query = db.query(ActivityLog)
    if level:
        query = query.filter(ActivityLog.level == level.upper())
    if action:
        query = query.filter(ActivityLog.action.like(f"{action}%"))
    return query.order_by(ActivityLog.timestamp.desc()).limit(limit).all()


@router.get("/health", response_model=SystemHealthResponse)
def system_health(db: Session = Depends(get_db)):
    """System health snapshot: DB connectivity, capabilities and counts."""
    database_connected = True
    try:
        db.query(func.count(User.id)).scalar()
    except Exception:
        database_connected = False

    try:
        from app.core.capabilities import get_capabilities
        capabilities = get_capabilities()
    except Exception:
        capabilities = {}

    counts = {
        "users": db.query(func.count(User.id)).scalar() or 0,
        "candidates": db.query(func.count(Candidate.id)).scalar() or 0,
        "jobs": db.query(func.count(JobCriteria.id)).scalar() or 0,
        "match_results": db.query(func.count(MatchResult.id)).scalar() or 0,
        "logs": db.query(func.count(ActivityLog.id)).scalar() or 0,
    }

    level_rows = (
        db.query(ActivityLog.level, func.count(ActivityLog.id))
        .group_by(ActivityLog.level)
        .all()
    )
    log_levels = {level: count for level, count in level_rows}

    return SystemHealthResponse(
        status="ok" if database_connected else "degraded",
        database_connected=database_connected,
        capabilities=capabilities,
        counts=counts,
        log_levels=log_levels,
    )


# ===========================================================================
# Configurer les paramètres du pipeline IA
# ===========================================================================

def _pipeline_config_response() -> PipelineConfigResponse:
    cfg = settings_store.get_runtime_pipeline_config()
    return PipelineConfigResponse(defaults=settings_store.DEFAULT_PIPELINE_CONFIG, **cfg)


@router.get("/pipeline-config", response_model=PipelineConfigResponse)
def get_pipeline_config(db: Session = Depends(get_db)):
    """Return the current AI matching pipeline parameters."""
    settings_store.load_pipeline_config(db)
    return _pipeline_config_response()


@router.put("/pipeline-config", response_model=PipelineConfigResponse)
def update_pipeline_config(
    payload: PipelineConfigUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_user),
):
    """Update one or more pipeline parameters (weights / thresholds)."""
    partial = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not partial:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Aucun paramètre fourni")

    errors = settings_store.validate_pipeline_config(partial)
    if errors:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=errors)

    settings_store.update_pipeline_config(db, partial, updated_by=admin.id)
    log_activity(db, "pipeline.config.update", user_id=admin.id, detail=str(partial))
    return _pipeline_config_response()


@router.post("/pipeline-config/reset", response_model=PipelineConfigResponse)
def reset_pipeline_config(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_user),
):
    """Reset pipeline parameters back to their default values."""
    settings_store.reset_pipeline_config(db, updated_by=admin.id)
    log_activity(db, "pipeline.config.reset", user_id=admin.id, detail="Réinitialisation des paramètres")
    return _pipeline_config_response()
