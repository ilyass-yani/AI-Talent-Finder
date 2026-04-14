"""
NLP Service Container - Singleton for Loading HuggingFace Model Once

This module provides a singleton pattern for the NLP service,
ensuring the model is loaded only once at application startup,
then reused for all subsequent requests.

Place this file at: backend/app/core/nlp_container.py
"""

import logging
from typing import Optional
from ai_module.nlp.nlp_service import NLPService

logger = logging.getLogger(__name__)


class NLPContainer:
    """
    Singleton container for NLP service.
    
    Ensures the HuggingFace model is loaded only once,
    avoiding redundant memory usage and startup overhead.
    
    Usage:
        # Get service (loads on first call, returns cached on subsequent calls)
        service = NLPContainer.get_service()
        
        if service:
            results = service.find_similar("python", ["Python", "JavaScript"])
    """
    
    _instance: Optional[NLPService] = None
    _load_attempted: bool = False
    
    @classmethod
    def get_service(cls) -> Optional[NLPService]:
        """
        Get NLP service instance (singleton pattern).
        
        On first call: Loads the model from HuggingFace (takes ~1-2 seconds)
        On subsequent calls: Returns the cached instance instantly
        
        Returns:
            NLPService instance or None if loading failed
        """
        
        # Already loaded or load failed
        if cls._load_attempted:
            return cls._instance
        
        # Mark that we've attempted loading
        cls._load_attempted = True
        
        try:
            logger.info("=" * 60)
            logger.info("⏳ Loading NLP Service (one-time startup cost)...")
            logger.info("  Model: sentence-transformers/all-MiniLM-L6-v2")
            logger.info("  This may take 1-2 minutes on first run")
            logger.info("  (downloading model from HuggingFace)")
            logger.info("=" * 60)
            
            cls._instance = NLPService(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            
            logger.info("=" * 60)
            logger.info("✓ NLP Service loaded successfully!")
            logger.info("  Ready to use semantic matching for:")
            logger.info("    • Skill normalization")
            logger.info("    • Institution name matching")
            logger.info("    • Job title extraction")
            logger.info("=" * 60)
            
            return cls._instance
        
        except Exception as e:
            logger.warning("=" * 60)
            logger.warning(f"⚠ NLP Service failed to load: {e}")
            logger.warning("")
            logger.warning("Continuing without NLP capabilities:")
            logger.warning("  • Regex-based extraction will be used")
            logger.warning("  • No semantic skill matching")
            logger.warning("  • Lower accuracy for varied CV formats")
            logger.warning("")
            logger.warning("This might happen due to:")
            logger.warning("  • Network issues (can't download model)")
            logger.warning("  • Insufficient disk space")
            logger.warning("  • Insufficient memory (try using CPU instead)")
            logger.warning("=" * 60)
            
            cls._instance = None
            return None
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if NLP service is available"""
        service = cls.get_service()
        return service is not None
    
    @classmethod
    def reset(cls):
        """
        Reset the singleton (useful for testing or reloading).
        
        WARNING: Only use this if you know what you're doing!
        """
        if cls._instance:
            logger.info("Resetting NLP Service container...")
            cls._instance = None
        cls._load_attempted = False
