#!/usr/bin/env python3
"""Build TF-IDF + SVD features from extracted JSONL."""
import argparse
import json
from pathlib import Path

from app.features.tfidf_features import build_tfidf_corpus, reduce_dimensionality, save_artifacts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="extracted jsonl path")
    parser.add_argument("--out", required=True, help="output dir for artifacts")
    parser.add_argument("--svd-dim", type=int, default=128)
    args = parser.parse_args()

    p = Path(args.input)
    if not p.exists():
        raise SystemExit("Input not found")

    rows = [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
    texts = [r.get('structured', {}).get('profile_summary') or r.get('structured', {}).get('raw_text') or r.get('raw_text') or '' for r in rows]
    # fallback to raw_text when structured summary missing
    texts = [t if t else '' for t in texts]

    vect, X = build_tfidf_corpus(texts)
    svd, Xr = reduce_dimensionality(X, n_components=args.svd_dim)
    save_artifacts(args.out, vect, svd, Xr)
    print(f"Saved TF-IDF + SVD artifacts to {args.out}")


if __name__ == '__main__':
    main()
