# Resume NER Extractor - Implémentation Prête à l'Emploi
# Fichier: backend/ai_module/nlp/resume_ner_extractor.py

"""
Resume Parsing using BERT-based Named Entity Recognition
Modèle: AventIQ-AI/Resume-Parsing-NER-AI-Model
Utile pour: Extraction complète de CV (nom, email, compétences, expérience, etc.)
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("⚠️ Warning: transformers not installed. Install with: pip install transformers torch")


@dataclass
class ExtractedEntity:
    """Container for a single extracted entity"""
    text: str
    entity_type: str  # NAME, EMAIL, PHONE, JOB, COMPANY, SKILL, EDUCATION
    confidence: float
    start_char: int = 0
    end_char: int = 0


class ResumeNERExtractor:
    """
    Extract structured data from resume using BERT-based NER model
    
    Supported entity types:
    - NAME: Candidate's full name
    - EMAIL: Email addresses
    - PHONE: Phone numbers
    - JOB: Job titles (Senior Developer, Manager, etc.)
    - COMPANY: Company names
    - SKILL: Technical/soft skills
    - EDUCATION: Educational degrees and qualifications
    """
    
    MODEL_NAME = "AventIQ-AI/Resume-Parsing-NER-AI-Model"
    MIN_CONFIDENCE = 0.75  # Only extract if confidence > 75%
    MAX_TEXT_LENGTH = 512  # BERT max input
    
    # Mapping from model labels to normalized categories
    ENTITY_MAPPING = {
        "B-NAME": "NAME",
        "I-NAME": "NAME",
        "B-EMAIL": "EMAIL",
        "I-EMAIL": "EMAIL",
        "B-PHONE": "PHONE",
        "I-PHONE": "PHONE",
        "B-EDUCATION": "EDUCATION",
        "I-EDUCATION": "EDUCATION",
        "B-SKILL": "SKILL",
        "I-SKILL": "SKILL",
        "B-JOB": "JOB",
        "I-JOB": "JOB",
        "B-COMPANY": "COMPANY",
        "I-COMPANY": "COMPANY",
        "O": "OTHER"
    }
    
    def __init__(self):
        """Initialize the NER pipeline"""
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "Transformers library required. Install with: pip install transformers torch"
            )
        
        print("📍 Loading Resume NER model... (first time may take a minute)")
        try:
            self.ner_pipeline = pipeline(
                "ner",
                model=self.MODEL_NAME,
                aggregation_strategy="simple"  # Keep subwords separate
            )
            print("✅ Model loaded successfully!")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            raise
    
    def extract_all_entities(self, text: str) -> Dict[str, List[ExtractedEntity]]:
        """
        Extract all entities from resume text
        
        Args:
            text: Resume text (can be multi-paragraph)
        
        Returns:
            Dictionary with entity types as keys and list of ExtractedEntity as values
            {
                "NAME": [ExtractedEntity(...), ...],
                "EMAIL": [ExtractedEntity(...), ...],
                "SKILL": [...],
                ...
            }
        """
        if not text or len(text.strip()) == 0:
            return {}
        
        # Truncate to max length
        text = text[:self.MAX_TEXT_LENGTH]
        
        try:
            # Run NER pipeline
            ner_results = self.ner_pipeline(text)
        except Exception as e:
            print(f"❌ NER extraction failed: {e}")
            return {}
        
        # Parse results into structured format
        entities = self._parse_ner_results(ner_results, text)
        
        # Group by entity type
        grouped = {}
        for entity in entities:
            if entity.entity_type not in grouped:
                grouped[entity.entity_type] = []
            grouped[entity.entity_type].append(entity)
        
        return grouped
    
    def _parse_ner_results(self, ner_results: list, original_text: str) -> List[ExtractedEntity]:
        """
        Parse raw NER pipeline results into ExtractedEntity objects
        
        Args:
            ner_results: Output from transformers NER pipeline
            original_text: Original text (for position tracking)
        
        Returns:
            List of ExtractedEntity objects
        """
        entities = []
        current_entity = None
        
        for result in ner_results:
            token = result["word"]
            label = result["entity"]
            score = result["score"]
            
            # Normalize label
            entity_type = self.ENTITY_MAPPING.get(label, "OTHER")
            
            # Skip if confidence too low
            if score < self.MIN_CONFIDENCE:
                continue
            
            # Skip "other" entities
            if entity_type == "OTHER":
                if current_entity:
                    entities.append(current_entity)
                    current_entity = None
                continue
            
            # Handle B- (Beginning) tags
            if label.startswith("B-"):
                # Save previous entity if exists
                if current_entity:
                    entities.append(current_entity)
                
                # Start new entity
                current_entity = ExtractedEntity(
                    text=token,
                    entity_type=entity_type,
                    confidence=score
                )
            
            # Handle I- (Inside/continuation) tags
            elif label.startswith("I-") and current_entity:
                # Continue current entity
                if current_entity.entity_type == entity_type:
                    # Merge with space if needed
                    current_entity.text += f" {token}" if not token.startswith("##") else token.replace("##", "")
                    # Use minimum confidence
                    current_entity.confidence = min(current_entity.confidence, score)
                else:
                    # Entity type changed, save previous
                    entities.append(current_entity)
                    current_entity = ExtractedEntity(
                        text=token,
                        entity_type=entity_type,
                        confidence=score
                    )
        
        # Don't forget last entity
        if current_entity:
            entities.append(current_entity)
        
        return entities
    
    def extract_structured_profile(self, text: str) -> Dict:
        """
        Extract resume data into structured candidate profile
        
        Returns:
            {
                "name": str or None,
                "emails": List[str],
                "phones": List[str],
                "job_titles": List[{"title": str, "confidence": float}],
                "companies": List[{"name": str, "confidence": float}],
                "skills": List[{"name": str, "confidence": float}],
                "education": List[{"degree": str, "confidence": float}],
                "quality_score": float (0-100),
                "extraction_metadata": {...}
            }
        """
        # Extract all entities
        entities = self.extract_all_entities(text)
        
        # Build structured profile
        profile = {
            "name": None,
            "emails": [],
            "phones": [],
            "job_titles": [],
            "companies": [],
            "skills": [],
            "education": [],
            "extraction_metadata": {
                "total_entities_found": sum(len(v) for v in entities.values()),
                "entity_types_found": list(entities.keys()),
                "confidence_scores": {}
            }
        }
        
        # Process NAME
        if "NAME" in entities and entities["NAME"]:
            name_entity = max(entities["NAME"], key=lambda e: e.confidence)
            profile["name"] = name_entity.text.strip()
            profile["extraction_metadata"]["confidence_scores"]["name"] = name_entity.confidence
        
        # Process EMAIL
        if "EMAIL" in entities:
            profile["emails"] = [
                e.text.strip() for e in entities["EMAIL"]
            ]
        
        # Process PHONE
        if "PHONE" in entities:
            profile["phones"] = [
                e.text.strip() for e in entities["PHONE"]
            ]
        
        # Process JOB TITLES
        if "JOB" in entities:
            profile["job_titles"] = [
                {
                    "title": e.text.strip(),
                    "confidence": e.confidence
                }
                for e in entities["JOB"]
            ]
        
        # Process COMPANIES
        if "COMPANY" in entities:
            profile["companies"] = [
                {
                    "name": e.text.strip(),
                    "confidence": e.confidence
                }
                for e in entities["COMPANY"]
            ]
        
        # Process SKILLS
        if "SKILL" in entities:
            profile["skills"] = [
                {
                    "name": e.text.strip(),
                    "confidence": e.confidence
                }
                for e in entities["SKILL"]
            ]
        
        # Process EDUCATION
        if "EDUCATION" in entities:
            profile["education"] = [
                {
                    "degree": e.text.strip(),
                    "confidence": e.confidence
                }
                for e in entities["EDUCATION"]
            ]
        
        # Calculate quality score
        profile["quality_score"] = self._calculate_quality_score(profile)
        
        return profile
    
    def _calculate_quality_score(self, profile: Dict) -> float:
        """
        Calculate extraction quality score (0-100)
        Based on: name, email, job titles, companies, skills
        """
        score = 0
        max_score = 100
        
        weights = {
            "name": 20,
            "emails": 20,
            "job_titles": 20,
            "companies": 20,
            "skills": 20,
        }
        
        if profile.get("name"):
            score += weights["name"]
        if profile.get("emails"):
            score += weights["emails"]
        if profile.get("job_titles"):
            score += weights["job_titles"]
        if profile.get("companies"):
            score += weights["companies"]
        if profile.get("skills"):
            score += weights["skills"]
        
        return min(score, max_score)
    
    def extract_with_fallback(self, text: str, fallback_extractor=None) -> Dict:
        """
        Extract using NER, fallback to other extractor if needed
        
        Args:
            text: Resume text
            fallback_extractor: Optional fallback (e.g., SkillExtractor)
        
        Returns:
            Combined extraction results
        """
        # Try NER extraction first
        ner_results = self.extract_structured_profile(text)
        
        # If quality is low, try fallback
        if fallback_extractor and ner_results.get("quality_score", 0) < 50:
            print("⚠️ NER quality low, attempting fallback extraction...")
            # Could merge with other extractors here
        
        return ner_results


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == "__main__":
    # Example 1: Basic usage
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Entity Extraction")
    print("="*60)
    
    extractor = ResumeNERExtractor()
    
    sample_text = """
    John Smith
    john.smith@gmail.com
    Tel: +33612345678
    
    Professional Experience:
    Senior Python Developer at Google (2020-2023)
    Full Stack Engineer at Amazon (2018-2020)
    
    Skills: Python, FastAPI, React, Docker, Kubernetes, AWS
    
    Education:
    Bachelor of Science in Computer Science
    University of California, Berkeley
    """
    
    # Extract all entities
    entities = extractor.extract_all_entities(sample_text)
    
    print("\nExtracted Entities:")
    for entity_type, entity_list in entities.items():
        print(f"\n{entity_type}:")
        for entity in entity_list:
            print(f"  - {entity.text:40} (confidence: {entity.confidence:.2f})")
    
    # Example 2: Structured profile
    print("\n" + "="*60)
    print("EXAMPLE 2: Structured Profile Extraction")
    print("="*60)
    
    profile = extractor.extract_structured_profile(sample_text)
    
    import json
    print(json.dumps(profile, indent=2))
    
    # Example 3: Read from file
    print("\n" + "="*60)
    print("EXAMPLE 3: Extract from File")
    print("="*60)
    
    try:
        with open("backend/test_cv.txt", "r", encoding="utf-8") as f:
            cv_text = f.read()
        
        profile = extractor.extract_structured_profile(cv_text)
        print(f"\nQuality Score: {profile['quality_score']:.1f}/100")
        print(f"Name: {profile['name']}")
        print(f"Emails: {profile['emails']}")
        print(f"Skills found: {len(profile['skills'])}")
        print(f"Job titles: {len(profile['job_titles'])}")
    except FileNotFoundError:
        print("⚠️ test_cv.txt not found")
