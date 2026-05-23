"""Unit tests for the scoring layer."""
from __future__ import annotations

import pytest

from ai_pipeline.scoring.business_rules import BusinessContext, BusinessRulesEngine
from ai_pipeline.scoring.decision_engine import Decision, DecisionEngine
from ai_pipeline.scoring.weighted_scorer import ScoringSignals, ScoringWeights, WeightedScorer


def test_weighted_scorer_with_all_signals():
    scorer = WeightedScorer()
    signals = ScoringSignals(
        semantic=0.8,
        cross_encoder=0.7,
        skill_overlap=0.9,
        experience=1.0,
        education=1.0,
        language=1.0,
    )
    result = scorer.score(signals)
    assert 0.7 <= result.final_score <= 0.95
    assert sum(result.effective_weights.values()) == pytest.approx(1.0)


def test_weighted_scorer_handles_missing_signals():
    scorer = WeightedScorer()
    # Only semantic provided
    result = scorer.score(ScoringSignals(semantic=0.5))
    assert result.final_score == pytest.approx(0.5)


def test_weighted_scorer_empty_returns_zero():
    scorer = WeightedScorer()
    assert scorer.score(ScoringSignals()).final_score == 0.0


def test_business_rules_blocker_on_low_skill_coverage():
    engine = BusinessRulesEngine()
    ctx = BusinessContext(
        candidate_skills={"javascript"},
        required_skills={"python", "fastapi", "postgresql", "docker"},
    )
    score, rules = engine.apply(0.9, ctx)
    assert score <= 0.5
    assert any(r.is_blocker for r in rules)


def test_business_rules_no_penalty_when_satisfied():
    engine = BusinessRulesEngine()
    ctx = BusinessContext(
        candidate_skills={"python", "fastapi", "postgresql", "docker"},
        required_skills={"python", "fastapi", "postgresql", "docker"},
        candidate_years_exp=3,
        required_years_exp=2,
    )
    score, rules = engine.apply(0.9, ctx)
    assert score == pytest.approx(0.9, abs=0.05)
    assert not any(r.is_blocker for r in rules)


def test_decision_engine_classifies_correctly():
    engine = DecisionEngine()

    # High score → accepted
    res = engine.decide(ScoringSignals(semantic=0.9, skill_overlap=0.9, experience=0.9))
    assert res.decision == Decision.ACCEPTED

    # Mid score → to_review
    res = engine.decide(ScoringSignals(semantic=0.6, skill_overlap=0.55, experience=0.6))
    assert res.decision == Decision.TO_REVIEW

    # Low score → rejected
    res = engine.decide(ScoringSignals(semantic=0.2, skill_overlap=0.1, experience=0.3))
    assert res.decision == Decision.REJECTED
