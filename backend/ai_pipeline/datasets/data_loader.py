"""Unified dataset loader for matching training data.

Supports:
  - CSV with columns ``cv_text, job_text, label[, score]``
  - JSONL with the same fields
  - HuggingFace ``datasets.Dataset``

Provides train/val/test splits with stratification and class-rebalancing.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class MatchingRecord:
    cv_text: str
    job_text: str
    label: str = "partial"
    score: float = 0.5
    metadata: Dict = field(default_factory=dict)


class DataLoader:
    """Load and split matching datasets."""

    LABELS = ("incompatible", "partial", "compatible")

    @staticmethod
    def load_csv(path: str | Path) -> List[MatchingRecord]:
        import csv

        records: List[MatchingRecord] = []
        with open(path, "r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                records.append(
                    MatchingRecord(
                        cv_text=row.get("cv_text", "") or row.get("cv", ""),
                        job_text=row.get("job_text", "") or row.get("job", ""),
                        label=row.get("label", "partial"),
                        score=float(row.get("score", 0.5) or 0.5),
                        metadata={
                            k: v
                            for k, v in row.items()
                            if k not in {"cv_text", "cv", "job_text", "job", "label", "score"}
                        },
                    )
                )
        return records

    @staticmethod
    def load_jsonl(path: str | Path) -> List[MatchingRecord]:
        records: List[MatchingRecord] = []
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                records.append(
                    MatchingRecord(
                        cv_text=obj.get("cv_text", ""),
                        job_text=obj.get("job_text", ""),
                        label=obj.get("label", "partial"),
                        score=float(obj.get("score", 0.5)),
                        metadata={k: v for k, v in obj.items() if k not in
                                  {"cv_text", "job_text", "label", "score"}},
                    )
                )
        return records

    @classmethod
    def load(cls, path: str | Path) -> List[MatchingRecord]:
        path = Path(path)
        if path.suffix.lower() == ".csv":
            return cls.load_csv(path)
        if path.suffix.lower() in {".jsonl", ".json"}:
            return cls.load_jsonl(path)
        raise ValueError(f"Unsupported file format: {path.suffix}")

    @staticmethod
    def split(
        records: List[MatchingRecord],
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        stratify: bool = True,
        seed: int = 42,
    ) -> Tuple[List[MatchingRecord], List[MatchingRecord], List[MatchingRecord]]:
        """Return ``(train, val, test)`` with stratification on ``label``."""
        import random as _rd

        rng = _rd.Random(seed)

        if stratify:
            groups: Dict[str, List[MatchingRecord]] = {}
            for r in records:
                groups.setdefault(r.label, []).append(r)
            train, val, test = [], [], []
            for lbl, recs in groups.items():
                rng.shuffle(recs)
                n = len(recs)
                n_tr = int(train_ratio * n)
                n_va = int(val_ratio * n)
                train.extend(recs[:n_tr])
                val.extend(recs[n_tr : n_tr + n_va])
                test.extend(recs[n_tr + n_va :])
            rng.shuffle(train)
            rng.shuffle(val)
            rng.shuffle(test)
            return train, val, test

        records = list(records)
        rng.shuffle(records)
        n = len(records)
        n_tr = int(train_ratio * n)
        n_va = int(val_ratio * n)
        return records[:n_tr], records[n_tr : n_tr + n_va], records[n_tr + n_va :]

    @staticmethod
    def class_distribution(records: List[MatchingRecord]) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for r in records:
            dist[r.label] = dist.get(r.label, 0) + 1
        return dist
