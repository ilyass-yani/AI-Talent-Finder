"""
CV text cleaning and preprocessing
Étape 6 - NLP preprocessing
"""

import re
from typing import List


class CVCleaner:
    """Clean and preprocess CV text"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean and normalize CV text
        
        Args:
            text: Raw CV text
        
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # 1. Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 2. Remove URLs
        text = re.sub(r'http\S+|www\S+', '', text)
        
        # 3. Remove email patterns
        text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', text)
        
        # 4. Remove phone numbers
        text = re.sub(r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b', '', text)
        
        # 5. Remove special characters but keep spaces
        text = re.sub(r'[^a-zA-Z0-9\s\-]', '', text)
        
        return text
    
    @staticmethod
    def extract_sections(text: str) -> dict:
        """
        Try to extract CV sections (experience, education, skills, etc.)
        
        Args:
            text: CV text
        
        Returns:
            Dict with identified sections
        """
        sections = {
            "experience": "",
            "education": "",
            "skills": "",
            "summary": ""
        }
        
        # Common section headers (case-insensitive)
        exp_patterns = [r'(?:professional\s+)?experience', r'work\s+history', r'employment history']
        edu_patterns = [r'education', r'academic background', r'qualifications']
        skill_patterns = [r'skills?', r'competencies', r'technical skills']
        summary_patterns = [r'summary', r'objective', r'professional summary', r'about me']
        
        text_lower = text.lower()
        
        # Split by section headers
        current_section = "summary"
        current_text = ""
        
        for line in text.split('\n'):
            line_lower = line.lower()
            
            # Check for section headers
            is_exp = any(re.search(pattern, line_lower) for pattern in exp_patterns)
            is_edu = any(re.search(pattern, line_lower) for pattern in edu_patterns)
            is_skill = any(re.search(pattern, line_lower) for pattern in skill_patterns)
            is_summary = any(re.search(pattern, line_lower) for pattern in summary_patterns)
            
            if is_exp:
                sections[current_section] = current_text
                current_section = "experience"
                current_text = ""
            elif is_edu:
                sections[current_section] = current_text
                current_section = "education"
                current_text = ""
            elif is_skill:
                sections[current_section] = current_text
                current_section = "skills"
                current_text = ""
            elif is_summary:
                sections[current_section] = current_text
                current_section = "summary"
                current_text = ""
            else:
                current_text += " " + line
        
        sections[current_section] = current_text
        
        return sections
