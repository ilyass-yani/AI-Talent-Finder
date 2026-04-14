"""
Semantic Skill Matcher - Using sentence-transformers for semantic matching
Uses all-MiniLM-L6-v2 model to create embeddings and match candidate skills
with job requirements semantically.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
import os

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence-transformers not installed. Run: pip install sentence-transformers")


class SemanticSkillMatcher:
    """
    Match candidate skills with job criteria using semantic embeddings.
    Uses all-MiniLM-L6-v2 model for 384-dimensional dense vector embeddings.
    """
    
    # Model configuration
    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Cache for loaded model
    _model = None
    _embedding_cache = {}
    
    @classmethod
    def _load_model(cls) -> Optional['SentenceTransformer']:
        """
        Load and cache the sentence-transformers model.
        Only loads model once, subsequent calls return cached version.
        """
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
    
    @classmethod
    def get_embedding(cls, text: str) -> Optional[np.ndarray]:
        """
        Get embedding for a single piece of text.
        Uses cache to avoid recomputing same text embeddings.
        
        Args:
            text: Text to embed (skill name, job description, etc.)
        
        Returns:
            384-dimensional numpy array, or None if model unavailable
        """
        if text in cls._embedding_cache:
            return cls._embedding_cache[text]
        
        model = cls._load_model()
        if model is None:
            return None
        
        try:
            embedding = model.encode(text, convert_to_numpy=True)
            cls._embedding_cache[text] = embedding
            return embedding
        except Exception as e:
            print(f"Error embedding text '{text}': {e}")
            return None
    
    @classmethod
    def get_embeddings_batch(cls, texts: List[str]) -> Optional[np.ndarray]:
        """
        Get embeddings for multiple texts at once (more efficient).
        
        Args:
            texts: List of texts to embed
        
        Returns:
            Array of shape (len(texts), 384), or None if model unavailable
        """
        model = cls._load_model()
        if model is None:
            return None
        
        try:
            embeddings = model.encode(texts, convert_to_numpy=True)
            
            # Cache individual embeddings
            for text, embedding in zip(texts, embeddings):
                cls._embedding_cache[text] = embedding
            
            return embeddings
        except Exception as e:
            print(f"Error getting batch embeddings: {e}")
            return None
    
    @classmethod
    def semantic_similarity(cls, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two texts.
        Returns cosine similarity (0-1).
        
        Args:
            text1: First text (e.g., candidate skill)
            text2: Second text (e.g., job requirement)
        
        Returns:
            Similarity score 0-1, or 0 if embeddings unavailable
        """
        embed1 = cls.get_embedding(text1)
        embed2 = cls.get_embedding(text2)
        
        if embed1 is None or embed2 is None:
            return 0.0
        
        # Cosine similarity: (A·B) / (||A|| * ||B||)
        similarity = np.dot(embed1, embed2) / (
            np.linalg.norm(embed1) * np.linalg.norm(embed2)
        )
        
        # Clamp to [0, 1]
        return float(np.clip(similarity, 0.0, 1.0))
    
    @classmethod
    def match_candidate_skills(
        cls,
        candidate_skills: List[str],
        criteria_skills: List[Dict[str, any]],
        threshold: float = 0.6
    ) -> Dict[str, any]:
        """
        Match candidate skills to criteria skills using semantic similarity.
        
        Args:
            candidate_skills: List of candidate's skills (e.g., ["Python", "Django", "PostgreSQL"])
            criteria_skills: List of required skills (e.g., [{"name": "Python", "weight": 100}])
            threshold: Minimum similarity to consider a match (0-1)
        
        Returns:
            Dictionary containing:
            - matched_skills: List of matched skills with scores
            - score: Overall match score (0-100)
            - details: Detailed matching info
        """
        if not candidate_skills or not criteria_skills:
            return {
                "matched_skills": [],
                "score": 0.0,
                "details": "No skills to match"
            }
        
        candidate_skills_lower = [s.lower().strip() for s in candidate_skills]
        
        matched_skills = []
        total_weight = 0
        total_matched_weight = 0
        
        # For each criteria skill, find best matching candidate skill
        for criteria in criteria_skills:
            criteria_name = criteria.get("name", "").lower().strip()
            criteria_weight = criteria.get("weight", 50)
            
            if not criteria_name:
                continue
            
            total_weight += criteria_weight
            
            # Find best match among candidate skills
            best_match = None
            best_similarity = 0.0
            
            for candidate_skill in candidate_skills_lower:
                similarity = cls.semantic_similarity(candidate_skill, criteria_name)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = candidate_skill
            
            # If similarity above threshold, count as match
            if best_similarity >= threshold:
                total_matched_weight += criteria_weight
                matched_skills.append({
                    "criteria_skill": criteria_name,
                    "matched_skill": best_match,
                    "similarity": float(best_similarity),
                    "weight": criteria_weight
                })
        
        # Calculate overall score
        overall_score = (total_matched_weight / total_weight * 100) if total_weight > 0 else 0.0
        
        return {
            "matched_skills": matched_skills,
            "score": float(np.clip(overall_score, 0.0, 100.0)),
            "total_matches": len(matched_skills),
            "total_criteria": len(criteria_skills),
            "details": f"Matched {len(matched_skills)}/{len(criteria_skills)} criteria skills"
        }
    
    @classmethod
    def clear_cache(cls):
        """Clear the embedding cache (useful for memory management)."""
        cls._embedding_cache.clear()
    
    @classmethod
    def get_cache_size(cls) -> int:
        """Get current number of cached embeddings."""
        return len(cls._embedding_cache)


# Utility function for simple similarity check
def semantic_skill_match(skill1: str, skill2: str, threshold: float = 0.6) -> Tuple[bool, float]:
    """
    Simple function to check if two skills match semantically.
    
    Args:
        skill1: First skill name
        skill2: Second skill name
        threshold: Minimum similarity to consider a match
    
    Returns:
        Tuple of (is_match: bool, similarity_score: float)
    """
    similarity = SemanticSkillMatcher.semantic_similarity(skill1, skill2)
    is_match = similarity >= threshold
    return is_match, similarity
