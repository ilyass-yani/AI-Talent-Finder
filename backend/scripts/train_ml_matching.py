#!/usr/bin/env python3
"""
Complete ML Matching Pipeline
Trains and compares Logistic Regression, Random Forest, and XGBoost
on CV-job matching pairs. Outputs a comparison report and saves all models.

Pipeline:
  Raw texts (CV + job descriptions)
  → TF-IDF vectorization
  → SVD dimensionality reduction (optional)
  → Pair feature vector (diff, cosine, ratios)
  → Classifier training + cross-validation
  → Model selection and serialization

Usage:
  # From a JSONL of extracted CVs:
  PYTHONPATH=backend python backend/scripts/train_ml_matching.py \\
      --input data/extracted_cvs.jsonl \\
      --jobs data/job_descriptions.jsonl \\
      --out models/ml_matching/

  # Generate synthetic data and train:
  PYTHONPATH=backend python backend/scripts/train_ml_matching.py \\
      --synthetic 200 \\
      --out models/ml_matching/
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np

from sklearn.decomposition import TruncatedSVD
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

try:
    from xgboost import XGBClassifier
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Synthetic data generation
# ---------------------------------------------------------------------------

_CV_TEMPLATES = [
    "Python developer with {exp} years of experience in {skills}. Worked at {company}. "
    "Bachelor in Computer Science from {school}.",
    "Data scientist specializing in {skills}. {exp} years of hands-on experience. "
    "MSc Machine Learning.",
    "Full-stack engineer proficient in {skills}. {exp} years building web applications.",
    "DevOps engineer with expertise in {skills}. {exp} years managing cloud infrastructure.",
    "ML engineer with {exp} years developing {skills} models. PhD candidate.",
    "Software architect with {exp} years designing distributed systems using {skills}.",
    "Frontend developer, {exp} years experience with {skills}. Award-winning UX portfolio.",
    "Backend engineer focusing on {skills}. {exp} years at scale-ups and FAANG.",
]

_JOB_TEMPLATES = [
    "We are looking for a {level} engineer with strong skills in {skills}. "
    "{exp_req}+ years of experience required. Join our {team} team.",
    "Seeking a data scientist with expertise in {skills}. Must have {exp_req} years in ML/AI.",
    "Full-stack developer needed. Required: {skills}. {exp_req}+ years experience.",
    "Cloud DevOps role — expertise in {skills} essential. {exp_req} years minimum.",
    "ML engineer position. Deep knowledge of {skills}. PhD or {exp_req}+ years experience.",
    "Senior software architect needed. Expertise: {skills}. {exp_req} years in distributed systems.",
    "React/TypeScript frontend developer. Must know {skills}. {exp_req} years experience.",
    "Python backend engineer. Stack: {skills}. {exp_req}+ years at scale.",
]

_SKILL_POOLS = {
    "python": ["Python", "FastAPI", "Django", "Pandas", "NumPy", "Pytest"],
    "data": ["Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "Spark", "SQL"],
    "frontend": ["React", "TypeScript", "JavaScript", "CSS", "HTML", "Vue"],
    "devops": ["Docker", "Kubernetes", "AWS", "Terraform", "CI/CD", "Linux"],
    "java": ["Java", "Spring Boot", "Microservices", "Maven", "JUnit"],
}

_COMPANIES = ["Accenture", "Capgemini", "Thales", "Airbus", "BNP Paribas", "SNCF", "Orange"]
_SCHOOLS = ["Université Paris-Saclay", "École Polytechnique", "EPITA", "INSA Lyon", "CentraleSupélec"]
_LEVELS = ["Junior", "Mid-level", "Senior", "Lead", "Principal"]
_TEAMS = ["data", "platform", "product", "infrastructure", "AI/ML", "core backend"]


def _random_skills(pool_key: Optional[str] = None, n: int = 4) -> str:
    if pool_key and pool_key in _SKILL_POOLS:
        skills = _SKILL_POOLS[pool_key]
    else:
        pool_key = random.choice(list(_SKILL_POOLS.keys()))
        skills = _SKILL_POOLS[pool_key]
    return ", ".join(random.sample(skills, min(n, len(skills))))


def generate_synthetic_pairs(n: int = 300, positive_ratio: float = 0.5) -> Tuple[List[str], List[str], List[int]]:
    """Generate synthetic (cv_text, job_text, label) triples."""
    cv_texts, job_texts, labels = [], [], []

    n_positive = int(n * positive_ratio)
    n_negative = n - n_positive

    # Positive pairs: same skill domain
    for _ in range(n_positive):
        pool_key = random.choice(list(_SKILL_POOLS.keys()))
        exp = random.randint(1, 12)
        exp_req = max(1, exp - random.randint(0, 2))

        cv = random.choice(_CV_TEMPLATES).format(
            exp=exp,
            skills=_random_skills(pool_key),
            company=random.choice(_COMPANIES),
            school=random.choice(_SCHOOLS),
        )
        job = random.choice(_JOB_TEMPLATES).format(
            level=random.choice(_LEVELS),
            skills=_random_skills(pool_key),
            exp_req=exp_req,
            team=random.choice(_TEAMS),
        )
        cv_texts.append(cv)
        job_texts.append(job)
        labels.append(1)

    # Negative pairs: different skill domains
    pool_keys = list(_SKILL_POOLS.keys())
    for _ in range(n_negative):
        key_a, key_b = random.sample(pool_keys, 2)
        exp = random.randint(1, 12)

        cv = random.choice(_CV_TEMPLATES).format(
            exp=exp,
            skills=_random_skills(key_a),
            company=random.choice(_COMPANIES),
            school=random.choice(_SCHOOLS),
        )
        job = random.choice(_JOB_TEMPLATES).format(
            level=random.choice(_LEVELS),
            skills=_random_skills(key_b),
            exp_req=random.randint(1, 8),
            team=random.choice(_TEAMS),
        )
        cv_texts.append(cv)
        job_texts.append(job)
        labels.append(0)

    # Shuffle
    combined = list(zip(cv_texts, job_texts, labels))
    random.shuffle(combined)
    cv_texts, job_texts, labels = zip(*combined)
    return list(cv_texts), list(job_texts), list(labels)


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

def build_features(
    cv_texts: List[str],
    job_texts: List[str],
    vectorizer: Optional[TfidfVectorizer] = None,
    svd: Optional[TruncatedSVD] = None,
    fit: bool = False,
) -> Tuple[np.ndarray, TfidfVectorizer, Optional[TruncatedSVD]]:
    """
    Build pair-level feature vectors.

    Features:
    - |v_cv - v_job| (element-wise absolute difference)
    - v_cv * v_job   (element-wise product)
    - cosine_similarity(v_cv, v_job)
    - token overlap ratio
    - text length ratio
    """
    all_texts = cv_texts + job_texts

    if fit or vectorizer is None:
        vectorizer = TfidfVectorizer(
            max_features=15_000,
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=1,
        )
        X_all = vectorizer.fit_transform(all_texts)
    else:
        X_all = vectorizer.transform(all_texts)

    n = len(cv_texts)
    X_cv = X_all[:n]
    X_job = X_all[n:]

    if fit:
        n_components = min(150, X_all.shape[1] - 1)
        if n_components > 1:
            svd = TruncatedSVD(n_components=n_components, random_state=42)
            svd.fit(X_all)
        else:
            svd = None

    if svd is not None:
        X_cv_d = svd.transform(X_cv)
        X_job_d = svd.transform(X_job)
    else:
        X_cv_d = X_cv.toarray()
        X_job_d = X_job.toarray()

    # Pair features
    diff = np.abs(X_cv_d - X_job_d)
    prod = X_cv_d * X_job_d

    cos_sims = np.array([
        cosine_similarity(X_cv_d[i].reshape(1, -1), X_job_d[i].reshape(1, -1))[0][0]
        for i in range(n)
    ]).reshape(-1, 1)

    # Lexical overlap
    overlaps = np.array([
        _token_overlap(cv_texts[i], job_texts[i])
        for i in range(n)
    ]).reshape(-1, 1)

    # Length ratio
    len_ratios = np.array([
        min(len(cv_texts[i]), len(job_texts[i])) / (max(len(cv_texts[i]), len(job_texts[i])) + 1)
        for i in range(n)
    ]).reshape(-1, 1)

    X = np.hstack([diff, prod, cos_sims, overlaps, len_ratios])
    return X, vectorizer, svd


def _token_overlap(text_a: str, text_b: str) -> float:
    tokens_a = set(text_a.lower().split())
    tokens_b = set(text_b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


# ---------------------------------------------------------------------------
# Model definitions
# ---------------------------------------------------------------------------

def build_models() -> Dict:
    models = {
        "logistic_regression": LogisticRegression(
            C=1.0,
            max_iter=1000,
            solver="lbfgs",
            class_weight="balanced",
            random_state=42,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_split=5,
            class_weight="balanced",
            n_jobs=-1,
            random_state=42,
        ),
        "gradient_boosting": GradientBoostingClassifier(
            n_estimators=150,
            learning_rate=0.1,
            max_depth=4,
            random_state=42,
        ),
    }

    if XGB_AVAILABLE:
        models["xgboost"] = XGBClassifier(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=5,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="logloss",
            use_label_encoder=False,
            random_state=42,
            verbosity=0,
        )

    return models


# ---------------------------------------------------------------------------
# Training + evaluation
# ---------------------------------------------------------------------------

def evaluate_model(model, X_test: np.ndarray, y_test: np.ndarray, name: str) -> Dict:
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else y_pred

    metrics = {
        "model": name,
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_test, y_pred, zero_division=0), 4),
        "f1": round(f1_score(y_test, y_pred, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y_test, y_proba), 4),
    }
    return metrics


def train_and_compare(
    cv_texts: List[str],
    job_texts: List[str],
    labels: List[int],
    out_dir: Path,
    cv_folds: int = 5,
) -> Dict:
    y = np.array(labels)

    log.info("Building features for %d pairs…", len(cv_texts))
    X, vectorizer, svd = build_features(cv_texts, job_texts, fit=True)
    log.info("Feature matrix: %s", X.shape)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y
    )

    models = build_models()
    results: List[Dict] = []
    trained: Dict = {}

    for name, model in models.items():
        log.info("Training %s…", name)
        t0 = time.time()

        # Cross-validation
        cv_scores = cross_val_score(
            model, X_train, y_train,
            cv=StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42),
            scoring="f1",
            n_jobs=-1,
        )

        # Final fit on full training set
        model.fit(X_train, y_train)
        elapsed = time.time() - t0

        metrics = evaluate_model(model, X_test, y_test, name)
        metrics["cv_f1_mean"] = round(cv_scores.mean(), 4)
        metrics["cv_f1_std"] = round(cv_scores.std(), 4)
        metrics["train_time_s"] = round(elapsed, 2)

        log.info(
            "  %s → acc=%.3f f1=%.3f roc_auc=%.3f cv_f1=%.3f±%.3f",
            name,
            metrics["accuracy"],
            metrics["f1"],
            metrics["roc_auc"],
            metrics["cv_f1_mean"],
            metrics["cv_f1_std"],
        )
        log.info("  Detailed report:\n%s", classification_report(y_test, model.predict(X_test)))

        results.append(metrics)
        trained[name] = model

    # Best model by F1
    best = max(results, key=lambda r: r["f1"])
    log.info("Best model: %s (F1=%.4f)", best["model"], best["f1"])

    # Persist
    out_dir.mkdir(parents=True, exist_ok=True)

    artifact = {
        "vectorizer": vectorizer,
        "svd": svd,
        "scaler": scaler,
        "models": trained,
        "best_model_name": best["model"],
        "results": results,
    }
    bundle_path = out_dir / "ml_matching_bundle.joblib"
    joblib.dump(artifact, bundle_path)
    log.info("Saved full bundle → %s", bundle_path)

    # Also save best model standalone
    best_path = out_dir / "best_model.joblib"
    joblib.dump(
        {
            "model": trained[best["model"]],
            "vectorizer": vectorizer,
            "svd": svd,
            "scaler": scaler,
            "model_name": best["model"],
        },
        best_path,
    )
    log.info("Saved best model standalone → %s", best_path)

    # Save report
    report = {"results": results, "best": best, "n_pairs": len(labels), "n_features": X.shape[1]}
    report_path = out_dir / "training_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    log.info("Saved report → %s", report_path)

    return report


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def load_jsonl_texts(path: Path, text_field: str = "text") -> List[str]:
    texts = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                texts.append(rec.get(text_field) or rec.get("raw_text") or "")
            except json.JSONDecodeError:
                continue
    return texts


def load_labeled_pairs(path: Path) -> Tuple[List[str], List[str], List[int]]:
    """Load labeled (cv_text, job_text, label) triples from a JSONL file."""
    cv_texts, job_texts, labels = [], [], []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                cv_texts.append(rec["cv_text"])
                job_texts.append(rec["job_text"])
                labels.append(int(rec["label"]))
            except (KeyError, ValueError):
                continue
    return cv_texts, job_texts, labels


# ---------------------------------------------------------------------------
# Inference helper (can be imported by the API)
# ---------------------------------------------------------------------------

def predict_match(cv_text: str, job_text: str, bundle_path: str) -> Dict:
    """Load saved bundle and predict match probability for a CV-job pair."""
    artifact = joblib.load(bundle_path)
    vectorizer = artifact["vectorizer"]
    svd = artifact.get("svd")
    scaler = artifact["scaler"]
    model = artifact["models"][artifact["best_model_name"]]

    X, _, _ = build_features([cv_text], [job_text], vectorizer=vectorizer, svd=svd, fit=False)
    X_scaled = scaler.transform(X)

    proba = model.predict_proba(X_scaled)[0][1]
    label = int(proba >= 0.5)
    decision = "compatible" if label == 1 else "incompatible"

    return {
        "score": round(float(proba) * 100, 1),
        "label": label,
        "decision": decision,
        "model_used": artifact["best_model_name"],
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description="Train ML matching models (LR, RF, XGBoost)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--synthetic", type=int, metavar="N", help="Generate N synthetic pairs")
    group.add_argument("--pairs", type=str, metavar="JSONL", help="JSONL with {cv_text, job_text, label}")
    parser.add_argument("--out", default="models/ml_matching", help="Output directory")
    parser.add_argument("--cv-folds", type=int, default=5, help="Cross-validation folds")
    args = parser.parse_args(argv)

    out_dir = Path(args.out)

    if args.synthetic:
        log.info("Generating %d synthetic pairs…", args.synthetic)
        cv_texts, job_texts, labels = generate_synthetic_pairs(n=args.synthetic)
    else:
        pairs_path = Path(args.pairs)
        log.info("Loading labeled pairs from %s…", pairs_path)
        cv_texts, job_texts, labels = load_labeled_pairs(pairs_path)

    if not cv_texts:
        log.error("No data loaded — aborting")
        return 1

    log.info("Dataset: %d pairs (positive=%d, negative=%d)", len(labels), sum(labels), len(labels) - sum(labels))

    report = train_and_compare(cv_texts, job_texts, labels, out_dir, cv_folds=args.cv_folds)

    print("\n=== Training Report ===")
    for r in report["results"]:
        print(
            f"  {r['model']:<25} acc={r['accuracy']:.4f}  f1={r['f1']:.4f}"
            f"  roc_auc={r['roc_auc']:.4f}  cv_f1={r['cv_f1_mean']:.4f}±{r['cv_f1_std']:.4f}"
        )
    print(f"\nBest: {report['best']['model']} (F1={report['best']['f1']:.4f})")
    print(f"Models saved to: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
