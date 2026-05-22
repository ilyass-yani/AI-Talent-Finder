"""Optional FAISS helper: builds/loads a vector index using sentence-transformers.

This helper is optional — FAISS must be installed separately (`faiss-cpu` or `faiss-gpu`).
"""
from typing import List, Tuple, Optional
import os
import numpy as np
import logging

logger = logging.getLogger(__name__)


class FaissIndex:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._index = None
        self._embedder = None

        try:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(model_name)
        except Exception:
            logger.warning("SentenceTransformer unavailable for FAISS embeddings")
            self._embedder = None

    def build_index(self, texts: List[str]):
        try:
            import faiss
        except Exception:
            raise RuntimeError("faiss is not installed")

        if self._embedder is None:
            raise RuntimeError("embedder not available")

        emb = np.asarray(self._embedder.encode(texts, convert_to_numpy=True))
        dim = emb.shape[1]
        index = faiss.IndexFlatIP(dim)
        faiss.normalize_L2(emb)
        index.add(emb)
        self._index = index
        return index

    def search(self, query: str, top_k: int = 5) -> List[Tuple[int, float]]:
        if self._index is None:
            return []
        if self._embedder is None:
            return []
        q_emb = np.asarray(self._embedder.encode([query], convert_to_numpy=True))
        import faiss
        faiss.normalize_L2(q_emb)
        D, I = self._index.search(q_emb, top_k)
        return [(int(i), float(d)) for i, d in zip(I[0], D[0])]

    def save(self, path: str, texts: Optional[List[str]] = None):
        """Persist the FAISS index and optional texts/metadata to `path`.

        Creates `path.index` (faiss index) and `path.meta.npz` (texts + embeddings).
        """
        try:
            import faiss
        except Exception:
            raise RuntimeError("faiss is not installed")

        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        if self._index is None:
            raise RuntimeError("Index is empty")

        faiss.write_index(self._index, f"{path}.index")
        if texts and self._embedder is not None:
            emb = np.asarray(self._embedder.encode(texts, convert_to_numpy=True))
            np.savez_compressed(f"{path}.meta.npz", texts=np.array(texts, dtype=object), emb=emb)

    def load(self, path: str):
        """Load an index previously saved with `save(path, texts=...)`."""
        try:
            import faiss
        except Exception:
            raise RuntimeError("faiss is not installed")

        idx_path = f"{path}.index"
        meta_path = f"{path}.meta.npz"
        if not os.path.exists(idx_path):
            raise FileNotFoundError(idx_path)

        self._index = faiss.read_index(idx_path)
        if os.path.exists(meta_path) and self._embedder is not None:
            meta = np.load(meta_path, allow_pickle=True)
            texts = meta.get("texts")
            emb = meta.get("emb")
            return list(texts), emb
        return None
