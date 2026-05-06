"""Export training CSV of CV <-> Job pairs from the app DB.

Usage (local):

    source ../.venv/bin/activate
    python prepare_training_data.py --out ../data/training_pairs.csv --limit 5000

Notes: the script is a best-effort exporter; adjust filters per your dataset.
"""

import argparse
import csv
import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Change this default if your DATABASE_URL differs
DEFAULT_DB_URL = "sqlite:///../ai_talent_finder.db"


def get_session(database_url: str):
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    return Session()


def export_pairs(session, out_path: str, limit: int = 5000):
    """Export naive pairs: each job vs all candidates with heuristic label=-1 (unknown).
    Use this output for manual labeling or synthetic labeling rules."""
    # Import models lazily to avoid import-time heavy deps
    from app.models.models import Candidate, JobCriteria

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["cv_id", "job_id", "cv_text", "job_text", "label"])
        writer.writeheader()

        jobs = session.query(JobCriteria).order_by(JobCriteria.created_at.desc()).limit(100).all()
        count = 0
        for job in jobs:
            job_text = (job.title or "") + "\n" + (job.description or "")
            candidates = session.query(Candidate).order_by(Candidate.created_at.desc()).limit(limit).all()
            for cand in candidates:
                cv_text = cand.raw_text or ""
                writer.writerow({
                    "cv_id": cand.id,
                    "job_id": job.id,
                    "cv_text": cv_text.replace("\n", " ")[:10000],
                    "job_text": job_text.replace("\n", " ")[:5000],
                    "label": -1,
                })
                count += 1
                if count >= limit:
                    print(f"Exported {count} pairs to {out}")
                    return

    print(f"Exported {count} pairs to {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=DEFAULT_DB_URL, help="SQLAlchemy database URL")
    parser.add_argument("--out", required=True, help="Output CSV path")
    parser.add_argument("--limit", type=int, default=5000)

    args = parser.parse_args()
    sess = get_session(args.db)
    export_pairs(sess, args.out, limit=args.limit)
