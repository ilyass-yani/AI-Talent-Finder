"""HybridMatcher : combine plusieurs matchers pour le meilleur résultat.

Stratégie 2 étages :
    1. Recall  : bi-encoder + FAISS récupère top-K candidats (K=50-200)
    2. Rerank  : cross-encoder re-classe ces top-K
    3. Fusion  : combinaison pondérée avec règles métier (skill overlap, exp, edu)

Cette architecture est utilisée dans tous les systèmes IR modernes
(Google, Spotify, LinkedIn) et c'est l'approche production-ready à mettre en avant
en soutenance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from ai_pipeline.matching.base import BaseMatcher, MatchCandidate, MatchResult
from ai_pipeline.matching.bi_encoder import BiEncoderMatcher
from ai_pipeline.matching.cosine_matcher import CosineMatcher
from ai_pipeline.matching.cross_encoder import CROSS_ENCODER_AVAILABLE, CrossEncoderReranker


@dataclass
class HybridConfig:
    # Pondération de chaque source
    weight_semantic: float = 0.45
    weight_cross_encoder: float = 0.25
    weight_skill_cosine: float = 0.20
    weight_business: float = 0.10  # exp + edu + langues

    # Pipeline
    recall_top_k: int = 100        # candidats à reranker
    use_cross_encoder: bool = True
    final_top_k: Optional[int] = None


class HybridMatcher(BaseMatcher):
    """Combine bi-encoder + cross-encoder + skill cosine + règles métier."""

    name = "hybrid"

    def __init__(
        self,
        config: Optional[HybridConfig] = None,
        bi_encoder: Optional[BiEncoderMatcher] = None,
        cosine: Optional[CosineMatcher] = None,
        cross_encoder: Optional[CrossEncoderReranker] = None,
    ) -> None:
        self.config = config or HybridConfig()
        self.bi_encoder = bi_encoder or BiEncoderMatcher()
        self.cosine = cosine or CosineMatcher()

        self.cross_encoder: Optional[CrossEncoderReranker]
        if self.config.use_cross_encoder and CROSS_ENCODER_AVAILABLE:
            self.cross_encoder = cross_encoder or CrossEncoderReranker()
        else:
            self.cross_encoder = None

    # ------------------------------------------------------------------ #
    # Indexation
    # ------------------------------------------------------------------ #

    def index(self, candidates: Sequence[MatchCandidate]) -> None:
        self.bi_encoder.index(candidates)
        all_skills: List[str] = []
        for c in candidates:
            all_skills.extend(c.skills)
        self.cosine.update_universe(all_skills)

    # ------------------------------------------------------------------ #
    # Match
    # ------------------------------------------------------------------ #

    def match_one(
        self,
        candidate: MatchCandidate,
        job_text: str,
        job_skills: Optional[List[str]] = None,
    ) -> MatchResult:
        # Bi-encoder pair
        bi_result = self.bi_encoder.match_one(candidate, job_text, job_skills)
        # Skill cosine
        skill_result = self.cosine.match_one(candidate, job_text, job_skills)
        # Cross-encoder pair (si dispo)
        cross_score = None
        if self.cross_encoder is not None:
            cross_result = self.cross_encoder.match_one(candidate, job_text, job_skills)
            cross_score = cross_result.score

        # Business rules score (pour cette interface limitée on n'a que les skills)
        # → on calcule le skill coverage uniquement ici
        business_score = self._business_score(candidate, job_skills)

        final = self._fuse_scores(
            semantic=bi_result.score,
            skill_cosine=skill_result.score,
            cross=cross_score,
            business=business_score,
        )

        return MatchResult(
            candidate_id=candidate.id,
            score=round(final, 4),
            matched_skills=skill_result.matched_skills,
            missing_skills=skill_result.missing_skills,
            extra_skills=skill_result.extra_skills,
            details={
                "method": "hybrid",
                "semantic_score": bi_result.score,
                "skill_cosine_score": skill_result.score,
                "cross_encoder_score": cross_score,
                "business_score": business_score,
                "weights": {
                    "semantic": self.config.weight_semantic,
                    "cross_encoder": self.config.weight_cross_encoder,
                    "skill_cosine": self.config.weight_skill_cosine,
                    "business": self.config.weight_business,
                },
            },
        )

    def search(
        self,
        job_text: str,
        job_skills: Optional[List[str]] = None,
        top_k: Optional[int] = None,
    ) -> List[MatchResult]:
        """Recherche end-to-end avec pipeline 2 étages."""
        if not self.bi_encoder._candidates:
            return []

        top_k_final = top_k or self.config.final_top_k or 20

        # ÉTAPE 1 : RECALL via bi-encoder + FAISS
        recall_candidates = self.bi_encoder.search(
            job_text, job_skills,
            top_k=self.config.recall_top_k,
        )
        if not recall_candidates:
            return []

        # Récupérer les MatchCandidate objects à partir des IDs
        id_to_candidate = {c.id: c for c in self.bi_encoder._candidates}
        recall_objects = [
            id_to_candidate[r.candidate_id]
            for r in recall_candidates
            if r.candidate_id in id_to_candidate
        ]

        # ÉTAPE 2 : RE-RANK via cross-encoder
        if self.cross_encoder is not None:
            cross_results = self.cross_encoder.rerank(
                job_text, recall_objects, job_skills,
            )
            cross_scores = {r.candidate_id: r.score for r in cross_results}
        else:
            cross_scores = {}

        # ÉTAPE 3 : SKILL COSINE
        skill_scores: Dict[str, MatchResult] = {}
        for cand in recall_objects:
            skill_scores[cand.id] = self.cosine.match_one(cand, job_text, job_skills)

        # ÉTAPE 4 : FUSION
        bi_scores = {r.candidate_id: r.score for r in recall_candidates}
        final_results: List[MatchResult] = []
        for cand in recall_objects:
            skill_res = skill_scores[cand.id]
            business = self._business_score(cand, job_skills)
            final = self._fuse_scores(
                semantic=bi_scores.get(cand.id, 0.0),
                skill_cosine=skill_res.score,
                cross=cross_scores.get(cand.id),
                business=business,
            )
            final_results.append(MatchResult(
                candidate_id=cand.id,
                score=round(final, 4),
                matched_skills=skill_res.matched_skills,
                missing_skills=skill_res.missing_skills,
                extra_skills=skill_res.extra_skills,
                details={
                    "method": "hybrid_2stage",
                    "semantic_score": bi_scores.get(cand.id, 0.0),
                    "skill_cosine_score": skill_res.score,
                    "cross_encoder_score": cross_scores.get(cand.id),
                    "business_score": business,
                },
            ))

        final_results.sort(key=lambda r: r.score, reverse=True)
        return final_results[:top_k_final]

    # ------------------------------------------------------------------ #
    # Fusion + business
    # ------------------------------------------------------------------ #

    def _fuse_scores(
        self,
        semantic: float,
        skill_cosine: float,
        cross: Optional[float],
        business: float,
    ) -> float:
        cfg = self.config
        if cross is None:
            # Re-normaliser les poids sans cross-encoder
            total_weight = cfg.weight_semantic + cfg.weight_skill_cosine + cfg.weight_business
            if total_weight == 0:
                return 0.0
            return (
                cfg.weight_semantic * semantic +
                cfg.weight_skill_cosine * skill_cosine +
                cfg.weight_business * business
            ) / total_weight
        else:
            total_weight = (
                cfg.weight_semantic + cfg.weight_cross_encoder +
                cfg.weight_skill_cosine + cfg.weight_business
            )
            if total_weight == 0:
                return 0.0
            return (
                cfg.weight_semantic * semantic +
                cfg.weight_cross_encoder * cross +
                cfg.weight_skill_cosine * skill_cosine +
                cfg.weight_business * business
            ) / total_weight

    def _business_score(
        self,
        candidate: MatchCandidate,
        job_skills: Optional[List[str]],
    ) -> float:
        """Score business basique basé sur les métadonnées du candidat."""
        from ai_pipeline.preprocessing.skill_normalizer import SkillNormalizer
        norm = SkillNormalizer()
        cv_norm = set(norm.normalize_list(candidate.skills))
        job_norm = set(norm.normalize_list(job_skills or []))
        skill_coverage = (len(cv_norm & job_norm) / len(job_norm)) if job_norm else 0.5

        meta = candidate.metadata or {}
        exp_match = 1.0
        if meta.get("years_experience") is not None and meta.get("job_required_years"):
            cv_y = float(meta["years_experience"])
            req_y = float(meta["job_required_years"])
            if req_y > 0:
                exp_match = min(1.0, cv_y / req_y)

        edu_match = 1.0
        if meta.get("education_level") is not None and meta.get("job_required_education_level") is not None:
            cv_e = int(meta["education_level"])
            req_e = int(meta["job_required_education_level"])
            edu_match = 1.0 if cv_e >= req_e else max(0.0, 1.0 - (req_e - cv_e) * 0.2)

        return 0.6 * skill_coverage + 0.25 * exp_match + 0.15 * edu_match
