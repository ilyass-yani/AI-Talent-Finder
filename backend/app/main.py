"""
FastAPI application entry point.

Schema lifecycle is managed by Alembic — never call `Base.metadata.create_all`
in production. To apply pending migrations on startup, run:

    docker compose exec backend alembic upgrade head
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings


# ----- Logging configured before importing routes so their loggers inherit it.
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
)
logger = logging.getLogger("ai_talent_finder")

# Routes (imported after logging setup).
from app.api import (  # noqa: E402
    auth,
    candidates,
    educations,
    experiences,
    favorites,
    jobs,
    match_results,
    matching,
    skills,
)
from app.api.chat import router as chat_router  # noqa: E402
from app.api.criteria import criteria_router, matching_router  # noqa: E402
from app.api.export import router as export_router  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup checks; warn loudly when running with insecure defaults."""
    logger.info("Starting AI Talent Finder | env=%s debug=%s", settings.environment, settings.debug)

    if settings.is_production and settings.secret_key.startswith("dev-secret"):
        logger.error("SECRET_KEY is the development default while ENVIRONMENT=production. Set SECRET_KEY!")
    if not settings.effective_llm_api_key:
        logger.warning("No LLM_API_KEY set — chatbot and profile generation will fail at request time.")

    yield
    logger.info("Shutting down AI Talent Finder")


app = FastAPI(
    title="AI Talent Finder",
    version="1.0.0",
    description="Plateforme de recrutement IA — analyse CV, matching pondéré, chatbot.",
    redirect_slashes=False,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ---------- Middleware ----------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_log_middleware(request: Request, call_next):
    """Tag every request with an id and log method/path/status/duration."""
    request_id = request.headers.get("x-request-id", uuid.uuid4().hex[:12])
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.exception("[%s] %s %s -> 500 (%dms)", request_id, request.method, request.url.path, duration_ms)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id},
        )
    duration_ms = int((time.perf_counter() - start) * 1000)
    logger.info(
        "[%s] %s %s -> %d (%dms)",
        request_id, request.method, request.url.path, response.status_code, duration_ms,
    )
    response.headers["x-request-id"] = request_id
    return response


# ---------- Routes ----------

# Order matters: auth first so OpenAPI docs read top-down naturally.
app.include_router(auth.router)
app.include_router(candidates.router)
app.include_router(skills.router)
app.include_router(jobs.router)
app.include_router(criteria_router)
app.include_router(matching_router)
app.include_router(matching.router)
app.include_router(favorites.router)
app.include_router(experiences.router)
app.include_router(educations.router)
app.include_router(match_results.router)
app.include_router(chat_router)
app.include_router(export_router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness probe — used by Docker healthcheck and CI."""
    return {
        "status": "ok",
        "version": app.version,
        "environment": settings.environment,
    }


@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "name": app.title,
        "version": app.version,
        "docs": "/docs",
        "health": "/health",
    }
