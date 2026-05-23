"""Matcher baseline : cosine similarity sur vecteurs binaires de compétences.

Formule :
    sim(A, B) = (A · B) / (||A|| × ||B||)

Avantages :
    - Très rapide
    - Interprétable
    - Pas de dépendance externe (juste numpy)

Limitations :
    - Sensible aux noms exacts de skills (mais on normalise en amont)
    - Pas de compréhension sémantique (un "ML" et "Machine Learning" sans
      normalisation = distance maximale)
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence

from ai_pipeline.matching.base import BaseMatcher, MatchCandidate, MatchResult
from ai_pipeline.preprocessing.skill_normalizer import SkillNormalizer


class CosineMatcher(BaseMatcher):
    """Cosine similarity sur ensemble de compétences (binaire pondéré)."""

    name = "cosine"

    def __init__(self, skill_universe: Optional[Sequence[str]] = None) -> None:
        self.normalizer = SkillNormalizer()
        self._universe = self._normalize_universe(skill_universe or [])

    @staticmethod
    def _normalize_universe(skills: Sequence[str]) -> List[str]:
        seen = set()
        out = []
        norm = SkillNormalizer()
        for s in skills:
            n = norm.normalize(s)
            if n and n not in seen:
                seen.add(n)
                out.append(n)
        return out

    def update_universe(self, skills: Sequence[str]) -> None:
        """Étendre l'univers de skills (utile quand on indexe de nouveaux jobs)."""
        norm = self.normalizer
        for s in skills:
            n = norm.normalize(s)
            if n and n not in self._universe:
                self._universe.append(n)

    def _vector(self, skills: Sequence[str]) -> List[float]:
        normalized = set(self.normalizer.normalize_list(skills))
        return [1.0 if u in normalized else 0.0 for u in self._universe]

    def _weighted_vector(
        self,
        skills_with_weights: Sequence[tuple[str, float]],
    ) -> List[float]:
        lookup = {}
        for skill, weight in skills_with_weights:
            normalized = self.normalizer.normalize(skill)
            lookup[normalized] = weight
        return [lookup.get(u, 0.0) for u in self._universe]

    @staticmethod
    def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        return dot / (norm_a * norm_b)

    def match_one(
        self,
        candidate: MatchCandidate,
        job_text: str,
        job_skills: Optional[List[str]] = None,
    ) -> MatchResult:
        job_skills = job_skills or []
        if job_skills and not self._universe:
            self.update_universe(job_skills + candidate.skills)

        cv_norm = set(self.normalizer.normalize_list(candidate.skills))
        job_norm = set(self.normalizer.normalize_list(job_skills))

        # Si pas d'univers défini, on utilise l'union comme univers de la paire
        universe = self._universe if self._universe else sorted(cv_norm | job_norm)
        if not universe:
            return MatchResult(candidate_id=candidate.id, score=0.0)

        cv_vec = [1.0 if u in cv_norm else 0.0 for u in universe]
        job_vec = [1.0 if u in job_norm else 0.0 for u in universe]
        similarity = self._cosine(cv_vec, job_vec)

        matched = sorted(cv_norm & job_norm)
        missing = sorted(job_norm - cv_norm)
        extra = sorted(cv_norm - job_norm)

        return MatchResult(
            candidate_id=candidate.id,
            score=round(similarity, 4),
            matched_skills=matched,
            missing_skills=missing,
            extra_skills=extra,
            details={
                "method": "cosine_skills",
                "universe_size": len(universe),
                "cv_skill_count": len(cv_norm),
                "job_skill_count": len(job_norm),
                "matched_count": len(matched),
            },
        )


if __name__ == "__main__":
    matcher = CosineMatcher()
    candidate = MatchCandidate(
        id="C1",
        text="Senior Python dev",
        skills=["python", "fastapi", "docker", "ml"],
    )
    result = matcher.match_one(
        candidate=candidate,
        job_text="Looking for Python dev with FastAPI and Docker",
        job_skills=["Python", "FastAPI", "Docker", "Kubernetes"],
    )
    print("Score:", result.score)
    print("Matched:", result.matched_skills)
    print("Missing:", result.missing_skills)
