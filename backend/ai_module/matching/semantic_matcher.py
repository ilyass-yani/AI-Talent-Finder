"""Semantic skill matching using modern open-source embeddings + optional FAISS.

Default model:
- BAAI/bge-small-en

Key capabilities:
- text embedding cache
- cosine similarity
- optional FAISS inner-product index for fast nearest-neighbor lookup
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence-transformers not installed. Run: pip install sentence-transformers")

try:
    import faiss  # type: ignore

    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False


class SemanticSkillMatcher:
    """Match candidate skills with weighted criteria using semantic embeddings."""

    MODEL_NAME = os.getenv("SEMANTIC_EMBEDDING_MODEL", "BAAI/bge-small-en")
    DEFAULT_THRESHOLD = float(os.getenv("SEMANTIC_MATCH_THRESHOLD", "0.60"))

    _model = None
    _embedding_cache: Dict[str, np.ndarray] = {}
    
    @classmethod
    def _load_model(cls) -> Optional["SentenceTransformer"]:
        """Load and cache the sentence-transformers model once."""
        if cls._model is not None:
            return cls._model

        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            print("sentence-transformers not available")
            return None

        try:
            print(f"Loading {cls.MODEL_NAME}...")
            cls._model = SentenceTransformer(cls.MODEL_NAME)
            print(f"✓ Model loaded successfully. Embedding dimension: {cls._model.get_sentence_embedding_dimension()}")
            return cls._model
        except Exception as e:
            print(f"Error loading model: {e}")
            return None
    
    @staticmethod
    def _normalize(vecs: np.ndarray) -> np.ndarray:
        """L2 normalize vectors for cosine similarity via dot product."""
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        return vecs / norms

    @classmethod
    def get_embedding(cls, text: str) -> Optional[np.ndarray]:
        """Get one normalized embedding and cache it."""
        key = text.strip().lower()
        if key in cls._embedding_cache:
            return cls._embedding_cache[key]

        model = cls._load_model()
        if model is None:
            return None

        try:
            embedding = model.encode([text], convert_to_numpy=True).astype(np.float32)
            embedding = cls._normalize(embedding)[0]
            cls._embedding_cache[key] = embedding
            return embedding
        except Exception as e:
            print(f"Error embedding text '{text}': {e}")
            return None
    
    @classmethod
    def get_embeddings_batch(cls, texts: List[str]) -> Optional[np.ndarray]:
        """Get normalized embeddings for multiple texts and cache each item."""
        model = cls._load_model()
        if model is None:
            return None

        try:
            embeddings = model.encode(texts, convert_to_numpy=True).astype(np.float32)
            embeddings = cls._normalize(embeddings)

            for text, embedding in zip(texts, embeddings):
                cls._embedding_cache[text.strip().lower()] = embedding

            return embeddings
        except Exception as e:
            print(f"Error getting batch embeddings: {e}")
            return None
    
    @classmethod
    def semantic_similarity(cls, text1: str, text2: str) -> float:
        """Cosine similarity in [0, 1] between two texts."""
        embed1 = cls.get_embedding(text1)
        embed2 = cls.get_embedding(text2)

        if embed1 is None or embed2 is None:
            return 0.0

        similarity = float(np.dot(embed1, embed2))
        return float(np.clip(similarity, 0.0, 1.0))

    @classmethod
    def build_faiss_index(cls, corpus: List[str]) -> Optional[Tuple["faiss.IndexFlatIP", List[str]]]:
        """Build a FAISS inner-product index for a corpus of phrases."""
        if not FAISS_AVAILABLE:
            return None

        cleaned = [item.strip() for item in corpus if item and item.strip()]
        if not cleaned:
            return None

        embeddings = cls.get_embeddings_batch(cleaned)
        if embeddings is None:
            return None

        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings.astype(np.float32))
        return index, cleaned

    @classmethod
    def search_similar(cls, query: str, corpus: List[str], top_k: int = 5) -> List[Tuple[str, float]]:
        """Return top-k most similar corpus entries for query."""
        if not corpus:
            return []

        top_k = max(1, min(top_k, len(corpus)))
        q = cls.get_embedding(query)
        if q is None:
            return []

        # Use FAISS when available.
        index_bundle = cls.build_faiss_index(corpus)
        if index_bundle is not None:
            index, cleaned = index_bundle
            scores, idxs = index.search(np.expand_dims(q.astype(np.float32), axis=0), top_k)
            return [
                (cleaned[int(i)], float(np.clip(scores[0][rank], 0.0, 1.0)))
                for rank, i in enumerate(idxs[0])
                if int(i) >= 0
            ]

        # Fallback brute force.
        similarities = [(item, cls.semantic_similarity(query, item)) for item in corpus]
        similarities.sort(key=lambda pair: pair[1], reverse=True)
        return similarities[:top_k]
    
    @classmethod
    def match_candidate_skills(
        cls,
        candidate_skills: List[str],
        criteria_skills: List[Dict[str, object]],
        threshold: float = DEFAULT_THRESHOLD,
    ) -> Dict[str, object]:
        """Match candidate skills to weighted criteria with semantic nearest-neighbor."""
        if not candidate_skills or not criteria_skills:
            return {
                "matched_skills": [],
                "score": 0.0,
                "details": "No skills to match",
            }

        candidate_skills_clean = [s.strip() for s in candidate_skills if s and s.strip()]
        if not candidate_skills_clean:
            return {
                "matched_skills": [],
                "score": 0.0,
                "details": "No candidate skills available",
            }

        matched_skills: List[Dict[str, object]] = []
        total_weight = 0
        total_matched_weight = 0

        for criteria in criteria_skills:
            criteria_name = str(criteria.get("name", "")).strip()
            criteria_weight = int(criteria.get("weight", 50) or 50)

            if not criteria_name:
                continue

            total_weight += criteria_weight

            nearest = cls.search_similar(criteria_name, candidate_skills_clean, top_k=1)
            if not nearest:
                continue

            best_match, best_similarity = nearest[0]
            if best_similarity >= threshold:
                total_matched_weight += criteria_weight
                matched_skills.append({
                    "criteria_skill": criteria_name.lower(),
                    "matched_skill": best_match,
                    "similarity": float(best_similarity),
                    "weight": criteria_weight,
                })

        overall_score = (total_matched_weight / total_weight * 100) if total_weight > 0 else 0.0

        return {
            "matched_skills": matched_skills,
            "score": float(np.clip(overall_score, 0.0, 100.0)),
            "total_matches": len(matched_skills),
            "total_criteria": len(criteria_skills),
            "details": f"Matched {len(matched_skills)}/{len(criteria_skills)} criteria skills",
        }
    
    @classmethod
    def clear_cache(cls):
        """Clear embedding cache."""
        cls._embedding_cache.clear()

    @classmethod
    def release_resources(cls) -> None:
        """Release the cached embedding model and embeddings."""
        cls._embedding_cache.clear()
        cls._model = None
    
    @classmethod
    def get_cache_size(cls) -> int:
        """Return number of cached embeddings."""
        return len(cls._embedding_cache)


# Utility function for simple similarity check
def semantic_skill_match(skill1: str, skill2: str, threshold: float = 0.6) -> Tuple[bool, float]:
    """Simple helper that returns boolean semantic match + similarity."""
    similarity = SemanticSkillMatcher.semantic_similarity(skill1, skill2)
    is_match = similarity >= threshold
    return is_match, similarity
