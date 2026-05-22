import json
from pathlib import Path
from unittest.mock import patch

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.pipeline import router as pipeline_router

app = FastAPI()
app.include_router(pipeline_router)

client = TestClient(app)


def test_run_full_returns_decision_and_top_k():
    cv_path = Path('backend/uploads/txt/557dd1f18e7c4476996d4d8c808e2255_test1.txt')
    if not cv_path.exists():
        pytest.skip(f"CV sample not found: {cv_path}")

    job_payload = {
        'job_text': 'Python data science machine learning deep learning',
        'skills': ['python', 'machine learning'],
        'years_experience': 3,
        'top_k': 3,
    }

    with patch('app.services.matching_service.MatchingService.search_top_k_candidates', return_value=[
        {'rank': 1, 'index': 4, 'score': 0.9, 'file': 'backend/uploads/txt/160049e689fd42708e154cfa189c9c4d_cv.txt'},
        {'rank': 2, 'index': 2, 'score': 0.8, 'file': 'backend/uploads/txt/7505436675dc4cbbb9b64fa13c593136_cv.txt'},
    ]):
        response = client.post(
            '/api/pipeline/run-full',
            files={'cv': (cv_path.name, cv_path.read_bytes(), 'text/plain')},
            data={'job_json': json.dumps(job_payload)},
        )

    assert response.status_code == 200, response.text
    data = response.json()

    assert 'decision' in data
    assert 'top_k' in data
    assert 'results' in data['top_k']
    assert isinstance(data['top_k']['results'], list)
    assert len(data['top_k']['results']) == 2
    assert data['top_k']['results'][0]['rank'] == 1
    assert data['decision']['decision']['label'] in {'accepted', 'to_review', 'rejected'}
