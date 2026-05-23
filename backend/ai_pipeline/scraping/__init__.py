"""Job-board scrapers (LinkedIn, Indeed, Welcome to the Jungle)."""
from .base_scraper import BaseScraper, ScrapedJob
from .indeed_scraper import IndeedScraper
from .linkedin_scraper import LinkedInScraper
from .welcometothejungle_scraper import WelcomeToTheJungleScraper

__all__ = [
    "BaseScraper",
    "ScrapedJob",
    "LinkedInScraper",
    "IndeedScraper",
    "WelcomeToTheJungleScraper",
]
