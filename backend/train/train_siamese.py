"""Fine-tune a sentence-transformers Siamese model on CV/job pairs.

Input CSV format:
    cv_text,job_text,label

Typical usage:
    /Users/elhadjibassirousy/Desktop/AI-Talent-Finder/.venv/bin/python train/train_siamese.py \
        --data ../data/training_pairs.csv \
        --output-dir ../models/siamese_model

If sentence-transformers / torch are not installed, the script exits with a
clear message and a suggested install command.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

script_dir = Path(__file__).resolve().parent
repo_root = script_dir.parent.parent
if str(repo_root / "backend") not in sys.path:
    sys.path.insert(0, str(repo_root / "backend"))

from app.services.normalization import normalize_text


DEFAULT_BASE_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@dataclass
class Metrics:
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float | None


def _require_sentence_transformers():
    try:
        from sentence_transformers import InputExample, SentenceTransformer, losses
        from torch.utils.data import DataLoader
        return InputExample, SentenceTransformer, losses, DataLoader
    except Exception as exc:
        raise RuntimeError(
            "Missing dependencies for Siamese fine-tuning. Install with: "
            "pip install torch sentence-transformers transformers datasets"
        ) from exc


def _normalize_label(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    try:
        return int(value)
    except Exception:
        text = str(value).strip().lower()
        return 1 if text in {"1", "true", "yes", "compatible", "match"} else 0


def _load_pairs(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"cv_text", "job_text", "label"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df = df.copy()
    df["cv_text"] = df["cv_text"].fillna("").astype(str).map(normalize_text)
    df["job_text"] = df["job_text"].fillna("").astype(str).map(normalize_text)
    df["label"] = df["label"].apply(_normalize_label).astype(int)
    df = df.dropna(subset=["cv_text", "job_text"])
    df = df[(df["cv_text"].str.len() > 0) & (df["job_text"].str.len() > 0)]
    return df.reset_index(drop=True)


def _build_examples(InputExample, df: pd.DataFrame):
    examples = []
    for _, row in df.iterrows():
        label = float(row["label"])
        examples.append(InputExample(texts=[row["cv_text"], row["job_text"]], label=label))
    return examples


def _evaluate_classifier(model, pairs: pd.DataFrame) -> tuple[Metrics, list[float]]:
    scores = []
    labels = pairs["label"].tolist()
    for _, row in pairs.iterrows():
        embeddings = model.encode(
            [row["cv_text"], row["job_text"]],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        score = float(np.dot(embeddings[0], embeddings[1]))
        scores.append(score)

    preds = [1 if score >= 0.5 else 0 for score in scores]

    try:
        roc_auc = roc_auc_score(labels, scores)
    except Exception:
        roc_auc = None

    return Metrics(
        accuracy=accuracy_score(labels, preds),
        precision=precision_score(labels, preds, zero_division=0),
        recall=recall_score(labels, preds, zero_division=0),
        f1=f1_score(labels, preds, zero_division=0),
        roc_auc=roc_auc,
    ), scores


def train(args: argparse.Namespace) -> None:
    InputExample, SentenceTransformer, losses, DataLoader = _require_sentence_transformers()

    df = _load_pairs(args.data)
    if len(df) < 100:
        raise ValueError("Not enough rows to fine-tune a Siamese model. Need at least ~100 rows.")

    train_df, test_df = train_test_split(
        df,
        test_size=args.test_size,
        random_state=args.seed,
        stratify=df["label"],
    )

    model = SentenceTransformer(args.base_model)
    train_examples = _build_examples(InputExample, train_df)
    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=args.batch_size)
    train_loss = losses.CosineSimilarityLoss(model)

    warmup_steps = max(1, int(len(train_dataloader) * args.epochs * 0.1))
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=args.epochs,
        warmup_steps=warmup_steps,
        output_path=args.output_dir,
        show_progress_bar=True,
        optimizer_params={"lr": args.learning_rate},
    )

    metrics, scores = _evaluate_classifier(model, test_df)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "base_model": args.base_model,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "test_size": args.test_size,
        "seed": args.seed,
        "metrics": asdict(metrics),
        "rows_train": int(len(train_df)),
        "rows_test": int(len(test_df)),
    }
    (output_dir / "training_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=== Siamese fine-tuning complete ===")
    print(json.dumps(metadata, indent=2, ensure_ascii=False))
    print("Sample scores:", scores[:10])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="CSV with columns cv_text,job_text,label")
    parser.add_argument("--output-dir", required=True, help="Directory where the fine-tuned model will be saved")
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--test-size", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    train(args)


if __name__ == "__main__":
    main()