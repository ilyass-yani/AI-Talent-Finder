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
        Clean and normalize CV text while PRESERVING important contact information
        
        Args:
            text: Raw CV text
        
        Returns:
            Cleaned text (emails, URLs, phones preserved)
        """
        if not text:
            return ""
        
        # 1. Normalize whitespace (preserve paragraph structure)
        # Replace multiple spaces/tabs with single space
        text = re.sub(r'[ \t]+', ' ', text)
        # Replace multiple newlines with double newline
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        
        # 2. Remove control characters and unusual Unicode
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # 3. Fix common OCR artifacts
        # Replace common character substitutions
        text = text.replace('|', 'I')  # Vertical bar often becomes I
        
        # 4. Clean up excessive punctuation
        text = re.sub(r'([.!?,;:]){2,}', r'\1', text)
        
        # 5. Normalize common abbreviations spacing
        text = re.sub(r'\b([A-Z])\.\s+([A-Z])', r'\1. \2', text)
        
        return text.strip()
    
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
        
        # Common section headers (case-insensitive) in English and French
        exp_patterns = [
            r'(?:professional\s+)?experience', r'work\s+history', r'employment history',
            r'exp[ée]rience(?:s)?', r'exp[ée]riences\s+professionnelles?'
        ]
        edu_patterns = [
            r'education', r'academic background', r'qualifications',
            r'formation(?:s)?', r'dipl[ôo]me(?:s)?', r'parcours\s+scolaire'
        ]
        skill_patterns = [
            r'skills?', r'competencies', r'technical skills',
            r'comp[ée]tences?', r'savoir[-\s]?faire'
        ]
        summary_patterns = [
            r'summary', r'objective', r'professional summary', r'about me',
            r'profil', r'r[ée]sum[ée]', r'pr[ée]sentation'
        ]
        
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
