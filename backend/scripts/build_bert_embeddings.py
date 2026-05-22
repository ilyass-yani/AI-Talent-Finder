#!/usr/bin/env python3
"""Build BERT embeddings from extracted JSONL using sentence-transformers."""
import argparse
import json
from pathlib import Path

from app.features.bert_features import compute_sentence_embeddings, save_embeddings, SBT_AVAILABLE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--model", default=None)
    args = parser.parse_args()

    if not SBT_AVAILABLE:
        raise SystemExit("sentence-transformers not installed in this environment")

    p = Path(args.input)
    if not p.exists():
        raise SystemExit("Input not found")

    rows = [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
    texts = [r.get('raw_text') or r.get('structured', {}).get('profile_summary') or '' for r in rows]
    embs = compute_sentence_embeddings(texts, model_name=args.model)
    save_embeddings(args.out, embs)
    print(f"Saved embeddings to {args.out}")


if __name__ == '__main__':
    main()
