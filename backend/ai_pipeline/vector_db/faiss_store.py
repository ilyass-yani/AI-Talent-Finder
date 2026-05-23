"""FAISS-backed vector store for candidate/job embedding retrieval.

Stores embeddings + lightweight metadata in-memory and persists them
to disk.  Supports cosine similarity via inner product on L2-normalized
vectors, which is the standard pattern for sentence-transformers.
"""
from __future__ import annotations

import json
import logging
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FAISSSearchResult:
    id: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class FAISSVectorStore:
    """Cosine-similarity FAISS index with id/metadata management."""

    def __init__(self, embedding_dim: int, normalize: bool = True) -> None:
        self.embedding_dim = embedding_dim
        self.normalize = normalize
        self._index = None
        self._ids: List[str] = []
        self._metadata: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def _ensure_index(self) -> None:
        if self._index is None:
            import faiss  # type: ignore

            self._index = faiss.IndexFlatIP(self.embedding_dim)

    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        if not self.normalize:
            return vectors.astype("float32")
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (vectors / norms).astype("float32")

    # ------------------------------------------------------------------ #
    # CRUD
    # ------------------------------------------------------------------ #
    def add(
        self,
        ids: List[str],
        embeddings: np.ndarray,
        metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        if len(ids) != embeddings.shape[0]:
            raise ValueError("ids and embeddings must have the same length.")
        self._ensure_index()
        vecs = self._normalize(np.asarray(embeddings))
        self._index.add(vecs)
        self._ids.extend(ids)
        if metadata is not None:
            for id_, meta in zip(ids, metadata):
                self._metadata[id_] = meta

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
    ) -> List[FAISSSearchResult]:
        if self._index is None or self._index.ntotal == 0:
            return []
        q = self._normalize(np.asarray(query_embedding).reshape(1, -1))
        scores, idx = self._index.search(q, min(top_k, self._index.ntotal))
        out: List[FAISSSearchResult] = []
        for score, i in zip(scores[0], idx[0]):
            if i < 0:
                continue
            id_ = self._ids[i]
            out.append(
                FAISSSearchResult(
                    id=id_,
                    score=float(score),
                    metadata=self._metadata.get(id_, {}),
                )
            )
        return out

    def __len__(self) -> int:
        return self._index.ntotal if self._index is not None else 0

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #
    def save(self, path: str | Path) -> None:
        import faiss  # type: ignore

        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        if self._index is not None:
            faiss.write_index(self._index, str(path / "index.faiss"))
        (path / "ids.json").write_text(json.dumps(self._ids))
        with open(path / "metadata.pkl", "wb") as fh:
            pickle.dump(self._metadata, fh)
        (path / "config.json").write_text(
            json.dumps({"embedding_dim": self.embedding_dim, "normalize": self.normalize})
        )

    @classmethod
    def load(cls, path: str | Path) -> "FAISSVectorStore":
        import faiss  # type: ignore

        path = Path(path)
        cfg = json.loads((path / "config.json").read_text())
        store = cls(embedding_dim=cfg["embedding_dim"], normalize=cfg["normalize"])
        idx_path = path / "index.faiss"
        if idx_path.exists():
            store._index = faiss.read_index(str(idx_path))
        store._ids = json.loads((path / "ids.json").read_text())
        with open(path / "metadata.pkl", "rb") as fh:
            store._metadata = pickle.load(fh)
        return store
