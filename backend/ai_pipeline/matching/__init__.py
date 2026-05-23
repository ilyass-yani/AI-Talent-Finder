"""Modules de matching CV/Job — multiple stratégies, interface unifiée."""

from ai_pipeline.matching.base import BaseMatcher, MatchResult, MatchCandidate
from ai_pipeline.matching.cosine_matcher import CosineMatcher
from ai_pipeline.matching.semantic_matcher import SemanticMatcher
from ai_pipeline.matching.bi_encoder import BiEncoderMatcher
from ai_pipeline.matching.cross_encoder import CrossEncoderReranker
from ai_pipeline.matching.hybrid_matcher import HybridMatcher

__all__ = [
    "BaseMatcher",
    "MatchResult",
    "MatchCandidate",
    "CosineMatcher",
    "SemanticMatcher",
    "BiEncoderMatcher",
    "CrossEncoderReranker",
    "HybridMatcher",
]
