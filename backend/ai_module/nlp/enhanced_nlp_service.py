"""
Enhanced NLP Service with Configuration and Persistent Caching
Integrates HuggingFace models with embeddings cache for production use
"""

import logging
import os
from typing import Dict, List, Tuple, Optional
import numpy as np
import torch
from sentence_transformers import SentenceTransformer, util

from ai_module.config.model_config import ACTIVE_MODEL, ENCODING_SETTINGS, ACTIVE_MODEL_KEY
from ai_module.cache.embeddings_cache import EmbeddingsCacheManager

logger = logging.getLogger(__name__)


class EnhancedNLPService:
    """
    Enhanced NLP Service with:
    - Configurable HF models
    - Persistent embedding cache
    - Batch processing optimizations
    - Memory-efficient inference
    """
    
    def __init__(self, use_cache: bool = True):
        """
        Initialize Enhanced NLP Service
        
        Args:
            use_cache: Whether to use persistent embedding cache
        """
        self.config = ACTIVE_MODEL
        self.model: Optional[SentenceTransformer] = None
        self.device = self._setup_device()
        self.use_cache = use_cache
        self.cache = None
        
        logger.info(f"[NLP] Initializing Enhanced NLP Service")
        logger.info(f"  Model: {self.config.model_id}")
        logger.info(f"  Quality: {self.config.quality}")
        logger.info(f"  Embedding dim: {self.config.embedding_dim}")
        logger.info(f"  Device: {self.device}")
        logger.info(f"  Cache enabled: {use_cache}")
        
        self._load_model()
        
        if use_cache:
            from ai_module.config.model_config import get_embeddings_cache_path
            cache_path = get_embeddings_cache_path(ACTIVE_MODEL_KEY)
            self.cache = EmbeddingsCacheManager(cache_path)
            self._log_cache_stats()
    
    def _setup_device(self) -> str:
        """Setup device (CUDA if available, else CPU)"""
        if self.config.device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            device = self.config.device
        
        if device == "cuda" and torch.cuda.is_available():
            logger.info(f"[NLP] Using GPU: {torch.cuda.get_device_name()}")
        else:
            logger.info(f"[NLP] Using CPU")
        
        return device
    
    def _load_model(self):
        """Load model from HuggingFace"""
        try:
            logger.info(f"[NLP] Loading model from HuggingFace...")
            
            self.model = SentenceTransformer(
                self.config.model_id,
                device=self.device,
                cache_folder=self.config.cache_dir,
                trust_remote_code=True
            )
            
            logger.info(f"[NLP] ✓ Model loaded successfully")
            logger.info(f"  Embedding dimension: {self.model.get_sentence_embedding_dimension()}")
            logger.info(f"  Max sequence length: {self.model.max_seq_length}")
            
        except Exception as e:
            logger.error(f"[NLP] ✗ Error loading model: {str(e)}")
            raise
    
    def _log_cache_stats(self):
        """Log cache statistics"""
        if self.cache:
            stats = self.cache.get_cache_stats()
            logger.info(f"[CACHE] Statistics:")
            logger.info(f"  Cached embeddings: {stats['total_embeddings']}")
            logger.info(f"  Cache file size: {stats['cache_file_size_mb']}MB")
            logger.info(f"  Estimated memory: {stats['estimated_memory_mb']}MB")
    
    def encode_text(self, text: str) -> np.ndarray:
        """
        Encode single text to embedding
        
        Args:
            text: Text to encode
        
        Returns:
            numpy array embedding
        """
        # Check cache first
        if self.cache:
            cached = self.cache.get(text)
            if cached is not None:
                logger.debug(f"[NLP] Cache hit for: {text[:50]}...")
                return cached
        
        # Encode
        embedding = self.model.encode(text, **ENCODING_SETTINGS)
        
        # Save to cache
        if self.cache:
            self.cache.set(text, embedding, {'source': 'cv_extraction'})
        
        return embedding
    
    def encode_batch(self, texts: List[str], batch_size: Optional[int] = None) -> np.ndarray:
        """
        Encode multiple texts efficiently
        
        Args:
            texts: List of texts
            batch_size: Override default batch size
        
        Returns:
            numpy array of embeddings (shape: len(texts), embedding_dim)
        """
        if not texts:
            return np.array([])
        
        batch_size = batch_size or self.config.batch_size
        
        # Check what's in cache
        missing_texts = []
        cached_embeddings = {}
        
        if self.cache:
            cached_embeddings = self.cache.get_batch(texts)
            missing_texts = self.cache.get_missing_texts(texts)
            
            logger.info(f"[NLP] Batch encoding: {len(texts)} texts")
            logger.info(f"  Cache hits: {len(cached_embeddings)}")
            logger.info(f"  Missing: {len(missing_texts)}")
        else:
            missing_texts = texts
        
        # Encode missing texts
        if missing_texts:
            logger.debug(f"[NLP] Encoding {len(missing_texts)} texts in batches of {batch_size}...")
            new_embeddings = self.model.encode(
                missing_texts,
                batch_size=batch_size,
                show_progress_bar=True,
                **ENCODING_SETTINGS
            )
            
            # Save to cache
            if self.cache:
                self.cache.set_batch(
                    missing_texts,
                    new_embeddings,
                    {text.lower().strip(): {'source': 'batch_encoding'} for text in missing_texts}
                )
                self.cache.save_cache()
        else:
            new_embeddings = np.array([])
        
        # Combine cached + new embeddings in original order
        all_embeddings = []
        for text in texts:
            if text in cached_embeddings:
                all_embeddings.append(cached_embeddings[text])
            else:
                # Find in new_embeddings
                idx = missing_texts.index(text)
                all_embeddings.append(new_embeddings[idx])
        
        return np.array(all_embeddings)
    
    def find_similar(
        self,
        query: str,
        candidates: List[str],
        top_k: int = 5,
        threshold: float = 0.3
    ) -> List[Tuple[str, float]]:
        """
        Find most similar candidates to a query
        
        Args:
            query: Query text
            candidates: List of candidate texts
            top_k: Return top K results
            threshold: Minimum similarity (0-1)
        
        Returns:
            List of (text, score) tuples, sorted by score
        """
        if not candidates:
            return []
        
        # Encode query and candidates
        query_emb = self.encode_text(query)
        candidate_embs = self.encode_batch(candidates)
        
        if len(candidate_embs) == 0:
            return []
        
        # Convert to torch tensors for similarity computation
        query_tensor = torch.from_numpy(query_emb).unsqueeze(0)
        candidates_tensor = torch.from_numpy(candidate_embs)
        
        # Cosine similarity
        scores = util.pytorch_cos_sim(query_tensor, candidates_tensor)[0]
        
        # Filter and sort
        results = []
        for idx, score in enumerate(scores):
            score_val = float(score.item())
            if score_val >= threshold:
                results.append((candidates[idx], score_val))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    def semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts (0-1)"""
        emb1 = self.encode_text(text1)
        emb2 = self.encode_text(text2)
        
        # Cosine similarity
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return float(np.clip(similarity, 0.0, 1.0))
    
    def cache_texts(self, texts: List[str]):
        """
        Pre-compute and cache embeddings for texts
        Useful for pre-caching reference data like skills dictionary
        
        Args:
            texts: Texts to pre-cache
        """
        if not self.cache:
            logger.warning("[NLP] Cache disabled, skipping pre-cache")
            return
        
        missing = self.cache.get_missing_texts(texts)
        if not missing:
            logger.info(f"[NLP] All {len(texts)} texts already in cache")
            return
        
        logger.info(f"[NLP] Pre-caching {len(missing)} texts...")
        embeddings = self.encode_batch(missing)
        self.cache.set_batch(missing, embeddings)
        self.cache.save_cache()
        logger.info(f"[NLP] ✓ Pre-caching complete")
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        if self.cache:
            return self.cache.get_cache_stats()
        return {'cached': False}
