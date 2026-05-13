"""
Explainability Engine — Transparent Match Scoring

Provides complete breakdown of why a candidate matches (or doesn't match) a job.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class SkillMatchStatus(str, Enum):
    MATCHED = "matched"
    MISSING = "missing"
    BONUS = "bonus"


class ExplainabilityEngine:
    """Explains match scoring in detail."""
    
    WEIGHTS = {
        "skills": 0.50,
        "semantic": 0.20,
        "experience": 0.15,
        "education": 0.10,
        "bonus": 0.05,
    }
    
    def explain_score(self, candidate: Any, criteria: Any, total_score: float) -> Dict:
        """
        Generate complete explanation of match score.
        
        Args:
            candidate: Candidate model instance
            criteria: JobCriteria model instance
            total_score: Match score (0.0-1.0)
            
        Returns:
            Detailed explanation dict
        """
        
        # Compute component breakdowns
        skills_breakdown = self._explain_skills(candidate, criteria)
        semantic_breakdown = self._explain_semantic(candidate, criteria)
        experience_breakdown = self._explain_experience(candidate, criteria)
        education_breakdown = self._explain_education(candidate, criteria)
        
        # Identify strengths and gaps
        strengths = self._identify_strengths(skills_breakdown)
        gaps = self._identify_gaps(skills_breakdown, criteria)
        
        # Recommendation
        recommendation = self._recommend_action(total_score)
        
        # Confidence score
        confidence = self._calculate_confidence(
            candidate, criteria, skills_breakdown
        )
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "candidate": {
                "id": candidate.id,
                "name": candidate.full_name,
                "email": candidate.email,
            },
            "criteria": {
                "id": criteria.id,
                "title": criteria.title,
            },
            "score": {
                "total": round(total_score, 3),
                "percentage": f"{total_score*100:.1f}%",
                "components": {
                    "skills": round(skills_breakdown["score"], 3),
                    "semantic": round(semantic_breakdown.get("score", 0), 3),
                    "experience": round(experience_breakdown["score"], 3),
                    "education": round(education_breakdown.get("score", 0), 3),
                },
            },
            "breakdown": {
                "skills": skills_breakdown,
                "semantic": semantic_breakdown,
                "experience": experience_breakdown,
                "education": education_breakdown,
            },
            "insights": {
                "strengths": strengths,
                "gaps": gaps,
            },
            "decision": {
                "recommendation": recommendation["action"],
                "rationale": recommendation["rationale"],
                "next_step": recommendation.get("next_step"),
            },
            "confidence": confidence,
        }
    
    def _explain_skills(self, candidate: Any, criteria: Any) -> Dict:
        """Detail of skill matching."""
        matched = []
        missing = []
        
        # Get candidate skills
        candidate_skill_names = {
            s.skill.name.lower(): s.skill.name
            for s in candidate.candidate_skills
            if s.skill
        }
        
        # Compare vs criteria
        total_weight = sum(c.weight for c in criteria.criteria_skills) or 100
        
        for criterion in criteria.criteria_skills:
            if not criterion.skill:
                continue
            
            skill_name = criterion.skill.name
            is_present = skill_name.lower() in candidate_skill_names
            
            contribution = (criterion.weight / total_weight) if is_present else 0
            
            skill_info = {
                "skill": skill_name,
                "weight": criterion.weight,
                "status": SkillMatchStatus.MATCHED if is_present else SkillMatchStatus.MISSING,
                "contribution": round(contribution * 0.50, 3),  # 50% weight for skills
            }
            
            if is_present:
                matched.append(skill_info)
            else:
                missing.append(skill_info)
        
        score = len(matched) / max(1, len(matched) + len(missing))
        
        return {
            "score": score,
            "matched": matched,
            "missing": missing,
            "coverage": f"{len(matched)}/{len(matched) + len(missing)}",
            "summary": f"Matched {len(matched)}/{len(matched) + len(missing)} required skills"
        }
    
    def _explain_semantic(self, candidate: Any, criteria: Any) -> Dict:
        """Semantic similarity with job description."""
        # Simplified - in production, compute actual embeddings
        return {
            "score": 0.75,
            "reason": "Semantic alignment with job description",
            "details": []
        }
    
    def _explain_experience(self, candidate: Any, criteria: Any) -> Dict:
        """Experience fit assessment."""
        years = getattr(candidate, 'years_experience', 0) or 0
        
        if years >= 10:
            assessment = "Senior level"
            score = 0.95
        elif years >= 5:
            assessment = "Mid-level"
            score = 0.85
        elif years >= 2:
            assessment = "Junior-Mid level"
            score = 0.65
        else:
            assessment = "Early career"
            score = 0.40
        
        return {
            "score": min(score, 1.0),
            "years": years,
            "assessment": assessment,
        }
    
    def _explain_education(self, candidate: Any, criteria: Any) -> Dict:
        """Education fit assessment."""
        education = getattr(candidate, 'extracted_education', None) or "Not specified"
        
        # Simple heuristic
        has_bachelor = "bachelor" in education.lower()
        has_master = "master" in education.lower() or "ms" in education.lower()
        
        if has_master:
            score = 0.9
            assessment = "Advanced degree"
        elif has_bachelor:
            score = 0.8
            assessment = "Bachelor degree"
        else:
            score = 0.5
            assessment = "Educational background unclear"
        
        return {
            "score": score,
            "degree": education,
            "assessment": assessment,
        }
    
    def _identify_strengths(self, skills_breakdown: Dict) -> List[str]:
        """Identify top 3 strengths."""
        matched = skills_breakdown.get("matched", [])
        if not matched:
            return []
        
        # Top 3 by weight
        top = sorted(matched, key=lambda x: x["weight"], reverse=True)[:3]
        return [f"{s['skill']} ({s['weight']}%)" for s in top]
    
    def _identify_gaps(self, skills_breakdown: Dict, criteria: Any) -> List[str]:
        """Identify top 3 gaps."""
        missing = skills_breakdown.get("missing", [])
        if not missing:
            return []
        
        # Top 3 by weight
        top = sorted(missing, key=lambda x: x["weight"], reverse=True)[:3]
        return [f"{s['skill']} ({s['weight']}%)" for s in top]
    
    def _recommend_action(self, score: float) -> Dict:
        """Recommendation based on score."""
        if score >= 0.80:
            return {
                "action": "ACCEPT",
                "rationale": "Strong match on core criteria",
                "next_step": "Schedule interview immediately",
                "confidence": "High"
            }
        elif score >= 0.50:
            return {
                "action": "REVIEW",
                "rationale": "Good potential but verify specific skills",
                "next_step": "Phone screen to clarify experience",
                "confidence": "Medium"
            }
        else:
            return {
                "action": "PASS",
                "rationale": "Missing too many core skills",
                "next_step": "Consider for future roles",
                "confidence": "High"
            }
    
    def _calculate_confidence(self, candidate: Any, criteria: Any, 
                             skills_breakdown: Dict) -> float:
        """Calculate confidence in the score (0.0-1.0)."""
        confidence = 0.8  # Base
        
        # Penalize if few skills in criteria
        criteria_skills_count = len(criteria.criteria_skills)
        if criteria_skills_count < 3:
            confidence *= 0.7
        
        # Boost if all skills matched
        missing_count = len(skills_breakdown.get("missing", []))
        if missing_count == 0:
            confidence = min(confidence * 1.1, 1.0)
        
        # Reduce if too many missing
        if missing_count > criteria_skills_count * 0.5:
            confidence *= 0.8
        
        return round(confidence, 2)


def format_explanation_for_display(explanation: Dict) -> str:
    """Format explanation dict into human-readable text."""
    
    candidate = explanation["candidate"]["name"]
    score = explanation["score"]["percentage"]
    breakdown = explanation["breakdown"]["skills"]
    strengths = explanation["insights"]["strengths"]
    gaps = explanation["insights"]["gaps"]
    recommendation = explanation["decision"]["recommendation"]
    next_step = explanation["decision"].get("next_step", "")
    confidence = explanation["confidence"]
    
    text = f"""
📊 MATCH ANALYSIS: {candidate}

⭐ OVERALL SCORE: {score} (Confidence: {confidence:.0%})

✅ STRENGTHS ({len(breakdown['matched'])} matched):
{chr(10).join(['  • ' + s for s in strengths]) if strengths else '  (No strengths identified)'}

⚠️  GAPS ({len(breakdown['missing'])} missing):
{chr(10).join(['  • ' + g for g in gaps]) if gaps else '  (No gaps identified)'}

💡 RECOMMENDATION: {recommendation}
📍 NEXT STEP: {next_step}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    return text
