"""Fallback exporter using sqlite3 (no SQLAlchemy required).

Usage:
    python prepare_training_data_fallback.py --db ../ai_talent_finder.db --out ../data/training_pairs.csv --limit 5000
"""
import argparse
import csv
from pathlib import Path
import sqlite3


def export_pairs_sqlite(db_path: str, out_path: str, limit: int = 5000):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['cv_id', 'job_id', 'cv_text', 'job_text', 'label'])
        writer.writeheader()

        cur.execute("SELECT id, title, description FROM job_criteria ORDER BY created_at DESC LIMIT 100")
        jobs = cur.fetchall()
        if not jobs:
            print('No jobs found in job_criteria table.')

        count = 0
        for job in jobs:
            job_id = job['id']
            job_text = (job['title'] or '') + '\n' + (job['description'] or '')
            cur.execute("SELECT id, raw_text FROM candidates ORDER BY created_at DESC")
            candidates = cur.fetchall()
            for cand in candidates:
                cv_id = cand['id']
                cv_text = cand['raw_text'] or ''
                writer.writerow({
                    'cv_id': cv_id,
                    'job_id': job_id,
                    'cv_text': cv_text.replace('\n', ' ')[:10000],
                    'job_text': job_text.replace('\n', ' ')[:5000],
                    'label': -1,
                })
                count += 1
                if count >= limit:
                    print(f'Exported {count} pairs to {out_path}')
                    conn.close()
                    return

    print(f'Exported {count} pairs to {out_path}')
    conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default='../ai_talent_finder.db', help='Path to sqlite DB file')
    parser.add_argument('--out', required=True, help='Output CSV path')
    parser.add_argument('--limit', type=int, default=5000)
    args = parser.parse_args()

    export_pairs_sqlite(args.db, args.out, args.limit)
