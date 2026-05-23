"""Explainability engine: Generates human-readable justifications for matches."""

from dataclasses import dataclass
from typing import Callable
import math


@dataclass
class ExplainabilityBreakdown:
    """Human-readable breakdown of a match decision."""
    overall_score: float
    interpretation: str  # "Strong Match" / "Moderate Match" / "Weak Match"
    matching_skills: list[str]
    missing_skills: list[str]
    experience_alignment: str
    key_reason: str
    recommendations: list[str]


def generate_explanation(
    candidate_name: str,
    job_title: str,
    match_score: dict,
    matching_skills: list[str],
    missing_skills: list[str],
    candidate_years_exp: float = 0.0,
    required_years_exp: float = 0.0,
) -> ExplainabilityBreakdown:
    """
    Generate human-readable explanation for a CV-job match.
    
    Args:
        candidate_name: Candidate full name
        job_title: Job title
        match_score: Dict with 'overall', 'text_sim', 'skills_match' scores (0-1)
        matching_skills: List of skills that matched
        missing_skills: List of required skills not found
        candidate_years_exp: Candidate's years of experience
        required_years_exp: Required years for job
        
    Returns:
        ExplainabilityBreakdown with justification details
    """
    
    overall = match_score.get("match_score", 0.0)
    text_sim = match_score.get("text_similarity", 0.0)
    skill_match = match_score.get("skills_match", 0.0)
    
    # Interpretation
    if overall >= 0.80:
        interpretation = "🟢 Strong Match"
    elif overall >= 0.60:
        interpretation = "🟡 Moderate Match"
    else:
        interpretation = "🔴 Weak Match"
    
    # Experience alignment
    exp_gap = candidate_years_exp - required_years_exp
    if exp_gap >= 2:
        experience_alignment = f"✅ Highly experienced ({candidate_years_exp:.1f} years > {required_years_exp:.1f} required)"
    elif exp_gap >= 0:
        experience_alignment = f"✅ Meets experience requirement ({candidate_years_exp:.1f} years ≈ {required_years_exp:.1f} required)"
    elif exp_gap > -2:
        experience_alignment = f"⚠️ Slightly under-experienced ({candidate_years_exp:.1f} years < {required_years_exp:.1f} required)"
    else:
        experience_alignment = f"❌ Under-experienced ({candidate_years_exp:.1f} years < {required_years_exp:.1f} required)"
    
    # Key reason
    if len(matching_skills) >= 5 and skill_match > 0.85:
        key_reason = f"Strong technical skills alignment: {', '.join(matching_skills[:3])} + {len(matching_skills)-3} more"
    elif len(matching_skills) > 0:
        key_reason = f"Good skills match: {', '.join(matching_skills[:2])}"
    elif text_sim > 0.75:
        key_reason = "Strong text/profile similarity with job description"
    else:
        key_reason = "Limited overlap between background and job requirements"
    
    # Recommendations
    recommendations = []
    if len(missing_skills) > 0:
        recommendations.append(f"Consider candidates with: {', '.join(missing_skills[:2])}")
    if exp_gap < -1:
        recommendations.append("Candidate needs more industry experience")
    if overall > 0.60:
        recommendations.append("Recommended for interview or technical assessment")
    if overall < 0.50:
        recommendations.append("Better candidates may exist; consider re-posting")
    if not recommendations:
        recommendations.append("Strong candidate — proceed with hiring process")
    
    return ExplainabilityBreakdown(
        overall_score=round(overall, 2),
        interpretation=interpretation,
        matching_skills=matching_skills[:5],  # Top 5
        missing_skills=missing_skills[:3],    # Top 3
        experience_alignment=experience_alignment,
        key_reason=key_reason,
        recommendations=recommendations[:2],  # Top 2 recommendations
    )


def generate_shortlist_summary(
    matches: list[dict],
    job_title: str,
    top_n: int = 5,
) -> dict:
    """
    Generate summary for a shortlist of candidates.
    
    Args:
        matches: List of match results (each with candidate, score, skills data)
        job_title: Job title being matched
        top_n: Number of top candidates to feature
        
    Returns:
        Summary dict with insights and recommendations
    """
    
    if not matches:
        return {
            "total_candidates_screened": 0,
            "strong_matches": 0,
            "recommendations": ["No candidates found. Consider widening search criteria."],
            "top_skills_in_shortlist": [],
        }
    
    sorted_matches = sorted(matches, key=lambda x: x.get("score", 0), reverse=True)
    top_matches = sorted_matches[:top_n]
    
    strong = sum(1 for m in matches if m.get("score", 0) >= 0.80)
    moderate = sum(1 for m in matches if 0.60 <= m.get("score", 0) < 0.80)
    
    # Extract top skills from candidates
    all_skills = []
    for match in top_matches:
        if "matching_skills" in match:
            all_skills.extend(match["matching_skills"])
    
    from collections import Counter
    skill_counts = Counter(all_skills)
    top_skills = [skill for skill, count in skill_counts.most_common(5)]
    
    recommendations = []
    if strong >= 3:
        recommendations.append(f"✅ Excellent pool: {strong} strong matches. Recommend interviews for all.")
    elif strong >= 1:
        recommendations.append(f"👍 Good: {strong} strong match(es) available. Start with top candidates.")
    else:
        recommendations.append(f"⚠️ Limited strong matches ({strong}). Consider adjusting requirements or widening search.")
    
    if moderate > 0:
        recommendations.append(f"Consider {moderate} moderate matches for technical screening.")
    
    return {
        "total_candidates_screened": len(matches),
        "strong_matches": strong,
        "moderate_matches": moderate,
        "top_skills_in_pool": top_skills,
        "recommendations": recommendations,
    }
