"""Generate synthetic CV-job pairs using `backend/tests/mock_data.py`.

This creates:
- ../data/training_pairs.csv (N pairs, labels auto-generated heuristically)
- ../data/label_sample_200.csv (200 random samples for manual review)

Usage:
    python generate_synthetic_dataset.py --out ../data/training_pairs.csv --n 5000
"""
import argparse
import csv
import random
from pathlib import Path

import importlib.util
from pathlib import Path

# Load mock_data.py dynamically (works regardless of PYTHONPATH)
mock_path = Path(__file__).resolve().parents[1] / "tests" / "mock_data.py"
spec = importlib.util.spec_from_file_location("mock_data", str(mock_path))
mock_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mock_mod)
get_mock_candidates = mock_mod.get_mock_candidates
get_mock_criteria = mock_mod.get_mock_criteria


def simple_label(candidate, job):
    # heuristic: if any skill name from candidate appears in job title or description -> positive
    text = (job.get('title','') + ' ' + job.get('description','')).lower()
    cand_skills = [s['name'].lower() for s in candidate.get('skills', [])]
    matches = sum(1 for s in cand_skills if s in text)
    # label positive if at least one exact skill match; add noise
    if matches >= 1:
        return 1
    # small chance of false positive/negative
    return 0


def generate(out_path: str, n: int = 5000):
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    candidates = get_mock_candidates()
    jobs = get_mock_criteria()
    # if few candidates, create variants
    candidate_pool = []
    for cand in candidates:
        # create slight variants of raw_text
        for i in range(0, 10):
            variant = dict(cand)
            variant['id'] = int(cand['id'] * 100 + i)
            variant['raw_text'] = (cand['raw_text'] or '') + ' ' + ' '.join([s['name'] for s in cand.get('skills', [])])
            candidate_pool.append(variant)

    with out.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['cv_id', 'job_id', 'cv_text', 'job_text', 'label', 'auto_label'])
        writer.writeheader()

        count = 0
        while count < n:
            cand = random.choice(candidate_pool)
            job = random.choice(jobs)
            cv_text = cand.get('raw_text','')
            job_text = (job.get('title','') + '\n' + job.get('description',''))
            label = simple_label(cand, job)
            # add controlled noise: flip label with 5% chance
            if random.random() < 0.05:
                label = 1 - label
            writer.writerow({
                'cv_id': cand['id'],
                'job_id': job['id'],
                'cv_text': cv_text.replace('\n',' ')[:10000],
                'job_text': job_text.replace('\n',' ')[:5000],
                'label': label,
                'auto_label': 1,
            })
            count += 1

    # produce sample 200
    sample_out = out.parent / 'label_sample_200.csv'
    with out.open('r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    sample = random.sample(rows, min(200, len(rows)))
    with sample_out.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        for r in sample:
            writer.writerow(r)

    print(f'Generated {n} synthetic pairs -> {out_path}')
    print(f'Wrote sample 200 -> {sample_out}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--n', type=int, default=5000)
    args = parser.parse_args()
    generate(args.out, args.n)
