"""Candidate profile enrichment helpers.

This module builds richer candidate summaries from raw CV text and extracted skills.
It uses the existing ProfileGenerator rules, so it works even without external LLMs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ai_module.nlp.profile_generator import ProfileGenerator


@dataclass
class CandidateEnrichment:
    summary: str
    soft_skills: List[str]
    trajectory: str
    potential: str
    strengths: List[str]
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "soft_skills": self.soft_skills,
            "trajectory": self.trajectory,
            "potential": self.potential,
            "strengths": self.strengths,
            "recommendations": self.recommendations,
        }


class CandidateProfileEnricher:
    """Create richer recruiter-facing candidate summaries."""

    def enrich(self, candidate: Any, raw_text: Optional[str] = None) -> CandidateEnrichment:
        text = raw_text or getattr(candidate, "raw_text", "") or ""
        generated = ProfileGenerator.generate_from_text(text)

        ideal_skills = generated.get("ideal_skills") or []
        top_skill_names = [str(item.get("name")) for item in ideal_skills[:5] if isinstance(item, dict) and item.get("name")]

        soft_skills = self._derive_soft_skills(text, top_skill_names)
        trajectory = self._build_trajectory(candidate, generated)
        potential = self._assess_potential(generated)
        strengths = self._build_strengths(candidate, top_skill_names)
        recommendations = self._build_recommendations(top_skill_names, soft_skills)

        return CandidateEnrichment(
            summary=f"Profil enrichi pour {getattr(candidate, 'full_name', 'candidat')}",
            soft_skills=soft_skills,
            trajectory=trajectory,
            potential=potential,
            strengths=strengths,
            recommendations=recommendations,
        )

    def _derive_soft_skills(self, text: str, top_skills: List[str]) -> List[str]:
        lower = text.lower()
        values = []
        for skill in ["communication", "leadership", "teamwork", "autonomy", "problem solving", "adaptability"]:
            if skill in lower:
                values.append(skill.title())
        if top_skills and len(values) < 3:
            values.append("Learning agility")
        return list(dict.fromkeys(values))[:5]

    def _build_trajectory(self, candidate: Any, generated: Dict[str, Any]) -> str:
        years = generated.get("ideal_experience_years") or 0
        label = "senior" if years >= 5 else "mid-level" if years >= 3 else "junior"
        return f"Trajectory inferred as {label} ({years} years benchmark) for {getattr(candidate, 'full_name', 'candidate')}"

    def _assess_potential(self, generated: Dict[str, Any]) -> str:
        years = int(generated.get("ideal_experience_years") or 0)
        if years >= 5:
            return "High"
        if years >= 3:
            return "Medium"
        return "Emerging"

    def _build_strengths(self, candidate: Any, top_skills: List[str]) -> List[str]:
        candidate_skill_names = {
            str(getattr(getattr(item, 'skill', None), 'name', '')).lower()
            for item in getattr(candidate, 'candidate_skills', []) or []
            if getattr(getattr(item, 'skill', None), 'name', None)
        }
        strengths = [skill for skill in top_skills if skill.lower() in candidate_skill_names]
        return strengths[:5]

    def _build_recommendations(self, top_skills: List[str], soft_skills: List[str]) -> List[str]:
        recommendations = []
        if top_skills:
            recommendations.append(f"Focus on top technical skill: {top_skills[0]}")
        if soft_skills:
            recommendations.append(f"Highlight soft skills: {', '.join(soft_skills[:3])}")
        recommendations.append("Review candidate trajectory before interview")
        return recommendations[:5]
