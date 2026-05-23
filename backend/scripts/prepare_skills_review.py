#!/usr/bin/env python3
"""
Prepare a CSV for human review of skills enrichment suggestions.
Generates: backend/ai_module/data/skills_enrichment_review.csv
"""
import json
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[2]
SUGGEST = ROOT / 'backend' / 'ai_module' / 'data' / 'skills_enrichment_suggestions.json'
DICT = ROOT / 'backend' / 'ai_module' / 'data' / 'skills_dictionary.json'
OUT = ROOT / 'backend' / 'ai_module' / 'data' / 'skills_enrichment_review.csv'


def title_case(s: str) -> str:
    return s.title()


def main():
    if not SUGGEST.exists():
        print('No suggestions file found at', SUGGEST)
        return
    sugg = json.loads(SUGGEST.read_text(encoding='utf-8'))
    dict_data = json.loads(DICT.read_text(encoding='utf-8')) if DICT.exists() else {}
    # flatten dict into set
    existing = set()
    if isinstance(dict_data, dict):
        for v in dict_data.values():
            if isinstance(v, list):
                for item in v:
                    existing.add(item.lower())
    elif isinstance(dict_data, list):
        for item in dict_data:
            existing.add(item.lower())

    rows = []
    for item in sugg.get('missing_suggestions', []):
        skill = item['skill']
        count = item.get('count', 0)
        in_dict = 'yes' if skill.lower() in existing else 'no'
        suggestion = title_case(skill)
        rows.append((skill, count, in_dict, suggestion))

    with OUT.open('w', newline='', encoding='utf-8') as fh:
        writer = csv.writer(fh)
        writer.writerow(['skill_normalized','count','in_dictionary','suggested_label'])
        for r in rows:
            writer.writerow(r)

    print('Wrote review CSV to', OUT)

if __name__ == '__main__':
    main()
