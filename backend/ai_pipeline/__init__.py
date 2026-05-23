"""AI Talent Finder — Pipeline IA complet (ESISA-TechForge4).

Modules :
  * preprocessing         — nettoyage et normalisation des CV/offres
  * feature_engineering   — features classiques (TF-IDF) et sémantiques (embeddings)
  * matching              — cosinus, bi-encoder, cross-encoder, hybride
  * models                — ML classique (LR/RF/XGB) et BERT fine-tuning
  * llm                   — fine-tuning LoRA/QLoRA/DoRA et inférence
  * scoring               — scoring pondéré + règles métier + moteur de décision
  * explainability        — explications (règles + SHAP + LLM)
  * vector_db             — FAISS et ChromaDB
  * scraping              — LinkedIn, Indeed, Welcome to the Jungle
  * datasets              — données synthétiques, chargement, augmentation
  * pipeline              — orchestrateur de bout en bout
  * api                   — FastAPI (pipeline, LLM, scraping)
"""
from .config import (
    EmbeddingConfig,
    LLMConfig,
    PipelineConfig,
    ScoringConfig,
    VectorDBConfig,
)

__version__ = "1.0.0"
__team__ = "ESISA-TechForge4"

__all__ = [
    "PipelineConfig",
    "EmbeddingConfig",
    "LLMConfig",
    "ScoringConfig",
    "VectorDBConfig",
    "__version__",
    "__team__",
]
