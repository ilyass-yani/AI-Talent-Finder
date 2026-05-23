#!/usr/bin/env python
"""Train a classical ML matching model (LR / RF / XGBoost).

Usage:
    python scripts/train_classical.py \
        --data data/training_pairs.csv \
        --model rf \
        --output models/rf_matching.joblib

Expects a CSV with columns: cv_text, job_text, label (and optionally score).
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from ai_pipeline.datasets.data_loader import DataLoader
from ai_pipeline.feature_engineering.pair_features import PairExample, PairFeatureBuilder
from ai_pipeline.feature_engineering.semantic_features import SemanticFeatureExtractor
from ai_pipeline.models.ml_models import get_model
from ai_pipeline.preprocessing.skill_normalizer import SkillNormalizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


LABEL_TO_BINARY = {"compatible": 1, "partial": 1, "incompatible": 0}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train classical matching model")
    p.add_argument("--data", required=True, help="Path to CSV/JSONL with training pairs")
    p.add_argument("--model", default="rf", choices=["lr", "rf", "xgb"])
    p.add_argument("--output", default="models/classical_matching.joblib")
    p.add_argument("--embedding-model", default="paraphrase-multilingual-MiniLM-L12-v2")
    p.add_argument("--test-size", type=float, default=0.2)
    return p.parse_args()


def main() -> int:
    args = parse_args()

    logger.info("Loading data from %s", args.data)
    records = DataLoader.load(args.data)
    logger.info("Loaded %d records — distribution: %s",
                len(records), DataLoader.class_distribution(records))

    train, val, _ = DataLoader.split(records, train_ratio=1 - args.test_size, val_ratio=args.test_size, stratify=True)
    logger.info("Split: %d train / %d val", len(train), len(val))

    # Build features
    logger.info("Initializing feature extractors…")
    sem = SemanticFeatureExtractor(model_name=args.embedding_model)
    skill_norm = SkillNormalizer()
    builder = PairFeatureBuilder(semantic_extractor=sem, skill_normalizer=skill_norm)

    def to_examples(recs):
        return [
            PairExample(cv_text=r.cv_text, job_text=r.job_text, label=r.label)
            for r in recs
        ]

    logger.info("Building train features (this may take a while)…")
    X_train, y_train_raw, feat_names = builder.build_batch(to_examples(train))
    y_train = np.array([LABEL_TO_BINARY.get(l, 0) for l in y_train_raw])

    logger.info("Building val features…")
    X_val, y_val_raw, _ = builder.build_batch(to_examples(val))
    y_val = np.array([LABEL_TO_BINARY.get(l, 0) for l in y_val_raw])

    logger.info("Training %s model on %d features…", args.model, X_train.shape[1])
    model = get_model(args.model, feature_names=feat_names)
    model.fit(X_train, y_train)

    logger.info("Evaluating on held-out set…")
    metrics = model.evaluate(X_val, y_val)
    logger.info("Metrics: %s", metrics.to_dict())

    output = Path(args.output)
    model.save(output)
    logger.info("Saved model → %s", output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
