#!/usr/bin/env python
"""Build a FAISS vector index from a job corpus.

Usage:
    python scripts/build_vector_index.py \
        --input data/jobs.jsonl \
        --output indexes/jobs_faiss \
        --text-field description \
        --id-field external_id
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from ai_pipeline.feature_engineering.semantic_features import SemanticFeatureExtractor
from ai_pipeline.vector_db.faiss_store import FAISSVectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build FAISS index")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--text-field", default="description")
    p.add_argument("--id-field", default="external_id")
    p.add_argument("--embedding-model", default="paraphrase-multilingual-MiniLM-L12-v2")
    p.add_argument("--batch-size", type=int, default=64)
    return p.parse_args()


def main() -> int:
    args = parse_args()

    logger.info("Reading %s …", args.input)
    records = []
    with open(args.input, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    logger.info("Loaded %d records", len(records))

    sem = SemanticFeatureExtractor(model_name=args.embedding_model)
    texts = [str(r.get(args.text_field, "")) for r in records]
    ids = [str(r.get(args.id_field, i)) for i, r in enumerate(records)]

    logger.info("Encoding %d documents…", len(texts))
    embeddings = sem.encode(texts, batch_size=args.batch_size)
    if isinstance(embeddings, list):
        embeddings = np.asarray(embeddings)

    store = FAISSVectorStore(embedding_dim=embeddings.shape[1], normalize=True)
    store.add(ids=ids, embeddings=embeddings, metadata=records)

    logger.info("Saving FAISS index to %s …", args.output)
    store.save(args.output)
    logger.info("Done — indexed %d items.", len(store))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
