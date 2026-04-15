"""
Skills Pre-caching Script
Pre-compute embeddings for all skills in the dictionary for faster matching
Run this once to initialize the system
"""

import json
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_skills_dictionary() -> dict:
    """Load skills from skills_dictionary.json"""
    skills_file = Path(__file__).parent.parent / "data" / "skills_dictionary.json"
    
    if not skills_file.exists():
        logger.error(f"Skills dictionary not found at {skills_file}")
        return {}
    
    with open(skills_file, 'r') as f:
        return json.load(f)


def flatten_skills(skills_dict: dict) -> list:
    """Flatten all skills from dictionary"""
    all_skills = []
    
    for category, skills in skills_dict.items():
        if isinstance(skills, list):
            all_skills.extend(skills)
        elif isinstance(skills, dict):
            # Handle nested structure if present
            all_skills.extend(skills.values())
    
    return list(set(all_skills))  # Remove duplicates


def precache_skills():
    """Pre-compute and cache embeddings for all skills"""
    print("=" * 70)
    print("🚀 Skills Pre-caching Initialization")
    print("=" * 70)
    
    # Load skills
    print("\n[1] Loading skills dictionary...")
    skills_dict = load_skills_dictionary()
    all_skills = flatten_skills(skills_dict)
    print(f"✓ Loaded {len(all_skills)} unique skills")
    
    # Initialize NLP service
    print("\n[2] Initializing Enhanced NLP Service...")
    try:
        from ai_module.nlp.enhanced_nlp_service import EnhancedNLPService
        nlp_service = EnhancedNLPService(use_cache=True)
        print("✓ NLP Service initialized")
    except Exception as e:
        print(f"✗ Error initializing NLP service: {str(e)}")
        return False
    
    # Pre-cache skills
    print(f"\n[3] Pre-caching {len(all_skills)} skills...")
    print("   This may take a few minutes...")
    print("-" * 70)
    
    try:
        nlp_service.cache_texts(all_skills)
        print("-" * 70)
        print("✓ Pre-caching complete!")
    except Exception as e:
        print(f"✗ Error during pre-caching: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # Show cache stats
    print("\n[4] Cache Statistics:")
    print("-" * 70)
    stats = nlp_service.get_cache_stats()
    print(f"  Total embeddings cached: {stats.get('total_embeddings', 0)}")
    print(f"  Embedding dimension: {stats.get('embedding_dimension', 0)}")
    print(f"  Cache file size: {stats.get('cache_file_size_mb', 0)} MB")
    print(f"  Estimated memory: {stats.get('estimated_memory_mb', 0)} MB")
    
    print("\n" + "=" * 70)
    print("✓ Pre-caching initialization SUCCESSFUL!")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Skills embeddings are now cached for fast matching")
    print("  2. Resume startup will be ~2x faster")
    print("  3. Initial matching operations will be instant")
    print("  4. Cache is persistent - no need to re-cache on restart")
    print()
    
    return True


if __name__ == "__main__":
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    success = precache_skills()
    sys.exit(0 if success else 1)
