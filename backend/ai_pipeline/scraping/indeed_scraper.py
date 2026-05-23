"""Indeed scraper using Selenium (headless Chrome).

Indeed renders search results with JS and protects against headless
clients.  We use Selenium with stealth flags and a realistic user-agent
to retrieve the listings, then parse each card with BeautifulSoup.
"""
from __future__ import annotations

import logging
from typing import List, Optional
from urllib.parse import quote_plus

from .base_scraper import BaseScraper, ScrapedJob

logger = logging.getLogger(__name__)


class IndeedScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "indeed"

    def _make_driver(self):
        from selenium import webdriver  # type: ignore
        from selenium.webdriver.chrome.options import Options  # type: ignore

        opts = Options()
        opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument(f"--user-agent={self._random_user_agent()}")
        opts.add_argument("--window-size=1920,1080")
        return webdriver.Chrome(options=opts)

    def _search(self, query: str, location: str, max_results: int) -> List[str]:
        from bs4 import BeautifulSoup  # type: ignore

        driver = self._make_driver()
        urls: List[str] = []
        try:
            per_page = 10
            for page in range((max_results // per_page) + 1):
                search_url = (
                    "https://fr.indeed.com/jobs"
                    f"?q={quote_plus(query)}"
                    f"&l={quote_plus(location or '')}"
                    f"&start={page * per_page}"
                )
                driver.get(search_url)
                self._random_delay()
                soup = BeautifulSoup(driver.page_source, "html.parser")
                for card in soup.select("a.tapItem, a[data-jk]"):
                    jk = card.get("data-jk")
                    if jk:
                        urls.append(f"https://fr.indeed.com/viewjob?jk={jk}")
                    if len(urls) >= max_results:
                        return urls[:max_results]
        finally:
            driver.quit()
        return urls[:max_results]

    def _parse_job(self, url: str) -> Optional[ScrapedJob]:
        from bs4 import BeautifulSoup  # type: ignore

        driver = self._make_driver()
        try:
            driver.get(url)
            self._random_delay()
            soup = BeautifulSoup(driver.page_source, "html.parser")
        finally:
            driver.quit()

        title_el = soup.select_one("h1.jobsearch-JobInfoHeader-title, h1[data-testid='jobsearch-JobInfoHeader-title']")
        company_el = soup.select_one("div[data-company-name='true'] a, div[data-testid='inlineHeader-companyName']")
        loc_el = soup.select_one("div[data-testid='inlineHeader-companyLocation'], div.jobsearch-CompanyInfoContainer")
        desc_el = soup.select_one("div#jobDescriptionText, div.jobsearch-jobDescriptionText")

        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            return None

        jk = ""
        if "jk=" in url:
            jk = url.split("jk=")[-1].split("&")[0]

        return ScrapedJob(
            source="indeed",
            external_id=jk,
            title=title,
            company=company_el.get_text(strip=True) if company_el else "",
            location=loc_el.get_text(strip=True) if loc_el else "",
            description=desc_el.get_text("\n", strip=True) if desc_el else "",
            url=url,
        )
