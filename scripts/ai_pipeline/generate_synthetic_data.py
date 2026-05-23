#!/usr/bin/env python
"""Generate a synthetic CV ↔ Job matching dataset.

Usage:
    python scripts/generate_synthetic_data.py \
        --n 5000 \
        --output data/synthetic_pairs.jsonl
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from ai_pipeline.datasets.synthetic_generator import SyntheticGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Synthetic data generation")
    p.add_argument("--n", type=int, default=5000)
    p.add_argument("--output", default="data/synthetic_pairs.jsonl")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--format", default="jsonl", choices=["jsonl", "csv"])
    return p.parse_args()


def main() -> int:
    args = parse_args()
    gen = SyntheticGenerator(seed=args.seed)

    logger.info("Generating %d synthetic examples…", args.n)
    examples = gen.generate(n=args.n)

    dist = {}
    for ex in examples:
        dist[ex.label] = dist.get(ex.label, 0) + 1
    logger.info("Class distribution: %s", dist)

    out = Path(args.output)
    if args.format == "csv":
        gen.save_csv(examples, out)
    else:
        gen.save_jsonl(examples, out)
    logger.info("Saved → %s (%d examples)", out, len(examples))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
