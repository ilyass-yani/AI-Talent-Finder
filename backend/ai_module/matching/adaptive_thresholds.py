"""
Adaptive Threshold Engine — Domain-Aware Scoring

Adjust matching thresholds based on job domain.
Example: Data Science "high bar" vs Startup "low bar"
"""

from typing import Dict, Tuple
import re
from enum import Enum


class DomainType(str, Enum):
    DATA_SCIENCE = "data_science"
    FINANCE = "finance"
    BACKEND = "backend"
    FRONTEND = "frontend"
    STARTUP = "startup"
    PRODUCT = "product"
    BUSINESS = "business"
    MACHINE_LEARNING = "machine_learning"
    DEVOPS = "devops"
    DEFAULT = "default"


class AdaptiveThresholdEngine:
    """Selects matching thresholds based on job domain."""
    
    DOMAIN_CONFIG = {
        DomainType.DATA_SCIENCE: {
            "accept": 0.75,
            "review": 0.45,
            "confidence": 0.90,
            "rationale": "High bar - specialized talent"
        },
        DomainType.FINANCE: {
            "accept": 0.80,
            "review": 0.50,
            "confidence": 0.85,
            "rationale": "Very strict - compliance critical"
        },
        DomainType.BACKEND: {
            "accept": 0.70,
            "review": 0.40,
            "confidence": 0.85,
            "rationale": "Moderate - diverse tech ok"
        },
        DomainType.FRONTEND: {
            "accept": 0.70,
            "review": 0.38,
            "confidence": 0.80,
            "rationale": "Moderate - UX skills valuable"
        },
        DomainType.STARTUP: {
            "accept": 0.60,
            "review": 0.30,
            "confidence": 0.75,
            "rationale": "Low bar - versatility valued"
        },
        DomainType.PRODUCT: {
            "accept": 0.65,
            "review": 0.35,
            "confidence": 0.80,
            "rationale": "Moderate - soft skills matter"
        },
        DomainType.BUSINESS: {
            "accept": 0.60,
            "review": 0.32,
            "confidence": 0.75,
            "rationale": "Low bar - personality critical"
        },
        DomainType.MACHINE_LEARNING: {
            "accept": 0.78,
            "review": 0.48,
            "confidence": 0.90,
            "rationale": "High bar - specialized"
        },
        DomainType.DEVOPS: {
            "accept": 0.72,
            "review": 0.42,
            "confidence": 0.85,
            "rationale": "High bar - reliability critical"
        },
        DomainType.DEFAULT: {
            "accept": 0.80,
            "review": 0.50,
            "confidence": 0.80,
            "rationale": "Standard thresholds"
        }
    }
    
    DOMAIN_KEYWORDS = {
        DomainType.DATA_SCIENCE: [
            "data scientist", "data science", "analytics", "statistical",
            "machine learning", "ml engineer", "data engineer", "big data", "analyst"
        ],
        DomainType.FINANCE: [
            "financial", "accountant", "trader", "analyst", "finance",
            "risk", "banking", "investment", "portfolio", "accounting"
        ],
        DomainType.BACKEND: [
            "backend", "server", "api", "python", "java", "golang", "rust",
            "infrastructure", "architect", "systems engineer", "performance"
        ],
        DomainType.FRONTEND: [
            "frontend", "ui", "ux", "react", "vue", "angular",
            "web developer", "designer", "visual", "css", "javascript"
        ],
        DomainType.STARTUP: [
            "startups", "founder", "early stage", "mvp", "bootstrapped",
            "rapid", "agile", "full stack", "jack of all trades", "gig"
        ],
        DomainType.PRODUCT: [
            "product manager", "pm", "product owner", "po",
            "roadmap", "strategy", "vision", "user experience", "product"
        ],
        DomainType.BUSINESS: [
            "sales", "business development", "marketing", "bd",
            "account manager", "customer", "commercial", "partnership", "growth"
        ],
        DomainType.MACHINE_LEARNING: [
            "machine learning", "ml", "deep learning", "neural",
            "tensorflow", "pytorch", "ai engineer", "ai scientist", "cv"
        ],
        DomainType.DEVOPS: [
            "devops", "sre", "kubernetes", "docker", "infrastructure",
            "ci/cd", "deployment", "cloud", "aws", "gcp", "azure", "terraform"
        ],
    }
    
    def detect_domain(self, job_title: str) -> DomainType:
        """Detect job domain from title."""
        if not job_title:
            return DomainType.DEFAULT
        
        job_lower = job_title.lower()
        domain_scores = {}
        
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in job_lower)
            domain_scores[domain] = score
        
        best_domain = max(domain_scores.items(), key=lambda x: x[1])[0]
        
        if domain_scores[best_domain] == 0:
            return DomainType.DEFAULT
        
        return best_domain
    
    def get_thresholds(self, job_title: str) -> Dict[str, float]:
        """Get adaptive thresholds for a job."""
        domain = self.detect_domain(job_title)
        config = self.DOMAIN_CONFIG.get(domain, self.DOMAIN_CONFIG[DomainType.DEFAULT])
        
        return {
            "accept": config["accept"],
            "review": config["review"],
            "confidence": config["confidence"],
        }
    
    def get_thresholds_with_explanation(self, job_title: str) -> Dict:
        """Get thresholds with explanation."""
        domain = self.detect_domain(job_title)
        config = self.DOMAIN_CONFIG.get(domain, self.DOMAIN_CONFIG[DomainType.DEFAULT])
        
        return {
            "domain": domain.value,
            "job_title": job_title,
            "thresholds": {
                "accept": config["accept"],
                "review": config["review"],
                "confidence": config["confidence"],
            },
            "rationale": config["rationale"],
        }
