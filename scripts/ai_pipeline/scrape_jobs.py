#!/usr/bin/env python
"""Scrape jobs from a public board into a JSONL file.

Usage:
    python scripts/scrape_jobs.py \
        --source welcometothejungle \
        --query "data scientist" \
        --location France \
        --max 30 \
        --output data/wttj_jobs.jsonl
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from ai_pipeline.scraping.indeed_scraper import IndeedScraper
from ai_pipeline.scraping.linkedin_scraper import LinkedInScraper
from ai_pipeline.scraping.welcometothejungle_scraper import WelcomeToTheJungleScraper

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SCRAPERS = {
    "linkedin": LinkedInScraper,
    "indeed": IndeedScraper,
    "welcometothejungle": WelcomeToTheJungleScraper,
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Scrape jobs from a public board")
    p.add_argument("--source", required=True, choices=list(SCRAPERS))
    p.add_argument("--query", required=True)
    p.add_argument("--location", default="")
    p.add_argument("--max", type=int, default=20)
    p.add_argument("--output", required=True)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    scraper = SCRAPERS[args.source]()
    jobs = scraper.scrape(query=args.query, location=args.location, max_results=args.max)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        for j in jobs:
            fh.write(json.dumps(j.to_dict(), ensure_ascii=False) + "\n")
    logger.info("Wrote %d jobs → %s", len(jobs), out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
