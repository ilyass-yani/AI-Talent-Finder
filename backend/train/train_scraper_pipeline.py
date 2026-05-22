"""
LinkedIn scraper training script - collect job postings for model training
Usage:
    python train/train_scraper_pipeline.py --query "Data Scientist" --num-jobs 100 --output scraped_jobs
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from jobs.linkedin_scraper import scrape_jobs_batch, LinkedInJobScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Scrape job postings for model training")
    parser.add_argument("--query", type=str, default="Data Scientist", help="Job search query")
    parser.add_argument("--locations", type=str, nargs="+", default=["France", "Remote"], help="Job locations")
    parser.add_argument("--num-jobs", type=int, default=50, help="Number of jobs per query")
    parser.add_argument("--output", type=str, default="scraped_jobs", help="Output directory")
    parser.add_argument("--proxy", type=str, default=None, help="HTTP proxy URL")
    parser.add_argument("--cookies", type=str, default=None, help="Path to cookies file")
    parser.add_argument("--headless", action="store_true", default=True, help="Run in headless mode")
    
    args = parser.parse_args()
    
    logger.info("🚀 Starting LinkedIn job scraper...")
    logger.info(f"   Query: {args.query}")
    logger.info(f"   Locations: {', '.join(args.locations)}")
    logger.info(f"   Jobs per location: {args.num_jobs}")
    
    # Batch scrape
    queries = [args.query]
    results = scrape_jobs_batch(
        queries=queries,
        locations=args.locations,
        num_jobs_per_query=args.num_jobs,
        output_dir=args.output,
        use_proxy=args.proxy,
        cookies_path=args.cookies,
    )
    
    # Summary
    total_jobs = sum(len(v) for v in results.values())
    logger.info(f"✅ Scraping completed!")
    logger.info(f"   Total jobs scraped: {total_jobs}")
    logger.info(f"   Output directory: {args.output}")
    
    for key, jobs in results.items():
        logger.info(f"   - {key}: {len(jobs)} jobs")


if __name__ == "__main__":
    main()
