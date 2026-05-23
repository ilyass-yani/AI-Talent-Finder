"""
Smart Fallback Module — Context-Aware Responses Without API

When Anthropic API is unavailable, provide intelligent fallback responses
using data from the database instead of generic templates.
"""

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SmartFallbackResponder:
    """Generate context-aware fallback responses without LLM API."""
    
    def explain_score_fallback(self, candidate: Any, criteria: Any, 
                              match_score: float, explanation: Optional[Dict] = None) -> str:
        """Fallback explanation when Claude API unavailable."""
        
        # Use explainability data if provided
        if explanation:
            strengths = explanation.get("insights", {}).get("strengths", [])
            gaps = explanation.get("insights", {}).get("gaps", [])
            recommendation = explanation.get("decision", {}).get("recommendation", "REVIEW")
            next_step = explanation.get("decision", {}).get("next_step", "")
        else:
            # Build from scratch
            candidate_skill_names = {s.skill.name for s in candidate.candidate_skills if s.skill}
            criteria_skill_names = {c.skill.name for c in criteria.criteria_skills if c.skill}
            
            strengths = [f"{s}" for s in list(candidate_skill_names & criteria_skill_names)[:3]]
            gaps = [f"{s}" for s in list(criteria_skill_names - candidate_skill_names)[:3]]
            
            if match_score >= 0.80:
                recommendation = "ACCEPT"
                next_step = "Schedule interview"
            elif match_score >= 0.50:
                recommendation = "REVIEW"
                next_step = "Phone screen"
            else:
                recommendation = "PASS"
                next_step = "Keep in database"
        
        strengths_text = ", ".join(strengths) if strengths else "(None identified)"
        gaps_text = ", ".join(gaps) if gaps else "(None identified)"
        
        return f"""
📊 {candidate.full_name} — {criteria.title}

⭐ Score: {match_score:.1%}

✨ Strengths: {strengths_text}

⚠️  Gaps: {gaps_text}

💡 Status: {recommendation}
📍 Next: {next_step}
"""
    
    def compare_candidates_fallback(self, candidates_with_scores: List[tuple],
                                    criteria: Any) -> str:
        """Fallback comparison of multiple candidates."""
        
        if len(candidates_with_scores) < 2:
            return "Need at least 2 candidates to compare."
        
        # Sort by score descending
        sorted_list = sorted(candidates_with_scores, key=lambda x: x[1], reverse=True)
        
        lines = [f"📊 CANDIDATE COMPARISON — {criteria.title}", ""]
        
        for i, (candidate, score) in enumerate(sorted_list[:5], 1):
            status = "🟢 STRONG" if score >= 0.80 else "🟡 REVIEW" if score >= 0.50 else "🔴 PASS"
            lines.append(f"{i}. {candidate.full_name}: {score:.1%} {status}")
        
        if len(sorted_list) >= 2:
            winner = sorted_list[0]
            runner_up = sorted_list[1]
            gap = winner[1] - runner_up[1]
            lines.append("")
            lines.append(f"🏆 Recommendation: {winner[0].full_name} leads by +{gap:.1%}")
        
        return "\n".join(lines)
    
    def ideal_profile_fallback(self, criteria: Any) -> str:
        """Fallback ideal profile generation."""
        
        if not criteria.criteria_skills:
            return "No criteria skills defined yet."
        
        # Sort by weight
        sorted_skills = sorted(
            criteria.criteria_skills,
            key=lambda x: x.weight,
            reverse=True
        )
        
        top_5 = sorted_skills[:5]
        total_weight = sum(c.weight for c in top_5)
        
        lines = [f"👤 IDEAL PROFILE — {criteria.title}", ""]
        lines.append("🎯 Core Competencies:")
        
        for skill in top_5:
            pct = (skill.weight / total_weight * 100) if total_weight else 0
            lines.append(f"  • {skill.skill.name}: {skill.weight}% importance")
        
        lines.append("")
        lines.append("📋 Expected Background:")
        lines.append(f"  • Master the top {len(top_5)} skills above")
        lines.append("  • 3-5 years of relevant experience")
        lines.append("  • Bachelor degree or equivalent")
        lines.append("  • Strong communication & collaboration")
        
        lines.append("")
        lines.append("💡 Nice to Have:")
        lines.append("  • Experience in similar industry")
        lines.append("  • Track record of shipping products")
        lines.append("  • Growth mindset & continuous learning")
        
        return "\n".join(lines)
    
    def search_candidates_fallback(self, candidates: List[Any], skill: str,
                                   min_score: Optional[float] = None) -> str:
        """Fallback search for candidates by skill."""
        
        matching = []
        
        for candidate in candidates:
            skill_names = {s.skill.name.lower() for s in candidate.candidate_skills if s.skill}
            if skill.lower() in skill_names or skill.lower() in candidate.raw_text.lower():
                matching.append(candidate.full_name)
        
        if matching:
            return f"Found {len(matching)} candidates with {skill}:\n" + \
                   "\n".join([f"  • {name}" for name in matching[:10]])
        else:
            return f"No candidates found with skill: {skill}"
    
    def adjust_weight_fallback(self, criteria: Any, skill_name: str,
                              new_weight: int) -> str:
        """Fallback weight adjustment confirmation."""
        
        # Find the skill
        for criterion in criteria.criteria_skills:
            if criterion.skill and criterion.skill.name.lower() == skill_name.lower():
                old_weight = criterion.weight
                
                # Show impact
                lines = [
                    f"✅ Weight adjusted: {criterion.skill.name}",
                    f"  Before: {old_weight}%",
                    f"  After: {new_weight}%",
                    f"  Change: {new_weight - old_weight:+d}%",
                    "",
                    "Updated priorities:",
                ]
                
                # Show new rankings
                sorted_skills = sorted(
                    criteria.criteria_skills,
                    key=lambda x: x.weight,
                    reverse=True
                )
                
                for rank, cs in enumerate(sorted_skills[:5], 1):
                    marker = "→" if cs.skill.name.lower() == skill_name.lower() else " "
                    lines.append(f"  {marker} {rank}. {cs.skill.name}: {cs.weight}%")
                
                return "\n".join(lines)
        
        return f"Skill {skill_name} not found in criteria."
    
    def greeting_fallback(self, criteria: Optional[Any] = None,
                         top_candidate: Optional[Any] = None) -> str:
        """Fallback greeting message."""
        
        if criteria and top_candidate:
            return f"""
👋 Salut! Je suis votre assistant de recrutement.

Je suis prêt à vous aider pour: {criteria.title}

🏆 Meilleur candidat actuel: {top_candidate.full_name}

Vous pouvez:
  • "Explique le score de [candidat]"
  • "Compare [candidat1] vs [candidat2]"
  • "Cherche des candidats avec [skill]"
  • "Augmente le poids de [skill]"
  • "Qui est le profil idéal?"
"""
        else:
            return """
👋 Salut! Je suis votre assistant de recrutement.

Commencez par lancer un matching ou charger une matrice de critères.
"""
