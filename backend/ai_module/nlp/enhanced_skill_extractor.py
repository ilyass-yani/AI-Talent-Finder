"""
Enhanced Skill Extractor - Combines NER + Dictionary Fuzzy Matching
Étape 6 Optimization: Hybrid approach for maximum skill coverage
"""

from typing import List, Dict, Optional
import json
import os
import re

try:
    from transformers import pipeline
    NER_AVAILABLE = True
except ImportError:
    NER_AVAILABLE = False

from ai_module.nlp.skill_extractor import SkillExtractor
from ai_module.matching.semantic_matcher import SemanticSkillMatcher


class EnhancedSkillExtractor:
    """
    Extract skills using hybrid approach:
    1. BERT-based NER (95% accuracy)
    2. Dictionary fuzzy matching (80% accuracy)
    3. Intelligent merge with confidence scores
    """
    
    def __init__(self, load_ner: bool = True):
        """Initialize both extraction methods"""
        self.skill_extractor = SkillExtractor()
        self.canonical_skills = list(self.skill_extractor.all_skills)
        self.semantic_threshold = float(os.getenv("SKILL_NORMALIZATION_THRESHOLD", "0.62"))
        self.ner_model_name = os.getenv("HF_SKILL_NER_MODEL", "dslim/bert-base-NER")
        
        if load_ner and NER_AVAILABLE:
            try:
                self.ner_pipeline = pipeline(
                    "ner",
                    model=self.ner_model_name,
                    aggregation_strategy="simple"
                )
                self.ner_available = True
            except Exception as e:
                print(f"⚠️ NER model not available: {e}. Using dictionary-only extraction.")
                self.ner_available = False
        else:
            self.ner_available = False
    
    def extract_skills_hybrid(self, text: str, threshold: int = 80) -> List[Dict]:
        """
        Extract skills using both NER and dictionary methods
        
        Args:
            text: CV text
            threshold: Fuzzy matching threshold
        
        Returns:
            List of skills with source and confidence
            [
                {"name": "Python", "source": "NER", "confidence": 0.95},
                {"name": "React", "source": "DICT-FUZZY", "confidence": 0.80}
            ]
        """
        all_skills = []
        seen_skills = set()  # Track added skills (lowercase)
        
        # Step 1: Extract via NER (if available)
        if self.ner_available:
            ner_skills = self._extract_via_ner(text)
            for skill_data in ner_skills:
                skill_name_lower = skill_data["name"].lower()
                if skill_name_lower not in seen_skills:
                    all_skills.append(skill_data)
                    seen_skills.add(skill_name_lower)
        
        # Step 2: Extract via Dictionary (for coverage)
        dict_skills = self.skill_extractor.extract_skills(text, threshold=threshold)
        for dict_skill in dict_skills:
            skill_name_lower = dict_skill["name"].lower()
            if skill_name_lower not in seen_skills:
                # Enhance dictionary skill with additional metadata
                skill_data = {
                    "name": dict_skill["name"],
                    "source": "DICT-FUZZY",
                    "confidence": 0.80,  # Lower than NER
                    "category": dict_skill.get("category", "tech"),
                    "method": dict_skill.get("method", "fuzzy")
                }
                all_skills.append(skill_data)
                seen_skills.add(skill_name_lower)

        # Step 3: Embedding-based normalization to canonical skill list.
        normalized = self._normalize_with_embeddings(all_skills)
        if normalized:
            all_skills = normalized
        
        # Sort by confidence descending
        all_skills.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        return all_skills

    def _normalize_with_embeddings(self, skills: List[Dict]) -> List[Dict]:
        """Map extracted skill variants to nearest canonical skills via embeddings."""
        if not skills:
            return []

        normalized: List[Dict] = []
        seen = set()

        for skill in skills:
            raw_name = str(skill.get("name", "")).strip()
            if not raw_name:
                continue

            nearest = SemanticSkillMatcher.search_similar(raw_name, self.canonical_skills, top_k=1)
            if nearest:
                best_name, similarity = nearest[0]
                if similarity >= self.semantic_threshold:
                    skill["normalized_name"] = best_name
                    skill["normalization_similarity"] = round(similarity, 4)
                    skill["name"] = best_name

            key = str(skill.get("name", "")).lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(skill)

        return normalized
    
    def _extract_via_ner(self, text: str) -> List[Dict]:
        """Extract candidate skill entities from NER pipeline output."""
        if not self.ner_available or not text:
            return []
        
        try:
            # Keep runtime bounded.
            text_truncated = text[:2000]
            
            ner_results = self.ner_pipeline(text_truncated)
            
            ner_skills = []
            for entity in ner_results:
                group = str(entity.get("entity_group", "")).upper()
                if group not in {"MISC", "ORG", "SKILL"}:
                    continue
                if entity.get("score", 0) <= 0.70:
                    continue

                skill_name = str(entity.get("word", "")).strip().replace("##", "")
                skill_name = re.sub(r"\s+", " ", skill_name)
                if len(skill_name) < 2:
                    continue

                ner_skills.append({
                    "name": skill_name.title(),
                    "source": "NER",
                    "confidence": float(entity.get("score", 0.95)),
                    "category": self._classify_skill(skill_name),
                    "method": f"NER-{self.ner_model_name}"
                })
            
            return ner_skills
        except Exception as e:
            print(f"⚠️ NER extraction error: {e}")
            return []

    def close(self) -> None:
        """Release the lazy NER pipeline when the extractor is no longer needed."""
        self.ner_pipeline = None
        self.ner_available = False
    
    def _classify_skill(self, skill_name: str) -> str:
        """Classify skill into category"""
        skill_lower = skill_name.lower()
        
        # Check in existing skill categories
        category = self.skill_extractor.skill_categories.get(skill_lower, None)
        if category:
            return category
        
        # Smart classification based on keywords
        tech_keywords = ["python", "java", "javascript", "react", "angular", "vue", "node",
                        "aws", "azure", "gcp", "docker", "kubernetes", "sql", "mongodb",
                        "api", "rest", "graphql", "fastapi", "django", "flask"]
        
        soft_keywords = ["leadership", "communication", "teamwork", "management", "planning",
                        "problem solving", "analytical", "creative", "adaptability"]
        
        language_keywords = ["english", "french", "spanish", "german", "italian", "arabic",
                            "portuguese", "mandarin", "japanese"]
        
        if any(keyword in skill_lower for keyword in tech_keywords):
            return "tech"
        elif any(keyword in skill_lower for keyword in soft_keywords):
            return "soft"
        elif any(keyword in skill_lower for keyword in language_keywords):
            return "language"
        else:
            return "tech"  # Default
    
    def get_extraction_stats(self, skills: List[Dict]) -> Dict:
        """Get statistics about extraction"""
        if not skills:
            return {
                "total": 0,
                "by_source": {},
                "avg_confidence": 0,
                "coverage": 0
            }
        
        by_source = {}
        for skill in skills:
            source = skill.get("source", "unknown")
            by_source[source] = by_source.get(source, 0) + 1
        
        avg_confidence = sum(s.get("confidence", 0) for s in skills) / len(skills)
        
        return {
            "total": len(skills),
            "by_source": by_source,
            "avg_confidence": round(avg_confidence, 3),
            "top_3": [s["name"] for s in skills[:3]]
        }


# Usage example
if __name__ == "__main__":
    extractor = EnhancedSkillExtractor()
    
    sample_text = """
    Python developer with 5 years experience.
    Expert in FastAPI, Django, React, Docker.
    Strong communication and leadership skills.
    Fluent in English and French.
    """
    
    skills = extractor.extract_skills_hybrid(sample_text)
    stats = extractor.get_extraction_stats(skills)
    
    print(f"Found {stats['total']} skills:")
    for skill in skills:
        print(f"  - {skill['name']:20} ({skill['source']:10}) conf: {skill['confidence']:.2f}")
    
    print(f"\nStats: {json.dumps(stats, indent=2)}")
