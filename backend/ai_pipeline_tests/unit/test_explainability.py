"""Unit tests for the explainability layer."""
from __future__ import annotations

from ai_pipeline.explainability.explainer import RuleBasedExplainer
from ai_pipeline.scoring.business_rules import BusinessContext
from ai_pipeline.scoring.decision_engine import DecisionEngine
from ai_pipeline.scoring.weighted_scorer import ScoringSignals


def _make_decision(score: float = 0.8):
    engine = DecisionEngine()
    sig = ScoringSignals(semantic=score, skill_overlap=score, experience=score)
    return engine.decide(sig, BusinessContext(
        candidate_skills={"python", "fastapi"},
        required_skills={"python", "fastapi", "postgresql"},
    ))


def test_explainer_lists_matched_and_missing_skills():
    exp = RuleBasedExplainer()
    decision = _make_decision(0.7)
    result = exp.explain(
        decision=decision,
        candidate_skills={"python", "fastapi", "docker"},
        required_skills={"python", "fastapi", "postgresql"},
        nice_to_have_skills={"docker"},
    )
    assert "python" in result.matched_skills
    assert "fastapi" in result.matched_skills
    assert "postgresql" in result.missing_skills
    assert result.summary  # non-empty


def test_explainer_summary_reflects_decision_label():
    exp = RuleBasedExplainer()
    for raw in (0.9, 0.6, 0.2):
        decision = _make_decision(raw)
        result = exp.explain(
            decision=decision,
            candidate_skills={"python"},
            required_skills={"python"},
        )
        # The decision label appears in the summary
        assert decision.label_fr.lower() in result.summary.lower()


def test_explainer_top_contributors_sorted():
    exp = RuleBasedExplainer()
    decision = _make_decision(0.8)
    result = exp.explain(
        decision=decision,
        candidate_skills={"python", "fastapi"},
        required_skills={"python", "fastapi"},
    )
    contribs = [c["contribution"] for c in result.top_contributors]
    assert contribs == sorted(contribs, reverse=True)
