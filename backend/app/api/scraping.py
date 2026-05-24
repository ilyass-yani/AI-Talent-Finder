"""
Scraping API Router
Provides endpoints to trigger job scraping and manage scraped results.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.models import JobCriteria, ScrapedJob, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scraping", tags=["scraping"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ScrapeRequest(BaseModel):
    keywords: str = Field(..., min_length=2, max_length=200, description="Job search keywords")
    location: str = Field("France", max_length=100)
    sources: List[str] = Field(default=["linkedin", "indeed"])
    max_per_source: int = Field(25, ge=1, le=100)
    fetch_descriptions: bool = Field(False, description="Fetch full job descriptions (slower)")


class ScrapedJobOut(BaseModel):
    id: int
    title: str
    company: Optional[str]
    location: Optional[str]
    description: Optional[str]
    url: Optional[str]
    source: Optional[str]
    keywords: Optional[str]
    contract_type: Optional[str]
    salary_range: Optional[str]
    posted_at: Optional[str]
    imported: bool

    class Config:
        from_attributes = True


class ImportJobRequest(BaseModel):
    recruiter_id: Optional[int] = None  # override; defaults to current user


class ScrapeStatusOut(BaseModel):
    total: int
    sources: dict
    keywords_summary: List[str]


# ---------------------------------------------------------------------------
# Background scraping task
# ---------------------------------------------------------------------------

def _run_scraping(
    keywords: str,
    location: str,
    sources: List[str],
    max_per_source: int,
    fetch_descriptions: bool,
    db: Session,
) -> int:
    """Background task: scrape and persist results."""
    try:
        from app.services.job_scraper import scrape_jobs
        offers = scrape_jobs(
            keywords=keywords,
            location=location,
            sources=sources,
            max_per_source=max_per_source,
            fetch_descriptions=fetch_descriptions,
        )
    except Exception as exc:
        logger.error("Scraping failed: %s", exc)
        return 0

    saved = 0
    for offer in offers:
        # Skip duplicates already in DB
        if offer.url:
            existing = db.query(ScrapedJob).filter(ScrapedJob.url == offer.url).first()
            if existing:
                continue

        job = ScrapedJob(
            title=offer.title,
            company=offer.company or None,
            location=offer.location or None,
            description=offer.description or None,
            url=offer.url or None,
            source=offer.source,
            keywords=keywords,
            contract_type=offer.contract_type or None,
            salary_range=offer.salary_range or None,
            posted_at=offer.posted_at or None,
        )
        db.add(job)
        saved += 1

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("DB commit failed: %s", exc)
        return 0

    logger.info("Saved %d new scraped jobs", saved)
    return saved


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/jobs", summary="Trigger job scraping", status_code=202)
async def trigger_scraping(
    req: ScrapeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Launch a background job scraping task.
    Scraped offers are stored in the `scraped_jobs` table.
    Returns immediately with a 202 Accepted response.
    """
    valid_sources = {"linkedin", "indeed"}
    sources = [s.lower() for s in req.sources if s.lower() in valid_sources]
    if not sources:
        raise HTTPException(status_code=400, detail="No valid sources specified. Use 'linkedin' and/or 'indeed'.")

    background_tasks.add_task(
        _run_scraping,
        keywords=req.keywords,
        location=req.location,
        sources=sources,
        max_per_source=req.max_per_source,
        fetch_descriptions=req.fetch_descriptions,
        db=db,
    )

    return {
        "status": "accepted",
        "message": f"Scraping started for '{req.keywords}' on {sources}. Results will be available shortly.",
        "keywords": req.keywords,
        "sources": sources,
    }


@router.post("/jobs/sync", summary="Scrape jobs synchronously (wait for result)")
def trigger_scraping_sync(
    req: ScrapeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Scrape jobs and wait for the result. Use for small requests (max_per_source ≤ 10).
    """
    if req.max_per_source > 10:
        raise HTTPException(
            status_code=400,
            detail="max_per_source must be ≤ 10 for synchronous scraping. Use the async endpoint for larger requests.",
        )

    valid_sources = {"linkedin", "indeed"}
    sources = [s.lower() for s in req.sources if s.lower() in valid_sources]
    if not sources:
        raise HTTPException(status_code=400, detail="No valid sources specified.")

    saved = _run_scraping(
        keywords=req.keywords,
        location=req.location,
        sources=sources,
        max_per_source=req.max_per_source,
        fetch_descriptions=req.fetch_descriptions,
        db=db,
    )

    return {"saved": saved, "keywords": req.keywords, "sources": sources}


@router.get("/jobs", response_model=List[ScrapedJobOut], summary="List scraped jobs")
def list_scraped_jobs(
    keywords: Optional[str] = Query(None, description="Filter by keywords"),
    source: Optional[str] = Query(None, description="Filter by source (linkedin/indeed)"),
    imported: Optional[bool] = Query(None, description="Filter by import status"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return stored scraped job offers with optional filters."""
    q = db.query(ScrapedJob)
    if keywords:
        q = q.filter(ScrapedJob.keywords.ilike(f"%{keywords}%"))
    if source:
        q = q.filter(ScrapedJob.source == source.lower())
    if imported is not None:
        q = q.filter(ScrapedJob.imported == imported)
    return q.order_by(ScrapedJob.scraped_at.desc()).offset(offset).limit(limit).all()


@router.get("/jobs/stats", response_model=ScrapeStatusOut, summary="Scraping statistics")
def scraping_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total = db.query(ScrapedJob).count()
    from sqlalchemy import func
    source_counts = (
        db.query(ScrapedJob.source, func.count(ScrapedJob.id))
        .group_by(ScrapedJob.source)
        .all()
    )
    keyword_rows = (
        db.query(ScrapedJob.keywords)
        .distinct()
        .limit(20)
        .all()
    )
    return ScrapeStatusOut(
        total=total,
        sources={src: count for src, count in source_counts},
        keywords_summary=[r[0] for r in keyword_rows if r[0]],
    )


@router.get("/jobs/{job_id}", response_model=ScrapedJobOut, summary="Get a scraped job")
def get_scraped_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(ScrapedJob).filter(ScrapedJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Scraped job not found")
    return job


@router.post("/jobs/{job_id}/import", summary="Import scraped job as JobCriteria")
def import_scraped_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Convert a scraped job offer into a JobCriteria record so it can be
    used for candidate matching.
    """
    scraped = db.query(ScrapedJob).filter(ScrapedJob.id == job_id).first()
    if not scraped:
        raise HTTPException(status_code=404, detail="Scraped job not found")

    if scraped.imported:
        raise HTTPException(status_code=409, detail="This job has already been imported")

    criteria = JobCriteria(
        recruiter_id=current_user.id,
        title=scraped.title,
        description=scraped.description or f"{scraped.title} @ {scraped.company or 'Unknown'}",
    )
    db.add(criteria)

    scraped.imported = True
    db.commit()
    db.refresh(criteria)

    return {
        "message": "Job imported successfully",
        "criteria_id": criteria.id,
        "scraped_job_id": scraped.id,
    }


@router.delete("/jobs/{job_id}", summary="Delete a scraped job", status_code=204)
def delete_scraped_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(ScrapedJob).filter(ScrapedJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Scraped job not found")
    db.delete(job)
    db.commit()
