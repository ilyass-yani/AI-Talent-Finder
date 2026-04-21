"""
Centralised application settings.

Loaded once from environment variables (and optional .env file) at import time.
Use `from app.core.config import settings` everywhere — never read os.environ
directly outside this module.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve project root (.env lives at <repo>/.env, two levels above this file's parent).
_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- Database ----
    database_url: str = Field(..., alias="DATABASE_URL")

    # ---- Security / JWT ----
    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(48))"
    secret_key: str = Field(
        default="dev-secret-do-not-use-in-production-please-set-SECRET_KEY-32+chars",
        alias="SECRET_KEY",
        min_length=32,
    )
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # ---- LLM ----
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    # Backwards-compat: existing code reads ANTHROPIC_API_KEY.
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    llm_model: str = Field(default="claude-sonnet-4-6", alias="LLM_MODEL")
    llm_max_tokens: int = Field(default=2048, alias="LLM_MAX_TOKENS")
    llm_temperature: float = Field(default=0.3, alias="LLM_TEMPERATURE")

    # ---- NLP ----
    spacy_model: str = Field(default="fr_core_news_md", alias="SPACY_MODEL")

    # ---- Application ----
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")
    backend_url: str = Field(default="http://localhost:8000", alias="BACKEND_URL")
    frontend_url: str = Field(default="http://localhost:3000", alias="FRONTEND_URL")
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:3001",
        alias="ALLOWED_ORIGINS",
    )

    # ---- Uploads ----
    cv_upload_dir: str = Field(default="./uploads/cvs", alias="CV_UPLOAD_DIR")
    max_upload_size_mb: int = Field(default=10, alias="MAX_UPLOAD_SIZE_MB")

    # ---- Rate limiting ----
    rate_limit_auth: str = Field(default="5/minute", alias="RATE_LIMIT_AUTH")
    rate_limit_default: str = Field(default="100/minute", alias="RATE_LIMIT_DEFAULT")

    # ---------- Derived helpers ----------
    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def effective_llm_api_key(self) -> str:
        """Prefer LLM_API_KEY, fall back to ANTHROPIC_API_KEY for backwards compat."""
        return self.llm_api_key or self.anthropic_api_key

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @field_validator("database_url")
    @classmethod
    def _normalize_postgres_scheme(cls, v: str) -> str:
        # Some providers (Heroku/Render) hand out postgres:// — SQLAlchemy 2 wants postgresql://.
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


# Singleton — import this everywhere.
settings = get_settings()
