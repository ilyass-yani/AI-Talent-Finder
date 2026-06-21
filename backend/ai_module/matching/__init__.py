"""Matching Module - Init"""

# Keep package initialization lightweight.
# Heavy submodules such as semantic_matcher and bert_classifier_adapter should be
# imported explicitly by the caller when needed (they pull in torch/transformers).

# Convenience re-exports for common use:
#   from ai_module.matching import HybridConfig, HybridMatcher
#   from ai_module.matching import BertClassifierAdapter
from ai_module.matching.hybrid_matcher import HybridConfig, HybridMatcher
from ai_module.matching.bert_classifier_adapter import BertClassifierAdapter, get_default_adapter
from ai_module.matching.scorer import CosineScorer

__all__ = [
    "HybridConfig",
    "HybridMatcher",
    "BertClassifierAdapter",
    "get_default_adapter",
    "CosineScorer",
]

