"""Phase 3: Skill Recommendations Engine - Suggest trending skills and certifications."""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from collections import Counter
import json


@dataclass
class SkillRecommendation:
    """Single skill recommendation."""
    skill_name: str
    frequency: int  # How many successful candidates have it
    trending_score: float  # 0-1, how trending it is
    category: str  # "tech" | "soft" | "language"
    reason: str  # Why we recommend it
    average_proficiency: str  # "beginner" | "intermediate" | "advanced"


class SkillRecommendationsEngine:
    """
    Suggest skills based on:
    - Frequently matched skills for job domain
    - Trending skills across successful hires
    - Skills that close gaps for hard-to-fill positions
    """

    def __init__(self, db=None):
        """Initialize with optional database session."""
        self.db = db
        # Predefined trending skills per domain (fallback if no DB data)
        self.domain_trends = {
            "data science": [
                ("Python", 0.95, 150),
                ("Machine Learning", 0.92, 120),
                ("SQL", 0.90, 140),
                ("TensorFlow", 0.85, 90),
                ("PyTorch", 0.84, 85),
                ("Statistical Analysis", 0.82, 100),
                ("Pandas", 0.80, 95),
            ],
            "backend": [
                ("Python", 0.93, 180),
                ("JavaScript/Node.js", 0.91, 160),
                ("Java", 0.88, 150),
                ("Docker", 0.86, 130),
                ("Kubernetes", 0.82, 100),
                ("SQL", 0.90, 140),
                ("REST APIs", 0.87, 120),
                ("Message Queues", 0.75, 60),
            ],
            "frontend": [
                ("React", 0.94, 200),
                ("JavaScript", 0.95, 210),
                ("TypeScript", 0.88, 140),
                ("CSS", 0.92, 180),
                ("Vue.js", 0.78, 100),
                ("Angular", 0.75, 95),
                ("UI/UX Design", 0.70, 80),
                ("Responsive Design", 0.85, 130),
            ],
            "devops": [
                ("Docker", 0.92, 140),
                ("Kubernetes", 0.89, 120),
                ("CI/CD", 0.91, 130),
                ("Jenkins", 0.80, 95),
                ("AWS", 0.88, 125),
                ("Terraform", 0.82, 100),
                ("Monitoring", 0.75, 85),
                ("Security", 0.80, 90),
            ],
            "ai": [
                ("Python", 0.94, 170),
                ("Machine Learning", 0.93, 140),
                ("Deep Learning", 0.90, 120),
                ("NLP", 0.85, 95),
                ("Transformers", 0.82, 85),
                ("TensorFlow", 0.86, 100),
                ("PyTorch", 0.85, 95),
                ("Research", 0.75, 70),
            ],
        }

    def recommend_skills(
        self,
        job_title: str,
        current_skills: List[str],
        missing_skills: List[str],
        top_k: int = 5,
    ) -> List[SkillRecommendation]:
        """
        Recommend skills for a job position.
        
        Args:
            job_title: Job title (to infer domain)
            current_skills: Skills candidate already has
            missing_skills: Skills required but candidate lacks
            top_k: Number of recommendations to return
        
        Returns:
            List of SkillRecommendation ordered by relevance
        """
        domain = self._infer_domain(job_title)
        recommendations = []
        
        # Get trending skills for domain
        trending = self.domain_trends.get(domain, [])
        
        # Filter: recommend skills that fill gaps
        for skill_name, trending_score, frequency in trending:
            if skill_name.lower() in [s.lower() for s in current_skills]:
                continue  # Skip skills candidate already has
            
            # Higher score if skill is in missing_skills (prioritize gaps)
            is_gap_filler = any(
                skill_name.lower() in missing_skill.lower()
                for missing_skill in missing_skills
            )
            
            reason = f"Trending in {domain}; ~{frequency} successful hires"
            if is_gap_filler:
                reason += " (closes critical gap)"
                trending_score += 0.05  # Boost for gap-filling
            
            recommendations.append(
                SkillRecommendation(
                    skill_name=skill_name,
                    frequency=frequency,
                    trending_score=min(1.0, trending_score),
                    category="tech",
                    reason=reason,
                    average_proficiency="intermediate",
                )
            )
        
        # Sort by trending_score descending
        recommendations.sort(key=lambda r: r.trending_score, reverse=True)
        
        return recommendations[:top_k]

    def get_complementary_skills(
        self,
        primary_skills: List[str],
        job_domain: str,
        top_k: int = 3,
    ) -> List[Dict]:
        """Suggest complementary skills to existing ones."""
        complementary_map = {
            "Python": ["SQL", "Git", "Data Analysis"],
            "React": ["JavaScript", "TypeScript", "CSS"],
            "Docker": ["Kubernetes", "CI/CD", "Linux"],
            "Java": ["Spring Boot", "Maven", "Test Automation"],
            "AWS": ["Docker", "Terraform", "CloudFormation"],
        }
        
        recommendations = []
        for skill in primary_skills:
            if skill in complementary_map:
                for comp_skill in complementary_map[skill]:
                    recommendations.append({
                        "primary_skill": skill,
                        "complementary": comp_skill,
                        "reason": f"Commonly paired with {skill}",
                    })
        
        return recommendations[:top_k]

    def get_certification_recommendations(self, job_title: str) -> List[Dict]:
        """Suggest relevant certifications for job domain."""
        certification_map = {
            "data science": [
                {"name": "Google Data Analytics", "platform": "Coursera", "difficulty": "beginner"},
                {"name": "AWS ML Specialty", "platform": "AWS", "difficulty": "advanced"},
                {"name": "Google Cloud ML Engineer", "platform": "Google Cloud", "difficulty": "advanced"},
            ],
            "backend": [
                {"name": "AWS Solutions Architect", "platform": "AWS", "difficulty": "intermediate"},
                {"name": "Kubernetes Administrator (CKA)", "platform": "Linux Foundation", "difficulty": "advanced"},
                {"name": "Docker Certified", "platform": "Docker", "difficulty": "intermediate"},
            ],
            "frontend": [
                {"name": "React Developer Certification", "platform": "Scrimba", "difficulty": "intermediate"},
                {"name": "Google UX Design", "platform": "Coursera", "difficulty": "beginner"},
                {"name": "Web Design Responsive", "platform": "freeCodeCamp", "difficulty": "beginner"},
            ],
            "devops": [
                {"name": "CKA - Kubernetes", "platform": "Linux Foundation", "difficulty": "advanced"},
                {"name": "AWS Solutions Architect", "platform": "AWS", "difficulty": "intermediate"},
                {"name": "Terraform Associate", "platform": "HashiCorp", "difficulty": "intermediate"},
            ],
            "security": [
                {"name": "CompTIA Security+", "platform": "CompTIA", "difficulty": "intermediate"},
                {"name": "CEH - Ethical Hacker", "platform": "EC-Council", "difficulty": "advanced"},
                {"name": "CISSP", "platform": "ISC2", "difficulty": "expert"},
            ],
        }
        
        domain = self._infer_domain(job_title)
        return certification_map.get(domain, [])

    def analyze_skill_gaps(
        self,
        candidate_skills: List[str],
        required_skills: List[str],
    ) -> Dict:
        """Analyze which skills to prioritize learning."""
        missing = set(s.lower() for s in required_skills) - set(
            s.lower() for s in candidate_skills
        )
        
        # Prioritize high-frequency skills
        skill_priority = {
            "python": 1,
            "javascript": 2,
            "sql": 2,
            "docker": 3,
            "react": 3,
            "kubernetes": 4,
            "aws": 4,
        }
        
        priority_gaps = sorted(
            missing,
            key=lambda s: skill_priority.get(s, 5)
        )
        
        return {
            "total_missing": len(missing),
            "missing_skills": list(missing),
            "priority_order": priority_gaps[:5],
            "learning_path": self._generate_learning_path(priority_gaps[:5]),
        }

    def _infer_domain(self, job_title: str) -> str:
        """Infer job domain from title."""
        title_lower = job_title.lower()
        
        domain_keywords = {
            "data science": ["data scientist", "ml", "machine", "analytics"],
            "backend": ["backend", "server", "api", "django", "flask", "nodejs"],
            "frontend": ["frontend", "react", "vue", "angular", "web"],
            "devops": ["devops", "infrastructure", "sre", "cloud"],
            "ai": ["ai", "nlp", "deep", "artificial", "neural"],
            "security": ["security", "infosec", "penetration"],
        }
        
        for domain, keywords in domain_keywords.items():
            if any(kw in title_lower for kw in keywords):
                return domain
        
        return "backend"  # Default

    def _generate_learning_path(self, skills: List[str]) -> List[Dict]:
        """Generate learning recommendations for skills."""
        paths = []
        for skill in skills[:3]:  # Top 3 skills
            paths.append({
                "skill": skill.title(),
                "resources": self._get_learning_resources(skill),
                "estimated_hours": 40 if skill in ["docker", "kubernetes"] else 30,
            })
        return paths

    def _get_learning_resources(self, skill: str) -> List[str]:
        """Get recommended learning resources for skill."""
        resources_map = {
            "python": ["Real Python", "Codecademy", "DataCamp"],
            "javascript": ["MDN Docs", "freeCodeCamp", "JavaScript.info"],
            "react": ["React Docs", "Scrimba React Course", "egghead.io"],
            "docker": ["Docker Docs", "Play with Docker", "Docker Mastery"],
            "kubernetes": ["Kubernetes Docs", "KataCoda", "Linux Academy"],
            "sql": ["W3Schools", "HackerRank", "LeetCode"],
        }
        return resources_map.get(skill.lower(), ["Official Documentation", "Coursera", "Udemy"])
