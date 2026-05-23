"""Base scraper class with retry, throttling, and structured output."""
from __future__ import annotations

import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ScrapedJob:
    """Canonical job posting record produced by all scrapers."""

    source: str
    external_id: str
    title: str
    company: str = ""
    location: str = ""
    description: str = ""
    skills: List[str] = field(default_factory=list)
    seniority: str = ""
    contract_type: str = ""
    salary: str = ""
    posted_at: Optional[str] = None
    url: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "external_id": self.external_id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "description": self.description,
            "skills": self.skills,
            "seniority": self.seniority,
            "contract_type": self.contract_type,
            "salary": self.salary,
            "posted_at": self.posted_at,
            "url": self.url,
        }


class BaseScraper(ABC):
    """Abstract base scraper.

    Subclasses must implement :meth:`_search` (returns a list of listing URLs)
    and :meth:`_parse_job` (fetches a single URL and returns ``ScrapedJob``).
    The base class adds throttling, retry, and graceful failure.
    """

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    ]

    def __init__(
        self,
        min_delay: float = 1.5,
        max_delay: float = 4.0,
        max_retries: int = 3,
        timeout: int = 20,
    ) -> None:
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.timeout = timeout

    @property
    @abstractmethod
    def source_name(self) -> str: ...

    @abstractmethod
    def _search(self, query: str, location: str, max_results: int) -> List[str]: ...

    @abstractmethod
    def _parse_job(self, url: str) -> Optional[ScrapedJob]: ...

    # ------------------------------------------------------------------ #
    # Utilities
    # ------------------------------------------------------------------ #
    def _random_delay(self) -> None:
        time.sleep(random.uniform(self.min_delay, self.max_delay))

    def _random_user_agent(self) -> str:
        return random.choice(self.USER_AGENTS)

    def _retry(self, func, *args, **kwargs):
        last_exc = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "[%s] Attempt %d/%d failed: %s",
                    self.source_name,
                    attempt,
                    self.max_retries,
                    exc,
                )
                time.sleep(min(2**attempt, 30))
        if last_exc:
            raise last_exc

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def scrape(
        self,
        query: str,
        location: str = "",
        max_results: int = 25,
    ) -> List[ScrapedJob]:
        logger.info(
            "[%s] Scraping: query=%r location=%r max=%d",
            self.source_name,
            query,
            location,
            max_results,
        )
        urls = self._retry(self._search, query, location, max_results)
        jobs: List[ScrapedJob] = []
        for url in urls:
            self._random_delay()
            try:
                job = self._parse_job(url)
                if job:
                    jobs.append(job)
            except Exception as exc:
                logger.warning("[%s] Failed to parse %s: %s", self.source_name, url, exc)
        logger.info("[%s] Scraped %d jobs", self.source_name, len(jobs))
        return jobs
