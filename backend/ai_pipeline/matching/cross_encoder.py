"""Cross-Encoder pour le re-ranking des candidats.

Pipeline 2 étages (standard en IR moderne) :
    1. Bi-Encoder : récupère top-K (50-200) candidats rapidement
    2. Cross-Encoder : re-classe ces K candidats avec une précision plus fine

Le cross-encoder lit la PAIRE (CV, Job) ensemble dans le transformer,
ce qui donne un score plus précis mais avec un coût O(K) par requête
(vs O(1) pour bi-encoder).

Modèles recommandés :
    - cross-encoder/ms-marco-MiniLM-L-6-v2  (rapide, EN)
    - cross-encoder/ms-marco-MiniLM-L-12-v2 (qualité+, EN)
    - cross-encoder/stsb-roberta-base       (similarité STS)
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np

from ai_pipeline.matching.base import BaseMatcher, MatchCandidate, MatchResult
from ai_pipeline.preprocessing.skill_normalizer import SkillNormalizer

try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False


class CrossEncoderReranker(BaseMatcher):
    """Re-ranker basé sur Cross-Encoder.

    Usage typique :
        bi_results = bi_encoder.search(job, top_k=100)
        final = cross_reranker.rerank(job, bi_results, candidates)
    """

    name = "cross_encoder"

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        batch_size: int = 32,
        max_length: int = 512,
    ) -> None:
        if not CROSS_ENCODER_AVAILABLE:
            raise RuntimeError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            )
        self.model_name = model_name
        self.batch_size = batch_size
        self.max_length = max_length
        self._model = None
        self.skill_normalizer = SkillNormalizer()

    @property
    def model(self) -> "CrossEncoder":
        if self._model is None:
            self._model = CrossEncoder(self.model_name, max_length=self.max_length)
        return self._model

    # ------------------------------------------------------------------ #
    # Scoring
    # ------------------------------------------------------------------ #

    def score_pair(self, cv_text: str, job_text: str) -> float:
        scores = self.model.predict(
            [(cv_text, job_text)],
            batch_size=1,
            show_progress_bar=False,
        )
        # ms-marco models renvoient un raw score (logit), pas une proba.
        # On applique sigmoid pour avoir 0..1.
        return float(1.0 / (1.0 + np.exp(-scores[0])))

    def score_pairs(self, pairs: Sequence[Tuple[str, str]]) -> np.ndarray:
        raw = self.model.predict(
            list(pairs),
            batch_size=self.batch_size,
            show_progress_bar=False,
        )
        return 1.0 / (1.0 + np.exp(-np.array(raw)))

    # ------------------------------------------------------------------ #
    # Re-ranking
    # ------------------------------------------------------------------ #

    def rerank(
        self,
        job_text: str,
        candidates: Sequence[MatchCandidate],
        job_skills: Optional[List[str]] = None,
        top_k: Optional[int] = None,
    ) -> List[MatchResult]:
        """Re-classe une liste de candidats selon le cross-encoder."""
        if not candidates:
            return []

        pairs = [(c.text, job_text) for c in candidates]
        scores = self.score_pairs(pairs)

        job_norm = set(self.skill_normalizer.normalize_list(job_skills or []))
        results: List[MatchResult] = []
        for candidate, score in zip(candidates, scores):
            cv_norm = set(self.skill_normalizer.normalize_list(candidate.skills))
            results.append(MatchResult(
                candidate_id=candidate.id,
                score=round(float(score), 4),
                matched_skills=sorted(cv_norm & job_norm),
                missing_skills=sorted(job_norm - cv_norm),
                extra_skills=sorted(cv_norm - job_norm),
                details={
                    "method": "cross_encoder_rerank",
                    "model": self.model_name,
                },
            ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k] if top_k else results

    # ------------------------------------------------------------------ #
    # BaseMatcher interface
    # ------------------------------------------------------------------ #

    def match_one(
        self,
        candidate: MatchCandidate,
        job_text: str,
        job_skills: Optional[List[str]] = None,
    ) -> MatchResult:
        score = self.score_pair(candidate.text, job_text)
        job_norm = set(self.skill_normalizer.normalize_list(job_skills or []))
        cv_norm = set(self.skill_normalizer.normalize_list(candidate.skills))
        return MatchResult(
            candidate_id=candidate.id,
            score=round(score, 4),
            matched_skills=sorted(cv_norm & job_norm),
            missing_skills=sorted(job_norm - cv_norm),
            extra_skills=sorted(cv_norm - job_norm),
            details={"method": "cross_encoder_pair"},
        )

    def match_many(
        self,
        candidates: List[MatchCandidate],
        job_text: str,
        job_skills: Optional[List[str]] = None,
        top_k: Optional[int] = None,
    ) -> List[MatchResult]:
        return self.rerank(job_text, candidates, job_skills, top_k)
