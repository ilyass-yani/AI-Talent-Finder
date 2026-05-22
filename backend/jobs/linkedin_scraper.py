"""
LinkedIn Job Scraper with Selenium
ÉTAPE 9: Web scraping pour collecte de données d'entraînement illimitées
"""

import os
import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import csv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)

logger = logging.getLogger(__name__)


class LinkedInJobScraper:
    """Scrape job postings from LinkedIn."""
    
    BASE_URL = "https://www.linkedin.com"
    JOBS_URL = f"{BASE_URL}/jobs/search"
    
    def __init__(
        self,
        headless: bool = True,
        proxy: Optional[str] = None,
        cookies_path: Optional[str] = None,
    ):
        """Initialize scraper with optional proxy and cookie authentication."""
        self.headless = headless
        self.proxy = proxy
        self.cookies_path = cookies_path
        self.driver = None
        self.wait = None
    
    def _setup_driver(self):
        """Setup Selenium WebDriver with Chrome."""
        logger.info("🌐 Setting up Chrome WebDriver...")
        
        options = Options()
        
        if self.headless:
            options.add_argument("--headless")
        
        # Performance and stealth options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")
        options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        
        # Proxy configuration
        if self.proxy:
            options.add_argument(f"--proxy-server={self.proxy}")
            logger.info(f"✅ Using proxy: {self.proxy}")
        
        # Disable images for faster loading
        prefs = {
            "profile.managed_default_content_settings.images": 2,
        }
        options.add_experimental_option("prefs", prefs)
        
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)
        
        logger.info("✅ WebDriver ready")
    
    def _load_cookies(self):
        """Load cookies from file for authentication."""
        if not self.cookies_path or not os.path.exists(self.cookies_path):
            logger.warning("⚠️ No cookies found. Using guest mode.")
            return
        
        logger.info(f"🔑 Loading cookies from {self.cookies_path}...")
        
        # Navigate to LinkedIn first
        self.driver.get(self.BASE_URL)
        time.sleep(2)
        
        try:
            with open(self.cookies_path, "r") as f:
                cookies = json.load(f)
            
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to add cookie: {e}")
            
            logger.info("✅ Cookies loaded")
        except Exception as e:
            logger.error(f"❌ Error loading cookies: {e}")
    
    def _save_cookies(self):
        """Save current cookies for future use."""
        cookies_dir = Path("cookies")
        cookies_dir.mkdir(exist_ok=True)
        
        cookies_file = cookies_dir / "linkedin_cookies.json"
        cookies = self.driver.get_cookies()
        
        with open(cookies_file, "w") as f:
            json.dump(cookies, f)
        
        logger.info(f"💾 Cookies saved to {cookies_file}")
    
    def scrape_job_listings(
        self,
        query: str,
        location: str = "France",
        num_jobs: int = 100,
    ) -> List[Dict]:
        """Scrape job listings from LinkedIn."""
        
        if not self.driver:
            self._setup_driver()
            self._load_cookies()
        
        jobs = []
        
        # Build search URL
        search_url = (
            f"{self.JOBS_URL}?"
            f"keywords={query.replace(' ', '%20')}&"
            f"location={location.replace(' ', '%20')}&"
            f"f_T=1%7C4&"  # Entry level + Mid level
            f"sortBy=DD"  # Most recent
        )
        
        logger.info(f"🔍 Scraping jobs for: {query} in {location}")
        
        self.driver.get(search_url)
        time.sleep(3)
        
        # Close popup if present
        self._close_popups()
        
        # Scroll to load jobs
        for i in range(5):
            self.driver.execute_script("window.scrollBy(0, 500)")
            time.sleep(1)
        
        try:
            # Get job listings
            job_cards = self.wait.until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "base-card"))
            )
            
            logger.info(f"📋 Found {len(job_cards)} job cards")
            
            # Extract job info from each card
            for idx, card in enumerate(job_cards):
                if len(jobs) >= num_jobs:
                    break
                
                try:
                    job_info = self._extract_job_info(card)
                    if job_info:
                        jobs.append(job_info)
                        logger.debug(f"✓ Extracted job {idx + 1}: {job_info.get('title')}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to extract job {idx}: {e}")
                    continue
            
            logger.info(f"✅ Successfully scraped {len(jobs)} jobs")
        
        except TimeoutException:
            logger.error("❌ Timeout waiting for job listings")
        
        return jobs
    
    def _close_popups(self):
        """Close LinkedIn popups."""
        try:
            close_button = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label*='Dismiss']")
            close_button.click()
            time.sleep(1)
        except NoSuchElementException:
            pass
    
    def _extract_job_info(self, card) -> Optional[Dict]:
        """Extract job information from a job card."""
        try:
            # Title
            title_elem = card.find_element(By.CSS_SELECTOR, "h3.base-search-card__title")
            title = title_elem.text.strip()
            
            # Company
            company_elem = card.find_element(By.CSS_SELECTOR, "h4.base-search-card__subtitle")
            company = company_elem.text.strip()
            
            # Location
            location_elem = card.find_element(By.CSS_SELECTOR, "span.job-search-card__location")
            location = location_elem.text.strip()
            
            # Job URL
            link_elem = card.find_element(By.CSS_SELECTOR, "a.base-card__full-link")
            job_url = link_elem.get_attribute("href")
            
            # Job ID
            job_id = job_url.split("/")[-2] if job_url else None
            
            # Posted date
            date_elem = card.find_element(By.CSS_SELECTOR, "time")
            posted_date = date_elem.get_attribute("datetime") if date_elem else None
            
            return {
                "id": job_id,
                "title": title,
                "company": company,
                "location": location,
                "url": job_url,
                "posted_date": posted_date,
                "scraped_at": datetime.now().isoformat(),
            }
        
        except (NoSuchElementException, StaleElementReferenceException) as e:
            logger.debug(f"Failed to extract job card: {e}")
            return None
    
    def scrape_job_details(self, job_url: str) -> Optional[Dict]:
        """Scrape full job details from job posting page."""
        try:
            logger.debug(f"📄 Scraping job details: {job_url}")
            
            self.driver.get(job_url)
            time.sleep(2)
            
            # Job description
            description = ""
            try:
                desc_elem = self.wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "show-more-less-html__markup"))
                )
                description = desc_elem.text.strip()
            except TimeoutException:
                logger.warning("⚠️ Could not find job description")
            
            # Requirements
            requirements = []
            try:
                req_section = self.driver.find_element(By.XPATH, "//h3[contains(text(), 'Requirements')]/../following-sibling::ul")
                req_items = req_section.find_elements(By.TAG_NAME, "li")
                requirements = [item.text.strip() for item in req_items]
            except NoSuchElementException:
                pass
            
            # Salary (if available)
            salary = None
            try:
                salary_elem = self.driver.find_element(By.CLASS_NAME, "salary-main-bullet")
                salary = salary_elem.text.strip()
            except NoSuchElementException:
                pass
            
            return {
                "description": description,
                "requirements": requirements,
                "salary": salary,
            }
        
        except Exception as e:
            logger.error(f"❌ Error scraping job details: {e}")
            return None
    
    def scrape_candidates(
        self,
        search_query: str,
        num_profiles: int = 50,
    ) -> List[Dict]:
        """Scrape candidate profiles from LinkedIn (requires login)."""
        
        if not self.driver:
            self._setup_driver()
            self._load_cookies()
        
        candidates = []
        
        # Build search URL
        search_url = (
            f"{self.BASE_URL}/search/results/people/?"
            f"keywords={search_query.replace(' ', '%20')}&"
            f"sortBy=DD"
        )
        
        logger.info(f"👥 Scraping candidate profiles for: {search_query}")
        
        self.driver.get(search_url)
        time.sleep(3)
        
        try:
            # Scroll to load profiles
            for i in range(3):
                self.driver.execute_script("window.scrollBy(0, 500)")
                time.sleep(1)
            
            # Get profile cards
            profile_cards = self.driver.find_elements(By.CLASS_NAME, "reusable-search__result-container")
            
            logger.info(f"📋 Found {len(profile_cards)} profile cards")
            
            for idx, card in enumerate(profile_cards):
                if len(candidates) >= num_profiles:
                    break
                
                try:
                    # Name
                    name_elem = card.find_element(By.CLASS_NAME, "name-badge__name-link")
                    name = name_elem.text.strip()
                    
                    # Headline (job title + company)
                    headline_elem = card.find_element(By.CLASS_NAME, "dist-value")
                    headline = headline_elem.text.strip()
                    
                    # URL
                    profile_url = name_elem.get_attribute("href")
                    
                    candidates.append({
                        "name": name,
                        "headline": headline,
                        "profile_url": profile_url,
                        "scraped_at": datetime.now().isoformat(),
                    })
                    
                    logger.debug(f"✓ Extracted profile {idx + 1}: {name}")
                
                except NoSuchElementException:
                    logger.debug(f"⚠️ Failed to extract profile {idx}")
                    continue
            
            logger.info(f"✅ Successfully scraped {len(candidates)} candidate profiles")
        
        except Exception as e:
            logger.error(f"❌ Error scraping candidates: {e}")
        
        return candidates
    
    def save_to_csv(
        self,
        data: List[Dict],
        output_file: str = "scraped_jobs.csv",
    ):
        """Save scraped data to CSV."""
        if not data:
            logger.warning("⚠️ No data to save")
            return
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write CSV
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        
        logger.info(f"💾 Saved {len(data)} records to {output_path}")
    
    def save_to_json(
        self,
        data: List[Dict],
        output_file: str = "scraped_jobs.json",
    ):
        """Save scraped data to JSON."""
        if not data:
            logger.warning("⚠️ No data to save")
            return
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Saved {len(data)} records to {output_path}")
    
    def close(self):
        """Close the WebDriver."""
        if self.driver:
            self.driver.quit()
            logger.info("🔌 WebDriver closed")


def scrape_jobs_batch(
    queries: List[str],
    locations: List[str] = None,
    num_jobs_per_query: int = 50,
    output_dir: str = "scrapes",
    use_proxy: Optional[str] = None,
    cookies_path: Optional[str] = None,
) -> Dict[str, List[Dict]]:
    """Batch scrape jobs across multiple queries and locations."""
    
    if locations is None:
        locations = ["France", "Remote"]
    
    results = {}
    scraper = LinkedInJobScraper(
        headless=True,
        proxy=use_proxy,
        cookies_path=cookies_path,
    )
    
    try:
        for query in queries:
            for location in locations:
                key = f"{query}_{location}".replace(" ", "_")
                
                logger.info(f"📥 Scraping: {query} in {location}")
                
                jobs = scraper.scrape_job_listings(
                    query=query,
                    location=location,
                    num_jobs=num_jobs_per_query,
                )
                
                results[key] = jobs
                
                # Save intermediate results
                output_path = Path(output_dir) / f"jobs_{key}.json"
                scraper.save_to_json(jobs, str(output_path))
        
        logger.info(f"✅ Batch scraping completed: {sum(len(v) for v in results.values())} jobs")
    
    finally:
        scraper.close()
    
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Example: Scrape jobs
    scraper = LinkedInJobScraper(headless=False)
    
    try:
        jobs = scraper.scrape_job_listings(
            query="Data Scientist",
            location="France",
            num_jobs=10,
        )
        
        # Save results
        scraper.save_to_json(jobs, "scraped_data_scientists.json")
        scraper.save_to_csv(jobs, "scraped_data_scientists.csv")
    
    finally:
        scraper.close()
