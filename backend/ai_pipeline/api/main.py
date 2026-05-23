"""FastAPI application entry point for the AI Talent Finder pipeline.

Boot the app with::

    uvicorn ai_pipeline.api.main:app --host 0.0.0.0 --port 8000 --reload
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .llm_router import router as llm_router
from .pipeline_router import router as pipeline_router
from .scraping_router import router as scraping_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Talent Finder pipeline API")
    yield
    logger.info("Shutting down AI Talent Finder pipeline API")


app = FastAPI(
    title="AI Talent Finder — Pipeline IA",
    description=(
        "API REST exposant le pipeline complet de matching intelligent "
        "CV ↔ offres d'emploi : extraction NLP, structuration, feature "
        "engineering, matching hybride (bi-encoder + cross-encoder), scoring "
        "métier, décision et explicabilité IA."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pipeline_router)
app.include_router(llm_router)
app.include_router(scraping_router)


@app.get("/", tags=["meta"])
def root():
    return {
        "name": "AI Talent Finder",
        "version": "1.0.0",
        "team": "ESISA-TechForge4",
        "docs": "/docs",
        "endpoints": [
            "/pipeline/match",
            "/pipeline/batch-match",
            "/llm/score",
            "/scraping/jobs",
        ],
    }
