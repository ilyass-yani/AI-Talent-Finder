"""ChromaDB vector store — persistent alternative to FAISS.

ChromaDB ships with native metadata filtering and persistent storage,
making it well-suited for production deployments where the candidate
pool grows incrementally over time.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ChromaSearchResult:
    id: str
    score: float
    document: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class ChromaVectorStore:
    """Persistent vector store using ChromaDB."""

    def __init__(
        self,
        collection_name: str,
        persist_dir: Optional[str] = None,
        distance: str = "cosine",
    ) -> None:
        self.collection_name = collection_name
        self.persist_dir = persist_dir
        self.distance = distance
        self._client = None
        self._collection = None

    def _connect(self) -> None:
        if self._collection is not None:
            return
        import chromadb  # type: ignore
        from chromadb.config import Settings  # type: ignore

        if self.persist_dir:
            Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=self.persist_dir, settings=Settings(anonymized_telemetry=False)
            )
        else:
            self._client = chromadb.Client(Settings(anonymized_telemetry=False))

        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": self.distance},
        )

    def add(
        self,
        ids: List[str],
        embeddings: np.ndarray,
        documents: Optional[List[str]] = None,
        metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self._connect()
        self._collection.add(
            ids=ids,
            embeddings=np.asarray(embeddings).tolist(),
            documents=documents or [""] * len(ids),
            metadatas=metadata or [{}] * len(ids),
        )

    def upsert(
        self,
        ids: List[str],
        embeddings: np.ndarray,
        documents: Optional[List[str]] = None,
        metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self._connect()
        self._collection.upsert(
            ids=ids,
            embeddings=np.asarray(embeddings).tolist(),
            documents=documents or [""] * len(ids),
            metadatas=metadata or [{}] * len(ids),
        )

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[ChromaSearchResult]:
        self._connect()
        res = self._collection.query(
            query_embeddings=[np.asarray(query_embedding).tolist()],
            n_results=top_k,
            where=where,
        )
        out: List[ChromaSearchResult] = []
        ids = res.get("ids", [[]])[0]
        distances = res.get("distances", [[]])[0]
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        for i, id_ in enumerate(ids):
            # ChromaDB returns distance; convert cosine distance → similarity
            score = 1.0 - float(distances[i]) if self.distance == "cosine" else float(distances[i])
            out.append(
                ChromaSearchResult(
                    id=id_,
                    score=score,
                    document=docs[i] if docs else "",
                    metadata=metas[i] if metas else {},
                )
            )
        return out

    def delete(self, ids: List[str]) -> None:
        self._connect()
        self._collection.delete(ids=ids)

    def count(self) -> int:
        self._connect()
        return self._collection.count()
