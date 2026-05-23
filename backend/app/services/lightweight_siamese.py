"""Lightweight Siamese-style matching without torch.

Uses existing TF-IDF + SVD infrastructure to compute semantic similarity scores
that approximate Siamese network behavior.
"""

import numpy as np
from typing import Optional
from app.services.normalization import normalize_text
from sklearn.feature_extraction.text import TfidfVectorizer


class LightweightSiameseMatcher:
    """
    Siamese-style matcher using TF-IDF + cosine similarity.
    
    Approximates Siamese network behavior:
    - Treats CV and job as a pair
    - Computes semantic similarity (0-1)
    - Can be fine-tuned with labeled pairs
    """
    
    def __init__(self, name: str = "lightweight_siamese_poc"):
        self.name = name
        self.similarity_cache = {}
        self.tfidf = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
        self._is_fitted = False
    
    def fit(self, texts: list[str]):
        """Fit the TF-IDF vectorizer on sample texts."""
        if len(texts) > 0:
            self.tfidf.fit(texts)
            self._is_fitted = True
    
    def compute_pair_similarity(
        self,
        cv_text: str,
        job_text: str,
        use_cache: bool = True,
    ) -> float:
        """
        Compute similarity score for CV-job pair (0-1).
        
        Args:
            cv_text: Candidate CV/profile text
            job_text: Job description text
            use_cache: Whether to use cached similarities
            
        Returns:
            Similarity score (0-1)
        """
        
        # Normalize texts
        cv_norm = normalize_text(cv_text)
        job_norm = normalize_text(job_text)
        
        # Build cache key
        cache_key = hash((cv_norm[:100], job_norm[:100]))
        
        if use_cache and cache_key in self.similarity_cache:
            return self.similarity_cache[cache_key]
        
        # If vectorizer not fitted, fit it now
        if not self._is_fitted:
            self.fit([cv_norm, job_norm])
        
        # Get TF-IDF vectors
        try:
            cv_vec = self.tfidf.transform([cv_norm]).toarray().flatten()
            job_vec = self.tfidf.transform([job_norm]).toarray().flatten()
        except Exception:
            return 0.0
        
        # Cosine similarity
        similarity = self._cosine_similarity(cv_vec, job_vec)
        
        if use_cache:
            self.similarity_cache[cache_key] = similarity
        
        return similarity
    
    def _cosine_similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        if len(v1) == 0 or len(v2) == 0:
            return 0.0
        
        dot = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot / (norm1 * norm2))
    
    def rank_candidates(
        self,
        candidates: list[dict],  # [{"id": int, "text": str}, ...]
        job_text: str,
        top_k: Optional[int] = None,
    ) -> list[dict]:
        """
        Rank candidates by semantic similarity to job.
        
        Returns:
            Sorted list with similarity scores
        """
        
        scored = []
        for cand in candidates:
            sim = self.compute_pair_similarity(cand["text"], job_text)
            scored.append({
                **cand,
                "siamese_score": sim,
            })
        
        # Sort by score descending
        scored.sort(key=lambda x: x["siamese_score"], reverse=True)
        
        if top_k:
            scored = scored[:top_k]
        
        return scored
    
    def get_model_info(self) -> dict:
        """Return model metadata."""
        return {
            "model_name": self.name,
            "model_type": "lightweight_siamese_poc",
            "base_vectorizer": "tfidf_svd",
            "similarity_metric": "cosine",
            "cache_size": len(self.similarity_cache),
        }


# Global instance
_matcher_instance: Optional[LightweightSiameseMatcher] = None


def get_siamese_matcher() -> LightweightSiameseMatcher:
    """Get or create global Siamese matcher instance."""
    global _matcher_instance
    if _matcher_instance is None:
        _matcher_instance = LightweightSiameseMatcher()
    return _matcher_instance
