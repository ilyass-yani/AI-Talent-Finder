import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from dotenv import load_dotenv

# Load environment variables from root .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from app.core.database import Base, engine
from app.core.capabilities import assert_required_features, get_capabilities, log_capabilities_summary
import importlib
import logging


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Middleware to ensure redirects use HTTPS in production.
    When deployed behind a reverse proxy (e.g., Railway), the request arrives as HTTP
    but should redirect to HTTPS. Starlette's redirect_slashes uses the request scheme,
    so we wrap the scope to force HTTPS redirects in production.
    """
    async def dispatch(self, request: Request, call_next):
        # In production, ensure the scheme seen by Starlette is HTTPS
        # by checking X-Forwarded-Proto header (set by reverse proxies)
        if (os.getenv("NODE_ENV") == "production" or 
            os.getenv("RAILWAY_ENVIRONMENT_NAME") == "production"):
            forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
            if forwarded_proto == "https":
                # Force the scope to use https so redirects are generated correctly
                request.scope["scheme"] = "https"
        
        return await call_next(request)


# Initialize FastAPI app early so lightweight endpoints work even if heavy
# ML-related dependencies fail to import. Routers are added conditionally.
app = FastAPI(
    title="AI Talent Finder",
    version="1.0.0",
    # Allow automatic redirect from paths without trailing slash to their
    # canonical route with trailing slash. This prevents 404s for clients
    # that omit the trailing slash while endpoints require it.
    redirect_slashes=True,
)

# Add HTTPS redirect middleware BEFORE CORS to catch all requests
app.add_middleware(HTTPSRedirectMiddleware)

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


_ROUTERS_REGISTERED = False


def register_optional_routers():
    global _ROUTERS_REGISTERED
    if _ROUTERS_REGISTERED:
        return

    include_optional_router("app.api.auth")
    include_optional_router("app.api.candidates")
    include_optional_router("app.api.skills")
    include_optional_router("app.api.jobs")
    include_optional_router("app.api.scoring")
    include_optional_router("app.api.criteria", "criteria_router")
    include_optional_router("app.api.criteria", "matching_router")
    include_optional_router("app.api.favorites")
    include_optional_router("app.api.experiences")
    include_optional_router("app.api.educations")
    include_optional_router("app.api.match_results")
    include_optional_router("app.api.chat", "router")
    include_optional_router("app.api.export", "router")
    # Ensure the full matching API (rich endpoints like /predict) is included when available
    include_optional_router("app.api.matching", "router")
    include_optional_router("app.api.pipeline", "router")
    include_optional_router("app.api.models", "router")
    # Advanced features: Mistral fine-tuning, BERT embeddings, web scraping
    include_optional_router("app.api.advanced_features", "router")
    _ROUTERS_REGISTERED = True


# Register routers immediately so bare TestClient(app) instances see them even
# when the startup event is not used.
register_optional_routers()


@app.on_event("startup")
def on_startup():
    # Ensure database tables exist (best-effort)
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        logging.exception("Failed to create database tables: %s", e)

    capabilities = log_capabilities_summary()
    assert_required_features(capabilities)

    # Conditionally include API routers. If a router import fails (e.g. heavy
    # ML dependencies missing), the app still starts and exposes /health.
    register_optional_routers()
    # Start optional background scheduler for scraping when configured
    try:
        if os.getenv("START_SCRAPER_SCHEDULER", "0") == "1":
            from jobs.scraper_scheduler import start_scheduler
            # configure via env vars
            interval = int(os.getenv("SCRAPER_INTERVAL_MINUTES", "60"))
            query = os.getenv("SCRAPER_QUERY", "data scientist")
            out_dir = os.getenv("SCRAPER_OUT_DIR", "scrapes")
            proxy = os.getenv("SCRAPER_PROXY", None)
            cookie_file = os.getenv("SCRAPER_COOKIE_FILE", None)
            start_scheduler(interval_minutes=interval, query=query, out_dir=out_dir, proxy=proxy, cookie_file=cookie_file)
    except Exception as e:
        logging.exception("Failed to start scraper scheduler: %s", e)
    # Phase 3: Feedback loop, recommendations, bias detection
    include_optional_router("app.api.feedback", "router")


# Health check endpoint (always available)
@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/health/deps")
def health_deps():
    return get_capabilities()
