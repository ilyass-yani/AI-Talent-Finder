"""
CV Extraction Service - Étape 5 Optimization
Combines PDF text extraction + NER structured data extraction
"""

import fitz  # PyMuPDF
import json
import os
import re
import logging
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime

try:
    from ai_module.nlp.resume_ner_extractor import ResumeNERExtractor
    NER_AVAILABLE = True
except ImportError:
    NER_AVAILABLE = False

from ai_module.nlp.cv_cleaner import CVCleaner
from ai_module.nlp.enhanced_skill_extractor import EnhancedSkillExtractor


logger = logging.getLogger(__name__)


@dataclass
class CVExtractionResult:
    """Result of CV extraction with full structured data"""
    raw_text: str
    structured: Dict
    skills: List[Dict]
    quality_score: float
    extraction_metadata: Dict


class CVExtractionService:
    """
    Complete CV extraction pipeline:
    1. Text extraction from PDF
    2. NER-based entity extraction (name, email, company, etc.)
    3. Enhanced skill extraction (NER + fuzzy matching)
    4. Quality scoring
    """
    
    def __init__(self):
        """Initialize extraction components"""
        self.cv_cleaner = CVCleaner()
        self.skill_extractor = EnhancedSkillExtractor(load_ner=False)  # Separate NER
        self.debug_enabled = os.getenv("CV_EXTRACTION_DEBUG", "0") == "1"
        
        try:
            self.ner_extractor = ResumeNERExtractor()
            self.ner_available = True
        except Exception as e:
            print(f"⚠️ NER not available: {e}")
            self.ner_available = False
    
    def extract_from_pdf(self, file_path: str) -> CVExtractionResult:
        """
        Complete extraction pipeline for PDF CV
        
        Args:
            file_path: Path to PDF file
        
        Returns:
            CVExtractionResult with full structured data
        """
        # Step 1: Extract raw text from PDF
        raw_text = extract_text_from_pdf(file_path)
        
        # Step 2: NER extraction BEFORE cleaning (important!)
        structured_data = {}
        quality_score = 0
        if self.ner_available:
            structured_data, quality_score = self._extract_structured_data(raw_text)
        else:
            print("⚠️ NER not available, using fallback extraction")
        
        # Step 3: Extract skills (hybrid: NER + fuzzy)
        skills = self.skill_extractor.extract_skills_hybrid(raw_text)
        
        # Step 4: Calculate metadata
        metadata = {
            "file_path": file_path,
            "extraction_date": datetime.utcnow().isoformat(),
            "raw_text_length": len(raw_text),
            "ner_available": self.ner_available,
            "skills_extracted": len(skills),
            "entities_found": structured_data.get("extraction_metadata", {}).get("total_entities", 0)
        }
        
        return CVExtractionResult(
            raw_text=raw_text,
            structured=structured_data,
            skills=skills,
            quality_score=quality_score,
            extraction_metadata=metadata
        )
    
    def _extract_structured_data(self, text: str) -> tuple:
        """
        Extract structured data via NER
        
        Returns:
            Tuple of (structured_dict, quality_score)
        """
        if not self.ner_available or not text:
            return {}, 0
        
        try:
            normalized_text = self._normalize_text_for_extraction(text)

            if self.debug_enabled:
                logger.info("TEXT EXTRACTED (preview): %s", normalized_text[:1000])

            structured = self.ner_extractor.extract_structured_profile(normalized_text)
            quality = self._compute_quality_score(structured)

            if self.debug_enabled:
                entity_counts = {
                    "name": int(bool(structured.get("full_name"))),
                    "email": int(bool(structured.get("email"))),
                    "phone": int(bool(structured.get("phone"))),
                    "job_titles": len(structured.get("job_titles", [])),
                    "companies": len(structured.get("companies", [])),
                    "education": len(structured.get("education", [])),
                    "skills": len(structured.get("skills", [])),
                }
                logger.info("ENTITIES SUMMARY: %s", entity_counts)

            return structured, quality
        except Exception as e:
            print(f"⚠️ Structured extraction failed: {e}")
            return {}, 0

    def _normalize_text_for_extraction(self, text: str) -> str:
        """Normalize noisy PDF extraction output to improve entity detection."""
        normalized = text.replace("\r", "\n")
        normalized = re.sub(r"[ \t]+", " ", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

    def _compute_quality_score(self, structured: Dict) -> float:
        """Compute a simple extraction quality score on a 0..100 scale."""
        score = 0.0
        if structured.get("full_name"):
            score += 20
        if structured.get("email"):
            score += 20
        if structured.get("phone"):
            score += 10
        if structured.get("job_titles"):
            score += 20
        if structured.get("companies"):
            score += 20
        if structured.get("education"):
            score += 10
        if structured.get("languages"):
            score += 5
        if structured.get("soft_skills"):
            score += 5
        if structured.get("interests"):
            score += 5
        if structured.get("profile_summary"):
            score += 5
        return min(score, 100.0)
    
    def extract_from_text(self, text: str) -> CVExtractionResult:
        """
        Extract from raw text (for testing, etc.)
        
        Args:
            text: Raw CV text
        
        Returns:
            CVExtractionResult
        """
        raw_text = text
        
        # NER extraction
        structured_data = {}
        quality_score = 0
        if self.ner_available:
            structured_data, quality_score = self._extract_structured_data(raw_text)
        
        # Skills extraction
        skills = self.skill_extractor.extract_skills_hybrid(raw_text)
        
        # Metadata
        metadata = {
            "extraction_date": datetime.utcnow().isoformat(),
            "raw_text_length": len(raw_text),
            "ner_available": self.ner_available,
            "skills_extracted": len(skills),
            "source": "text_input"
        }
        
        return CVExtractionResult(
            raw_text=raw_text,
            structured=structured_data,
            skills=skills,
            quality_score=quality_score,
            extraction_metadata=metadata
        )
    
    def to_candidate_dict(self, extraction: CVExtractionResult) -> Dict:
        """
        Convert extraction result to candidate database format
        
        Returns:
            Dict ready for Candidate model
        """
        structured = extraction.structured
        
        emails = structured.get("emails") or ([structured.get("email")] if structured.get("email") else [])
        phones = structured.get("phones") or ([structured.get("phone")] if structured.get("phone") else [])
        extracted_name = structured.get("name") or structured.get("full_name")
        fallback_name = self._infer_name_from_email(emails[0] if emails else structured.get("email"))
        effective_name = extracted_name or fallback_name
        
        return {
            # Auto-filled from NER
            "full_name": effective_name or "Unknown",
            "email": emails[0] if emails else None,
            "phone": phones[0] if phones else None,
            "linkedin_url": structured.get("linkedin_url"),
            "raw_text": extraction.raw_text,
            
            # NER fields
            "extracted_name": extracted_name,
            "extracted_emails": json.dumps(emails),
            "extracted_phones": json.dumps(phones),
            "extracted_job_titles": json.dumps(structured.get("job_titles", [])),
            "extracted_companies": json.dumps(structured.get("companies", [])),
            "extracted_education": json.dumps(structured.get("education", [])),
            "extraction_quality_score": extraction.quality_score,
            "ner_extraction_data": json.dumps(structured),
            "is_fully_extracted": extraction.quality_score >= 80,
        }

    def _infer_name_from_email(self, email: Optional[str]) -> Optional[str]:
        """Infer a human readable name from the local part of an email address."""
        if not email or "@" not in email:
            return None

        local_part = email.split("@", 1)[0]
        if not local_part or len(local_part) < 3:
            return None

        pieces = [piece for piece in re.split(r"[._\-+]+", local_part) if piece]
        if len(pieces) < 2:
            return None

        name = " ".join(piece.capitalize() for piece in pieces[:3])
        if len(name) < 5:
            return None

        return name


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file"""
    try:
        doc = fitz.open(file_path)
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts).strip()
    except Exception as e:
        print(f"❌ PDF extraction failed: {e}")
        return ""


def save_text_as_txt(text: str, output_dir: str, base_name: str) -> str:
    """Save text as .txt file"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    txt_name = Path(base_name).with_suffix(".txt").name
    txt_path = output_path / txt_name
    txt_path.write_text(text, encoding="utf-8")
    return str(txt_path)


# Convenience function for backward compatibility
def extract_and_structure_cv(pdf_path: str) -> CVExtractionResult:
    """Extract CV and get complete structured data"""
    service = CVExtractionService()
    return service.extract_from_pdf(pdf_path)