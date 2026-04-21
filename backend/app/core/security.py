"""
Password hashing and JWT token utilities.

Hashing uses Argon2id (preferred) with bcrypt as a fallback so legacy hashes
keep validating after migration.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.schemas.user import TokenData


# Re-exported for backwards compatibility with existing code that does
# `from app.core.security import ACCESS_TOKEN_EXPIRE_MINUTES`.
SECRET_KEY: str = settings.secret_key
ALGORITHM: str = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES: int = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS: int = settings.refresh_token_expire_days

# Argon2id is preferred (memory-hard, no 72-byte limit). bcrypt kept so users
# created before the migration can still log in until their next password change.
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    argon2__time_cost=3,
    argon2__memory_cost=64 * 1024,  # 64 MiB
    argon2__parallelism=2,
)


def _safe_for_bcrypt(password: str) -> str:
    """bcrypt silently truncates at 72 bytes — pre-truncate so behaviour is explicit."""
    return password.encode("utf-8")[:72].decode("utf-8", errors="ignore")


def get_password_hash(password: str) -> str:
    """Hash a plaintext password (Argon2id by default)."""
    return pwd_context.hash(_safe_for_bcrypt(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Constant-time verify a plaintext password against a stored hash."""
    if not hashed_password:
        return False
    try:
        return pwd_context.verify(_safe_for_bcrypt(plain_password), hashed_password)
    except (ValueError, TypeError):
        # Unrecognised hash format → treat as authentication failure (NEVER fall
        # back to plaintext compare; that would be a critical vulnerability).
        return False


def needs_rehash(hashed_password: str) -> bool:
    """True if the stored hash uses a deprecated scheme and should be upgraded."""
    return pwd_context.needs_update(hashed_password)


# ---------- JWT ----------

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _encode(claims: dict, expires_delta: timedelta) -> str:
    payload = claims.copy()
    payload.update({
        "exp": _now_utc() + expires_delta,
        "iat": _now_utc(),
    })
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a short-lived access token. `data` must include `sub` and `user_id`."""
    return _encode(
        {**data, "type": "access"},
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a long-lived refresh token used to mint new access tokens."""
    return _encode(
        {**data, "type": "refresh"},
        expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str, expected_type: str = "access") -> TokenData:
    """
    Decode a JWT and return its `TokenData`.

    Raises `JWTError` for any failure (expired, bad signature, missing claims,
    wrong token type). Callers should map this to HTTP 401.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise

    # Tokens minted before the type claim existed are treated as access tokens.
    token_type = payload.get("type", "access")
    if token_type != expected_type:
        raise JWTError(f"Expected token type '{expected_type}', got '{token_type}'")

    sub = payload.get("sub")
    user_id = payload.get("user_id")
    if not sub or user_id is None:
        raise JWTError("Token missing required claims (sub, user_id)")

    return TokenData(sub=sub, user_id=int(user_id))


# Alias kept so newer code can use the more conventional name.
verify_token = decode_token
