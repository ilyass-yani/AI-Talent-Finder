"""Interfaces communes pour tous les matchers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MatchCandidate:
    """Candidat à matcher contre une offre."""
    id: str
    text: str
    skills: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MatchResult:
    """Résultat d'un matching."""
    candidate_id: str
    score: float           # 0.0 — 1.0
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    extra_skills: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    explanation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "score": round(self.score, 4),
            "matched_skills": self.matched_skills,
            "missing_skills": self.missing_skills,
            "extra_skills": self.extra_skills,
            "details": self.details,
            "explanation": self.explanation,
        }


class BaseMatcher(ABC):
    """Interface commune à tous les matchers.

    Tout matcher doit implémenter :
        - match_one : match un candidat contre un job
        - match_many : match plusieurs candidats (peut être optimisé en batch)
    """

    name: str = "base"

    @abstractmethod
    def match_one(
        self,
        candidate: MatchCandidate,
        job_text: str,
        job_skills: Optional[List[str]] = None,
    ) -> MatchResult:
        ...

    def match_many(
        self,
        candidates: List[MatchCandidate],
        job_text: str,
        job_skills: Optional[List[str]] = None,
        top_k: Optional[int] = None,
    ) -> List[MatchResult]:
        """Implémentation par défaut séquentielle. Surcharger pour optim batch."""
        results = [
            self.match_one(c, job_text, job_skills)
            for c in candidates
        ]
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k] if top_k else results
