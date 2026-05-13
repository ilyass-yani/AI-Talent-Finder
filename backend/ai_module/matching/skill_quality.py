"""
Skill Quality Metrics — Monitor Dictionary Health

Track usage, coverage, and quality of the skill dictionary.
"""

from typing import Dict, List, Any
from collections import Counter
import logging

logger = logging.getLogger(__name__)


class SkillQualityAnalyzer:
    """Analyze and report on skill dictionary quality."""
    
    def compute_metrics(self, db: Any) -> Dict:
        """Compute comprehensive skill quality metrics."""
        
        try:
            from app.models.models import Skill, CandidateSkill
        except ImportError:
            logger.warning("Could not import models")
            return {}
        
        # Get all skills and usage
        all_skills = db.query(Skill).all()
        all_candidate_skills = db.query(CandidateSkill).all()
        
        # Compute metrics
        total_skills = len(all_skills)
        skill_usage = Counter([cs.skill.name for cs in all_candidate_skills if cs.skill])
        unique_skills = len(skill_usage)
        average_usage = round((sum(skill_usage.values()) / max(1, unique_skills)), 2)
        
        # Find unused skills
        used_skill_names = set(skill_usage.keys())
        unused_skills = [s.name for s in all_skills if s.name not in used_skill_names]
        
        # Compute coverage (Pareto)
        total_usage = sum(skill_usage.values())
        cumulative = 0
        skills_for_80_percent = 0
        
        for skill, count in skill_usage.most_common():
            cumulative += count
            skills_for_80_percent += 1
            if cumulative >= total_usage * 0.80:
                break
        
        coverage_ratio = skills_for_80_percent / max(1, len(skill_usage))
        coverage_percentage = round((unique_skills / max(1, total_skills)) * 100, 1)

        quality_score = self._compute_quality_score(
            total_skills, len(unused_skills), coverage_ratio
        )

        if quality_score >= 85:
            health_status = "excellent"
        elif quality_score >= 70:
            health_status = "good"
        elif quality_score >= 50:
            health_status = "fair"
        else:
            health_status = "poor"

        pareto_analysis = {
            "skills_for_80_percent": skills_for_80_percent,
            "pareto_ratio": round(coverage_ratio, 2),
            "coverage_percent": coverage_percentage,
        }

        trending_missing = self.detect_trending_skills(db)
        
        return {
            "total_skills": total_skills,
            "skills_in_use": len(skill_usage),
            "unique_skills": unique_skills,
            "average_usage": average_usage,
            "coverage_percentage": coverage_percentage,
            "unused_skills_count": len(unused_skills),
            "unused_skills": unused_skills[:20],
            "unused_skills_list": unused_skills[:20],  # Backward compatibility
            "most_used_skills": [
                {"skill": name, "usage_count": count}
                for name, count in skill_usage.most_common(10)
            ],
            "coverage": {
                "total_usage_records": total_usage,
                "skills_for_80_percent": skills_for_80_percent,
                "pareto_ratio": round(coverage_ratio, 2),
                "coverage_percent": coverage_percentage,
            },
            "quality_score": quality_score,
            "health_status": health_status,
            "pareto_analysis": pareto_analysis,
            "trending_missing": trending_missing,
            "recommendations": self._generate_recommendations(
                unused_skills, skill_usage, total_skills
            ),
        }
    
    def _compute_quality_score(self, total_skills: int, unused_count: int,
                               coverage_ratio: float) -> float:
        """
        Compute overall quality score (0-100).
        
        Factors:
        - Unused skills (penalty)
        - Coverage concentration (bonus if concentrated)
        """
        
        # Start at 100
        score = 100.0
        
        # Penalize unused skills
        unused_ratio = unused_count / max(1, total_skills)
        score -= unused_ratio * 20
        
        # Penalize if too scattered (good coverage is ~0.15-0.25)
        if coverage_ratio > 0.30:
            score -= (coverage_ratio - 0.30) * 10
        
        # Bonus if well-concentrated
        if 0.10 <= coverage_ratio <= 0.25:
            score += 10
        
        return max(0, min(100, round(score, 1)))
    
    def _generate_recommendations(self, unused_skills: List[str],
                                 skill_usage: Counter,
                                 total_skills: int) -> List[str]:
        """Generate actionable recommendations."""
        
        recommendations = []
        
        # Recommendation 1: Remove unused
        if len(unused_skills) > total_skills * 0.2:
            recommendations.append(
                f"🗑️  Remove {len(unused_skills)} unused skills to reduce clutter"
            )
        
        # Recommendation 2: Add trending
        if skill_usage:
            top_skill_count = max(skill_usage.values())
            if top_skill_count < 100:
                recommendations.append(
                    "📈 Consider adding more high-demand skills (usage < 100 records)"
                )
        
        # Recommendation 3: Balance
        if len(unused_skills) > 0:
            recommendations.append(
                f"⚖️  Review/consolidate remaining {len(unused_skills)} unused skills"
            )
        
        if not recommendations:
            recommendations.append("✅ Skill dictionary in good health!")
        
        return recommendations
    
    def get_skill_health_report(self, db: Any) -> str:
        """Generate human-readable health report."""
        
        metrics = self.compute_metrics(db)
        
        if not metrics:
            return "Unable to compute skill metrics"
        
        lines = [
            "📊 SKILL DICTIONARY HEALTH REPORT",
            "=" * 50,
            "",
            f"Total Skills: {metrics['total_skills']}",
            f"In Active Use: {metrics['skills_in_use']}",
            f"Unused: {metrics['unused_skills_count']}",
            f"Quality Score: {metrics['quality_score']}/100",
            "",
            "🎯 Coverage (Pareto):",
            f"  {metrics['coverage']['skills_for_80_percent']} skills cover 80% of usage",
            f"  Coverage ratio: {metrics['coverage']['pareto_ratio']}",
            f"  Dictionary utilization: {metrics['coverage']['coverage_percent']}%",
            "",
            "⭐ Top 5 Most Used:",
        ]
        
        for item in metrics.get('most_used_skills', [])[:5]:
            lines.append(f"  • {item['skill']}: {item['usage_count']} uses")
        
        if len(metrics.get('unused_skills_list', [])) > 0:
            lines.append("")
            lines.append("⚠️  Unused Skills (sample):")
            for skill in metrics['unused_skills_list'][:5]:
                lines.append(f"  • {skill}")
            if len(metrics.get('unused_skills_list', [])) > 5:
                lines.append(f"  ... and {len(metrics['unused_skills_list']) - 5} more")
        
        lines.append("")
        lines.append("💡 Recommendations:")
        for rec in metrics.get('recommendations', []):
            lines.append(f"  {rec}")
        
        return "\n".join(lines)
    
    def detect_trending_skills(self, db: Any, candidate_count_threshold: int = 2) -> List[str]:
        """Detect skills appearing frequently but not in our dict."""
        
        try:
            from app.models.models import Skill, CandidateSkill
        except ImportError:
            return []
        
        all_candidate_skills = db.query(CandidateSkill).all()
        dict_skills = {s.name.lower() for s in db.query(Skill).all()}
        
        # Count extracted skills
        extracted_skill_counts = Counter()
        
        for cs in all_candidate_skills:
            if cs.skill:
                extracted_skill_counts[cs.skill.name.lower()] += 1
        
        # Find frequently used but possibly missing
        trending = [
            skill for skill, count in extracted_skill_counts.items()
            if count >= candidate_count_threshold and skill not in dict_skills
        ]
        
        return sorted(trending, key=lambda s: extracted_skill_counts[s], reverse=True)
