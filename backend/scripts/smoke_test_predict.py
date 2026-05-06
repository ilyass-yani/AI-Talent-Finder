"""Simple smoke test: load baseline model and run a prediction on a sample pair.

Run from repository root:
    /Users/elhadjibassirousy/Desktop/AI-Talent-Finder/.venv/bin/python backend/scripts/smoke_test_predict.py

This script avoids starting the HTTP server and directly loads the saved model
and its TF-IDF + SVD meta to compute a prediction on a synthetic example.
"""
import sys
from pathlib import Path
import joblib
import numpy as np

script_dir = Path(__file__).resolve().parent
repo_root = script_dir.parent.parent
if str(repo_root / 'backend') not in sys.path:
    sys.path.insert(0, str(repo_root / 'backend'))

from app.services.feature_engineering import PairFeatureMeta, build_pair_features


def main():
    model_path = repo_root / 'models' / 'baseline_model.joblib'
    if not model_path.exists():
        print('Baseline model not found. Expected at', model_path)
        sys.exit(3)

    try:
        bundle = joblib.load(model_path)
    except Exception as e:
        print('Failed to load joblib model:', e)
        sys.exit(4)

    model = bundle.get('model')
    meta = bundle.get('meta') or {}

    if isinstance(meta, PairFeatureMeta):
        feature_meta = meta
    else:
        tf = meta.get('tfidf') or meta.get('tf')
        svd = meta.get('svd')
        if tf is None or svd is None:
            print('Model meta missing tfidf/tf or svd objects')
            sys.exit(5)
        feature_meta = PairFeatureMeta(tfidf=tf, svd=svd)

    cand_text = 'Jean Dupont; Python; SQL; Docker; 5 years experience as backend developer'
    job_text = 'Senior Python Backend Developer. Required: Python, SQL, Docker, microservices.'

    try:
        X = build_pair_features(cand_text, job_text, feature_meta)
    except Exception as e:
        print('Feature building failed:', e)
        sys.exit(6)

    try:
        prob = None
        try:
            prob = model.predict_proba(X)[:,1][0]
        except Exception:
            try:
                prob = model.decision_function(X)[0]
                prob = 1/(1+np.exp(-prob))
            except Exception:
                prob = float(model.predict(X)[0])

        print('Prediction probability (0-1):', prob)
        print('Prediction percent:', float(max(0, min(100, prob*100))))
    except Exception as e:
        print('Model prediction failed:', e)
        sys.exit(7)

    print('Smoke test OK')


if __name__ == '__main__':
    main()
