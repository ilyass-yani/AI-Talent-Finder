"""Welcome to the Jungle scraper.

WTTJ exposes a public Algolia-backed search API that returns clean JSON,
which is far more robust than HTML scraping.  The endpoint and search
parameters are public (used by their own frontend).
"""
from __future__ import annotations

import json
import logging
from typing import List, Optional

from .base_scraper import BaseScraper, ScrapedJob

logger = logging.getLogger(__name__)

_ALGOLIA_URL = (
    "https://csekhvms53-dsn.algolia.net/1/indexes/wttj_jobs_production_fr/query"
)
# These are public client-side credentials used by their web app
_ALGOLIA_APP_ID = "CSEKHVMS53"
_ALGOLIA_API_KEY = "ce2dd47e9bdde2cb1a7c7e9888a2cb05"


class WelcomeToTheJungleScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "welcometothejungle"

    def _post_json(self, url: str, payload: dict) -> dict:
        import requests  # type: ignore

        headers = {
            "Content-Type": "application/json",
            "User-Agent": self._random_user_agent(),
            "X-Algolia-Application-Id": _ALGOLIA_APP_ID,
            "X-Algolia-API-Key": _ALGOLIA_API_KEY,
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _search(self, query: str, location: str, max_results: int) -> List[str]:
        results: List[str] = []
        page = 0
        per_page = 20
        while len(results) < max_results:
            payload = {
                "query": query,
                "page": page,
                "hitsPerPage": per_page,
                "filters": f'offices.country_code:"FR"' if location.lower() == "france" else "",
            }
            data = self._retry(self._post_json, _ALGOLIA_URL, payload)
            hits = data.get("hits", [])
            if not hits:
                break
            for hit in hits:
                slug = hit.get("slug") or hit.get("objectID")
                if slug:
                    # store the full hit as a serialised URL to avoid a second fetch
                    results.append("wttj://" + json.dumps(hit))
                if len(results) >= max_results:
                    break
            page += 1
            self._random_delay()
        return results[:max_results]

    def _parse_job(self, url: str) -> Optional[ScrapedJob]:
        # We stored the full Algolia hit as JSON to avoid a second request
        if url.startswith("wttj://"):
            hit = json.loads(url[len("wttj://"):])
        else:
            return None

        title = hit.get("name") or hit.get("title", "")
        if not title:
            return None

        org = hit.get("organization", {}) or {}
        office = (hit.get("offices") or [{}])[0]
        contract = hit.get("contract_type", {}) or {}

        return ScrapedJob(
            source="welcometothejungle",
            external_id=hit.get("objectID", ""),
            title=title,
            company=org.get("name", ""),
            location=", ".join(filter(None, [office.get("city"), office.get("country")])),
            description=hit.get("description", "") or hit.get("description_employment_status", ""),
            contract_type=contract.get("en", "") or contract.get("fr", ""),
            posted_at=hit.get("published_at"),
            url=f"https://www.welcometothejungle.com/fr/jobs/{hit.get('slug', '')}",
            raw=hit,
        )
