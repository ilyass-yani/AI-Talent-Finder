#!/usr/bin/env python3
"""Build feature store: BOW / TF-IDF + optional SVD from extracted JSONL.

Usage:
  PYTHONPATH=backend python backend/scripts/build_feature_store.py --input data/extracted_full.jsonl --out models/feature_meta_tfidf.joblib --method tfidf --max-features 10000 --svd-components 100
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

import joblib

try:
    from app.services.cv_extractor import CVExtractionService
except Exception:
    CVExtractionService = None

from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import TruncatedSVD


def read_file_paths(jsonl_path: Path) -> List[Path]:
    files = []
    with jsonl_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
                f = rec.get("file")
                if f:
                    files.append(Path(f))
            except Exception:
                continue
    return files


def extract_texts(file_paths: List[Path]):
    texts = []
    service = CVExtractionService() if CVExtractionService is not None else None
    for p in file_paths:
        try:
            if p.suffix.lower() == ".txt":
                texts.append(p.read_text(encoding="utf-8", errors="ignore"))
            else:
                if service is not None:
                    res = service.extract_from_pdf(str(p))
                    texts.append(res.raw_text or "")
                else:
                    texts.append(p.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            texts.append("")
    return texts


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="extracted JSONL with file paths")
    parser.add_argument("--out", required=True, help="output joblib path for feature_meta")
    parser.add_argument("--method", choices=["tfidf", "bow", "both"], default="tfidf")
    parser.add_argument("--max-features", type=int, default=10000)
    parser.add_argument("--svd-components", type=int, default=100)
    parser.add_argument("--limit", type=int, default=0, help="limit number of files (0 = all)")
    args = parser.parse_args(argv)

    jsonl = Path(args.input)
    files = read_file_paths(jsonl)
    if args.limit and args.limit > 0:
        files = files[: args.limit]
    if not files:
        print("No files found to build feature store")
        return 2

    print(f"Found {len(files)} files, extracting texts...")
    texts = extract_texts(files)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    meta = {"method": args.method, "n_files": len(files)}

    if args.method in ("tfidf", "both"):
        print("Fitting TfidfVectorizer...")
        tfidf = TfidfVectorizer(max_features=args.max_features, ngram_range=(1,2))
        tfidf.fit(texts)
        meta["tfidf"] = tfidf
        # Fit SVD on TF-IDF matrix
        try:
            X = tfidf.transform(texts)
            n_comp = min(args.svd_components, max(2, X.shape[1] - 1))
            if n_comp > 0:
                print(f"Fitting TruncatedSVD with n_components={n_comp}...")
                svd = TruncatedSVD(n_components=n_comp)
                svd.fit(X)
                meta["svd"] = svd
            else:
                meta["svd"] = None
        except Exception as exc:
            print(f"SVD fit failed: {exc}")
            meta["svd"] = None

    if args.method in ("bow", "both"):
        print("Fitting CountVectorizer (BOW)...")
        bow = CountVectorizer(max_features=args.max_features)
        bow.fit(texts)
        meta["bow"] = bow

    joblib.dump(meta, out_path)
    print(f"Saved feature meta to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
