"""Production-oriented LinkedIn scraper helpers (conservative).

Features:
- optional login via cookies or credentials
- optional proxy support
- rate limiting and polite delays
- result persistence (JSONL)

LEGAL: Use only with explicit permission and in compliance with LinkedIn Terms of Service.
"""
from typing import List, Dict, Any, Optional
import time
import json
import logging

logger = logging.getLogger(__name__)


def scrape_with_options(query: str, max_results: int = 50, headless: bool = True, proxy: Optional[str] = None, cookie_file: Optional[str] = None, output: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
    except Exception:
        raise RuntimeError("Selenium not installed")

    options = Options()
    if headless:
        options.add_argument("--headless=new")
    if proxy:
        options.add_argument(f"--proxy-server={proxy}")

    driver = webdriver.Chrome(options=options)
    results: List[Dict[str, Any]] = []

    try:
        if cookie_file:
            try:
                with open(cookie_file, "r") as f:
                    cookies = json.load(f)
                driver.get("https://www.linkedin.com")
                for c in cookies:
                    driver.add_cookie(c)
                driver.refresh()
            except Exception:
                logger.warning("Failed to load cookies; continuing anonymously")

        search_url = f"https://www.linkedin.com/jobs/search/?keywords={query}"
        driver.get(search_url)
        time.sleep(3)

        cards = driver.find_elements(By.CSS_SELECTOR, ".jobs-search-results__list-item")
        for card in cards[:max_results]:
            try:
                title_el = card.find_element(By.CSS_SELECTOR, "h3")
                company_el = card.find_element(By.CSS_SELECTOR, ".base-search-card__subtitle")
                link_el = card.find_element(By.CSS_SELECTOR, "a")
                results.append({
                    "title": title_el.text.strip(),
                    "company": company_el.text.strip(),
                    "url": link_el.get_attribute("href"),
                })
            except Exception:
                continue

            time.sleep(0.5)  # polite pacing

        if output:
            with open(output, "w", encoding="utf-8") as f:
                for r in results:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")

    finally:
        driver.quit()

    return results
