"""Matching engine for customizable recruiter criteria."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from app.models.models import Candidate
from app.services.normalization import normalize_skill_name


def clamp_weight(weight: int) -> int:
    """Clamp recruiter weights to the supported 0..100 range."""
    try:
        return max(0, min(100, int(weight)))
    except (TypeError, ValueError):
        return 0


def _dedupe_preserve_order(values: Iterable[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for value in values:
        normalized = normalize_skill_name(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(value.strip())
    return ordered


def load_skill_dictionary_from_file() -> List[str]:
    """Load the bundled skill dictionary as a fallback skill universe."""
    dictionary_path = Path(__file__).resolve().parents[2] / "ai_module" / "data" / "skills_dictionary.json"
    if not dictionary_path.exists():
        return []

    try:
        payload = json.loads(dictionary_path.read_text(encoding="utf-8"))
    except Exception:
        return []

    skill_names: List[str] = []
    if isinstance(payload, dict):
        for values in payload.values():
            if isinstance(values, list):
                skill_names.extend(str(value) for value in values if str(value).strip())
    elif isinstance(payload, list):
        skill_names.extend(str(value) for value in payload if str(value).strip())

    return _dedupe_preserve_order(skill_names)


def extract_candidate_skill_names(candidate: Candidate) -> List[str]:
    """Build the set of skills available for a candidate."""
    skill_names: List[str] = []

    for candidate_skill in getattr(candidate, "candidate_skills", []) or []:
        skill = getattr(candidate_skill, "skill", None)
        skill_name = getattr(skill, "name", None)
        if skill_name:
            skill_names.append(skill_name)

    ner_payload = getattr(candidate, "ner_extraction_data", None)
    if ner_payload:
        try:
            parsed = json.loads(ner_payload)
            extracted_skills = parsed.get("skills", []) if isinstance(parsed, dict) else []
            for item in extracted_skills:
                if isinstance(item, str):
                    skill_names.append(item)
                elif isinstance(item, dict):
                    skill_name = item.get("name")
                    if skill_name:
                        skill_names.append(str(skill_name))
        except Exception:
            pass

    return _dedupe_preserve_order(skill_names)


def build_skill_universe(db) -> List[str]:
    """Get the dictionary of skills used as vector space."""
    try:
        from app.models.models import Skill

        db_skills = [row.name for row in db.query(Skill).order_by(Skill.name.asc()).all() if row.name]
    except Exception:
        db_skills = []

    if db_skills:
        return _dedupe_preserve_order(db_skills)

    fallback_skills = load_skill_dictionary_from_file()
    return fallback_skills


def _vector_norm(values: Sequence[float]) -> float:
    return math.sqrt(sum(value * value for value in values))


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    left_norm = _vector_norm(left)
    right_norm = _vector_norm(right)
    if left_norm == 0 or right_norm == 0:
        return 0.0

    dot_product = sum(left_value * right_value for left_value, right_value in zip(left, right))
    return dot_product / (left_norm * right_norm)


def score_candidate_against_criteria(
    candidate: Candidate,
    criteria_skills: Sequence[Dict[str, int]],
    skill_universe: Optional[Sequence[str]] = None,
) -> Tuple[float, Dict[str, object]]:
    """Score a candidate with a weighted cosine similarity over the selected criteria."""
    normalized_criteria = [
        {
            "name": str(item.get("name", "")).strip(),
            "weight": clamp_weight(item.get("weight", 0)),
        }
        for item in criteria_skills
        if str(item.get("name", "")).strip()
    ]

    if not normalized_criteria:
        return 0.0, {
            "similarity": 0.0,
            "matched_skills": [],
            "missing_skills": [],
            "skill_breakdown": [],
            "coverage": 0.0,
            "summary": "Aucun critère défini",
        }

    candidate_skills = {
        normalize_skill_name(skill_name)
        for skill_name in extract_candidate_skill_names(candidate)
        if normalize_skill_name(skill_name)
    }

    universe = [normalize_skill_name(skill_name) for skill_name in (skill_universe or []) if normalize_skill_name(skill_name)]
    if not universe:
        universe = [normalize_skill_name(item["name"]) for item in normalized_criteria]

    criteria_lookup = {
        normalize_skill_name(item["name"]): item["weight"]
        for item in normalized_criteria
    }

    candidate_vector = [1.0 if skill_name in candidate_skills else 0.0 for skill_name in universe]
    criteria_vector = [float(criteria_lookup.get(skill_name, 0.0)) / 100.0 for skill_name in universe]

    similarity = _cosine_similarity(candidate_vector, criteria_vector)
    score = round(max(0.0, min(100.0, similarity * 100.0)), 2)

    matched_skills: List[str] = []
    missing_skills: List[str] = []
    skill_breakdown: List[Dict[str, object]] = []
    matched_weight = 0
    total_weight = 0

    for item in normalized_criteria:
        skill_name = item["name"]
        normalized_name = normalize_skill_name(skill_name)
        weight = item["weight"]
        present = normalized_name in candidate_skills
        total_weight += weight
        if present:
            matched_weight += weight
            matched_skills.append(skill_name)
        else:
            missing_skills.append(skill_name)

        skill_breakdown.append({
            "skill": skill_name,
            "weight": weight,
            "present": present,
            "score": float(weight if present else 0),
            "contribution": float(weight if present else 0),
        })

    coverage = round((matched_weight / total_weight * 100.0) if total_weight else 0.0, 2)
    summary = f"{len(matched_skills)}/{len(normalized_criteria)} compétences couvertes"

    return score, {
        "similarity": round(similarity, 4),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "skill_breakdown": skill_breakdown,
        "coverage": coverage,
        "summary": summary,
        "skill_universe_size": len(skill_universe or []),
    }


def build_explanation_payload(score: float, details: Dict[str, object]) -> Dict[str, object]:
    """Build a compact payload that can be stored in the MatchResult explanation field."""
    return {
        "score": score,
        "summary": details.get("summary", ""),
        "coverage": details.get("coverage", 0),
        "matched_skills": details.get("matched_skills", []),
        "missing_skills": details.get("missing_skills", []),
        "skill_breakdown": details.get("skill_breakdown", []),
    }
