#!/usr/bin/env python3
"""Build BERT embeddings and FAISS index from extracted JSONL.

Usage:
  PYTHONPATH=backend python backend/scripts/build_bert_faiss.py --input data/extracted_full.jsonl --out models/faiss_index --model sentence-transformers/all-MiniLM-L6-v2 --batch 16
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

import numpy as np
import joblib

try:
    from app.services.cv_extractor import CVExtractionService
except Exception:
    CVExtractionService = None

# Try to import sentence-transformers, fallback to transformers
HAS_ST = True
try:
    from sentence_transformers import SentenceTransformer
except Exception:
    HAS_ST = False

# Try FAISS
HAS_FAISS = True
try:
    import faiss
except Exception:
    HAS_FAISS = False

from sklearn.neighbors import NearestNeighbors


def read_texts(jsonl_path: Path, limit: int = 0) -> List[dict]:
    items = []
    with jsonl_path.open("r", encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if limit and i >= limit:
                break
            try:
                rec = json.loads(line)
                items.append(rec)
            except Exception:
                continue
    return items


def extract_raw_texts(items: List[dict]):
    texts = []
    files = []
    service = CVExtractionService() if CVExtractionService is not None else None
    for rec in items:
        f = rec.get("file")
        raw = rec.get("raw_text")
        if raw:
            texts.append(raw)
            files.append(f)
            continue
        if not f:
            texts.append("")
            files.append("")
            continue
        p = Path(f)
        try:
            if p.suffix.lower() == ".txt":
                texts.append(p.read_text(encoding="utf-8", errors="ignore"))
                files.append(f)
            else:
                if service is not None:
                    res = service.extract_from_pdf(str(p))
                    texts.append(res.raw_text or "")
                    files.append(f)
                else:
                    texts.append("")
                    files.append(f)
        except Exception:
            texts.append("")
            files.append(f)
    return texts, files


def make_embeddings(texts: List[str], model_name: str, batch_size: int = 16):
    if HAS_ST:
        model = SentenceTransformer(model_name)
        embs = model.encode(texts, batch_size=batch_size, show_progress_bar=True, convert_to_numpy=True)
        return embs
    else:
        # Fallback: use HuggingFace transformers with mean pooling
        try:
            from transformers import AutoTokenizer, AutoModel
            import torch
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModel.from_pretrained(model_name)
            model.eval()
            embs = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                enc = tokenizer(batch, padding=True, truncation=True, return_tensors='pt')
                with torch.no_grad():
                    out = model(**enc)
                # mean pooling
                last = out.last_hidden_state
                mask = enc['attention_mask'].unsqueeze(-1)
                summed = (last * mask).sum(1)
                counts = mask.sum(1)
                emb = (summed / counts).cpu().numpy()
                embs.append(emb)
            return np.vstack(embs)
        except Exception as exc:
            raise RuntimeError("No sentence-transformers or transformers available: " + str(exc))


def build_faiss(embs: np.ndarray, out_dir: Path, use_faiss: bool = True):
    out_dir.mkdir(parents=True, exist_ok=True)
    emb_path = out_dir / 'embeddings.npy'
    np.save(str(emb_path), embs)

    if use_faiss and HAS_FAISS:
        d = embs.shape[1]
        index = faiss.IndexFlatIP(d)
        # normalize for cosine similarity
        faiss.normalize_L2(embs)
        index.add(embs)
        faiss.write_index(index, str(out_dir / 'faiss.index'))
        print(f"Saved FAISS index to {out_dir / 'faiss.index'}")
        return {'type': 'faiss', 'index_path': str(out_dir / 'faiss.index'), 'embeddings': str(emb_path)}
    else:
        nbrs = NearestNeighbors(n_neighbors=10, metric='cosine')
        nbrs.fit(embs)
        joblib.dump(nbrs, out_dir / 'nn_model.joblib')
        print(f"Saved sklearn NearestNeighbors fallback to {out_dir / 'nn_model.joblib'}")
        return {'type': 'sklearn', 'model_path': str(out_dir / 'nn_model.joblib'), 'embeddings': str(emb_path)}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='extracted JSONL')
    parser.add_argument('--out', required=True, help='output directory for index')
    parser.add_argument('--model', default='sentence-transformers/all-MiniLM-L6-v2')
    parser.add_argument('--batch', type=int, default=16)
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args(argv)

    jsonl = Path(args.input)
    out_dir = Path(args.out)

    items = read_texts(jsonl, limit=args.limit)
    texts, files = extract_raw_texts(items)
    print(f"Computing embeddings for {len(texts)} texts (model={args.model})")
    embs = make_embeddings(texts, args.model, batch_size=args.batch)
    meta = build_faiss(embs, out_dir, use_faiss=True)
    mapping = {'files': files, 'meta': meta}
    joblib.dump(mapping, out_dir / 'mapping.joblib')
    print(f"Saved mapping to {out_dir / 'mapping.joblib'}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
