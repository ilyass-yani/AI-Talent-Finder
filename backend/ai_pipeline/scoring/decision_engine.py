"""Decision engine: final verdict from raw signals + business rules.

Produces a 3-class decision (accepted / to_review / rejected) using
configurable thresholds, after applying business rules to the weighted
ML score.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .business_rules import BusinessContext, BusinessRulesEngine, RuleResult
from .weighted_scorer import ScoreBreakdown, ScoringSignals, ScoringWeights, WeightedScorer


class Decision(str, Enum):
    ACCEPTED = "accepted"
    TO_REVIEW = "to_review"
    REJECTED = "rejected"


@dataclass
class DecisionConfig:
    accept_threshold: float = 0.75
    review_threshold: float = 0.50


@dataclass
class DecisionResult:
    decision: Decision
    final_score: float
    raw_ml_score: float
    rules_multiplier: float
    breakdown: ScoreBreakdown
    rule_results: List[RuleResult] = field(default_factory=list)
    label_fr: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value,
            "label_fr": self.label_fr,
            "final_score": round(self.final_score, 4),
            "raw_ml_score": round(self.raw_ml_score, 4),
            "rules_multiplier": round(self.rules_multiplier, 4),
            "weighted_contributions": {
                k: round(v, 4) for k, v in self.breakdown.weighted_contributions.items()
            },
            "raw_signals": {k: round(v, 4) for k, v in self.breakdown.raw_signals.items()},
            "effective_weights": self.breakdown.effective_weights,
            "rules": [
                {
                    "name": r.name,
                    "multiplier": round(r.multiplier, 4),
                    "reason": r.reason,
                    "is_blocker": r.is_blocker,
                }
                for r in self.rule_results
            ],
        }


class DecisionEngine:
    def __init__(
        self,
        weights: Optional[ScoringWeights] = None,
        config: Optional[DecisionConfig] = None,
        rules_engine: Optional[BusinessRulesEngine] = None,
    ) -> None:
        self.scorer = WeightedScorer(weights)
        self.config = config or DecisionConfig()
        self.rules = rules_engine or BusinessRulesEngine()

    def decide(
        self,
        signals: ScoringSignals,
        context: Optional[BusinessContext] = None,
    ) -> DecisionResult:
        breakdown = self.scorer.score(signals)
        raw = breakdown.final_score

        if context is None:
            adjusted, rule_results = raw, []
        else:
            adjusted, rule_results = self.rules.apply(raw, context)

        mult = adjusted / raw if raw > 0 else 1.0

        if adjusted >= self.config.accept_threshold:
            decision, label = Decision.ACCEPTED, "Accepté"
        elif adjusted >= self.config.review_threshold:
            decision, label = Decision.TO_REVIEW, "À revoir"
        else:
            decision, label = Decision.REJECTED, "Rejeté"

        return DecisionResult(
            decision=decision,
            final_score=adjusted,
            raw_ml_score=raw,
            rules_multiplier=mult,
            breakdown=breakdown,
            rule_results=rule_results,
            label_fr=label,
        )
