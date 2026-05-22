"""Lightweight scraper scheduler using APScheduler.

Schedules periodic runs of the LinkedIn scraper and persists results to JSONL.
"""
import os
import json
import logging
from datetime import datetime
from typing import Optional
import sys
from pathlib import Path

# Ensure `scrapers` package is importable when running from project root
root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

logger = logging.getLogger(__name__)


def run_scrape_once(query: str, output_path: str, max_results: int = 50, proxy: Optional[str] = None, cookie_file: Optional[str] = None):
    try:
        from scrapers.linkedin_production import scrape_with_options
    except Exception as e:
        logger.exception("Scraper not available: %s", e)
        return

    results = scrape_with_options(query, max_results=max_results, headless=True, proxy=proxy, cookie_file=cookie_file, output=None)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "a", encoding="utf-8") as f:
        for r in results:
            payload = {"query": query, "timestamp": datetime.utcnow().isoformat(), **r}
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def start_scheduler(interval_minutes: int = 60, query: str = "data scientist", out_dir: str = "scrapes", proxy: Optional[str] = None, cookie_file: Optional[str] = None):
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except Exception:
        logger.error("APScheduler not installed; scheduler disabled")
        return None

    scheduler = BackgroundScheduler()

    def job():
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        out_path = os.path.join(out_dir, f"{query.replace(' ', '_')}_{ts}.jsonl")
        run_scrape_once(query=query, output_path=out_path, proxy=proxy, cookie_file=cookie_file)

    scheduler.add_job(job, 'interval', minutes=interval_minutes, next_run_time=datetime.utcnow())
    scheduler.start()
    logger.info("Scraper scheduler started: query=%s interval=%dm out=%s", query, interval_minutes, out_dir)
    return scheduler
