"""Demo script for soutenance.

This offline demo loads the saved baseline model and prints a small ranked
comparison between two sample candidates against one sample job profile.

Run from repo root:
    /Users/elhadjibassirousy/Desktop/AI-Talent-Finder/.venv/bin/python backend/scripts/demo_soutenance.py
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
from app.services.normalization import normalize_text


def build_features(candidate_text: str, job_text: str, meta: dict):
    if isinstance(meta, PairFeatureMeta):
        feature_meta = meta
    else:
        tf = meta.get("tfidf") or meta.get("tf")
        svd = meta.get("svd")
        feature_meta = PairFeatureMeta(tfidf=tf, svd=svd)
    return build_pair_features(candidate_text, job_text, feature_meta)


def score_candidate(model, meta, candidate_text: str, job_text: str):
    features = build_features(candidate_text, job_text, meta)
    try:
        probability = model.predict_proba(features)[:, 1][0]
    except Exception:
        decision = model.decision_function(features)[0]
        probability = 1 / (1 + np.exp(-decision))

    candidate_tokens = set(normalize_text(candidate_text).split())
    job_tokens = set(normalize_text(job_text).split())
    coverage = len(candidate_tokens & job_tokens) / max(1, len(job_tokens))
    blended_score = (0.25 * float(probability) + 0.75 * float(coverage)) * 100

    return float(blended_score), float(probability * 100), float(coverage * 100)


def main():
    model_path = repo_root / "models" / "baseline_model.joblib"
    if not model_path.exists():
        raise SystemExit(f"Model not found: {model_path}")

    bundle = joblib.load(model_path)
    model = bundle["model"]
    meta = bundle["meta"]

    job_text = (
        "Senior Python Backend Developer\n"
        "Required: Python, FastAPI, SQL, Docker, AWS, microservices."
    )

    candidates = [
        {
            "name": "Jean Dupont",
            "text": "Jean Dupont; Senior Python Backend Developer; Python; FastAPI; SQL; Docker; AWS; microservices; backend architecture; 6 years backend experience; team leadership",
        },
        {
            "name": "Sarah Martin",
            "text": "Sarah Martin; React; UI/UX; Figma; 4 years frontend experience; communication; design systems; product design",
        },
    ]

    scored = []
    for candidate in candidates:
        blended_score, model_score, coverage_score = score_candidate(model, meta, candidate["text"], job_text)
        scored.append((candidate["name"], blended_score, model_score, coverage_score, candidate["text"]))

    scored.sort(key=lambda item: item[1], reverse=True)

    print("=== Démo soutenance - Baseline matching ===")
    print("Poste:")
    print(job_text)
    print()
    for index, (name, score, model_score, coverage_score, text) in enumerate(scored, start=1):
        print(f"#{index} {name}: {score:.1f}% (modèle {model_score:.1f}%, couverture {coverage_score:.1f}%)")
        print(f"  CV: {text}")
        print()

    print("Conclusion: la démo combine le score du modèle et la couverture des compétences pour présenter un ranking lisible.")


if __name__ == "__main__":
    main()
