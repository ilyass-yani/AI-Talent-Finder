"""
Embedding Cache Manager - Persistent storage of text embeddings
Handles loading, saving, and updating embeddings cache to avoid recomputation
"""

import os
import pickle
import logging
import json
from typing import Dict, Optional, List, Set
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


class EmbeddingsCacheManager:
    """
    Manage persistent cache of text embeddings.
    
    Stores embeddings in pickle format for fast serialization.
    Can be queried to avoid recomputing embeddings for known texts.
    """
    
    def __init__(self, cache_path: str):
        """
        Initialize cache manager
        
        Args:
            cache_path: Path to pickle file for embeddings (.pkl)
        """
        self.cache_path = cache_path
        self.cache: Dict[str, np.ndarray] = {}
        self.metadata: Dict[str, Dict] = {}  # Metadata about each embedding
        self.loaded = False
        
        # Try to load existing cache
        self._load_cache()
    
    def _load_cache(self):
        """Load embeddings cache from disk"""
        if not os.path.exists(self.cache_path):
            logger.info(f"[CACHE] No existing cache at {self.cache_path}")
            self.loaded = True
            return
        
        try:
            with open(self.cache_path, 'rb') as f:
                data = pickle.load(f)
            
            self.cache = data.get('embeddings', {})
            self.metadata = data.get('metadata', {})
            
            logger.info(f"[CACHE] Loaded {len(self.cache)} cached embeddings from {self.cache_path}")
            self.loaded = True
            
        except Exception as e:
            logger.error(f"[CACHE] Error loading cache: {str(e)}")
            self.cache = {}
            self.metadata = {}
            self.loaded = True
    
    def save_cache(self):
        """Save embeddings cache to disk"""
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            
            data = {
                'embeddings': self.cache,
                'metadata': self.metadata,
                'saved_at': datetime.now().isoformat(),
                'total_embeddings': len(self.cache)
            }
            
            with open(self.cache_path, 'wb') as f:
                pickle.dump(data, f)
            
            logger.info(f"[CACHE] Saved {len(self.cache)} embeddings to {self.cache_path}")
            
        except Exception as e:
            logger.error(f"[CACHE] Error saving cache: {str(e)}")
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for consistent cache key generation"""
        return text.strip().lower()
    
    def get(self, text: str) -> Optional[np.ndarray]:
        """
        Get embedding from cache
        
        Args:
            text: Text to look up
        
        Returns:
            numpy array or None if not in cache
        """
        normalized = self.normalize_text(text)
        return self.cache.get(normalized)
    
    def get_batch(self, texts: List[str]) -> Dict[str, np.ndarray]:
        """
        Get multiple embeddings from cache
        
        Args:
            texts: List of texts to look up
        
        Returns:
            Dict mapping text -> embedding (only for found items)
        """
        result = {}
        for text in texts:
            normalized = self.normalize_text(text)
            if normalized in self.cache:
                result[text] = self.cache[normalized]
        return result
    
    def set(self, text: str, embedding: np.ndarray, metadata: Optional[Dict] = None):
        """
        Add embedding to cache
        
        Args:
            text: Original text
            embedding: numpy array
            metadata: Optional metadata dict
        """
        normalized = self.normalize_text(text)
        self.cache[normalized] = embedding
        
        self.metadata[normalized] = {
            'original_text': text,
            'embedding_dim': len(embedding),
            'added_at': datetime.now().isoformat(),
            **(metadata or {})
        }
    
    def set_batch(self, texts: List[str], embeddings: np.ndarray, metadata_dict: Optional[Dict] = None):
        """
        Add multiple embeddings to cache
        
        Args:
            texts: List of texts
            embeddings: numpy array of shape (len(texts), embedding_dim)
            metadata_dict: Dict mapping normalized_text -> metadata
        """
        for text, embedding in zip(texts, embeddings):
            meta = (metadata_dict or {}).get(text.lower().strip())
            self.set(text, embedding, meta)
    
    def get_missing_texts(self, texts: List[str]) -> List[str]:
        """
        Find texts not in cache (need embedding)
        
        Args:
            texts: List of texts to check
        
        Returns:
            List of texts not in cache
        """
        return [
            text for text in texts
            if self.normalize_text(text) not in self.cache
        ]
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        if not self.cache:
            return {
                'total_embeddings': 0,
                'cache_file_exists': os.path.exists(self.cache_path),
                'cache_file_size_mb': 0
            }
        
        # Get first embedding to check dimension
        first_embedding = next(iter(self.cache.values()))
        embedding_dim = len(first_embedding)
        
        file_size_mb = os.path.getsize(self.cache_path) / (1024 ** 2) if os.path.exists(self.cache_path) else 0
        
        return {
            'total_embeddings': len(self.cache),
            'embedding_dimension': embedding_dim,
            'cache_file_exists': os.path.exists(self.cache_path),
            'cache_file_size_mb': round(file_size_mb, 2),
            'estimated_memory_mb': round(len(self.cache) * embedding_dim * 4 / (1024 ** 2), 2),  # float32 = 4 bytes
        }
    
    def clear_cache(self):
        """Clear in-memory cache (does not delete file)"""
        self.cache = {}
        self.metadata = {}
        logger.warning("[CACHE] Cleared in-memory cache")
    
    def delete_cache_file(self):
        """Delete cache file from disk"""
        if os.path.exists(self.cache_path):
            os.remove(self.cache_path)
            logger.warning(f"[CACHE] Deleted cache file: {self.cache_path}")
            self.cache = {}
            self.metadata = {}
