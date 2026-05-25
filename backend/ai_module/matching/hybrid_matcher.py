"""Hybrid matcher combining semantic, BERT classifier, skill cosine, and business signals.

Weight breakdown (defaults from training config):
  semantic          0.35  — sentence-transformer cosine similarity on full texts
  cross_encoder     0.20  — deeper semantic re-ranking (falls back to semantic when unavailable)
  bert_classifier   0.25  — fine-tuned camembert compatibility classifier
  skill_cosine      0.12  — binary skill-vector cosine (CosineScorer)
  business          0.08  — structured rules: experience, location, availability

All weights must sum to 1.0; HybridConfig normalizes automatically if they don't.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class HybridConfig:
    weight_semantic: float = 0.35
    weight_cross_encoder: float = 0.20
    weight_bert_classifier: float = 0.25
    weight_skill_cosine: float = 0.12
    weight_business: float = 0.08

    def __post_init__(self) -> None:
        total = (
            self.weight_semantic
            + self.weight_cross_encoder
            + self.weight_bert_classifier
            + self.weight_skill_cosine
            + self.weight_business
        )
        if total <= 0:
            raise ValueError("HybridConfig: all weights are zero.")
        if abs(total - 1.0) > 1e-6:
            logger.debug("HybridConfig: weights sum to %.4f — normalizing.", total)
            self.weight_semantic /= total
            self.weight_cross_encoder /= total
            self.weight_bert_classifier /= total
            self.weight_skill_cosine /= total
            self.weight_business /= total


class HybridMatcher:
    """Combine multiple matchers into a single weighted score (0–100).

    Parameters
    ----------
    config:
        Weight configuration.
    bert_classifier:
        Pre-loaded BertClassifierAdapter. If None, the adapter is lazy-loaded
        from the default model directory (backend/models/bert_matching/).
    """

    def __init__(
        self,
        config: Optional[HybridConfig] = None,
        bert_classifier=None,
    ) -> None:
        self.config = config or HybridConfig()
        self._bert = bert_classifier  # may be None; resolved lazily

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score(
        self,
        candidate_text: str,
        job_text: str,
        candidate_skills: Optional[List[str]] = None,
        criteria_skills: Optional[Dict[str, float]] = None,
        business_signals: Optional[Dict[str, object]] = None,
    ) -> Dict[str, object]:
        """Return a hybrid score dict.

        Parameters
        ----------
        candidate_text:
            Free-text CV / candidate profile.
        job_text:
            Free-text job description / offer.
        candidate_skills:
            List of skill names the candidate has.
        criteria_skills:
            Dict {skill_name: weight_0_to_100} from recruiter criteria.
        business_signals:
            Optional structured signals, e.g.::

                {
                    "years_experience": 5,
                    "required_experience": 3,
                    "location_match": True,
                    "available": True,
                }

        Returns
        -------
        dict with keys: score (0–100), component_scores, weights_used
        """
        cfg = self.config
        components: Dict[str, float] = {}

        # 1. Semantic score
        components["semantic"] = self._semantic_score(candidate_text, job_text)

        # 2. Cross-encoder score (fallback to semantic when unavailable)
        components["cross_encoder"] = self._cross_encoder_score(candidate_text, job_text)

        # 3. BERT classifier score
        components["bert_classifier"] = self._bert_score(candidate_text, job_text)

        # 4. Skill cosine score
        components["skill_cosine"] = self._skill_cosine_score(
            candidate_skills or [], criteria_skills or {}
        )

        # 5. Business rules score
        components["business"] = self._business_score(business_signals or {})

        # Weighted sum
        raw = (
            cfg.weight_semantic * components["semantic"]
            + cfg.weight_cross_encoder * components["cross_encoder"]
            + cfg.weight_bert_classifier * components["bert_classifier"]
            + cfg.weight_skill_cosine * components["skill_cosine"]
            + cfg.weight_business * components["business"]
        )
        final_score = float(np.clip(raw * 100, 0.0, 100.0))

        return {
            "score": final_score,
            "component_scores": {k: round(v, 4) for k, v in components.items()},
            "weights_used": {
                "semantic": cfg.weight_semantic,
                "cross_encoder": cfg.weight_cross_encoder,
                "bert_classifier": cfg.weight_bert_classifier,
                "skill_cosine": cfg.weight_skill_cosine,
                "business": cfg.weight_business,
            },
        }

    # ------------------------------------------------------------------
    # Component scorers
    # ------------------------------------------------------------------

    def _semantic_score(self, candidate_text: str, job_text: str) -> float:
        try:
            from ai_module.matching.semantic_matcher import SemanticSkillMatcher

            return SemanticSkillMatcher.semantic_similarity(candidate_text, job_text)
        except Exception as exc:
            logger.debug("Semantic scorer unavailable: %s", exc)
            return 0.0

    def _cross_encoder_score(self, candidate_text: str, job_text: str) -> float:
        """Attempt a cross-encoder pass; fall back to semantic similarity."""
        try:
            from sentence_transformers import CrossEncoder

            if not hasattr(self, "_cross_encoder_model"):
                self._cross_encoder_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            score = self._cross_encoder_model.predict([[candidate_text, job_text]])[0]
            # ms-marco scores are logits; apply sigmoid
            import math

            return float(np.clip(1 / (1 + math.exp(-score)), 0.0, 1.0))
        except Exception:
            # Graceful fallback to standard semantic similarity
            return self._semantic_score(candidate_text, job_text)

    def _bert_score(self, candidate_text: str, job_text: str) -> float:
        bert = self._get_bert()
        if bert is None:
            return 0.0
        return bert.predict_score(candidate_text, job_text)

    def _skill_cosine_score(
        self,
        candidate_skills: List[str],
        criteria_skills: Dict[str, float],
    ) -> float:
        if not candidate_skills or not criteria_skills:
            return 0.0
        try:
            from ai_module.matching.scorer import CosineScorer

            all_skills = list(criteria_skills.keys())
            result = CosineScorer.calculate_match_score(
                candidate_skills, criteria_skills, all_skills
            )
            return float(result["score"]) / 100.0
        except Exception as exc:
            logger.debug("Skill cosine scorer failed: %s", exc)
            return 0.0

    def _business_score(self, signals: Dict[str, object]) -> float:
        """Simple rules-based business score in [0, 1]."""
        if not signals:
            return 0.5  # neutral when no signals provided

        score = 0.0
        count = 0

        # Experience
        years_exp = signals.get("years_experience")
        required_exp = signals.get("required_experience")
        if years_exp is not None and required_exp is not None:
            try:
                ratio = float(years_exp) / max(float(required_exp), 1.0)
                score += float(np.clip(ratio, 0.0, 1.0))
            except (TypeError, ValueError):
                score += 0.5
            count += 1

        # Location match
        location_match = signals.get("location_match")
        if location_match is not None:
            score += 1.0 if location_match else 0.2
            count += 1

        # Availability
        available = signals.get("available")
        if available is not None:
            score += 1.0 if available else 0.0
            count += 1

        return float(np.clip(score / max(count, 1), 0.0, 1.0))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_bert(self):
        if self._bert is not None:
            return self._bert
        try:
            from ai_module.matching.bert_classifier_adapter import get_default_adapter

            self._bert = get_default_adapter()
        except Exception as exc:
            logger.warning("Could not load BertClassifierAdapter: %s", exc)
            self._bert = None
        return self._bert
