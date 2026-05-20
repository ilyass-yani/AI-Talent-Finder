#!/usr/bin/env python3
"""Quick TF-IDF -> XGBoost training script for small validation runs.

Reads a JSONL of extraction records written by `run_extraction.py` (field `file`).
Builds synthetic positive/negative pairs and trains a lightweight classifier.

Usage:
  PYTHONPATH=backend python backend/scripts/quick_train_tfidf_xgb.py --input data/extracted_test.jsonl --out models/test_match_model.joblib --limit 20
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
import time

import joblib
import numpy as np

try:
    from app.services.cv_extractor import CVExtractionService
except Exception:
    CVExtractionService = None

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.model_selection import train_test_split
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.ensemble import GradientBoostingClassifier

try:
    from xgboost import XGBClassifier
    XGB_AVAILABLE = True
except Exception:
    XGB_AVAILABLE = False


def read_files_from_extracted(jsonl_path: Path, limit: int | None = None) -> list[Path]:
    files: list[Path] = []
    with jsonl_path.open("r", encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if limit and i >= limit:
                break
            try:
                rec = json.loads(line)
                files.append(Path(rec.get("file")))
            except Exception:
                continue
    return files


def extract_texts(file_paths: list[Path]) -> list[str]:
    texts: list[str] = []
    service = None
    if CVExtractionService is not None:
        service = CVExtractionService()
    for p in file_paths:
        try:
            if p.suffix.lower() == ".txt":
                texts.append(p.read_text(encoding="utf-8", errors="ignore"))
            else:
                if service is not None:
                    res = service.extract_from_pdf(str(p))
                    texts.append(res.raw_text or "")
                else:
                    # fallback: try reading as text
                    texts.append(p.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            texts.append("")
    return texts


def build_pairs(texts: list[str], negative_ratio: float = 1.0):
    pairs = []
    labels = []
    n = len(texts)
    for i in range(n):
        pairs.append((texts[i], texts[i]))
        labels.append(1)
    # negatives: random pairings
    negatives = int(n * negative_ratio)
    for _ in range(negatives):
        a, b = random.sample(range(n), 2)
        pairs.append((texts[a], texts[b]))
        labels.append(0)
    return pairs, labels


def pair_features(pairs, vectorizer, svd=None):
    # Flatten texts to fit vectorizer
    flat = [t for pair in pairs for t in pair]
    X_flat = vectorizer.transform(flat)
    if svd is not None:
        X_flat = svd.transform(X_flat)
    # reconstruct pairs
    Xp = []
    for i in range(0, len(flat), 2):
        v1 = X_flat[i]
        v2 = X_flat[i + 1]
        diff = np.abs(v1 - v2)
        cos = cosine_similarity(v1.reshape(1, -1), v2.reshape(1, -1))[0][0]
        feat = np.hstack([diff, [cos]])
        Xp.append(feat)
    return np.vstack(Xp)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="JSONL produced by run_extraction.py")
    parser.add_argument("--out", required=True, help="Output joblib model path")
    parser.add_argument("--limit", type=int, default=50, help="Max files to read")
    args = parser.parse_args(argv)

    jsonl = Path(args.input)
    files = read_files_from_extracted(jsonl, limit=args.limit)
    if not files:
        print("No files found in extracted JSONL")
        return 2
    print(f"Found {len(files)} files, extracting texts...")
    texts = extract_texts(files)
    # minimal preprocessing: filter empty
    texts = [t if t else "" for t in texts]

    pairs, labels = build_pairs(texts, negative_ratio=1.0)
    # Fit vectorizer on single texts
    corpus = texts
    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1,2))
    vectorizer.fit(corpus)
    # Transform full corpus for SVD fit
    X_corpus = vectorizer.transform(corpus)
    svd = TruncatedSVD(n_components=min(50, X_corpus.shape[1]-1)) if X_corpus.shape[1] > 2 else None
    if svd is not None:
        svd.fit(X_corpus)

    print("Building pair features...")
    X = pair_features(pairs, vectorizer, svd)
    y = np.array(labels)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    if XGB_AVAILABLE:
        model = XGBClassifier(use_label_encoder=False, eval_metric="logloss", n_estimators=50, verbosity=0)
    else:
        model = GradientBoostingClassifier(n_estimators=50)

    print("Training model...")
    model.fit(X_train, y_train)
    score = model.score(X_test, y_test)
    print(f"Validation accuracy: {score:.3f}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "vectorizer": vectorizer, "svd": svd}, out_path)
    print(f"Saved model to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
