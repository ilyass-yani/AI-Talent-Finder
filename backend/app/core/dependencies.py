"""
FastAPI dependencies: DB session + authentication / authorization.

Other modules should import from here (or from `app.core.deps`, which is an
alias kept for the prompt's spec). Routes already in the codebase rely on this
exact path — do not move it.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.models import User, UserRole


__all__ = [
    "get_db",
    "get_current_user",
    "get_current_active_user",
    "require_role",
    "get_current_admin",
    "get_current_recruiter",
    "get_current_candidate",
]


_BEARER_HEADERS = {"WWW-Authenticate": "Bearer"}


def _extract_bearer(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers=_BEARER_HEADERS,
        )
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format (expected 'Bearer <token>')",
            headers=_BEARER_HEADERS,
        )
    return parts[1]


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the current user from the `Authorization: Bearer <jwt>` header."""
    token = _extract_bearer(authorization)
    try:
        token_data = decode_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers=_BEARER_HEADERS,
        )

    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers=_BEARER_HEADERS,
        )
    return user


def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    """Like `get_current_user` but rejects deactivated accounts."""
    is_active = getattr(user, "is_active", True)
    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    return user


def require_role(*roles: UserRole):
    """Dependency factory: ensures the current user has one of the given roles."""
    allowed = {r.value if isinstance(r, UserRole) else r for r in roles}

    def checker(user: User = Depends(get_current_active_user)) -> User:
        user_role = user.role.value if hasattr(user.role, "value") else str(user.role)
        if user_role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {sorted(allowed)}",
            )
        return user

    return checker


def get_current_admin(user: User = Depends(get_current_active_user)) -> User:
    user_role = user.role.value if hasattr(user.role, "value") else str(user.role)
    if user_role != UserRole.admin.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user


def get_current_recruiter(user: User = Depends(get_current_active_user)) -> User:
    user_role = user.role.value if hasattr(user.role, "value") else str(user.role)
    if user_role not in {UserRole.recruiter.value, UserRole.admin.value}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Recruiter role required")
    return user


def get_current_candidate(user: User = Depends(get_current_active_user)) -> User:
    user_role = user.role.value if hasattr(user.role, "value") else str(user.role)
    if user_role != UserRole.candidate.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Candidate role required")
    return user
