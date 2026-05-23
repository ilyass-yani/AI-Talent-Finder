"""Embeddings sémantiques via Sentence-Transformers.

Modèles supportés (selon ressources) :
    - BAAI/bge-small-en-v1.5            (384d, rapide, EN, top quality)
    - sentence-transformers/all-MiniLM-L6-v2  (384d, classique)
    - sentence-transformers/all-mpnet-base-v2 (768d, qualité+, plus lent)
    - paraphrase-multilingual-MiniLM-L12-v2   (384d, FR/EN/AR/ES, ...)
    - intfloat/multilingual-e5-large    (1024d, top multilingue)

Avec cache mémoire + cache disque pour éviter de re-encoder les mêmes textes.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    SBERT_AVAILABLE = True
except ImportError:
    SBERT_AVAILABLE = False

from ai_pipeline.config import get_config


class SemanticFeatureExtractor:
    """Encodeur Sentence-Transformers avec cache mémoire + disque."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        cache_dir: Optional[str] = None,
        batch_size: int = 32,
        normalize: bool = True,
        device: Optional[str] = None,
    ) -> None:
        cfg = get_config().embedding
        self.model_name = model_name or cfg.model_name
        self.batch_size = batch_size or cfg.batch_size
        self.normalize = normalize and cfg.normalize_embeddings
        self.device = device

        self._model = None
        self._mem_cache: Dict[str, np.ndarray] = {}
        self._cache_dir = Path(cache_dir) if cache_dir else None
        if self._cache_dir:
            self._cache_dir.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------------------------------- #
    # Chargement du modèle (paresseux)
    # ----------------------------------------------------------------- #

    @property
    def model(self) -> "SentenceTransformer":
        if self._model is None:
            if not SBERT_AVAILABLE:
                raise RuntimeError(
                    "sentence-transformers not installed. "
                    "Run: pip install sentence-transformers"
                )
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    @property
    def dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()

    # ----------------------------------------------------------------- #
    # Encodage avec cache
    # ----------------------------------------------------------------- #

    def encode(self, texts: Sequence[str], show_progress: bool = False) -> np.ndarray:
        """Encode une liste de textes en gérant les caches."""
        if not texts:
            return np.array([])

        # Préparer la liste avec marqueurs pour les hits cache
        results: List[Optional[np.ndarray]] = [None] * len(texts)
        to_encode: List[str] = []
        to_encode_idx: List[int] = []

        for i, text in enumerate(texts):
            key = self._cache_key(text)
            if key in self._mem_cache:
                results[i] = self._mem_cache[key]
            elif self._cache_dir:
                cached = self._load_from_disk(key)
                if cached is not None:
                    results[i] = cached
                    self._mem_cache[key] = cached
                else:
                    to_encode.append(text)
                    to_encode_idx.append(i)
            else:
                to_encode.append(text)
                to_encode_idx.append(i)

        # Batch encode tout ce qui n'est pas en cache
        if to_encode:
            embeddings = self.model.encode(
                to_encode,
                batch_size=self.batch_size,
                show_progress_bar=show_progress,
                normalize_embeddings=self.normalize,
                convert_to_numpy=True,
            )
            for idx, emb in zip(to_encode_idx, embeddings):
                results[idx] = emb
                key = self._cache_key(texts[idx])
                self._mem_cache[key] = emb
                if self._cache_dir:
                    self._save_to_disk(key, emb)

        return np.stack(results)

    def encode_single(self, text: str) -> np.ndarray:
        return self.encode([text])[0]

    # ----------------------------------------------------------------- #
    # Similarité
    # ----------------------------------------------------------------- #

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    def pair_similarity(self, text_a: str, text_b: str) -> float:
        emb = self.encode([text_a, text_b])
        return self.cosine_similarity(emb[0], emb[1])

    def batch_similarity(
        self,
        queries: Sequence[str],
        corpus: Sequence[str],
    ) -> np.ndarray:
        """Retourne une matrice (n_queries, n_corpus) de similarités."""
        q_emb = self.encode(queries)
        c_emb = self.encode(corpus)
        if self.normalize:
            # Si normalisé, dot product = cosine
            return q_emb @ c_emb.T
        # Sinon calcul cosine manuel
        q_norm = q_emb / np.clip(np.linalg.norm(q_emb, axis=1, keepdims=True), 1e-8, None)
        c_norm = c_emb / np.clip(np.linalg.norm(c_emb, axis=1, keepdims=True), 1e-8, None)
        return q_norm @ c_norm.T

    def most_similar(
        self,
        query: str,
        candidates: Sequence[str],
        top_k: int = 5,
    ) -> List[tuple]:
        """Renvoie [(index, candidate, score), ...] triés par score décroissant."""
        sims = self.batch_similarity([query], candidates)[0]
        top_indices = np.argsort(sims)[::-1][:top_k]
        return [(int(i), candidates[int(i)], float(sims[int(i)])) for i in top_indices]

    # ----------------------------------------------------------------- #
    # Gestion du cache disque
    # ----------------------------------------------------------------- #

    def _cache_key(self, text: str) -> str:
        clean = text.strip().lower()
        h = hashlib.md5((self.model_name + "::" + clean).encode("utf-8")).hexdigest()
        return h

    def _cache_path(self, key: str) -> Path:
        return self._cache_dir / f"{key}.npy"

    def _load_from_disk(self, key: str) -> Optional[np.ndarray]:
        path = self._cache_path(key)
        if path.exists():
            try:
                return np.load(path)
            except Exception:
                return None
        return None

    def _save_to_disk(self, key: str, emb: np.ndarray) -> None:
        try:
            np.save(self._cache_path(key), emb)
        except Exception:
            pass

    def clear_cache(self) -> None:
        self._mem_cache.clear()


if __name__ == "__main__":
    # Petit test (nécessite sentence-transformers installé)
    if not SBERT_AVAILABLE:
        print("Install sentence-transformers to test.")
    else:
        extractor = SemanticFeatureExtractor(model_name="sentence-transformers/all-MiniLM-L6-v2")
        cv = "Senior Python developer, FastAPI, Machine Learning, PyTorch."
        job = "Looking for an ML engineer with FastAPI and Python expertise."
        unrelated = "Marketing manager with 10 years of B2B experience."

        print(f"Dim: {extractor.dimension}")
        print(f"sim(CV, job)       = {extractor.pair_similarity(cv, job):.4f}")
        print(f"sim(CV, unrelated) = {extractor.pair_similarity(cv, unrelated):.4f}")
