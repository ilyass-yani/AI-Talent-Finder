"""Scoring and decision logic with calibrated business rules."""

from typing import Dict, Any, List, Tuple
from enum import Enum


class MatchDecision(str, Enum):
    ACCEPTED = "accepted"  # Score >= 0.8
    REVIEW = "to_review"    # 0.5 <= Score < 0.8
    REJECTED = "rejected"   # Score < 0.5


def compute_match_score(
    cv_skills: List[str],
    job_skills: List[str],
    cv_years: int = 0,
    job_years: int = 0,
    cv_edu_level: int = 2,
    job_edu_level: int = 2,
    similarity_score: float = 0.0,  # from semantic matching 0..1
) -> float:
    """Compute calibrated match score [0..1].

    Weights:
    - Skill matching: 50%
    - Semantic similarity: 20%
    - Experience: 15%
    - Education: 10%
    - Bonus: 5% for perfect match
    """
    score = 0.0

    # Skill matching (weight: 50%)
    if job_skills:
        required_set = set(s.lower() for s in job_skills)
        cv_set = set(s.lower() for s in cv_skills)
        intersection = required_set & cv_set
        skill_score = len(intersection) / len(required_set) if intersection else 0.0
        score += skill_score * 0.50
    else:
        score += 0.50  # no skills required

    # Semantic similarity (weight: 20%)
    score += (similarity_score or 0.0) * 0.20

    # Experience match (weight: 15%)
    if job_years > 0:
        if cv_years >= job_years:
            score += 0.15
        else:
            # Linear penalty: each missing year = 15% / job_years penalty
            penalty = (job_years - cv_years) / job_years
            score += max(0, 0.15 * (1 - penalty))
    else:
        score += 0.15

    # Education match (weight: 10%)
    if job_edu_level > 0:
        if cv_edu_level >= job_edu_level:
            score += 0.10
        else:
            # Penalty proportional to gap
            penalty = (job_edu_level - cv_edu_level) / job_edu_level
            score += max(0, 0.10 * (1 - penalty))
    else:
        score += 0.10

    # Bonus for perfect skill + experience match (up to 5%)
    if job_skills and cv_years >= job_years and len(intersection) == len(required_set):
        score += 0.05

    return min(1.0, max(0.0, score))


def decide_match(score: float) -> MatchDecision:
    """Map score to decision."""
    if score >= 0.80:
        return MatchDecision.ACCEPTED
    elif score >= 0.50:
        return MatchDecision.REVIEW
    else:
        return MatchDecision.REJECTED


def get_decision_explanation(
    decision: MatchDecision,
    score: float,
    skill_match: float,
    experience_gap: int,
    missing_skills: List[str],
) -> str:
    """Generate human-readable explanation for the decision."""
    if decision == MatchDecision.ACCEPTED:
        msg = f"✅ Strong match (score: {score:.1%}). Candidate has the required experience and skills."
    elif decision == MatchDecision.REVIEW:
        msg = f"🟠 Worth reviewing (score: {score:.1%}). Some experience or skill gaps but overall promising."
    else:
        msg = f"❌ Not a match (score: {score:.1%}). Significant gaps in skills or experience."

    if missing_skills:
        msg += f"\n⚠️  Missing skills: {', '.join(missing_skills[:3])}"
    if experience_gap > 0:
        msg += f"\n📅 Experience gap: {experience_gap} years below requirement"

    return msg


def apply_business_rules(match_info: Dict[str, Any]) -> Dict[str, Any]:
    """Apply calibrated business rules and return enriched decision.

    Expected input keys:
    - score: float [0..1]
    - cv_skills: List[str]
    - job_skills: List[str]
    - cv_years: int
    - job_years: int
    - cv_edu: int (0-4)
    - job_edu: int (0-4)
    """
    score = match_info.get("score", 0.0)
    decision = decide_match(score)

    skill_match = 0.0
    missing = []
    if match_info.get("job_skills"):
        req = set(s.lower() for s in match_info.get("job_skills", []))
        cv = set(s.lower() for s in match_info.get("cv_skills", []))
        intersection = req & cv
        skill_match = len(intersection) / len(req) if req else 0
        missing = list(req - cv)

    exp_gap = max(0, match_info.get("job_years", 0) - match_info.get("cv_years", 0))

    explanation = get_decision_explanation(
        decision=decision,
        score=score,
        skill_match=skill_match,
        experience_gap=exp_gap,
        missing_skills=missing,
    )

    return {
        "decision": decision.value,
        "score": score,
        "skill_match_ratio": skill_match,
        "experience_gap_years": exp_gap,
        "missing_skills": missing,
        "explanation": explanation,
    }


__all__ = [
    "MatchDecision",
    "compute_match_score",
    "decide_match",
    "get_decision_explanation",
    "apply_business_rules",
]


if __name__ == "__main__":
    # Quick test
    result = apply_business_rules({
        "score": 0.75,
        "cv_skills": ["React", "Python", "AWS", "Docker"],
        "job_skills": ["React", "Node.js", "AWS"],
        "cv_years": 5,
        "job_years": 3,
        "cv_edu": 2,
        "job_edu": 2,
    })
    print(result)
