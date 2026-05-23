"""FastAPI router for job-board scraping endpoints."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..scraping.indeed_scraper import IndeedScraper
from ..scraping.linkedin_scraper import LinkedInScraper
from ..scraping.welcometothejungle_scraper import WelcomeToTheJungleScraper

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scraping", tags=["scraping"])

_SCRAPERS = {
    "linkedin": LinkedInScraper,
    "indeed": IndeedScraper,
    "welcometothejungle": WelcomeToTheJungleScraper,
}


class JobScrapeResponse(BaseModel):
    source: str
    count: int
    jobs: List[Dict[str, Any]]


@router.get(
    "/jobs",
    response_model=JobScrapeResponse,
    summary="Scrape les offres d'emploi d'une source",
    description=(
        "Récupère un échantillon d'offres depuis une source publique. "
        "Limites de débit appliquées; usage académique uniquement."
    ),
)
def scrape_jobs(
    source: str = Query(..., pattern="^(linkedin|indeed|welcometothejungle)$"),
    query: str = Query(..., min_length=2),
    location: str = "",
    max_results: int = Query(10, ge=1, le=50),
) -> JobScrapeResponse:
    scraper_cls = _SCRAPERS.get(source)
    if scraper_cls is None:
        raise HTTPException(status_code=400, detail=f"Unknown source: {source}")

    scraper = scraper_cls()
    try:
        jobs = scraper.scrape(query=query, location=location, max_results=max_results)
    except Exception as exc:
        logger.exception("Scrape failed")
        raise HTTPException(status_code=502, detail=f"Scrape error: {exc}")

    return JobScrapeResponse(
        source=source,
        count=len(jobs),
        jobs=[j.to_dict() for j in jobs],
    )
