"""Matcher sémantique : sentence-transformer + (optionnel) FAISS.

Pour un job donné, calcule la similarité cosine entre l'embedding du job
et celui de chaque candidat. Très utile en remplacement du cosine bête de skills
quand on a peu de chevauchement exact.

Avec FAISS, on peut faire de la recherche approximative en O(log N) sur des
millions de CV (cf. vector_db/faiss_store.py).
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np

from ai_pipeline.feature_engineering.semantic_features import SemanticFeatureExtractor
from ai_pipeline.matching.base import BaseMatcher, MatchCandidate, MatchResult
from ai_pipeline.preprocessing.skill_normalizer import SkillNormalizer


class SemanticMatcher(BaseMatcher):
    """Bi-encoder léger basé sur Sentence-Transformers."""

    name = "semantic"

    def __init__(
        self,
        encoder: Optional[SemanticFeatureExtractor] = None,
        boost_with_skill_overlap: bool = True,
        skill_boost_weight: float = 0.20,
    ) -> None:
        self.encoder = encoder or SemanticFeatureExtractor()
        self.boost_with_skill_overlap = boost_with_skill_overlap
        self.skill_boost_weight = skill_boost_weight
        self.skill_normalizer = SkillNormalizer()

    def match_one(
        self,
        candidate: MatchCandidate,
        job_text: str,
        job_skills: Optional[List[str]] = None,
    ) -> MatchResult:
        # 1. Similarité sémantique
        cv_emb = self.encoder.encode_single(candidate.text)
        job_emb = self.encoder.encode_single(job_text)
        sem_score = SemanticFeatureExtractor.cosine_similarity(cv_emb, job_emb)
        # bge produit des scores [0..1] (cosine). On clamp.
        sem_score = max(0.0, min(1.0, sem_score))

        # 2. Skill overlap (en bonus)
        job_norm = set(self.skill_normalizer.normalize_list(job_skills or []))
        cv_norm = set(self.skill_normalizer.normalize_list(candidate.skills))
        matched = sorted(cv_norm & job_norm)
        missing = sorted(job_norm - cv_norm)
        extra = sorted(cv_norm - job_norm)
        skill_overlap = (len(matched) / len(job_norm)) if job_norm else 0.0

        # 3. Score final
        if self.boost_with_skill_overlap and job_norm:
            score = (1.0 - self.skill_boost_weight) * sem_score + self.skill_boost_weight * skill_overlap
        else:
            score = sem_score

        return MatchResult(
            candidate_id=candidate.id,
            score=round(score, 4),
            matched_skills=matched,
            missing_skills=missing,
            extra_skills=extra,
            details={
                "method": "semantic_biencoder",
                "model": self.encoder.model_name,
                "semantic_similarity": round(sem_score, 4),
                "skill_overlap": round(skill_overlap, 4),
                "skill_boost_weight": self.skill_boost_weight,
            },
        )

    def match_many(
        self,
        candidates: List[MatchCandidate],
        job_text: str,
        job_skills: Optional[List[str]] = None,
        top_k: Optional[int] = None,
    ) -> List[MatchResult]:
        """Version batch : encode tous les CV en une passe (beaucoup + rapide)."""
        if not candidates:
            return []

        # Batch encoding
        cv_texts = [c.text for c in candidates]
        cv_embs = self.encoder.encode(cv_texts)
        job_emb = self.encoder.encode_single(job_text)

        # Cosine en batch
        # Si normalize_embeddings=True, dot product = cosine
        if self.encoder.normalize:
            sims = cv_embs @ job_emb
        else:
            sims = []
            for emb in cv_embs:
                sims.append(SemanticFeatureExtractor.cosine_similarity(emb, job_emb))
            sims = np.array(sims)

        sims = np.clip(sims, 0.0, 1.0)

        results: List[MatchResult] = []
        job_norm = set(self.skill_normalizer.normalize_list(job_skills or []))

        for candidate, sem_score in zip(candidates, sims):
            cv_norm = set(self.skill_normalizer.normalize_list(candidate.skills))
            matched = sorted(cv_norm & job_norm)
            missing = sorted(job_norm - cv_norm)
            extra = sorted(cv_norm - job_norm)
            skill_overlap = (len(matched) / len(job_norm)) if job_norm else 0.0

            if self.boost_with_skill_overlap and job_norm:
                score = (1.0 - self.skill_boost_weight) * float(sem_score) + \
                        self.skill_boost_weight * skill_overlap
            else:
                score = float(sem_score)

            results.append(MatchResult(
                candidate_id=candidate.id,
                score=round(score, 4),
                matched_skills=matched,
                missing_skills=missing,
                extra_skills=extra,
                details={
                    "method": "semantic_biencoder_batch",
                    "semantic_similarity": round(float(sem_score), 4),
                    "skill_overlap": round(skill_overlap, 4),
                },
            ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k] if top_k else results
