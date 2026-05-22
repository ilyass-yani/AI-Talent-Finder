import json
import os
from app.api.pipeline import run_pipeline


def test_pipeline_run_smoke_direct():
    # Ensure we have an extracted sample
    if not os.path.exists('data/extracted_full.jsonl'):
        return
    rows = [json.loads(l) for l in open('data/extracted_full.jsonl', 'r', encoding='utf-8').read().splitlines() if l.strip()]
    payload = {'candidate': {'raw_text': rows[0].get('raw_text','')}, 'job': {'job_text': 'Looking for a Python ML engineer', 'skills': ['python','ml']}}
    body = run_pipeline(payload)
    assert 'final_score' in body
    assert 'decision' in body
