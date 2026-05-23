"""Weighted scorer that fuses multiple matching signals into a final score.

Inputs are normalized to ``[0, 1]`` and combined as a convex combination
(weights sum to 1.0).  Missing signals are simply ignored and the remaining
weights are re-normalized so the result is always interpretable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ScoringWeights:
    """Default fusion weights, tuned empirically on the training set."""

    semantic: float = 0.30
    cross_encoder: float = 0.25
    skill_overlap: float = 0.20
    experience: float = 0.10
    education: float = 0.05
    language: float = 0.05
    llm: float = 0.05

    def to_dict(self) -> Dict[str, float]:
        return {
            "semantic": self.semantic,
            "cross_encoder": self.cross_encoder,
            "skill_overlap": self.skill_overlap,
            "experience": self.experience,
            "education": self.education,
            "language": self.language,
            "llm": self.llm,
        }


@dataclass
class ScoringSignals:
    semantic: Optional[float] = None
    cross_encoder: Optional[float] = None
    skill_overlap: Optional[float] = None
    experience: Optional[float] = None
    education: Optional[float] = None
    language: Optional[float] = None
    llm: Optional[float] = None

    def to_dict(self) -> Dict[str, float]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class ScoreBreakdown:
    final_score: float
    weighted_contributions: Dict[str, float] = field(default_factory=dict)
    raw_signals: Dict[str, float] = field(default_factory=dict)
    effective_weights: Dict[str, float] = field(default_factory=dict)


class WeightedScorer:
    """Convex combination of available signals with renormalization."""

    def __init__(self, weights: Optional[ScoringWeights] = None) -> None:
        self.weights = weights or ScoringWeights()

    def score(self, signals: ScoringSignals) -> ScoreBreakdown:
        raw = signals.to_dict()
        if not raw:
            return ScoreBreakdown(final_score=0.0)

        weight_map = self.weights.to_dict()
        available = {k: weight_map[k] for k in raw if k in weight_map}
        total_w = sum(available.values())
        if total_w == 0:
            return ScoreBreakdown(final_score=0.0, raw_signals=raw)

        effective = {k: w / total_w for k, w in available.items()}
        contribs = {k: max(0.0, min(1.0, raw[k])) * effective[k] for k in available}
        final = sum(contribs.values())

        return ScoreBreakdown(
            final_score=max(0.0, min(1.0, final)),
            weighted_contributions=contribs,
            raw_signals=raw,
            effective_weights=effective,
        )
