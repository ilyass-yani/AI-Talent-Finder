"""LLM fine-tuning and inference for CV ↔ Job matching."""
from .dataset_builder import MatchingDatasetBuilder, TrainingExample
from .inference import InferenceResult, MatchingLLM
from .lora_trainer import DoRATrainer, LoRATrainer, QLoRATrainer
from .prompts import (
    MATCHING_SYSTEM_PROMPT,
    build_matching_prompt,
    parse_matching_response,
)

__all__ = [
    "MatchingDatasetBuilder",
    "TrainingExample",
    "InferenceResult",
    "MatchingLLM",
    "LoRATrainer",
    "QLoRATrainer",
    "DoRATrainer",
    "MATCHING_SYSTEM_PROMPT",
    "build_matching_prompt",
    "parse_matching_response",
]
