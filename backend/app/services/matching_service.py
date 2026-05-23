"""Matching service: continuous similarity, vector similarity, and deep-learning matcher.

Provides a small, dependency-tolerant wrapper around semantic models and
vector-based fallbacks so the API can offer `mode=semantic|vector|continuous|deep`.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
import joblib

logger = logging.getLogger(__name__)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


class MatchingService:
    """High-level matching utilities.

    Attempts to use `sentence_transformers` when available and falls back to
    TF-IDF vector similarity otherwise.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._embedder = None
        self._faiss_index = None
        self._faiss_files: List[str] = []
        try:
            from sentence_transformers import SentenceTransformer

            self._embedder = SentenceTransformer(model_name)
            logger.info("Loaded SentenceTransformer: %s", model_name)
        except Exception:
            logger.warning("SentenceTransformer unavailable; semantic mode will fall back to TF-IDF.")
            self._embedder = None

    def _load_faiss_store(self, index_dir: str = "models/faiss_index") -> bool:
        """Load a FAISS index built by `backend/scripts/build_bert_faiss.py`."""
        index_path = Path(index_dir) / "faiss.index"
        mapping_path = Path(index_dir) / "mapping.joblib"

        if not index_path.exists() or not mapping_path.exists():
            return False

        try:
            import faiss
        except Exception:
            logger.warning("FAISS unavailable; top-k search disabled")
            return False

        try:
            mapping = joblib.load(mapping_path)
            self._faiss_files = list(mapping.get("files", [])) if isinstance(mapping, dict) else []
            self._faiss_index = faiss.read_index(str(index_path))
            return True
        except Exception as exc:
            logger.warning("Unable to load FAISS store from %s: %s", index_dir, exc)
            self._faiss_index = None
            self._faiss_files = []
            return False

    def embed(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 0))
        if self._embedder is not None:
            return np.asarray(self._embedder.encode(texts, show_progress_bar=False, convert_to_numpy=True))

        # fallback: simple TF-IDF dense vectors via sklearn
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer

            vect = TfidfVectorizer(max_features=4096)
            mat = vect.fit_transform(texts)
            return mat.toarray()
        except Exception:
            return np.zeros((len(texts), 1))

    def vector_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        return _cosine(a, b)

    def semantic_similarity(self, left_text: str, right_text: str) -> float:
        emb = self.embed([left_text, right_text])
        if emb.shape[0] < 2:
            return 0.0
        return float(_cosine(emb[0], emb[1]))

    def continuous_similarity(self, job_text: str, candidate_text: str, window: int = 64) -> Dict[str, Any]:
        """Compute continuous similarity by comparing job embedding with sliding
        window embeddings of the candidate document. Returns summary stats.
        """
        # Split candidate into sentences for robustness
        import re

        sents = [s.strip() for s in re.split(r"(?<=[.!?\n])\s+", candidate_text) if s.strip()]
        if not sents:
            return {"mean": 0.0, "max": 0.0, "top_k": []}

        # Build embeddings in batches
        chunks = []
        for i in range(0, len(sents), window):
            chunks.append(" ".join(sents[i : i + window]))

        emb_job = self.embed([job_text])[0]
        emb_chunks = self.embed(chunks)

        scores = [float(_cosine(emb_job, e)) for e in emb_chunks]
        ranked = sorted(list(enumerate(scores)), key=lambda x: x[1], reverse=True)
        top_k = [(chunks[idx], float(score)) for idx, score in ranked[:3]]

        return {"mean": float(np.mean(scores)), "max": float(np.max(scores)), "top_k": top_k}

    def deep_match_score(self, job_text: str, candidate_text: str) -> float:
        """Alias for semantic_similarity (keeps API naming clear for 'deep' mode)."""
        return self.semantic_similarity(job_text, candidate_text)

    def search_top_k_candidates(self, job_text: str, top_k: int = 5, index_dir: str = "models/faiss_index") -> List[Dict[str, Any]]:
        """Return the top-K candidate files for a job description using FAISS."""
        if not job_text.strip():
            return []

        if self._embedder is None:
            logger.warning("SentenceTransformer unavailable; top-k search not available")
            return []

        if self._faiss_index is None and not self._load_faiss_store(index_dir=index_dir):
            return []

        try:
            import faiss
        except Exception:
            return []

        query_emb = np.asarray(self._embedder.encode([job_text], show_progress_bar=False, convert_to_numpy=True))
        faiss.normalize_L2(query_emb)
        distances, indices = self._faiss_index.search(query_emb, top_k)

        results: List[Dict[str, Any]] = []
        for rank, (idx, score) in enumerate(zip(indices[0], distances[0]), start=1):
            if idx < 0:
                continue
            file_path = self._faiss_files[idx] if idx < len(self._faiss_files) else None
            results.append({
                "rank": rank,
                "index": int(idx),
                "score": float(score),
                "file": file_path,
            })
        return results


__all__ = ["MatchingService"]
