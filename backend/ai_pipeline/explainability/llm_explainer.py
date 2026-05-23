"""LLM-based explainer.

Uses a (Q)LoRA-fine-tuned LLM (via :class:`MatchingLLM`) to produce a
recruiter-friendly natural-language justification of a matching decision.

If the LLM is unavailable, falls back gracefully to the rule-based
explanation produced by :class:`RuleBasedExplainer`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..llm.inference import InferenceResult, MatchingLLM
from .explainer import Explanation, RuleBasedExplainer

logger = logging.getLogger(__name__)


@dataclass
class LLMExplanationResult:
    rule_based: Explanation
    llm_result: Optional[InferenceResult] = None
    final_rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        out = self.rule_based.to_dict()
        if self.llm_result is not None:
            out["llm"] = self.llm_result.to_dict()
        out["final_rationale"] = self.final_rationale
        return out


class LLMExplainer:
    """Combine rule-based + LLM-generated explanations."""

    def __init__(
        self,
        llm: Optional[MatchingLLM] = None,
        fallback_to_rules: bool = True,
    ) -> None:
        self.llm = llm
        self.fallback = fallback_to_rules
        self.rule_explainer = RuleBasedExplainer()

    def explain(
        self,
        cv_text: str,
        job_text: str,
        decision,
        candidate_skills,
        required_skills,
        nice_to_have_skills=None,
    ) -> LLMExplanationResult:
        rule_exp = self.rule_explainer.explain(
            decision=decision,
            candidate_skills=candidate_skills,
            required_skills=required_skills,
            nice_to_have_skills=nice_to_have_skills,
        )

        llm_res: Optional[InferenceResult] = None
        if self.llm is not None:
            try:
                llm_res = self.llm.score(cv_text=cv_text, job_text=job_text)
            except Exception as exc:  # pragma: no cover - runtime dependent
                logger.warning("LLM explanation failed: %s", exc)
                if not self.fallback:
                    raise

        final = llm_res.rationale if llm_res and llm_res.rationale else rule_exp.summary
        return LLMExplanationResult(
            rule_based=rule_exp,
            llm_result=llm_res,
            final_rationale=final,
        )
