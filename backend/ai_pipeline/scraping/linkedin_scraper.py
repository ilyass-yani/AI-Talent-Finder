"""LinkedIn job scraper using LinkedIn's public guest-view endpoint.

LinkedIn exposes a paginated job-listing endpoint at
``/jobs-guest/jobs/api/seeMoreJobPostings/search`` that returns HTML
fragments without requiring authentication.  We parse those fragments
with BeautifulSoup, then fetch each job's detail card.

Note on legality: scraping LinkedIn at scale violates their ToS. Use
this module only for academic experimentation, with low rates, and on
data you legitimately need to demonstrate the pipeline.
"""
from __future__ import annotations

import logging
import re
from typing import List, Optional
from urllib.parse import quote_plus

from .base_scraper import BaseScraper, ScrapedJob

logger = logging.getLogger(__name__)

_LISTING_URL = (
    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    "?keywords={kw}&location={loc}&start={start}"
)
_DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"


class LinkedInScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "linkedin"

    def _http_get(self, url: str) -> str:
        import requests  # type: ignore

        headers = {
            "User-Agent": self._random_user_agent(),
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        }
        resp = requests.get(url, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.text

    def _search(self, query: str, location: str, max_results: int) -> List[str]:
        from bs4 import BeautifulSoup  # type: ignore

        ids: List[str] = []
        per_page = 25
        for page in range((max_results // per_page) + 1):
            url = _LISTING_URL.format(
                kw=quote_plus(query),
                loc=quote_plus(location or ""),
                start=page * per_page,
            )
            html = self._retry(self._http_get, url)
            soup = BeautifulSoup(html, "html.parser")
            for card in soup.select("div.base-card"):
                jid = card.get("data-entity-urn", "").split(":")[-1]
                if jid and jid.isdigit():
                    ids.append(jid)
                if len(ids) >= max_results:
                    return ids[:max_results]
            self._random_delay()
        return ids[:max_results]

    def _parse_job(self, job_id_or_url: str) -> Optional[ScrapedJob]:
        from bs4 import BeautifulSoup  # type: ignore

        job_id = job_id_or_url.rsplit("/", 1)[-1]
        url = _DETAIL_URL.format(job_id=job_id)
        html = self._retry(self._http_get, url)
        soup = BeautifulSoup(html, "html.parser")

        title_el = soup.select_one("h2.top-card-layout__title, h1.top-card-layout__title")
        company_el = soup.select_one("a.topcard__org-name-link, span.topcard__flavor")
        loc_el = soup.select_one("span.topcard__flavor--bullet")
        desc_el = soup.select_one("div.show-more-less-html__markup")
        seniority_el = soup.find("h3", string=re.compile("Seniority", re.I))
        seniority = ""
        if seniority_el and seniority_el.find_next("span"):
            seniority = seniority_el.find_next("span").get_text(strip=True)

        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            return None

        return ScrapedJob(
            source="linkedin",
            external_id=job_id,
            title=title,
            company=company_el.get_text(strip=True) if company_el else "",
            location=loc_el.get_text(strip=True) if loc_el else "",
            description=desc_el.get_text("\n", strip=True) if desc_el else "",
            seniority=seniority,
            url=f"https://www.linkedin.com/jobs/view/{job_id}",
        )
