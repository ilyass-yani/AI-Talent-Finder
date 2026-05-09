#!/usr/bin/env python3
"""
Analyze skills dictionary coverage and propose enrichments.
Run: PYTHONPATH=. python3 backend/scripts/analyze_and_enrich_skills.py
Generates: backend/ai_module/data/skills_enrichment_suggestions.json
"""
import json
import csv
from pathlib import Path
import re
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
SKILLS_FILE = ROOT / 'backend' / 'ai_module' / 'data' / 'skills_dictionary.json'
OUT_FILE = ROOT / 'backend' / 'ai_module' / 'data' / 'skills_enrichment_suggestions.json'
DATA_DIR = ROOT / 'data'

skill_norm_re = re.compile(r"[^a-z0-9+#+\.\- ]+")


def normalize(s: str) -> str:
    s2 = s.strip().lower()
    s2 = s2.replace('/', ' ').replace('&', ' and ')
    s2 = skill_norm_re.sub(' ', s2)
    s2 = re.sub(r'\s+', ' ', s2).strip()
    return s2


def load_skills_dict():
    if not SKILLS_FILE.exists():
        print('Skills dictionary not found at', SKILLS_FILE)
        return set()
    data = json.loads(SKILLS_FILE.read_text(encoding='utf-8'))
    # assume file is list of skills or dict with keys
    if isinstance(data, dict):
        items = []
        for k, v in data.items():
            if isinstance(v, list):
                items.extend(v)
            else:
                items.append(k)
    elif isinstance(data, list):
        items = data
    else:
        items = []
    normalized = set(normalize(x) for x in items if x)
    return normalized


def scan_data_files():
    files = list(DATA_DIR.glob('**/*.csv'))
    tokens = Counter()
    for f in files:
        try:
            with f.open('r', encoding='utf-8') as fh:
                reader = csv.reader(fh)
                headers = next(reader, None)
                if not headers:
                    continue
                # find indices for cv_text and job_text if present
                header_map = {h: i for i, h in enumerate(headers)}
                cv_idx = header_map.get('cv_text')
                job_idx = header_map.get('job_text')

                for row in reader:
                    candidates = []
                    if cv_idx is not None and cv_idx < len(row):
                        candidates.append(row[cv_idx])
                    if job_idx is not None and job_idx < len(row):
                        candidates.append(row[job_idx])

                    for cell in candidates:
                        if not cell:
                            continue
                        cell = cell.replace('\r', ' ').replace('\n', ' ')
                        # Try to extract after SKILLS markers
                        m = re.search(r"skills\s*[:\-]\s*(.+)$", cell, flags=re.IGNORECASE)
                        if m:
                            skills_blob = m.group(1)
                            parts = re.split(r'[;,\\|]+', skills_blob)
                        else:
                            # fallback: take last 200 characters which often include compact skill lists
                            tail = cell[-400:]
                            parts = re.split(r'[;,\\|]+', tail)

                        for p in parts:
                            p = p.strip()
                            if len(p) < 2:
                                continue
                            # heuristics: keep phrases up to 5 words
                            if len(p.split()) <= 6 and any(c.isalpha() for c in p):
                                tokens[normalize(p)] += 1
        except Exception as e:
            print('Skipping', f, 'error', e)
    return tokens


def extract_skill_phrases(counter: Counter, top_n=200):
    # filter out likely non-skills (e.g., long phrases)
    filtered = Counter()
    for k, v in counter.most_common(top_n * 5):
        if len(k) < 3:
            continue
        words = k.split()
        if len(words) > 5:
            continue
        # ignore sentences with verbs commonly
        if any(tok in k for tok in ('experience', 'looking', 'years', 'year', 'candidate', 'engineer', 'developer')):
            continue
        filtered[k] = v
    return Counter(filtered).most_common(top_n)


def main():
    print('Loading skills dictionary...')
    dict_skills = load_skills_dict()
    print(f'Loaded {len(dict_skills)} normalized skills from dictionary')

    print('Scanning data CSV files for skill-like phrases...')
    tokens = scan_data_files()
    print(f'Extracted {len(tokens)} candidate tokens from data files')

    top = extract_skill_phrases(tokens, top_n=300)

    missing = []
    for phrase, count in top:
        if phrase not in dict_skills:
            missing.append({'skill': phrase, 'count': count})

    print(f'Found {len(missing)} high-frequency tokens missing from dictionary (top {len(top)})')

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps({'missing_suggestions': missing, 'summary': {'dict_count': len(dict_skills), 'tokens_scanned': len(tokens)}}, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Wrote suggestions to', OUT_FILE)

if __name__ == '__main__':
    main()
