"""Rule-based explainer.

Generates a structured, recruiter-facing explanation from the decision
result.  This explainer does NOT require an LLM and is deterministic;
use :mod:`ai_pipeline.explainability.llm_explainer` for richer prose.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

from ..scoring.decision_engine import DecisionResult


@dataclass
class Explanation:
    summary: str
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    rule_explanations: List[str] = field(default_factory=list)
    top_contributors: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "matched_skills": self.matched_skills,
            "missing_skills": self.missing_skills,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "rule_explanations": self.rule_explanations,
            "top_contributors": self.top_contributors,
        }


class RuleBasedExplainer:
    """Build a recruiter-facing explanation from a :class:`DecisionResult`."""

    def explain(
        self,
        decision: DecisionResult,
        candidate_skills: Set[str],
        required_skills: Set[str],
        nice_to_have_skills: Set[str] = None,
    ) -> Explanation:
        nice_to_have_skills = nice_to_have_skills or set()
        matched = sorted(candidate_skills & required_skills)
        missing = sorted(required_skills - candidate_skills)
        bonus = sorted(candidate_skills & nice_to_have_skills)

        # Top signal contributors (sorted by weighted contribution)
        contribs = decision.breakdown.weighted_contributions
        top = sorted(contribs.items(), key=lambda kv: kv[1], reverse=True)[:3]
        top_contrib = [
            {
                "signal": name,
                "contribution": round(val, 4),
                "raw_value": round(decision.breakdown.raw_signals.get(name, 0.0), 4),
            }
            for name, val in top
        ]

        strengths: List[str] = []
        weaknesses: List[str] = []
        if matched:
            strengths.append(
                f"Couvre {len(matched)}/{len(required_skills)} compétences requises"
                if required_skills
                else f"{len(matched)} compétences pertinentes identifiées"
            )
        if bonus:
            strengths.append(f"Compétences bonus: {', '.join(bonus[:5])}")
        if missing:
            weaknesses.append(
                f"Compétences manquantes: {', '.join(missing[:5])}"
                + (f" (+{len(missing) - 5} autres)" if len(missing) > 5 else "")
            )

        # Add rule-based weaknesses/strengths
        rule_explanations = []
        for r in decision.rule_results:
            rule_explanations.append(f"[{r.name}] {r.reason}")
            if r.multiplier < 0.9:
                weaknesses.append(r.reason)
            elif r.multiplier >= 1.0 and r.name in ("experience", "education"):
                strengths.append(r.reason)

        summary = self._build_summary(decision, matched, missing)

        return Explanation(
            summary=summary,
            matched_skills=matched,
            missing_skills=missing,
            strengths=strengths,
            weaknesses=weaknesses,
            rule_explanations=rule_explanations,
            top_contributors=top_contrib,
        )

    def _build_summary(self, decision: DecisionResult, matched, missing) -> str:
        verdict = decision.label_fr
        score_pct = int(round(decision.final_score * 100))
        n_matched = len(matched)
        n_missing = len(missing)

        if decision.decision.value == "accepted":
            return (
                f"{verdict} ({score_pct}%) — Profil aligné avec l'offre. "
                f"{n_matched} compétences correspondent, {n_missing} manquantes. "
                "Le candidat peut être contacté pour un entretien."
            )
        if decision.decision.value == "to_review":
            return (
                f"{verdict} ({score_pct}%) — Profil intermédiaire. "
                f"{n_matched} compétences correspondent mais {n_missing} manquent. "
                "Examen manuel recommandé."
            )
        return (
            f"{verdict} ({score_pct}%) — Le profil ne correspond pas aux exigences. "
            f"Seulement {n_matched} compétences sur les requises sont présentes."
        )
