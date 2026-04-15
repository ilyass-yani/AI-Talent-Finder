"""
Skill extraction from CV text
Main component of NLP pipeline
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Tuple
from fuzzywuzzy import fuzz
from fuzzywuzzy import process


class SkillExtractor:
    """
    Extract skills from CV text using:
    1. Dictionary matching (exact + fuzzy)
    2. Regex patterns for known technologies
    3. Context-aware extraction
    """
    
    def __init__(self, skills_dict_path: str = None):
        """
        Initialize skill extractor with skills dictionary
        
        Args:
            skills_dict_path: Path to skills_dictionary.json
        """
        if skills_dict_path is None:
            # Default path relative to this file
            skills_dict_path = str(Path(__file__).parent.parent / "data" / "skills_dictionary.json")
        
        self.skills_dict = self._load_skills_dictionary(skills_dict_path)
        self.all_skills = self._flatten_skills_dict()
        self.skill_categories = self._build_category_map()
    
    def _load_skills_dictionary(self, path: str) -> Dict:
        """Load skills dictionary from JSON file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Skills dictionary not found at {path}")
            return {"tech": [], "soft": [], "language": []}
    
    def _flatten_skills_dict(self) -> List[str]:
        """
        Flatten the skills dictionary into a single list of all skills
        """
        all_skills = []
        for category, skills in self.skills_dict.items():
            if isinstance(skills, list):
                all_skills.extend(skills)
        return all_skills
    
    def _build_category_map(self) -> Dict[str, str]:
        """
        Build a mapping of skill name -> category for quick lookups
        """
        category_map = {}
        for category, skills in self.skills_dict.items():
            if isinstance(skills, list):
                for skill in skills:
                    category_map[skill.lower()] = category
        return category_map
    
    def extract_skills(self, text: str, threshold: int = 90) -> List[Dict]:
        """
        Extract skills from text
        
        Args:
            text: CV text content
            threshold: Fuzzy matching threshold (0-100)
        
        Returns:
            List of extracted skills with category and method
            [{"name": "Python", "category": "tech", "method": "exact", "confidence": 100}, ...]
        """
        if not text:
            return []
        
        # Convert to lowercase for matching
        text_lower = text.lower()
        extracted = []
        seen = set()  # To avoid duplicates
        
        # 1. Exact matching
        for skill in self.all_skills:
            skill_lower = skill.lower()
            
            # Check for exact word match (with word boundaries)
            pattern = r'\b' + re.escape(skill_lower) + r'\b'
            if re.search(pattern, text_lower) and skill_lower not in seen:
                extracted.append({
                    "name": skill,
                    "category": self.skill_categories.get(skill.lower(), "unknown"),
                    "method": "exact",
                    "confidence": 100
                })
                seen.add(skill_lower)
        
        # 2. Fuzzy matching for variations
        words = re.findall(r'\b[\w\-]+\b', text_lower)
        unique_words = list(set(words))

        stopwords = {
            "resume", "cv", "profile", "profil", "experience", "expérience", "expériences",
            "education", "education", "formation", "formations", "skills", "competences", "compétences",
            "contact", "address", "adresse", "telephone", "téléphone", "email", "mail", "page",
            "photo", "objective", "summary", "about", "me"
        }
        
        for word in unique_words:
            if word in stopwords or word in seen or len(word) < 4:
                continue

            if word.isdigit() or re.fullmatch(r"\d+", word):
                continue

            # Find best match in skills dictionary
            matches = process.extract(word, self.all_skills, limit=1, scorer=fuzz.token_sort_ratio)

            if matches and matches[0][1] >= threshold:
                best_match = matches[0][0]
                if best_match.lower() not in seen:
                    extracted.append({
                        "name": best_match,
                        "category": self.skill_categories.get(best_match.lower(), "unknown"),
                        "method": "fuzzy",
                        "confidence": matches[0][1]
                    })
                    seen.add(best_match.lower())
        
        return extracted
    
    def extract_proficiency(self, text: str, skill: str) -> str:
        """
        Estimate proficiency level for a skill based on context
        
        Args:
            text: CV text
            skill: Skill name to assess
        
        Returns:
            "expert", "advanced", "intermediate", or "beginner"
        """
        text_lower = text.lower()
        skill_lower = skill.lower()
        
        # Find context around skill mention (±100 chars)
        pattern = r'.{0,100}\b' + re.escape(skill_lower) + r'\b.{0,100}'
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        
        if not matches:
            return "beginner"
        
        context = " ".join(matches)
        
        # Keywords for proficiency levels
        expert_keywords = ["expert", "lead", "architect", "senior", "principal", "master", "specialized"]
        advanced_keywords = ["advanced", "proficient", "strong", "deep", "extensive"]
        intermediate_keywords = ["familiar", "experience", "worked", "used", "knowledge"]
        
        # Count keyword matches
        context_lower = context.lower()
        for keyword in expert_keywords:
            if keyword in context_lower:
                return "expert"
        
        for keyword in advanced_keywords:
            if keyword in context_lower:
                return "advanced"
        
        for keyword in intermediate_keywords:
            if keyword in context_lower:
                return "intermediate"
        
        return "beginner"
