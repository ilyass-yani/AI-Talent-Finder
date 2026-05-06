import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from root .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from app.core.database import Base, engine
import importlib
import logging

# Initialize FastAPI app early so lightweight endpoints work even if heavy
# ML-related dependencies fail to import. Routers are added conditionally.
app = FastAPI(
    title="AI Talent Finder",
    version="1.0.0",
    redirect_slashes=False,
)

# Configure CORS
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def include_optional_router(module_path: str, attr_name: str = "router"):
    try:
        module = importlib.import_module(module_path)
        router = getattr(module, attr_name)
        app.include_router(router)
        logging.info(f"Included router {module_path}.{attr_name}")
    except Exception as e:
        logging.warning(f"Skipping router {module_path}.{attr_name}: {e}")


@app.on_event("startup")
def on_startup():
    # Ensure database tables exist (best-effort)
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        logging.exception("Failed to create database tables: %s", e)

    # Conditionally include API routers. If a router import fails (e.g. heavy
    # ML dependencies missing), the app still starts and exposes /health.
    include_optional_router("app.api.auth")
    include_optional_router("app.api.candidates")
    include_optional_router("app.api.skills")
    include_optional_router("app.api.jobs")
    # Ensure static matching endpoints in app.api.matching are registered
    # before the dynamic routes in app.api.criteria.matching_router so
    # paths like /api/matching/generate-and-match don't get captured by
    # the generic /api/matching/{criteria_id} route.
    include_optional_router("app.api.matching")
    include_optional_router("app.api.scoring")
    include_optional_router("app.api.criteria", "criteria_router")
    include_optional_router("app.api.favorites")
    include_optional_router("app.api.experiences")
    include_optional_router("app.api.educations")
    include_optional_router("app.api.match_results")
    include_optional_router("app.api.chat", "router")
    include_optional_router("app.api.export", "router")


# Health check endpoint (always available)
@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
