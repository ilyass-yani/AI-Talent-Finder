"""
Smart Skill Deduplication — Semantic Clustering

Removes duplicate skills using semantic similarity instead of string matching.
Example: ["Python", "python", "Python 3"] → ["Python"]
"""

from typing import List
from collections import defaultdict
import logging

from app.services.normalization import normalize_skill_name

logger = logging.getLogger(__name__)


class SmartSkillDeduplicator:
    """Deduplicates skills using semantic clustering."""
    
    def __init__(self, embedder=None, similarity_threshold: float = 0.82):
        """
        Args:
            embedder: SentenceTransformer instance (optional)
            similarity_threshold: Min similarity to merge skills (0.0-1.0)
        """
        self.embedder = embedder
        self.similarity_threshold = similarity_threshold
    
    def deduplicate(self, skills: List[str]) -> List[str]:
        """
        Deduplicate a list of skills via semantic clustering.
        
        Args:
            skills: ["Python", "python", "ML", "Machine Learning"]
            
        Returns:
            ["Python", "Machine Learning"]  # Canonical names
        """
        if not skills:
            return []
        
        if len(skills) <= 1:
            return skills
        
        # Normalize: lowercase, trim, remove empty
        normalized = [s.strip().lower() for s in skills if s and s.strip()]
        
        # First pass: exact string deduplication (preserve order)
        first_pass = list(dict.fromkeys(normalized))
        
        if len(first_pass) <= 1:
            return [normalize_skill_name(skill) for skill in first_pass]
        
        # Second pass: semantic clustering (if embedder available)
        if self.embedder:
            try:
                clusters = self._cluster_by_similarity(first_pass)
                canonical = self._extract_canonical(skills, clusters)
                return canonical
            except Exception as e:
                logger.warning(f"Embedding failed ({e}), using string dedup")
                return [normalize_skill_name(skill) for skill in first_pass]

        return [normalize_skill_name(skill) for skill in first_pass]
    
    def _cluster_by_similarity(self, skills: List[str]) -> List[List[int]]:
        """Cluster skills by semantic similarity."""
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np
        except ImportError:
            logger.warning("sklearn not available, skipping semantic clustering")
            return [[i] for i in range(len(skills))]
        
        # Generate embeddings
        embeddings = self.embedder.encode(skills)  # shape: (N, dim)
        
        # Compute similarity matrix
        similarity_matrix = cosine_similarity(embeddings)
        
        # Clustering via connected components
        clusters = []
        used = set()
        
        for i in range(len(skills)):
            if i in used:
                continue
            
            # Start new cluster
            cluster = [i]
            used.add(i)
            
            # Find all similar skills
            for j in range(i + 1, len(skills)):
                if j in used:
                    continue
                
                if similarity_matrix[i][j] > self.similarity_threshold:
                    cluster.append(j)
                    used.add(j)
            
            clusters.append(cluster)
        
        return clusters
    
    def _extract_canonical(self, original_skills: List[str], 
                          clusters: List[List[int]]) -> List[str]:
        """
        Extract canonical skill for each cluster.
        Heuristic: longest skill = most descriptive
        """
        canonical = []
        
        for cluster in clusters:
            # Get original skills (preserving case/format)
            cluster_skills = [original_skills[i] for i in cluster]
            
            # Heuristic: longest = most descriptive
            canonical_skill = max(cluster_skills, key=len)
            canonical.append(canonical_skill)
        
        return canonical
