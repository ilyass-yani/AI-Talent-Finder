"""Configuration centrale du pipeline IA.

Toute la config est ici pour pouvoir basculer entre modes (lite/full),
choisir les modèles, ajuster les seuils, etc.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
CACHE_DIR = PROJECT_ROOT / ".cache"

for _p in (DATA_DIR, MODELS_DIR, CACHE_DIR):
    _p.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# Modèles d'embeddings
# --------------------------------------------------------------------------- #

@dataclass
class EmbeddingConfig:
    # bge-small-en : 384-dim, rapide, excellent rapport perf/coût pour le RH
    # all-MiniLM-L6-v2 : 384-dim, classique, multilingue partiel
    # all-mpnet-base-v2 : 768-dim, meilleure qualité, plus lent
    # paraphrase-multilingual-MiniLM-L12-v2 : 384-dim, multilingue (FR/EN/AR)
    model_name: str = os.getenv("SEMANTIC_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    multilingual_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    max_seq_length: int = 256
    batch_size: int = 32
    normalize_embeddings: bool = True
    cache_embeddings: bool = True
    cache_dir: Optional[str] = str(CACHE_DIR / "embeddings")


# --------------------------------------------------------------------------- #
# LLM Fine-tuning
# --------------------------------------------------------------------------- #

@dataclass
class LLMConfig:
    """Config pour fine-tuning LoRA/QLoRA/DoRA.

    Modèles recommandés selon GPU :
        - 8GB VRAM  : Qwen2.5-0.5B / Qwen2.5-1.5B en QLoRA 4-bit
        - 12GB VRAM : Mistral-7B en QLoRA 4-bit
        - 16GB VRAM : Mistral-7B en LoRA 8-bit
        - 24GB+     : Llama-3.1-8B en LoRA fp16
    """

    # Modèle de base (peut être surchargé via env)
    base_model: str = os.getenv("LLM_BASE_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")

    # Alternatives selon contraintes
    candidate_models: List[str] = field(default_factory=lambda: [
        "Qwen/Qwen2.5-0.5B-Instruct",      # Très léger, 8GB OK
        "Qwen/Qwen2.5-1.5B-Instruct",      # Recommandé : équilibre qualité/coût
        "mistralai/Mistral-7B-Instruct-v0.3",  # Référence qualité, 12GB+ en 4-bit
        "meta-llama/Llama-3.2-1B-Instruct",     # Excellent en few-shot
        "meta-llama/Llama-3.1-8B-Instruct",     # Top qualité, 16GB+
    ])

    # Quantization (QLoRA)
    load_in_4bit: bool = True
    bnb_4bit_quant_type: str = "nf4"          # nf4 > fp4 pour LLM
    bnb_4bit_compute_dtype: str = "bfloat16"  # bfloat16 > float16 sur A100/H100
    bnb_4bit_use_double_quant: bool = True

    # LoRA params (état de l'art 2025)
    lora_r: int = 16                          # rang : 16 = bon compromis ; 8 = light, 32 = lourd
    lora_alpha: int = 32                      # alpha = 2*r est une bonne heuristique
    lora_dropout: float = 0.05
    lora_target_modules: List[str] = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ])
    lora_bias: str = "none"
    use_rslora: bool = True                   # Rank-Stabilized LoRA (meilleure stabilité)
    use_dora: bool = False                    # DoRA : décompose magnitude/direction

    # Training
    output_dir: str = str(MODELS_DIR / "lora_adapter")
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 4
    per_device_eval_batch_size: int = 4
    gradient_accumulation_steps: int = 4      # batch effectif = 4*4 = 16
    gradient_checkpointing: bool = True
    learning_rate: float = 2e-4               # LoRA tolère lr 10x plus grand qu'un full fine-tune
    weight_decay: float = 0.01
    warmup_ratio: float = 0.03
    lr_scheduler_type: str = "cosine"
    max_seq_length: int = 1024
    optim: str = "paged_adamw_8bit"           # paged_adamw_8bit : indispensable en QLoRA
    fp16: bool = False
    bf16: bool = True
    logging_steps: int = 10
    save_strategy: str = "epoch"
    eval_strategy: str = "epoch"
    save_total_limit: int = 2
    seed: int = 42

    # Inférence
    max_new_tokens: int = 256
    temperature: float = 0.1                  # bas car tâche de scoring (déterministe)
    top_p: float = 0.9
    do_sample: bool = False


# --------------------------------------------------------------------------- #
# Scoring & décision
# --------------------------------------------------------------------------- #

@dataclass
class ScoringConfig:
    # Poids par défaut (modifiables par recruteur)
    weight_skills: float = 0.45
    weight_semantic: float = 0.20
    weight_experience: float = 0.15
    weight_education: float = 0.10
    weight_languages: float = 0.05
    weight_seniority: float = 0.05

    # Seuils de décision par défaut
    threshold_accept: float = 0.75
    threshold_review: float = 0.50

    # Bonus / malus
    bonus_perfect_match: float = 0.05
    penalty_missing_hard_skill: float = 0.15
    hard_skills_priority: bool = True


# --------------------------------------------------------------------------- #
# Vector DB
# --------------------------------------------------------------------------- #

@dataclass
class VectorDBConfig:
    backend: str = os.getenv("VECTOR_DB", "faiss")  # "faiss" ou "chroma"
    index_path: str = str(CACHE_DIR / "vector_index")
    embedding_dim: int = 384
    metric: str = "cosine"
    top_k_default: int = 20


# --------------------------------------------------------------------------- #
# Pipeline global
# --------------------------------------------------------------------------- #

@dataclass
class PipelineConfig:
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    vector_db: VectorDBConfig = field(default_factory=VectorDBConfig)

    # Modes
    use_llm_inference: bool = bool(int(os.getenv("USE_LLM_INFERENCE", "0")))
    use_cross_encoder: bool = bool(int(os.getenv("USE_CROSS_ENCODER", "1")))
    use_faiss: bool = bool(int(os.getenv("USE_FAISS", "1")))
    use_shap: bool = bool(int(os.getenv("USE_SHAP", "0")))

    # Performance
    enable_cache: bool = True
    parallel_workers: int = int(os.getenv("PIPELINE_WORKERS", "4"))


# Instance globale (à importer partout)
config = PipelineConfig()


def get_config() -> PipelineConfig:
    return config


def update_config(**overrides) -> PipelineConfig:
    """Mise à jour atomique de la config (utile pour les tests)."""
    global config
    for key, value in overrides.items():
        if hasattr(config, key):
            setattr(config, key, value)
    return config
