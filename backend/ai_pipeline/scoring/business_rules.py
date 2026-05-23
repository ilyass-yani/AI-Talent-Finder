"""Business rules for matching decisions.

These rules encode domain knowledge that ML scores alone cannot capture:
hard-skill blockers, seniority gaps, language requirements, location, etc.
Each rule contributes a multiplicative penalty/bonus to the raw score.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class BusinessContext:
    """All information business rules can inspect about a candidate↔job pair."""

    candidate_skills: Set[str] = field(default_factory=set)
    required_skills: Set[str] = field(default_factory=set)
    nice_to_have_skills: Set[str] = field(default_factory=set)
    candidate_years_exp: float = 0.0
    required_years_exp: float = 0.0
    candidate_edu_level: int = 0
    required_edu_level: int = 0
    candidate_languages: Dict[str, str] = field(default_factory=dict)
    required_languages: Dict[str, str] = field(default_factory=dict)
    candidate_location: Optional[str] = None
    job_location: Optional[str] = None
    remote_ok: bool = True


@dataclass
class RuleResult:
    name: str
    multiplier: float
    reason: str
    is_blocker: bool = False


# CECRL ordering for language proficiency comparison
_CECRL_RANK = {"a1": 1, "a2": 2, "b1": 3, "b2": 4, "c1": 5, "c2": 6, "native": 7}


def _lang_rank(level: str) -> int:
    return _CECRL_RANK.get((level or "").lower().strip(), 0)


class BusinessRulesEngine:
    """Apply ordered business rules to a raw match score."""

    def __init__(
        self,
        min_hard_skills_ratio: float = 0.5,
        hard_skill_blocker_threshold: float = 0.3,
        seniority_tolerance_years: float = 1.0,
        education_penalty: float = 0.15,
        language_penalty: float = 0.20,
        location_penalty: float = 0.10,
    ) -> None:
        self.min_hard_skills_ratio = min_hard_skills_ratio
        self.hard_skill_blocker_threshold = hard_skill_blocker_threshold
        self.seniority_tolerance_years = seniority_tolerance_years
        self.education_penalty = education_penalty
        self.language_penalty = language_penalty
        self.location_penalty = location_penalty

    # ------------------------------------------------------------------ #
    # Individual rules
    # ------------------------------------------------------------------ #
    def _rule_hard_skills(self, ctx: BusinessContext) -> RuleResult:
        if not ctx.required_skills:
            return RuleResult("hard_skills", 1.0, "Aucune compétence requise spécifiée.")
        matched = ctx.candidate_skills & ctx.required_skills
        ratio = len(matched) / max(len(ctx.required_skills), 1)
        if ratio < self.hard_skill_blocker_threshold:
            return RuleResult(
                "hard_skills",
                0.4,
                f"Couverture critique: seulement {len(matched)}/{len(ctx.required_skills)} "
                f"compétences clés couvertes ({ratio:.0%}).",
                is_blocker=True,
            )
        if ratio < self.min_hard_skills_ratio:
            return RuleResult(
                "hard_skills",
                0.75,
                f"Couverture partielle: {len(matched)}/{len(ctx.required_skills)} "
                f"compétences clés ({ratio:.0%}).",
            )
        return RuleResult(
            "hard_skills",
            1.0,
            f"Bonne couverture: {len(matched)}/{len(ctx.required_skills)} ({ratio:.0%}).",
        )

    def _rule_experience(self, ctx: BusinessContext) -> RuleResult:
        if ctx.required_years_exp <= 0:
            return RuleResult("experience", 1.0, "Aucune exigence d'expérience.")
        gap = ctx.required_years_exp - ctx.candidate_years_exp
        if gap <= self.seniority_tolerance_years:
            return RuleResult(
                "experience",
                1.0,
                f"Expérience suffisante ({ctx.candidate_years_exp:.0f} ans vs "
                f"{ctx.required_years_exp:.0f} ans requis).",
            )
        if gap <= 3:
            return RuleResult(
                "experience",
                0.85,
                f"Léger manque d'expérience ({gap:.0f} ans de moins).",
            )
        return RuleResult(
            "experience",
            0.6,
            f"Manque significatif d'expérience ({gap:.0f} ans).",
        )

    def _rule_education(self, ctx: BusinessContext) -> RuleResult:
        if ctx.required_edu_level <= 0:
            return RuleResult("education", 1.0, "Aucun diplôme requis.")
        if ctx.candidate_edu_level >= ctx.required_edu_level:
            return RuleResult("education", 1.0, "Niveau d'études satisfait.")
        gap = ctx.required_edu_level - ctx.candidate_edu_level
        return RuleResult(
            "education",
            1.0 - self.education_penalty * gap,
            f"Niveau d'études inférieur ({gap} niveau(x) en dessous).",
        )

    def _rule_languages(self, ctx: BusinessContext) -> RuleResult:
        if not ctx.required_languages:
            return RuleResult("languages", 1.0, "Aucune exigence linguistique.")
        missing = []
        downgraded = []
        for lang, req_level in ctx.required_languages.items():
            cand_level = ctx.candidate_languages.get(lang, "")
            if not cand_level:
                missing.append(lang)
            elif _lang_rank(cand_level) < _lang_rank(req_level):
                downgraded.append(f"{lang} ({cand_level}/{req_level})")
        if missing:
            return RuleResult(
                "languages",
                1.0 - self.language_penalty,
                f"Langues manquantes: {', '.join(missing)}.",
            )
        if downgraded:
            return RuleResult(
                "languages",
                1.0 - self.language_penalty / 2,
                f"Niveau insuffisant: {', '.join(downgraded)}.",
            )
        return RuleResult("languages", 1.0, "Exigences linguistiques satisfaites.")

    def _rule_location(self, ctx: BusinessContext) -> RuleResult:
        if ctx.remote_ok or not ctx.job_location or not ctx.candidate_location:
            return RuleResult("location", 1.0, "Localisation non bloquante.")
        if ctx.candidate_location.strip().lower() == ctx.job_location.strip().lower():
            return RuleResult("location", 1.0, "Même localisation.")
        return RuleResult(
            "location",
            1.0 - self.location_penalty,
            f"Localisation différente ({ctx.candidate_location} vs {ctx.job_location}).",
        )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def evaluate(self, ctx: BusinessContext) -> List[RuleResult]:
        return [
            self._rule_hard_skills(ctx),
            self._rule_experience(ctx),
            self._rule_education(ctx),
            self._rule_languages(ctx),
            self._rule_location(ctx),
        ]

    def apply(self, raw_score: float, ctx: BusinessContext) -> Tuple[float, List[RuleResult]]:
        """Apply all rules; return (adjusted_score, rule_results)."""
        results = self.evaluate(ctx)
        score = raw_score
        for r in results:
            score *= r.multiplier
        # Blockers cap the score at 0.5
        if any(r.is_blocker for r in results):
            score = min(score, 0.5)
        return max(0.0, min(1.0, score)), results
