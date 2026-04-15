"""
Hugging Face Model Configuration
Centralized configuration for all HF models used in the project
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional

# ============================================================================
# MODEL SELECTION
# ============================================================================

@dataclass
class ModelConfig:
    """Configuration for a single HF model"""
    
    # Model identifier on HuggingFace Hub
    model_id: str
    
    # Embedding dimension
    embedding_dim: int
    
    # Model size in MB (approximate)
    size_mb: int
    
    # Quality level (tradeoff between speed and accuracy)
    quality: str  # "lightweight", "balanced", "heavy"
    
    # Cache directory
    cache_dir: Optional[str] = None
    
    # Device placement
    device: str = "auto"  # "auto", "cuda", "cpu"
    
    # Batch size for encoding
    batch_size: int = 128
    
    # Max sequence length
    max_seq_length: int = 512
    
    def __post_init__(self):
        """Set default cache directory"""
        if self.cache_dir is None:
            self.cache_dir = os.path.expanduser("~/.cache/ai-talent-finder/models")


# ============================================================================
# AVAILABLE MODELS
# ============================================================================

MODELS: Dict[str, ModelConfig] = {
    # LIGHTWEIGHT - Fast, small, production-ready
    "lightweight": ModelConfig(
        model_id="sentence-transformers/all-MiniLM-L6-v2",
        embedding_dim=384,
        size_mb=22,
        quality="lightweight",
        batch_size=256,  # Can handle larger batches
    ),
    
    # BALANCED - Good accuracy + speed (recommended for most use cases)
    "balanced": ModelConfig(
        model_id="sentence-transformers/all-mpnet-base-v2",
        embedding_dim=768,
        size_mb=420,
        quality="balanced",
        batch_size=128,
    ),
    
    # HEAVY - Best accuracy (for critical matching)
    "heavy": ModelConfig(
        model_id="sentence-transformers/all-roberta-large-v1",
        embedding_dim=768,
        size_mb=1000,
        quality="heavy",
        batch_size=32,  # Larger model = smaller batches
    ),
    
    # MULTILINGUAL - For international CVs
    "multilingual": ModelConfig(
        model_id="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        embedding_dim=768,
        size_mb=420,
        quality="balanced",
        batch_size=128,
    ),
}


# ============================================================================
# CURRENT PRODUCTION MODEL
# ============================================================================
# Change this to switch all models globally
ACTIVE_MODEL_KEY = "lightweight"
ACTIVE_MODEL = MODELS[ACTIVE_MODEL_KEY]


# ============================================================================
# DATA PATHS
# ============================================================================

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
DATA_DIR = os.path.join(PROJECT_ROOT, "ai_module", "data")
EMBEDDINGS_DIR = os.path.join(DATA_DIR, "embeddings_cache")
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")

# Ensure directories exist
os.makedirs(ACTIVE_MODEL.cache_dir, exist_ok=True)
os.makedirs(EMBEDDINGS_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)


# ============================================================================
# EMBEDDING CACHE PATHS
# ============================================================================

def get_embeddings_cache_path(model_key: str = ACTIVE_MODEL_KEY) -> str:
    """Get path to pickled embeddings cache for a model"""
    return os.path.join(EMBEDDINGS_DIR, f"{model_key}_embeddings.pkl")


def get_skills_embeddings_cache_path(model_key: str = ACTIVE_MODEL_KEY) -> str:
    """Get path to pickled skill embeddings for a model"""
    return os.path.join(EMBEDDINGS_DIR, f"{model_key}_skills.pkl")


# ============================================================================
# MODEL OPTIMIZATION SETTINGS
# ============================================================================

ENCODING_SETTINGS = {
    "show_progress_bar": True,
    "convert_to_numpy": True,
    "normalize_embeddings": True,  # Normalize for cosine similarity
    "multi_gpu": True,  # Use multiple GPUs if available
}

# Batch processing thresholds
BATCH_PRECOMPUTE_THRESHOLD = 100  # Pre-compute embeddings if > 100 texts
BATCH_ENCODING_SIZE = ACTIVE_MODEL.batch_size


# ============================================================================
# LOGGING & MONITORING
# ============================================================================

LOG_MODEL_LOADING = True
LOG_EMBEDDING_CACHE = True
LOG_BATCH_PROCESSING = True

# Track embedding computation times (for optimization)
TRACK_COMPUTE_TIME = True
