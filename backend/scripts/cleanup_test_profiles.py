#!/usr/bin/env python3
"""Safe cleanup for test/demo candidate profiles.

Creates a backup JSON of affected candidates and removes their DB rows and uploaded CV files.
Run from project root with the same python env used for the backend.

Example:
  DATABASE_URL=sqlite:///./ai_talent_finder.db .venv/bin/python backend/scripts/cleanup_test_profiles.py
"""
import os
import json
import sqlite3
from pathlib import Path
import shutil

DB_PATH = os.environ.get("DATABASE_URL", "sqlite:///./ai_talent_finder.db")

def sqlite_path_from_url(url: str) -> Path:
    # supports sqlite:///./relative.db or sqlite:////abs/path.db
    if url.startswith("sqlite:///"):
        path = url.replace("sqlite:///", "")
        return Path(path).resolve()
    raise ValueError("Unsupported DB URL: " + url)


def main():
    db_path = sqlite_path_from_url(DB_PATH)
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        return

    out_dir = Path("archive") / "cleanups"
    out_dir.mkdir(parents=True, exist_ok=True)
    backup_file = out_dir / f"candidates_backup_{os.getpid()}.json"

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Identify candidate rows to remove: low quality or placeholder names/emails
    query = """
    SELECT id, full_name, email, cv_path, extraction_quality_score, is_fully_extracted
    FROM candidates
    WHERE (extraction_quality_score IS NULL OR extraction_quality_score < 80)
       OR lower(full_name) LIKE '%unknown%'
       OR lower(full_name) LIKE '%test%'
       OR lower(full_name) LIKE '%demo%'
       OR lower(email) LIKE 'candidate-%'
    """

    rows = cur.execute(query).fetchall()
    rows_data = [dict(r) for r in rows]
    if not rows_data:
        print("No candidate rows matched the cleanup criteria.")
        return

    # Backup
    with backup_file.open("w", encoding="utf-8") as f:
        json.dump(rows_data, f, ensure_ascii=False, indent=2)
    print(f"Backed up {len(rows_data)} candidates to {backup_file}")

    # Remove uploaded CV files and related candidate_skill links if present
    uploads_root = Path(__file__).resolve().parents[2] / "uploads"
    for r in rows_data:
        cv = r.get("cv_path")
        if cv:
            file_path = Path(__file__).resolve().parents[2] / cv
            try:
                if file_path.exists():
                    file_path.unlink()
                    print(f"Removed upload: {file_path}")
            except Exception as e:
                print(f"Failed to remove {file_path}: {e}")

    # Delete candidates from DB (and cascade if FK constraints exist)
    ids = [str(r["id"]) for r in rows_data]
    id_list = ",".join(ids)
    try:
        cur.execute(f"PRAGMA foreign_keys = ON;")
        cur.execute(f"DELETE FROM candidate_skills WHERE candidate_id IN ({id_list})")
        cur.execute(f"DELETE FROM favorites WHERE candidate_id IN ({id_list})")
        cur.execute(f"DELETE FROM match_results WHERE candidate_id IN ({id_list})")
        cur.execute(f"DELETE FROM candidates WHERE id IN ({id_list})")
        conn.commit()
        print(f"Deleted {len(ids)} candidate rows from DB.")
    except Exception as e:
        conn.rollback()
        print(f"DB deletion failed: {e}")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
