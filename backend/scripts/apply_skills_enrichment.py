#!/usr/bin/env python3
"""
Apply skills enrichment suggestions by merging into skills_dictionary.json.
Backs up original dictionary to skills_dictionary.json.bak.TIMESTAMP
"""
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
SUGGEST = ROOT / 'backend' / 'ai_module' / 'data' / 'skills_enrichment_suggestions.json'
DICT = ROOT / 'backend' / 'ai_module' / 'data' / 'skills_dictionary.json'


def title_case(s: str) -> str:
    return s.title()


def load_dict():
    if not DICT.exists():
        return {}
    return json.loads(DICT.read_text(encoding='utf-8'))


def save_dict(data):
    DICT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')


def main():
    if not SUGGEST.exists():
        print('No suggestions file')
        return
    sugg = json.loads(SUGGEST.read_text(encoding='utf-8'))
    data = load_dict()
    # ensure we operate on dict with categories
    if not isinstance(data, dict):
        data = {'tech': data}

    # Build existing lowercase set
    existing = set()
    for k, v in data.items():
        for item in v:
            existing.add(item.lower())

    to_add = []
    for it in sugg.get('missing_suggestions', []):
        norm = it['skill']
        label = title_case(norm)
        if norm.lower() not in existing:
            to_add.append(label)
            existing.add(norm.lower())

    if not to_add:
        print('No new skills to add')
        return

    # Backup
    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    bak = DICT.with_name(f"skills_dictionary.json.bak.{ts}")
    DICT.replace(bak)
    print('Backed up original dict to', bak)

    # Merge into 'tech' category (create if missing)
    tech = data.get('tech', [])
    tech.extend(to_add)
    # dedupe preserving order
    seen = set()
    newtech = []
    for s in tech:
        if s.lower() not in seen:
            seen.add(s.lower())
            newtech.append(s)
    data['tech'] = newtech

    save_dict(data)
    print(f'Added {len(to_add)} skills and saved to', DICT)

if __name__ == '__main__':
    main()
