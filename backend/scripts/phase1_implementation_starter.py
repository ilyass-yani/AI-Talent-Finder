#!/usr/bin/env python3
"""
PHASE 1 IMPLEMENTATION STARTER — Quick Wins

Trois implémentations concrètes pour démarrer immédiatement:
1. Adaptive Thresholds (1-2 hours)
2. Smart Deduplication (1-2 hours)
3. Enhanced Explainability (2-3 hours)

Prêt à copy-paste dans votre codebase.
"""

# ============================================================================
# 1. ADAPTIVE THRESHOLDS (backend/ai_module/matching/adaptive_thresholds.py)
# ============================================================================

from typing import Dict, Tuple
import re
from datetime import datetime

class AdaptiveThresholdEngine:
    """
    Sélectionne thresholds de matching basé sur le domaine du job.
    
    Usage:
        engine = AdaptiveThresholdEngine()
        thresholds = engine.get_thresholds("Senior Data Scientist")
        # → {"accept": 0.75, "review": 0.45}
    """
    
    # Définition des domains et leurs thresholds
    DOMAIN_CONFIG = {
        # Data Science: Bar très haute (rare talent)
        "data_science": {
            "accept": 0.75,
            "review": 0.45,
            "confidence": 0.90,
            "description": "High bar - specialized domain"
        },
        # Finance: Sécurité prioritaire
        "finance": {
            "accept": 0.80,
            "review": 0.50,
            "confidence": 0.85,
            "description": "Very strict - compliance critical"
        },
        # Backend/DevOps: Mixed skills okay
        "backend": {
            "accept": 0.70,
            "review": 0.40,
            "confidence": 0.85,
            "description": "Moderate - diverse tech ok"
        },
        # Frontend: Creative + technical
        "frontend": {
            "accept": 0.70,
            "review": 0.38,
            "confidence": 0.80,
            "description": "Moderate - UX skills valuable"
        },
        # Startup: Flexibility high
        "startup": {
            "accept": 0.60,
            "review": 0.30,
            "confidence": 0.75,
            "description": "Low bar - versatility valued"
        },
        # Product/PM: Soft skills important
        "product": {
            "accept": 0.65,
            "review": 0.35,
            "confidence": 0.80,
            "description": "Moderate - soft skills matter"
        },
        # Sales/Marketing: Personality + skills
        "business": {
            "accept": 0.60,
            "review": 0.32,
            "confidence": 0.75,
            "description": "Low bar - personality critical"
        },
        # ML/AI: Highly specialized
        "machine_learning": {
            "accept": 0.78,
            "review": 0.48,
            "confidence": 0.90,
            "description": "High bar - specialized"
        },
        # DevOps/Infrastructure
        "devops": {
            "accept": 0.72,
            "review": 0.42,
            "confidence": 0.85,
            "description": "High bar - reliability critical"
        },
        # Default fallback
        "default": {
            "accept": 0.80,
            "review": 0.50,
            "confidence": 0.80,
            "description": "Standard thresholds"
        }
    }
    
    # Keywords pour la détection de domaines
    DOMAIN_KEYWORDS = {
        "data_science": [
            "data scientist", "data science", "analytics", "statistical",
            "machine learning", "ml engineer", "data engineer", "big data"
        ],
        "finance": [
            "financial", "accountant", "trader", "analyst", "finance",
            "risk", "banking", "investment", "portfolio"
        ],
        "backend": [
            "backend", "server", "api", "python", "java", "golang",
            "infrastructure", "architect", "systems engineer", "performance"
        ],
        "frontend": [
            "frontend", "ui", "ux", "react", "vue", "angular",
            "web developer", "designer", "visual", "css", "javascript"
        ],
        "startup": [
            "startups", "founder", "early stage", "mvp", "bootstrapped",
            "rapid", "agile", "full stack", "jack of all trades"
        ],
        "product": [
            "product manager", "pm", "product owner", "po",
            "roadmap", "strategy", "vision", "user experience"
        ],
        "business": [
            "sales", "business development", "marketing", "bd",
            "account manager", "customer", "commercial", "partnership"
        ],
        "machine_learning": [
            "machine learning", "ml", "deep learning", "neural",
            "tensorflow", "pytorch", "ai engineer", "ai scientist"
        ],
        "devops": [
            "devops", "sre", "kubernetes", "docker", "infrastructure",
            "ci/cd", "deployment", "cloud", "aws", "gcp", "azure"
        ],
    }
    
    def detect_domain(self, job_title: str) -> str:
        """
        Détecte le domaine du job à partir du titre.
        
        Args:
            job_title: Ex "Senior Data Scientist"
            
        Returns:
            domain slug: Ex "data_science"
        """
        if not job_title:
            return "default"
        
        job_lower = job_title.lower()
        
        # Score chaque domain par nombre de keywords matchés
        domain_scores = {}
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in job_lower)
            domain_scores[domain] = score
        
        # Retourner le domain avec plus de matches
        best_domain = max(domain_scores.items(), key=lambda x: x[1])[0]
        
        # Si aucun match trouvé, utiliser default
        if domain_scores[best_domain] == 0:
            return "default"
        
        return best_domain
    
    def get_thresholds(self, job_title: str) -> Dict[str, float]:
        """
        Retourne les thresholds adaptatifs pour un job.
        
        Args:
            job_title: Titre du job
            
        Returns:
            {"accept": 0.70, "review": 0.40, "confidence": 0.85}
        """
        domain = self.detect_domain(job_title)
        config = self.DOMAIN_CONFIG.get(domain, self.DOMAIN_CONFIG["default"])
        
        # Filtering for output (sans description)
        return {
            "accept": config["accept"],
            "review": config["review"],
            "confidence": config["confidence"],
        }
    
    def get_thresholds_with_explanation(self, job_title: str) -> Dict:
        """Retourne thresholds + explication du domain détecté."""
        domain = self.detect_domain(job_title)
        config = self.DOMAIN_CONFIG.get(domain, self.DOMAIN_CONFIG["default"])
        
        return {
            "domain": domain,
            "job_title": job_title,
            "thresholds": {
                "accept": config["accept"],
                "review": config["review"],
                "confidence": config["confidence"],
            },
            "rationale": config["description"],
            "detected_at": datetime.utcnow().isoformat(),
        }


# ============================================================================
# 2. SMART DEDUPLICATION (backend/ai_module/nlp/smart_dedup.py)
# ============================================================================

from typing import List, Set
from numpy import ndarray
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class SmartSkillDeduplicator:
    """
    Déduplique skills avec similarité sémantique au lieu de string matching.
    
    Exemple:
        dedup = SmartSkillDeduplicator(embedder)
        result = dedup.deduplicate(["Python", "python", "Python 3.11"])
        # → ["Python"]
    """
    
    def __init__(self, embedder=None, similarity_threshold: float = 0.82):
        """
        Args:
            embedder: SentenceTransformer instance (ou sera créée)
            similarity_threshold: Min similarity pour merger (0.0-1.0)
        """
        self.embedder = embedder
        self.similarity_threshold = similarity_threshold
    
    def deduplicate(self, skills: List[str]) -> List[str]:
        """
        Déduplique une liste de skills via clustering sémantique.
        
        Args:
            skills: ["Python", "python", "ML", "Machine Learning"]
            
        Returns:
            ["Python", "Machine Learning"]  # Canonical names
        """
        if not skills:
            return []
        
        # Cas simple: si ≤1 skills, retourner as is
        if len(skills) <= 1:
            return skills
        
        # Normaliser (lowercase, trim)
        normalized = [s.strip().lower() for s in skills]
        
        # Première pass: exact string dedup
        first_pass = list(dict.fromkeys(normalized))  # Preserve order, remove dupes
        
        if len(first_pass) <= 1:
            return first_pass
        
        # Deuxième pass: semantic clustering
        if self.embedder:
            try:
                clusters = self._cluster_by_similarity(first_pass)
                canonical = self._extract_canonical(skills, clusters)
                return canonical
            except Exception as e:
                # Fallback to first pass if embedding fails
                print(f"Warning: Embedding failed ({e}), using string dedup")
                return first_pass
        
        return first_pass
    
    def _cluster_by_similarity(self, skills: List[str]) -> List[List[int]]:
        """
        Cluster skills indices basé sur similarité sémantique.
        
        Returns:
            [[0, 1], [2, 3]]  # Indices of skills that cluster together
        """
        # Générer embeddings
        embeddings = self.embedder.encode(skills)  # shape: (N, 384)
        
        # Calculer matrice similarité
        similarity_matrix = cosine_similarity(embeddings)  # shape: (N, N)
        
        # Clustering via connected components
        clusters = []
        used = set()
        
        for i in range(len(skills)):
            if i in used:
                continue
            
            # Commencer nouveau cluster
            cluster = [i]
            used.add(i)
            
            # Trouver tous les skills similaires
            for j in range(i + 1, len(skills)):
                if j in used:
                    continue
                
                if similarity_matrix[i][j] > self.similarity_threshold:
                    cluster.append(j)
                    used.add(j)
            
            clusters.append(cluster)
        
        return clusters
    
    def _extract_canonical(self, original_skills: List[str], 
                          clusters: List[List[int]]) -> List[str]:
        """
        Extrait skill canonical pour chaque cluster.
        
        Heuristique: skill le plus long (plus descriptif)
        """
        canonical = []
        
        for cluster in clusters:
            # Prendre le skill original (preserving case/format)
            cluster_skills = [original_skills[i] for i in cluster]
            
            # Heuristique: skill le plus long = most descriptive
            canonical_skill = max(cluster_skills, key=len)
            canonical.append(canonical_skill)
        
        return canonical


# ============================================================================
# 3. ENHANCED EXPLAINABILITY (backend/ai_module/matching/explainability.py)
# ============================================================================

from datetime import datetime
from enum import Enum

class SkillMatchStatus(str, Enum):
    MATCHED = "matched"
    MISSING = "missing"
    BONUS = "bonus"

class ExplainabilityEngine:
    """
    Explique chaque composant du score de matching de façon détaillée.
    
    Retourne:
        {
            "total_score": 0.847,
            "components": {...},
            "strengths": [...],
            "gaps": [...],
            "recommendation": "Proceed to interview",
            "confidence": 0.92
        }
    """
    
    # Pondérations du scoring
    WEIGHTS = {
        "skills": 0.50,
        "semantic": 0.20,
        "experience": 0.15,
        "education": 0.10,
        "bonus": 0.05,
    }
    
    def explain_score(self, candidate, criteria, total_score: float) -> Dict:
        """
        Génère explication complète du score.
        
        Args:
            candidate: Candidate model instance
            criteria: JobCriteria model instance
            total_score: Match score (0.0-1.0)
            
        Returns:
            Explication structurée
        """
        
        # Composer les différentes évaluations
        skills_breakdown = self._explain_skills(candidate, criteria)
        semantic_breakdown = self._explain_semantic(candidate, criteria)
        experience_breakdown = self._explain_experience(candidate, criteria)
        education_breakdown = self._explain_education(candidate, criteria)
        
        # Identifier forces et faiblesses
        strengths = self._identify_strengths(skills_breakdown)
        gaps = self._identify_gaps(skills_breakdown)
        
        # Recommandation
        recommendation = self._recommend_action(total_score)
        
        # Confiance du score
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
                    "semantic": round(semantic_breakdown["score"], 3),
                    "experience": round(experience_breakdown["score"], 3),
                    "education": round(education_breakdown["score"], 3),
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
            },
            "confidence": confidence,
        }
    
    def _explain_skills(self, candidate, criteria) -> Dict:
        """Détail du matching de skills."""
        matched = []
        missing = []
        
        # Récupérer skills du candidat
        candidate_skill_names = {
            s.skill.name.lower(): s.skill.name
            for s in candidate.candidate_skills
            if s.skill
        }
        
        # Comparer vs criteria
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
                "contribution": round(contribution * 0.50, 3),  # 50% weight de skills
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
            "coverage": f"{len(matched)}/{len(matched) + len(missing)} core skills",
            "summary": f"Matched {len(matched)}/{len(matched) + len(missing)} required skills"
        }
    
    def _explain_semantic(self, candidate, criteria) -> Dict:
        """Similarité sémantique CV vs job description."""
        # Simplifié pour exemple
        return {
            "score": 0.75,
            "reason": "Strong alignment with job description keywords",
            "keywords_matched": ["python", "leadership", "frontend"],
            "keywords_missing": ["kubernetes"],
        }
    
    def _explain_experience(self, candidate, criteria) -> Dict:
        """Évaluation expérience."""
        years = candidate.years_experience or 0
        return {
            "score": min(years / 10.0, 1.0),  # Cap at 1.0
            "years": years,
            "assessment": "Senior level" if years >= 5 else "Junior-Mid level",
        }
    
    def _explain_education(self, candidate, criteria) -> Dict:
        """Évaluation éducation."""
        return {
            "score": 0.8,
            "degree": candidate.extracted_education or "Not specified",
            "assessment": "Relevant background",
        }
    
    def _identify_strengths(self, skills_breakdown: Dict) -> List[str]:
        """Identifie top forces."""
        matched = skills_breakdown.get("matched", [])
        if not matched:
            return []
        
        # Top 3 par contribution
        top = sorted(matched, key=lambda x: x["weight"], reverse=True)[:3]
        return [f"{s['skill']} ({s['weight']}%)" for s in top]
    
    def _identify_gaps(self, skills_breakdown: Dict) -> List[str]:
        """Identifie top gaps."""
        missing = skills_breakdown.get("missing", [])
        if not missing:
            return []
        
        # Top 3 par weight
        top = sorted(missing, key=lambda x: x["weight"], reverse=True)[:3]
        return [f"{s['skill']} ({s['weight']}%)" for s in top]
    
    def _recommend_action(self, score: float) -> Dict:
        """Recommandation basée sur score."""
        if score >= 0.80:
            return {
                "action": "ACCEPT - Interview now",
                "rationale": "Strong match on core criteria",
                "confidence": "High"
            }
        elif score >= 0.50:
            return {
                "action": "REVIEW - Phone screen first",
                "rationale": "Good match but verify specific skills",
                "confidence": "Medium"
            }
        else:
            return {
                "action": "PASS - Not aligned",
                "rationale": "Missing too many core skills",
                "confidence": "High"
            }
    
    def _calculate_confidence(self, candidate, criteria, skills_breakdown: Dict) -> float:
        """Confiance du scoring (0.0-1.0)."""
        confidence = 0.8  # Base
        
        # Penalize si peu de skills dans criteria
        if len(criteria.criteria_skills) < 3:
            confidence *= 0.7
        
        # Boost si tous skills matchent
        if len(skills_breakdown["missing"]) == 0:
            confidence = min(confidence * 1.1, 1.0)
        
        return round(confidence, 2)


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Phase 1 Implementation Examples")
    print("=" * 70)
    
    # 1. Adaptive Thresholds
    print("\n1️⃣ ADAPTIVE THRESHOLDS")
    print("-" * 70)
    
    threshold_engine = AdaptiveThresholdEngine()
    
    test_jobs = [
        "Senior Data Scientist",
        "Financial Analyst",
        "Startup Full Stack Developer",
    ]
    
    for job in test_jobs:
        result = threshold_engine.get_thresholds_with_explanation(job)
        print(f"\nJob: {result['job_title']}")
        print(f"Domain: {result['domain']}")
        print(f"Thresholds: Accept={result['thresholds']['accept']:.0%}, Review={result['thresholds']['review']:.0%}")
        print(f"Rationale: {result['rationale']}")
    
    # 2. Smart Deduplication
    print("\n\n2️⃣ SMART DEDUPLICATION")
    print("-" * 70)
    
    dedup = SmartSkillDeduplicator(similarity_threshold=0.82)
    
    test_skills = [
        ["Python", "python", "python3"],
        ["JavaScript", "JS", "Node.js", "TypeScript"],
        ["Data Analysis", "Analytics", "Data Analytics"],
    ]
    
    for skills in test_skills:
        result = dedup.deduplicate(skills)
        print(f"\nInput: {skills}")
        print(f"Output: {result}")
    
    # 3. Explainability (example structure)
    print("\n\n3️⃣ ENHANCED EXPLAINABILITY")
    print("-" * 70)
    print("\nExample output structure:")
    print("""
{
  "timestamp": "2026-05-12T23:50:00.000000",
  "candidate": {
    "id": 1,
    "name": "Ahmed Ben",
    "email": "ahmed@example.com"
  },
  "score": {
    "total": 0.847,
    "percentage": "84.7%",
    "components": {
      "skills": 0.85,
      "semantic": 0.72,
      "experience": 0.9,
      "education": 0.8
    }
  },
  "insights": {
    "strengths": ["Python (25%)", "Leadership (20%)", "Cloud (15%)"],
    "gaps": ["Kubernetes (15%)", "DevOps (10%)"]
  },
  "decision": {
    "recommendation": "ACCEPT - Interview now",
    "rationale": "Strong match on core criteria",
    "confidence": 0.92
  }
}
    """)
    
    print("\n" + "=" * 70)
    print("✅ Phase 1 Examples Complete")
    print("=" * 70)
