"""End-to-end pipeline orchestrator.

Wires together every stage of the official PFA pipeline::

    CV brut → Extraction NLP → Structuration → Feature Engineering
            → Matching → Scoring → Décision

Each stage is optional and injectable to keep the orchestrator testable
and to allow swapping implementations (e.g. FAISS ↔ Chroma, classical ↔
LLM scoring).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from ..config import PipelineConfig
from ..explainability.explainer import Explanation, RuleBasedExplainer
from ..explainability.llm_explainer import LLMExplainer
from ..feature_engineering.semantic_features import SemanticFeatureExtractor
from ..matching.hybrid_matcher import HybridMatcher
from ..preprocessing.cv_cleaner import CVCleaner
from ..preprocessing.data_normalizer import DataNormalizer, NormalizedCandidate
from ..preprocessing.skill_normalizer import SkillNormalizer
from ..scoring.business_rules import BusinessContext, BusinessRulesEngine
from ..scoring.decision_engine import DecisionEngine, DecisionResult
from ..scoring.weighted_scorer import ScoringSignals

logger = logging.getLogger(__name__)


@dataclass
class MatchingRequest:
    """Inputs the orchestrator needs for a single CV ↔ Job evaluation."""

    cv_text: str
    job_text: str
    job_required_skills: Optional[Set[str]] = None
    job_nice_to_have_skills: Optional[Set[str]] = None
    job_min_years: float = 0.0
    job_min_edu_level: int = 0
    job_required_languages: Optional[Dict[str, str]] = None
    job_location: Optional[str] = None
    remote_ok: bool = True
    use_llm: bool = False


@dataclass
class MatchingResponse:
    decision: DecisionResult
    explanation: Explanation
    normalized_candidate: Optional[NormalizedCandidate] = None
    timings_ms: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.to_dict(),
            "explanation": self.explanation.to_dict(),
            "normalized_candidate": (
                self.normalized_candidate.to_dict()
                if self.normalized_candidate
                else None
            ),
            "timings_ms": self.timings_ms,
        }


class MatchingOrchestrator:
    """Run the full PFA pipeline for one (CV, Job) pair."""

    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
        semantic_extractor: Optional[SemanticFeatureExtractor] = None,
        hybrid_matcher: Optional[HybridMatcher] = None,
        decision_engine: Optional[DecisionEngine] = None,
        llm_explainer: Optional[LLMExplainer] = None,
    ) -> None:
        self.config = config or PipelineConfig()
        self.cv_cleaner = CVCleaner()
        self.skill_normalizer = SkillNormalizer()
        self.data_normalizer = DataNormalizer(skill_normalizer=self.skill_normalizer)
        self.semantic_extractor = semantic_extractor or SemanticFeatureExtractor(
            model_name=self.config.embedding.model_name,
            cache_dir=self.config.embedding.cache_dir,
        )
        self.hybrid_matcher = hybrid_matcher
        self.decision_engine = decision_engine or DecisionEngine()
        self.rule_explainer = RuleBasedExplainer()
        self.llm_explainer = llm_explainer

    # ------------------------------------------------------------------ #
    # Stage 1+2: cleaning & normalization
    # ------------------------------------------------------------------ #
    def _normalize_candidate(self, cv_text: str) -> NormalizedCandidate:
        cleaned = self.cv_cleaner.clean_text_only(cv_text)
        return self.data_normalizer.normalize_from_text(cleaned)

    # ------------------------------------------------------------------ #
    # Stage 3: feature engineering — semantic embeddings
    # ------------------------------------------------------------------ #
    def _semantic_similarity(self, cv_text: str, job_text: str) -> float:
        return float(self.semantic_extractor.similarity(cv_text, job_text))

    # ------------------------------------------------------------------ #
    # Stage 4: matching + 5: scoring → decision
    # ------------------------------------------------------------------ #
    def _build_signals(
        self,
        cv_text: str,
        job_text: str,
        candidate: NormalizedCandidate,
        req: MatchingRequest,
    ) -> ScoringSignals:
        semantic = self._semantic_similarity(cv_text, job_text)

        required = req.job_required_skills or set()
        candidate_skills = set(candidate.skills)
        if required:
            overlap = len(candidate_skills & required) / len(required)
        else:
            overlap = 0.0

        # Experience / education / language sub-scores
        exp_score = 1.0
        if req.job_min_years > 0:
            exp_score = min(1.0, candidate.years_experience / req.job_min_years)

        edu_score = 1.0
        if req.job_min_edu_level > 0:
            edu_score = min(1.0, candidate.education_level / req.job_min_edu_level)

        lang_score = 1.0
        if req.job_required_languages:
            matches = sum(
                1 for lang in req.job_required_languages if lang in candidate.languages
            )
            lang_score = matches / len(req.job_required_languages)

        return ScoringSignals(
            semantic=semantic,
            skill_overlap=overlap,
            experience=exp_score,
            education=edu_score,
            language=lang_score,
        )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def match(self, request: MatchingRequest) -> MatchingResponse:
        timings: Dict[str, float] = {}

        t0 = time.time()
        candidate = self._normalize_candidate(request.cv_text)
        timings["normalize_ms"] = (time.time() - t0) * 1000

        t0 = time.time()
        signals = self._build_signals(
            request.cv_text, request.job_text, candidate, request
        )
        timings["features_ms"] = (time.time() - t0) * 1000

        t0 = time.time()
        ctx = BusinessContext(
            candidate_skills=set(candidate.skills),
            required_skills=request.job_required_skills or set(),
            nice_to_have_skills=request.job_nice_to_have_skills or set(),
            candidate_years_exp=candidate.years_experience,
            required_years_exp=request.job_min_years,
            candidate_edu_level=candidate.education_level,
            required_edu_level=request.job_min_edu_level,
            candidate_languages=candidate.languages,
            required_languages=request.job_required_languages or {},
            candidate_location=candidate.location,
            job_location=request.job_location,
            remote_ok=request.remote_ok,
        )
        decision = self.decision_engine.decide(signals, ctx)
        timings["decision_ms"] = (time.time() - t0) * 1000

        # Explanation (rule-based by default, LLM-enhanced if requested)
        t0 = time.time()
        if request.use_llm and self.llm_explainer is not None:
            llm_res = self.llm_explainer.explain(
                cv_text=request.cv_text,
                job_text=request.job_text,
                decision=decision,
                candidate_skills=set(candidate.skills),
                required_skills=request.job_required_skills or set(),
                nice_to_have_skills=request.job_nice_to_have_skills,
            )
            explanation = llm_res.rule_based
            explanation.summary = llm_res.final_rationale or explanation.summary
        else:
            explanation = self.rule_explainer.explain(
                decision=decision,
                candidate_skills=set(candidate.skills),
                required_skills=request.job_required_skills or set(),
                nice_to_have_skills=request.job_nice_to_have_skills,
            )
        timings["explanation_ms"] = (time.time() - t0) * 1000

        return MatchingResponse(
            decision=decision,
            explanation=explanation,
            normalized_candidate=candidate,
            timings_ms=timings,
        )

    def batch_match(self, requests: List[MatchingRequest]) -> List[MatchingResponse]:
        return [self.match(r) for r in requests]
