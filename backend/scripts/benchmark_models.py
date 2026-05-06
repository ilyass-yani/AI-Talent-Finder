"""Benchmark baseline vs Siamese on CV-job pairs and propose decision thresholds.

Usage:
  source ../.venv-phase2/bin/activate
  python scripts/benchmark_models.py \
      --data ../data/training_pairs.csv \
      --baseline ../models/baseline_model.joblib \
      --siamese ../models/siamese_model_phase2_full \
      --out-json ../reports/model_comparison.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_recall_curve, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

script_dir = Path(__file__).resolve().parent
repo_root = script_dir.parent.parent
if str(repo_root / "backend") not in sys.path:
    sys.path.insert(0, str(repo_root / "backend"))

from app.services.feature_engineering import PairFeatureMeta, build_pair_features  # noqa: E402
from app.services.normalization import normalize_text  # noqa: E402


def _load_baseline(path: Path) -> tuple[Any, dict[str, Any]]:
    bundle = joblib.load(path)
    return bundle["model"], bundle.get("meta") or {}


def _baseline_scores(model: Any, meta: dict[str, Any], cv_texts: list[str], job_texts: list[str]) -> np.ndarray:
    if isinstance(meta, PairFeatureMeta):
        feature_meta = meta
    else:
        feature_meta = PairFeatureMeta(tfidf=meta["tf"], svd=meta["svd"])
    X = np.vstack([build_pair_features(c, j, feature_meta) for c, j in zip(cv_texts, job_texts)])

    try:
        scores = model.predict_proba(X)[:, 1]
    except Exception:
        try:
            raw = model.decision_function(X)
            scores = 1.0 / (1.0 + np.exp(-raw))
        except Exception:
            scores = model.predict(X).astype(float)
    return np.clip(scores, 0.0, 1.0)


def _siamese_scores(model_path: Path, cv_texts: list[str], job_texts: list[str]) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(str(model_path))
    cv_emb = model.encode(cv_texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
    job_emb = model.encode(job_texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
    cosine = np.sum(cv_emb * job_emb, axis=1)
    return np.clip(cosine, 0.0, 1.0)


def _metrics(y_true: np.ndarray, scores: np.ndarray, threshold: float = 0.5) -> dict[str, float]:
    preds = (scores >= threshold).astype(int)
    return {
        "accuracy": float(accuracy_score(y_true, preds)),
        "precision": float(precision_score(y_true, preds, zero_division=0)),
        "recall": float(recall_score(y_true, preds, zero_division=0)),
        "f1": float(f1_score(y_true, preds, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, scores)),
        "threshold": float(threshold),
    }


def _best_f1_threshold(y_true: np.ndarray, scores: np.ndarray) -> float:
    candidates = np.linspace(0.0, 1.0, 101)
    best_t = 0.5
    best_f1 = -1.0
    for t in candidates:
        f1 = f1_score(y_true, (scores >= t).astype(int), zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_t = float(t)
    return best_t


def _threshold_for_precision(
    y_true: np.ndarray,
    scores: np.ndarray,
    target_precision: float,
    fallback: float,
    min_threshold: float,
) -> float:
    precision, recall, thresholds = precision_recall_curve(y_true, scores)
    if len(thresholds) == 0:
        return fallback

    candidates: list[float] = []
    for idx, threshold in enumerate(thresholds):
        p = precision[idx + 1]
        if p >= target_precision and float(threshold) >= min_threshold:
            candidates.append(float(threshold))

    if not candidates:
        return fallback
    return min(candidates)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=str(repo_root / "data" / "training_pairs.csv"))
    parser.add_argument("--baseline", default=str(repo_root / "models" / "baseline_model.joblib"))
    parser.add_argument("--siamese", default=str(repo_root / "models" / "siamese_model_phase2_full"))
    parser.add_argument("--test-size", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-json", default=str(repo_root / "reports" / "model_comparison.json"))
    args = parser.parse_args()

    df = pd.read_csv(args.data)
    df["label"] = df["label"].astype(int)
    df["cv_text"] = df["cv_text"].fillna("").astype(str).map(normalize_text)
    df["job_text"] = df["job_text"].fillna("").astype(str).map(normalize_text)

    train_df, test_df = train_test_split(
        df,
        test_size=args.test_size,
        random_state=args.seed,
        stratify=df["label"],
    )

    y_test = test_df["label"].to_numpy()
    cv_texts = test_df["cv_text"].tolist()
    job_texts = test_df["job_text"].tolist()

    baseline_model, baseline_meta = _load_baseline(Path(args.baseline))
    baseline_scores = _baseline_scores(baseline_model, baseline_meta, cv_texts, job_texts)

    siamese_scores = _siamese_scores(Path(args.siamese), cv_texts, job_texts)

    baseline_default = _metrics(y_test, baseline_scores, threshold=0.5)
    siamese_default = _metrics(y_test, siamese_scores, threshold=0.5)

    baseline_best_t = _best_f1_threshold(y_test, baseline_scores)
    siamese_best_t = _best_f1_threshold(y_test, siamese_scores)

    baseline_best = _metrics(y_test, baseline_scores, threshold=baseline_best_t)
    siamese_best = _metrics(y_test, siamese_scores, threshold=siamese_best_t)

    # Business calibration from the best default ROC-AUC model.
    selected_model = "baseline" if baseline_default["roc_auc"] >= siamese_default["roc_auc"] else "siamese"
    selected_scores = baseline_scores if selected_model == "baseline" else siamese_scores

    accept_t = _threshold_for_precision(
        y_test,
        selected_scores,
        target_precision=0.90,
        fallback=0.80,
        min_threshold=0.50,
    )
    review_t = _threshold_for_precision(
        y_test,
        selected_scores,
        target_precision=0.70,
        fallback=0.50,
        min_threshold=0.30,
    )
    review_t = float(min(review_t, accept_t - 0.05)) if accept_t > 0.05 else 0.50

    result = {
        "dataset": {
            "path": str(Path(args.data).resolve()),
            "rows_total": int(len(df)),
            "rows_train": int(len(train_df)),
            "rows_test": int(len(test_df)),
            "seed": int(args.seed),
            "test_size": float(args.test_size),
        },
        "baseline": {
            "default_threshold_0_5": baseline_default,
            "best_f1": baseline_best,
        },
        "siamese": {
            "default_threshold_0_5": siamese_default,
            "best_f1": siamese_best,
            "model_path": str(Path(args.siamese).resolve()),
        },
        "production_recommendation": {
            "model": selected_model,
            "accept_threshold_score_pct": round(accept_t * 100.0, 2),
            "review_threshold_score_pct": round(review_t * 100.0, 2),
            "env": {
                "MATCH_ACCEPT_THRESHOLD": str(round(accept_t * 100.0, 2)),
                "MATCH_REVIEW_THRESHOLD": str(round(review_t * 100.0, 2)),
            },
        },
    }

    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=== Model comparison complete ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Saved report to {out_path}")


if __name__ == "__main__":
    main()
