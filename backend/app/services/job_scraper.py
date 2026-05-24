"""
Job Scraper Service
Scrapes job offers from LinkedIn and Indeed using Selenium.
Designed to be used both from FastAPI endpoints and standalone CLI scripts.
"""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional imports with graceful degradation
# ---------------------------------------------------------------------------
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (
        TimeoutException,
        NoSuchElementException,
        WebDriverException,
    )
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("selenium not installed – job scraping disabled")

try:
    from bs4 import BeautifulSoup  # type: ignore
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class JobOffer:
    title: str
    company: str = ""
    location: str = ""
    description: str = ""
    url: str = ""
    source: str = ""
    keywords: str = ""
    contract_type: str = ""
    salary_range: str = ""
    posted_at: str = ""


# ---------------------------------------------------------------------------
# User-Agent pool (rotate to reduce bot detection)
# ---------------------------------------------------------------------------

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]


def _build_driver(headless: bool = True) -> "webdriver.Chrome":
    """Create a Selenium Chrome WebDriver with anti-detection options."""
    options = ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(f"--user-agent={random.choice(_USER_AGENTS)}")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=fr-FR,fr;q=0.9,en;q=0.8")

    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    return driver


def _random_delay(min_s: float = 1.5, max_s: float = 4.0) -> None:
    time.sleep(random.uniform(min_s, max_s))


# ---------------------------------------------------------------------------
# LinkedIn scraper
# ---------------------------------------------------------------------------

class LinkedInScraper:
    """Scrapes job listings from LinkedIn Jobs (public search, no login required)."""

    BASE_URL = "https://www.linkedin.com/jobs/search/"

    def __init__(self, headless: bool = True):
        self.headless = headless

    def scrape(
        self,
        keywords: str,
        location: str = "France",
        max_results: int = 25,
    ) -> List[JobOffer]:
        if not SELENIUM_AVAILABLE:
            raise RuntimeError("selenium is required for LinkedIn scraping")

        driver = _build_driver(self.headless)
        offers: List[JobOffer] = []
        try:
            offers = self._do_scrape(driver, keywords, location, max_results)
        finally:
            try:
                driver.quit()
            except Exception:
                pass
        return offers

    def _do_scrape(
        self,
        driver: "webdriver.Chrome",
        keywords: str,
        location: str,
        max_results: int,
    ) -> List[JobOffer]:
        url = (
            f"{self.BASE_URL}?keywords={quote_plus(keywords)}"
            f"&location={quote_plus(location)}&f_TPR=r604800"  # last 7 days
        )
        logger.info("LinkedIn → %s", url)
        driver.get(url)
        _random_delay(2, 4)

        offers: List[JobOffer] = []
        page = 0

        while len(offers) < max_results:
            # Scroll to load lazy items
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            _random_delay(1, 2)

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "ul.jobs-search__results-list li")
                    )
                )
            except TimeoutException:
                break

            cards = driver.find_elements(By.CSS_SELECTOR, "ul.jobs-search__results-list li")
            if not cards:
                break

            for card in cards[len(offers):]:
                if len(offers) >= max_results:
                    break
                try:
                    offer = self._parse_card(card, keywords)
                    if offer:
                        offers.append(offer)
                except Exception as exc:
                    logger.debug("Card parse error: %s", exc)
                    continue

            # Try pagination
            page += 1
            try:
                next_btn = driver.find_element(
                    By.CSS_SELECTOR, f'button[aria-label="Page {page + 1}"]'
                )
                next_btn.click()
                _random_delay(2, 4)
            except NoSuchElementException:
                break

        logger.info("LinkedIn scraped %d offers for '%s'", len(offers), keywords)
        return offers

    def _parse_card(self, card, keywords: str) -> Optional[JobOffer]:
        title = self._text(card, "h3.base-search-card__title")
        company = self._text(card, "h4.base-search-card__subtitle")
        location = self._text(card, "span.job-search-card__location")
        posted_at = self._text(card, "time")
        url = ""
        try:
            link = card.find_element(By.CSS_SELECTOR, "a.base-card__full-link")
            url = link.get_attribute("href") or ""
            url = url.split("?")[0]  # strip tracking params
        except NoSuchElementException:
            pass

        if not title:
            return None

        return JobOffer(
            title=title,
            company=company,
            location=location,
            url=url,
            source="linkedin",
            keywords=keywords,
            posted_at=posted_at,
        )

    @staticmethod
    def _text(parent, selector: str) -> str:
        try:
            return parent.find_element(By.CSS_SELECTOR, selector).text.strip()
        except NoSuchElementException:
            return ""


# ---------------------------------------------------------------------------
# Indeed scraper
# ---------------------------------------------------------------------------

class IndeedScraper:
    """Scrapes job listings from Indeed (fr.indeed.com)."""

    BASE_URL = "https://fr.indeed.com/jobs"

    def __init__(self, headless: bool = True):
        self.headless = headless

    def scrape(
        self,
        keywords: str,
        location: str = "France",
        max_results: int = 25,
    ) -> List[JobOffer]:
        if not SELENIUM_AVAILABLE:
            raise RuntimeError("selenium is required for Indeed scraping")

        driver = _build_driver(self.headless)
        offers: List[JobOffer] = []
        try:
            offers = self._do_scrape(driver, keywords, location, max_results)
        finally:
            try:
                driver.quit()
            except Exception:
                pass
        return offers

    def _do_scrape(
        self,
        driver: "webdriver.Chrome",
        keywords: str,
        location: str,
        max_results: int,
    ) -> List[JobOffer]:
        url = (
            f"{self.BASE_URL}?q={quote_plus(keywords)}"
            f"&l={quote_plus(location)}&fromage=7"
        )
        logger.info("Indeed → %s", url)
        driver.get(url)
        _random_delay(2, 4)

        # Dismiss cookie banner if present
        for selector in ["#onetrust-accept-btn-handler", "button[id*='accept']"]:
            try:
                btn = driver.find_element(By.CSS_SELECTOR, selector)
                btn.click()
                _random_delay(0.5, 1)
                break
            except NoSuchElementException:
                pass

        offers: List[JobOffer] = []

        while len(offers) < max_results:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            _random_delay(1, 2)

            soup = BeautifulSoup(driver.page_source, "html.parser") if BS4_AVAILABLE else None

            if soup:
                cards = soup.select("div.job_seen_beacon")
                if not cards:
                    cards = soup.select("div.tapItem")
            else:
                cards = driver.find_elements(By.CSS_SELECTOR, "div.job_seen_beacon")

            if not cards:
                break

            for card in cards[len(offers):]:
                if len(offers) >= max_results:
                    break
                try:
                    offer = self._parse_card_soup(card, keywords) if soup else None
                    if offer:
                        offers.append(offer)
                except Exception as exc:
                    logger.debug("Card parse error: %s", exc)
                    continue

            # Pagination
            try:
                next_link = driver.find_element(By.CSS_SELECTOR, 'a[data-testid="pagination-page-next"]')
                next_link.click()
                _random_delay(2, 4)
            except NoSuchElementException:
                break

        logger.info("Indeed scraped %d offers for '%s'", len(offers), keywords)
        return offers

    def _parse_card_soup(self, card, keywords: str) -> Optional[JobOffer]:
        title_tag = card.select_one("h2.jobTitle span[title], h2.jobTitle a span")
        title = title_tag.get_text(strip=True) if title_tag else ""

        company_tag = card.select_one("span.companyName, [data-testid='company-name']")
        company = company_tag.get_text(strip=True) if company_tag else ""

        location_tag = card.select_one("div.companyLocation, [data-testid='text-location']")
        location = location_tag.get_text(strip=True) if location_tag else ""

        salary_tag = card.select_one("div.salary-snippet-container, div.estimated-salary")
        salary = salary_tag.get_text(strip=True) if salary_tag else ""

        date_tag = card.select_one("span.date")
        posted_at = date_tag.get_text(strip=True) if date_tag else ""

        link_tag = card.select_one("h2.jobTitle a")
        url = ""
        if link_tag and link_tag.get("href"):
            raw = link_tag["href"]
            url = f"https://fr.indeed.com{raw}" if raw.startswith("/") else raw
            url = url.split("?")[0]

        if not title:
            return None

        return JobOffer(
            title=title,
            company=company,
            location=location,
            salary_range=salary,
            url=url,
            source="indeed",
            keywords=keywords,
            posted_at=posted_at,
        )


# ---------------------------------------------------------------------------
# Detail fetcher (optional: fetch full job description)
# ---------------------------------------------------------------------------

class JobDetailFetcher:
    """Fetches the full description for a single job URL."""

    def __init__(self, headless: bool = True):
        self.headless = headless

    def fetch(self, offer: JobOffer) -> JobOffer:
        if not SELENIUM_AVAILABLE or not offer.url:
            return offer
        driver = _build_driver(self.headless)
        try:
            driver.get(offer.url)
            _random_delay(1.5, 3)
            description = self._extract_description(driver, offer.source)
            if description:
                offer.description = description
        except Exception as exc:
            logger.debug("Detail fetch error for %s: %s", offer.url, exc)
        finally:
            try:
                driver.quit()
            except Exception:
                pass
        return offer

    def _extract_description(self, driver: "webdriver.Chrome", source: str) -> str:
        selectors = {
            "linkedin": [
                "div.show-more-less-html__markup",
                "section.description div",
            ],
            "indeed": [
                "div#jobDescriptionText",
                "div.jobsearch-jobDescriptionText",
            ],
        }
        for selector in selectors.get(source, []):
            try:
                el = driver.find_element(By.CSS_SELECTOR, selector)
                return el.text.strip()
            except NoSuchElementException:
                continue
        # Generic fallback
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            return body.text[:3000]
        except Exception:
            return ""


# ---------------------------------------------------------------------------
# High-level orchestration
# ---------------------------------------------------------------------------

def scrape_jobs(
    keywords: str,
    location: str = "France",
    sources: List[str] | None = None,
    max_per_source: int = 25,
    fetch_descriptions: bool = False,
    headless: bool = True,
) -> List[JobOffer]:
    """
    Orchestrate scraping across multiple job boards.

    Args:
        keywords: Job search keywords (e.g. "data scientist python")
        location: Geographic filter
        sources: List of sources to use — "linkedin", "indeed". Defaults to both.
        max_per_source: Max offers per source
        fetch_descriptions: Whether to visit each offer URL for the full description
        headless: Run browser in headless mode

    Returns:
        Deduplicated list of JobOffer objects
    """
    if not SELENIUM_AVAILABLE:
        raise RuntimeError(
            "selenium is not installed. Install it with: pip install selenium"
        )

    if sources is None:
        sources = ["linkedin", "indeed"]

    all_offers: List[JobOffer] = []

    scraper_map = {
        "linkedin": LinkedInScraper(headless=headless),
        "indeed": IndeedScraper(headless=headless),
    }

    for source in sources:
        scraper = scraper_map.get(source)
        if scraper is None:
            logger.warning("Unknown source '%s', skipping", source)
            continue
        try:
            offers = scraper.scrape(keywords, location, max_per_source)
            all_offers.extend(offers)
        except Exception as exc:
            logger.error("Scraping failed for source '%s': %s", source, exc)

    # Deduplicate by URL (keep first occurrence)
    seen_urls: set = set()
    unique_offers: List[JobOffer] = []
    for offer in all_offers:
        key = offer.url or f"{offer.title}|{offer.company}"
        if key and key not in seen_urls:
            seen_urls.add(key)
            unique_offers.append(offer)

    if fetch_descriptions:
        fetcher = JobDetailFetcher(headless=headless)
        enriched: List[JobOffer] = []
        for offer in unique_offers:
            try:
                enriched.append(fetcher.fetch(offer))
                _random_delay(1, 2)
            except Exception:
                enriched.append(offer)
        unique_offers = enriched

    logger.info(
        "Total scraped: %d unique offers for '%s' (%s)",
        len(unique_offers),
        keywords,
        ", ".join(sources),
    )
    return unique_offers
