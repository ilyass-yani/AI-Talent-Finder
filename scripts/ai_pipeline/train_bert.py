#!/usr/bin/env python
"""Fine-tune BERT (CamemBERT by default) on matching pairs.

Usage:
    python scripts/train_bert.py --data data/training_pairs.csv \
        --output models/bert_matching --epochs 3
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from ai_pipeline.datasets.data_loader import DataLoader
from ai_pipeline.models.bert_finetuner import BertFineTuneConfig, BertMatchingFineTuner

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fine-tune BERT for matching")
    p.add_argument("--data", required=True)
    p.add_argument("--model", default="camembert-base")
    p.add_argument("--output", default="models/bert_matching")
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--lr", type=float, default=2e-5)
    p.add_argument("--max-length", type=int, default=384)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    records = DataLoader.load(args.data)
    logger.info("Loaded %d records", len(records))

    train, val, _ = DataLoader.split(records, train_ratio=0.85, val_ratio=0.15, stratify=True)

    train_examples = [
        {"cv_text": r.cv_text, "job_text": r.job_text, "label": r.label} for r in train
    ]
    val_examples = [
        {"cv_text": r.cv_text, "job_text": r.job_text, "label": r.label} for r in val
    ]

    config = BertFineTuneConfig(
        model_name=args.model,
        output_dir=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        max_length=args.max_length,
    )
    tuner = BertMatchingFineTuner(config=config)
    metrics = tuner.train(train_examples, val_examples)
    logger.info("Final metrics: %s", metrics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
