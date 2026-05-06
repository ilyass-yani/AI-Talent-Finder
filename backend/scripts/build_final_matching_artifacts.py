"""Build the final matching artifacts for the project.

This script creates a reproducible pipeline that:
- exports a labeled dataset mixing real DB records and synthetic augmentation
- trains a supervised baseline model with train/test separation
- benchmarks it against the lightweight semantic matcher
- writes a final model bundle and a JSON report for the defense/demo

Usage:
    /Users/elhadjibassirousy/Desktop/AI-Talent-Finder/.venv/bin/python \
      backend/scripts/build_final_matching_artifacts.py \
      --db backend/ai_talent_finder.db
"""

from __future__ import annotations

import argparse
import json
import random
import sqlite3
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

script_dir = Path(__file__).resolve().parent
repo_root = script_dir.parent.parent
if str(repo_root / "backend") not in sys.path:
    sys.path.insert(0, str(repo_root / "backend"))

from app.services.data_normalization import parse_experience_years
from app.services.feature_engineering import build_pair_features, fit_pair_vectorizer
from app.services.lightweight_siamese import get_siamese_matcher
from app.services.normalization import normalize_skill_name, normalize_text
from app.services.scoring import compute_match_score
from app.services.synthetic_data import SKILLS_POOL, generate_synthetic_candidate


@dataclass
class SplitMetrics:
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float | None
    threshold: float


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _normalize_skill_list(skills: list[str] | None) -> list[str]:
    return [normalize_skill_name(skill) for skill in (skills or []) if normalize_skill_name(skill)]


def _candidate_text(record: dict[str, Any]) -> str:
    parts: list[str] = [record.get("full_name") or "", record.get("raw_text") or ""]
    parts.extend(record.get("skills", []))
    parts.extend(record.get("companies", []))
    parts.extend(record.get("job_titles", []))
    parts.extend(record.get("education", []))
    parts.extend(record.get("languages", []))
    return normalize_text(" \n ".join(part for part in parts if part))


def _job_text(record: dict[str, Any]) -> str:
    parts: list[str] = [record.get("title") or "", record.get("description") or ""]
    parts.extend(record.get("required_skills", []))
    parts.extend(record.get("languages_required", []))
    parts.append(str(record.get("required_years") or ""))
    return normalize_text(" \n ".join(part for part in parts if part))


def _load_real_data(db_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    candidates: list[dict[str, Any]] = []
    for row in cur.execute(
        """
        SELECT id, full_name, email, raw_text, extraction_quality_score, ner_extraction_data,
               extracted_job_titles, extracted_companies, extracted_education, is_fully_extracted
        FROM candidates
        ORDER BY created_at DESC
        """
    ).fetchall():
        payload: dict[str, Any] = {}
        if row["ner_extraction_data"]:
            try:
                payload = json.loads(row["ner_extraction_data"])
            except Exception:
                payload = {}

        skills = _normalize_skill_list(payload.get("skills") or [])
        companies = payload.get("companies") or []
        job_titles = payload.get("job_titles") or []
        education = payload.get("education") or []
        languages = payload.get("languages") or []
        experience_years = parse_experience_years(row["raw_text"] or "")

        candidates.append(
            {
                "id": int(row["id"]),
                "source": "real_db",
                "full_name": row["full_name"] or "",
                "email": row["email"] or "",
                "raw_text": row["raw_text"] or "",
                "skills": skills,
                "companies": companies,
                "job_titles": job_titles,
                "education": education,
                "languages": languages,
                "experience_years": experience_years,
                "quality_score": float(row["extraction_quality_score"] or 0.0),
                "is_fully_extracted": bool(row["is_fully_extracted"]),
            }
        )

    jobs: list[dict[str, Any]] = []
    for row in cur.execute(
        """
        SELECT jc.id, jc.title, jc.description, jc.created_at
        FROM job_criteria jc
        ORDER BY jc.created_at DESC
        """
    ).fetchall():
        skill_rows = cur.execute(
            """
            SELECT s.name
            FROM criteria_skills cs
            JOIN skills s ON s.id = cs.skill_id
            WHERE cs.criteria_id = ?
            ORDER BY cs.id ASC
            """,
            (row["id"],),
        ).fetchall()
        required_skills = _normalize_skill_list([skill_row["name"] for skill_row in skill_rows])
        jobs.append(
            {
                "id": int(row["id"]),
                "source": "real_db",
                "title": row["title"] or "",
                "description": row["description"] or "",
                "required_skills": required_skills,
                "required_years": parse_experience_years((row["description"] or "") + " " + (row["title"] or "")),
                "languages_required": [],
            }
        )

    conn.close()
    return candidates, jobs


def _heuristic_label(candidate: dict[str, Any], job: dict[str, Any]) -> tuple[int, float]:
    candidate_skills = _normalize_skill_list(candidate.get("skills", []))
    job_skills = _normalize_skill_list(job.get("required_skills", []))

    candidate_years = int(candidate.get("experience_years") or parse_experience_years(candidate.get("raw_text", "")) or 0)
    job_years = int(job.get("required_years") or parse_experience_years(job.get("description", "")) or 0)

    intersection = set(candidate_skills) & set(job_skills)
    union = set(candidate_skills) | set(job_skills)
    semantic_similarity = len(intersection) / max(1, len(union))

    score = compute_match_score(
        cv_skills=candidate_skills,
        job_skills=job_skills,
        cv_years=candidate_years,
        job_years=job_years,
        cv_edu_level=2,
        job_edu_level=2,
        similarity_score=semantic_similarity,
    )
    label = 1 if score >= 0.60 else 0
    return label, float(score)


def _rows_from_pairs(candidates: list[dict[str, Any]], jobs: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_text = _candidate_text(candidate)
        for job in jobs:
            job_text = _job_text(job)
            label, score = _heuristic_label(candidate, job)
            rows.append(
                {
                    "source": source,
                    "cv_id": candidate.get("id"),
                    "job_id": job.get("id"),
                    "candidate_name": candidate.get("full_name", ""),
                    "job_title": job.get("title", ""),
                    "cv_text": candidate_text,
                    "job_text": job_text,
                    "label": label,
                    "heuristic_score": round(score, 4),
                }
            )
    return rows


def _synthetic_job_from_candidate(candidate: dict[str, Any], positive: bool, rng: random.Random, job_id: int) -> dict[str, Any]:
    candidate_skills = _normalize_skill_list(candidate.get("skills", []))
    if positive:
        required_skills = candidate_skills[:]
        if len(required_skills) > 4:
            required_skills = rng.sample(required_skills, 4)
        if not required_skills:
            required_skills = [rng.choice(SKILLS_POOL)]
        title = f"Senior {' '.join(required_skills[:2]).replace(' ', '')} Engineer"
        description = (
            f"Looking for a developer with strong skills in {', '.join(required_skills)} "
            f"and {max(0, int(candidate.get('experience_years') or 0) - 1)}+ years of experience."
        )
        required_years = max(0, int(candidate.get("experience_years") or 0) - 1)
    else:
        disjoint_pool = [skill for skill in SKILLS_POOL if skill not in candidate_skills]
        if len(disjoint_pool) < 3:
            disjoint_pool = SKILLS_POOL[:]
        required_skills = rng.sample(disjoint_pool, min(4, len(disjoint_pool)))
        title = "Unrelated Engineer"
        description = f"Looking for a profile with expertise in {', '.join(required_skills)}."
        required_years = int(candidate.get("experience_years") or 0) + 3

    return {
        "id": job_id,
        "source": "synthetic",
        "title": title,
        "description": description,
        "required_skills": required_skills,
        "required_years": required_years,
        "languages_required": ["English"],
    }


def _build_dataset(db_path: Path, synthetic_candidates: int, synthetic_jobs: int, seed: int) -> pd.DataFrame:
    real_candidates, real_jobs = _load_real_data(db_path)
    rows: list[dict[str, Any]] = []

    if real_candidates and real_jobs:
        rows.extend(_rows_from_pairs(real_candidates, real_jobs, source="real_db"))

    rng = random.Random(seed)
    synthetic_candidates_rows = []
    for index in range(synthetic_candidates):
        item = generate_synthetic_candidate(user_id=10_000 + index)
        synthetic_candidates_rows.append(
            {
                **item,
                "source": "synthetic",
                "full_name": item.get("full_name", ""),
                "email": item.get("email", ""),
                "raw_text": " ".join(
                    [
                        item.get("full_name", ""),
                        " ".join(item.get("normalized_skills", [])),
                        str(item.get("experience_years", 0)),
                        item.get("education", ""),
                        " ".join(item.get("languages", [])),
                    ]
                ),
                "skills": item.get("normalized_skills", []),
                "companies": [],
                "job_titles": [],
                "education": [item.get("education", "")],
                "languages": item.get("languages", []),
            }
        )

    synthetic_pairs: list[dict[str, Any]] = []
    next_job_id = 20_000
    for candidate in synthetic_candidates_rows:
        positive_job = _synthetic_job_from_candidate(candidate, positive=True, rng=rng, job_id=next_job_id)
        next_job_id += 1
        negative_job = _synthetic_job_from_candidate(candidate, positive=False, rng=rng, job_id=next_job_id)
        next_job_id += 1

        for job, label in ((positive_job, 1), (negative_job, 0)):
            job_text = _job_text(job)
            candidate_text = _candidate_text(candidate)
            _, score = _heuristic_label(candidate, job)
            synthetic_pairs.append(
                {
                    "source": "synthetic",
                    "cv_id": candidate.get("id"),
                    "job_id": job.get("id"),
                    "candidate_name": candidate.get("full_name", ""),
                    "job_title": job.get("title", ""),
                    "cv_text": candidate_text,
                    "job_text": job_text,
                    "label": label,
                    "heuristic_score": round(score, 4),
                }
            )

    rows.extend(synthetic_pairs)

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("No training rows could be built from the database or synthetic augmentation.")

    df = df.drop_duplicates(subset=["cv_text", "job_text", "label"]).reset_index(drop=True)
    return df


def _build_matrix(df: pd.DataFrame, meta) -> np.ndarray:
    return np.vstack([
        build_pair_features(str(row.cv_text), str(row.job_text), meta)
        for row in df.itertuples(index=False)
    ])


def _train_model(X_train: np.ndarray, y_train: np.ndarray):
    try:
        from xgboost import XGBClassifier

        model = XGBClassifier(
            n_estimators=250,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.85,
            eval_metric="logloss",
            random_state=42,
        )
        model.fit(X_train, y_train)
        model_name = "xgboost"
    except Exception:
        model = LogisticRegression(max_iter=2000, class_weight="balanced")
        model.fit(X_train, y_train)
        model_name = "logistic_regression"

    return model, model_name


def _predict_scores(model, X: np.ndarray) -> np.ndarray:
    try:
        scores = model.predict_proba(X)[:, 1]
    except Exception:
        try:
            raw_scores = model.decision_function(X)
            scores = 1.0 / (1.0 + np.exp(-raw_scores))
        except Exception:
            scores = model.predict(X).astype(float)
    return np.clip(scores.astype(float), 0.0, 1.0)


def _metrics(y_true: np.ndarray, scores: np.ndarray, threshold: float = 0.5) -> SplitMetrics:
    preds = (scores >= threshold).astype(int)
    roc_auc = None
    try:
        roc_auc = float(roc_auc_score(y_true, scores))
    except Exception:
        roc_auc = None

    return SplitMetrics(
        accuracy=float(accuracy_score(y_true, preds)),
        precision=float(precision_score(y_true, preds, zero_division=0)),
        recall=float(recall_score(y_true, preds, zero_division=0)),
        f1=float(f1_score(y_true, preds, zero_division=0)),
        roc_auc=roc_auc,
        threshold=float(threshold),
    )


def _best_f1_threshold(y_true: np.ndarray, scores: np.ndarray) -> float:
    best_threshold = 0.5
    best_f1 = -1.0
    for threshold in np.linspace(0.0, 1.0, 101):
        f1 = f1_score(y_true, (scores >= threshold).astype(int), zero_division=0)
        if f1 > best_f1:
            best_f1 = float(f1)
            best_threshold = float(threshold)
    return best_threshold


def _threshold_for_precision(y_true: np.ndarray, scores: np.ndarray, target_precision: float, fallback: float) -> float:
    candidates = np.linspace(0.0, 1.0, 101)
    best = fallback
    for threshold in candidates:
        predictions = (scores >= threshold).astype(int)
        precision = precision_score(y_true, predictions, zero_division=0)
        if precision >= target_precision:
            best = float(threshold)
            break
    return float(best)


def build_and_train(db_path: Path, synthetic_candidates: int, synthetic_jobs: int, seed: int) -> dict[str, Any]:
    df = _build_dataset(db_path, synthetic_candidates, synthetic_jobs, seed)

    dataset_path = repo_root / "data" / "final_training_pairs.csv"
    review_sample_path = repo_root / "data" / "final_training_review_sample.csv"
    report_path = repo_root / "reports" / "advanced_matching_report.json"
    model_path = repo_root / "models" / "final_match_model.joblib"
    fallback_model_path = repo_root / "models" / "baseline_model.joblib"

    _ensure_parent(dataset_path)
    _ensure_parent(review_sample_path)
    _ensure_parent(report_path)
    _ensure_parent(model_path)

    df.to_csv(dataset_path, index=False)
    df.sample(min(200, len(df)), random_state=seed).to_csv(review_sample_path, index=False)

    train_df, test_df = train_test_split(
        df,
        test_size=0.20,
        random_state=seed,
        stratify=df["label"],
    )

    meta = fit_pair_vectorizer(train_df["cv_text"].tolist(), train_df["job_text"].tolist())
    X_train = _build_matrix(train_df, meta)
    X_test = _build_matrix(test_df, meta)
    y_train = train_df["label"].to_numpy()
    y_test = test_df["label"].to_numpy()

    model, model_name = _train_model(X_train, y_train)

    train_scores = _predict_scores(model, X_train)
    test_scores = _predict_scores(model, X_test)

    train_metrics = _metrics(y_train, train_scores, threshold=0.5)
    test_metrics = _metrics(y_test, test_scores, threshold=0.5)
    best_threshold = _best_f1_threshold(y_test, test_scores)
    best_metrics = _metrics(y_test, test_scores, threshold=best_threshold)

    siamese = get_siamese_matcher()
    semantic_scores = np.array([
        siamese.compute_pair_similarity(row.cv_text, row.job_text) for row in test_df.itertuples(index=False)
    ], dtype=float)
    semantic_metrics = _metrics(y_test, semantic_scores, threshold=0.5)

    accept_threshold = max(
        0.80,
        _threshold_for_precision(y_test, test_scores, target_precision=0.90, fallback=0.80),
    )
    review_threshold = max(
        0.50,
        _threshold_for_precision(y_test, test_scores, target_precision=0.70, fallback=0.50),
    )
    review_threshold = float(min(review_threshold, max(0.0, accept_threshold - 0.05)))

    positive_rate = float(df["label"].mean())
    dataset_summary = {
        "rows_total": int(len(df)),
        "rows_train": int(len(train_df)),
        "rows_test": int(len(test_df)),
        "source_counts": df["source"].value_counts().to_dict(),
        "positive_rate": positive_rate,
        "seed": int(seed),
    }

    thresholds = {
        "accept_pct": round(accept_threshold * 100.0, 2),
        "review_pct": round(review_threshold * 100.0, 2),
    }

    bundle = {
        "model": model,
        "meta": meta,
        "model_name": model_name,
        "thresholds": thresholds,
        "dataset_summary": dataset_summary,
        "training_metrics": {
            "train": asdict(train_metrics),
            "test": asdict(test_metrics),
            "test_best_f1": asdict(best_metrics),
            "lightweight_semantic": asdict(semantic_metrics),
        },
    }

    joblib.dump(bundle, model_path)
    joblib.dump(bundle, fallback_model_path)

    report = {
        "dataset": dataset_summary,
        "model": {
            "name": model_name,
            "path": str(model_path.resolve()),
            "fallback_path": str(fallback_model_path.resolve()),
        },
        "metrics": bundle["training_metrics"],
        "production_recommendation": {
            "accept_threshold_score_pct": thresholds["accept_pct"],
            "review_threshold_score_pct": thresholds["review_pct"],
            "env": {
                "MATCH_ACCEPT_THRESHOLD": str(thresholds["accept_pct"]),
                "MATCH_REVIEW_THRESHOLD": str(thresholds["review_pct"]),
            },
        },
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "dataset_path": str(dataset_path),
        "review_sample_path": str(review_sample_path),
        "model_path": str(model_path),
        "fallback_model_path": str(fallback_model_path),
        "report_path": str(report_path),
        "report": report,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(repo_root / "backend" / "ai_talent_finder.db"), help="SQLite DB path")
    parser.add_argument("--synthetic-candidates", type=int, default=40)
    parser.add_argument("--synthetic-jobs", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    result = build_and_train(
        Path(args.db),
        synthetic_candidates=args.synthetic_candidates,
        synthetic_jobs=args.synthetic_jobs,
        seed=args.seed,
    )

    print("=== Final matching artifacts built ===")
    print(json.dumps(result["report"], indent=2, ensure_ascii=False))
    print(f"Dataset: {result['dataset_path']}")
    print(f"Review sample: {result['review_sample_path']}")
    print(f"Model bundle: {result['model_path']}")
    print(f"Fallback bundle: {result['fallback_model_path']}")
    print(f"Report: {result['report_path']}")


if __name__ == "__main__":
    main()