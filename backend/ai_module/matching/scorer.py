"""
Matching Module - Similarity scoring and ranking
Étape 7 - Moteur de matching
"""

import numpy as np
from typing import List, Dict, Tuple


class CosineScorer:
    """
    Calculate cosine similarity between candidate skills and job criteria
    Étape 7 - Algorithme de scoring personnalisable
    """
    
    @staticmethod
    def vectorize_skills(skills: List[str], all_skills: List[str]) -> np.ndarray:
        """
        Convert list of skills to binary vector
        
        Args:
            skills: List of skill names candidate has
            all_skills: Complete list of all possible skills (dictionary)
        
        Returns:
            Binary numpy array (1 if has skill, 0 if doesn't)
        """
        vector = np.zeros(len(all_skills))
        skills_lower = {s.lower() for s in skills}
        
        for i, skill in enumerate(all_skills):
            if skill.lower() in skills_lower:
                vector[i] = 1
        
        return vector
    
    @staticmethod
    def vectorize_criteria(criteria_skills: Dict[str, float], all_skills: List[str]) -> np.ndarray:
        """
        Convert criteria (skills + weights) to weighted vector
        
        Args:
            criteria_skills: Dict of {skill_name: weight (0-100)}
            all_skills: Complete list of all possible skills
        
        Returns:
            Weighted numpy array (normalized 0-1)
        """
        vector = np.zeros(len(all_skills))
        
        for i, skill in enumerate(all_skills):
            skill_lower = skill.lower()
            for crit_skill, weight in criteria_skills.items():
                if crit_skill.lower() == skill_lower:
                    # Normalize weight to 0-1
                    vector[i] = weight / 100.0
                    break
        
        # Normalize the vector
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        return vector
    
    @staticmethod
    def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors
        
        Args:
            vec1: Candidate skills vector
            vec2: Job criteria vector
        
        Returns:
            Score 0-1
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    @staticmethod
    def calculate_match_score(
        candidate_skills: List[str],
        criteria_skills: Dict[str, float],
        all_skills: List[str]
    ) -> Dict:
        """
        Calculate complete match score with breakdown
        
        Args:
            candidate_skills: List of candidate's skills
            criteria_skills: Dict of {skill: weight (0-100)}
            all_skills: Dictionary of all skills
        
        Returns:
            {
                "score": 0-100,
                "similarity": 0-1,
                "matched_skills": ["skill1", "skill2", ...],
                "missing_skills": ["skill3", ...],
                "skill_breakdown": {"skill": score, ...}
            }
        """
        # Vectorize
        candidate_vec = CosineScorer.vectorize_skills(candidate_skills, all_skills)
        criteria_vec = CosineScorer.vectorize_criteria(criteria_skills, all_skills)
        
        # Calculate similarity
        similarity = CosineScorer.cosine_similarity(candidate_vec, criteria_vec)
        score = similarity * 100  # Convert to 0-100
        
        # Find matched and missing skills
        candidate_skills_lower = {s.lower() for s in candidate_skills}
        matched_skills = []
        missing_skills = []
        
        for skill in criteria_skills.keys():
            if skill.lower() in candidate_skills_lower:
                matched_skills.append(skill)
            else:
                missing_skills.append(skill)
        
        # Skill-by-skill breakdown
        skill_breakdown = {}
        for skill, weight in criteria_skills.items():
            if skill.lower() in candidate_skills_lower:
                skill_breakdown[skill] = weight  # Full weight if skill is present
            else:
                skill_breakdown[skill] = 0  # 0 if missing
        
        return {
            "score": min(100.0, max(0.0, score)),  # Clamp to 0-100
            "similarity": similarity,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "skill_breakdown": skill_breakdown,
            "matching_percentage": len(matched_skills) / len(criteria_skills) * 100 if criteria_skills else 0
        }
