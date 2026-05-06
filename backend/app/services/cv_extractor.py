"""
CV Extraction Service - Étape 5 Optimization
Combines PDF text extraction + NER structured data extraction
"""

import fitz  # PyMuPDF
import io
import json
import os
import re
import logging
from pathlib import Path
from typing import Any, Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime

try:
    import pdfplumber  # type: ignore
    PDFPLUMBER_AVAILABLE = True
except Exception:
    PDFPLUMBER_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

try:
    import pytesseract  # type: ignore
    TESSERACT_AVAILABLE = True
except Exception:
    TESSERACT_AVAILABLE = False

try:
    from ai_module.nlp.cv_parser import HFResumeNERParser
    HF_NER_PARSER_AVAILABLE = True
except ImportError:
    HF_NER_PARSER_AVAILABLE = False

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
        self.hf_ner_model_name = os.getenv("HF_CV_NER_MODEL", "dslim/bert-base-NER")
        self.hf_parser = None

        if HF_NER_PARSER_AVAILABLE:
            try:
                self.hf_parser = HFResumeNERParser(model_name=self.hf_ner_model_name)
            except Exception as e:
                print(f"⚠️ HF NER parser not available: {e}")
                self.hf_parser = None
        
        try:
            self.ner_extractor = ResumeNERExtractor()
            self.ner_available = True
        except Exception as e:
            print(f"⚠️ NER not available: {e}")
            self.ner_available = False

        self._email_re = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
        self._phone_digits_re = re.compile(r"\D")
    
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
            hf_structured: Dict = {}
            hf_quality = 0.0

            # Run modern HF parser first (high precision on identity entities),
            # then merge with the richer legacy extractor output.
            if self.hf_parser is not None and self.hf_parser.available:
                hf_structured, hf_quality = self.hf_parser.extract_structured_profile(normalized_text)

            if self.debug_enabled:
                logger.info("TEXT EXTRACTED (preview): %s", normalized_text[:1000])

            structured = self.ner_extractor.extract_structured_profile(normalized_text)
            quality = self._compute_quality_score(structured)

            if hf_structured:
                structured = self._merge_structured_profiles(base=structured, hf=hf_structured)

            structured = self._postprocess_structured(structured)
            quality = max(quality, hf_quality, self._compute_quality_score(structured))

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

    def _merge_structured_profiles(self, base: Dict, hf: Dict) -> Dict:
        """Merge legacy and HF structured outputs while preserving richer fields."""
        merged = dict(base or {})

        # Fill scalar identity fields only when missing in base.
        for key in ["full_name", "name", "email", "phone", "linkedin_url", "profile_summary"]:
            if not merged.get(key) and hf.get(key):
                merged[key] = hf[key]

        # Merge list fields with de-duplication while preserving order.
        list_keys = [
            "emails", "phones", "companies", "job_titles", "education", "skills",
            "languages", "soft_skills", "interests", "certifications", "projects",
            "experiences", "linkedin_urls", "github_urls", "portfolio_urls", "locations",
        ]
        for key in list_keys:
            base_list = merged.get(key) if isinstance(merged.get(key), list) else []
            hf_list = hf.get(key) if isinstance(hf.get(key), list) else []

            combined = []
            seen = set()
            for item in base_list + hf_list:
                marker = json.dumps(item, sort_keys=True, ensure_ascii=False) if isinstance(item, dict) else str(item).strip().lower()
                if not marker or marker in seen:
                    continue
                seen.add(marker)
                combined.append(item)

            if combined:
                merged[key] = combined

        # Keep extraction metadata traceable.
        base_meta = merged.get("extraction_metadata") if isinstance(merged.get("extraction_metadata"), dict) else {}
        hf_meta = hf.get("extraction_metadata") if isinstance(hf.get("extraction_metadata"), dict) else {}
        merged["extraction_metadata"] = {
            **base_meta,
            **hf_meta,
            "fusion": "legacy+hf",
            "models": list(dict.fromkeys([m for m in [base_meta.get("model"), hf_meta.get("model")] if m])),
        }

        return merged

    def _postprocess_structured(self, structured: Dict) -> Dict:
        """Normalize and validate extracted entities to improve precision."""
        cleaned = dict(structured or {})

        cleaned["emails"] = self._clean_emails(cleaned.get("emails"), cleaned.get("email"))
        cleaned["email"] = cleaned["emails"][0] if cleaned["emails"] else None

        cleaned["phones"] = self._clean_phones(cleaned.get("phones"), cleaned.get("phone"))
        cleaned["phone"] = cleaned["phones"][0] if cleaned["phones"] else None

        cleaned["full_name"] = self._clean_name(cleaned.get("full_name") or cleaned.get("name"))
        cleaned["name"] = cleaned["full_name"]

        cleaned["companies"] = self._clean_labeled_list(
            cleaned.get("companies"),
            max_items=8,
            min_len=2,
            max_len=80,
            banned_tokens={"linkedin", "github", "gmail", "hotmail", "outlook", "formation", "education", "skills", "competences"},
        )
        cleaned["job_titles"] = self._clean_labeled_list(
            cleaned.get("job_titles"),
            max_items=8,
            min_len=3,
            max_len=80,
            banned_tokens={"linkedin", "github", "gmail", "hotmail", "outlook", "formation", "education"},
        )
        cleaned["education"] = self._clean_labeled_list(
            cleaned.get("education"),
            max_items=6,
            min_len=3,
            max_len=120,
            banned_tokens={"linkedin", "github", "gmail", "hotmail", "outlook"},
            allow_years=True,
        )
        cleaned["skills"] = self._clean_labeled_list(
            cleaned.get("skills"),
            max_items=30,
            min_len=2,
            max_len=60,
            banned_tokens={"linkedin", "github", "gmail", "hotmail", "outlook"},
        )
        cleaned["languages"] = self._clean_labeled_list(
            cleaned.get("languages"),
            max_items=8,
            min_len=2,
            max_len=30,
            banned_tokens=set(),
        )
        cleaned["soft_skills"] = self._clean_labeled_list(
            cleaned.get("soft_skills"),
            max_items=20,
            min_len=2,
            max_len=60,
            banned_tokens={"linkedin", "github", "gmail", "hotmail", "outlook"},
        )
        cleaned["projects"] = self._clean_labeled_list(
            cleaned.get("projects"),
            max_items=15,
            min_len=4,
            max_len=180,
            banned_tokens={"linkedin", "github", "gmail", "hotmail", "outlook"},
            allow_years=True,
        )
        cleaned["certifications"] = self._clean_labeled_list(
            cleaned.get("certifications"),
            max_items=15,
            min_len=3,
            max_len=140,
            banned_tokens={"linkedin", "github", "gmail", "hotmail", "outlook"},
            allow_years=True,
        )

        metadata = cleaned.get("extraction_metadata") if isinstance(cleaned.get("extraction_metadata"), dict) else {}
        metadata["postprocessed"] = True
        cleaned["extraction_metadata"] = metadata

        return cleaned

    def _clean_name(self, name: Any) -> Optional[str]:
        value = str(name or "").strip()
        if not value:
            return None
        if "@" in value or "http" in value.lower():
            return None
        if any(ch.isdigit() for ch in value):
            return None
        words = [w for w in re.split(r"\s+", value) if w]
        if len(words) < 2 or len(words) > 4:
            return None
        return " ".join(word.capitalize() for word in words)

    def _clean_emails(self, emails: Any, scalar_email: Any) -> List[str]:
        values = []
        if isinstance(emails, list):
            values.extend(str(v).strip().lower() for v in emails)
        if scalar_email:
            values.append(str(scalar_email).strip().lower())

        unique = []
        seen = set()
        for email in values:
            if not email or email in seen:
                continue
            if not self._email_re.match(email):
                continue
            seen.add(email)
            unique.append(email)
        return unique[:5]

    def _clean_phones(self, phones: Any, scalar_phone: Any) -> List[str]:
        values = []
        if isinstance(phones, list):
            values.extend(str(v).strip() for v in phones)
        if scalar_phone:
            values.append(str(scalar_phone).strip())

        unique = []
        seen = set()
        for phone in values:
            if not phone:
                continue
            digits = self._phone_digits_re.sub("", phone)
            if len(digits) < 10 or len(digits) > 15:
                continue
            if digits in seen:
                continue
            seen.add(digits)
            unique.append(phone)
        return unique[:3]

    def _clean_labeled_list(
        self,
        values: Any,
        *,
        max_items: int,
        min_len: int,
        max_len: int,
        banned_tokens: set,
        allow_years: bool = False,
    ) -> List[Any]:
        if not isinstance(values, list):
            return []

        cleaned: List[Any] = []
        seen = set()

        for item in values:
            if isinstance(item, dict):
                marker = json.dumps(item, sort_keys=True, ensure_ascii=False)
                if marker in seen:
                    continue
                seen.add(marker)
                cleaned.append(item)
                if len(cleaned) >= max_items:
                    break
                continue

            value = str(item or "").strip()
            if not value:
                continue

            normalized = re.sub(r"\s+", " ", value).strip()
            lowered = normalized.lower()

            if len(normalized) < min_len or len(normalized) > max_len:
                continue
            if "@" in lowered or "http" in lowered:
                continue
            if (not allow_years) and re.search(r"\b(19|20)\d{2}\b", lowered):
                continue
            if any(token in lowered for token in banned_tokens):
                continue

            if lowered in seen:
                continue
            seen.add(lowered)
            cleaned.append(normalized)
            if len(cleaned) >= max_items:
                break

        return cleaned

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
    """Extract text from PDF using multiple strategies and keep the best result."""
    candidates: List[str] = []

    try:
        doc = fitz.open(file_path)
        text_parts_default = []
        text_parts_block = []
        for page in doc:
            text_parts_default.append(page.get_text())
            text_parts_block.append(page.get_text("blocks"))
        doc.close()

        # Default extraction.
        candidates.append("\n".join(text_parts_default).strip())

        # Block extraction often improves OCR-like and layout-heavy CVs.
        block_lines = []
        for page_blocks in text_parts_block:
            if not isinstance(page_blocks, list):
                continue
            sorted_blocks = sorted(page_blocks, key=lambda b: (b[1], b[0]))
            for block in sorted_blocks:
                if len(block) >= 5 and isinstance(block[4], str):
                    value = block[4].strip()
                    if value:
                        block_lines.append(value)
        if block_lines:
            candidates.append("\n".join(block_lines).strip())
    except Exception as e:
        print(f"❌ PDF extraction failed: {e}")

    if PDFPLUMBER_AVAILABLE:
        try:
            with pdfplumber.open(file_path) as pdf:
                pages = [page.extract_text() or "" for page in pdf.pages]
                candidates.append("\n".join(pages).strip())
        except Exception:
            pass

    candidates = [text for text in candidates if text and text.strip()]
    if not candidates:
        return ""

    best_text = max(candidates, key=_score_extracted_text)
    best_score = _score_extracted_text(best_text)

    # OCR fallback for scanned/image-only PDFs.
    ocr_mode = os.getenv("CV_OCR_MODE", "auto").strip().lower()
    ocr_threshold = int(os.getenv("CV_OCR_TRIGGER_SCORE", "700"))
    should_try_ocr = (
        ocr_mode == "aggressive"
        or ocr_mode == "ultra"
        or (ocr_mode == "auto" and best_score < ocr_threshold)
    )

    if should_try_ocr and TESSERACT_AVAILABLE and PIL_AVAILABLE:
        ocr_text = _extract_text_from_pdf_ocr(file_path)
        if ocr_text:
            ocr_score = _score_extracted_text(ocr_text)
            if ocr_score > best_score:
                best_text = ocr_text
                best_score = ocr_score

        if ocr_mode == "ultra":
            ultra_text = _extract_text_from_pdf_ultra(file_path)
            if ultra_text:
                ultra_score = _score_extracted_text(ultra_text)
                if ultra_score > best_score:
                    return ultra_text

    return best_text


def _score_extracted_text(text: str) -> int:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    alpha = sum(1 for ch in text if ch.isalpha())
    emails = len(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text))
    phones = len(re.findall(r"\+?\d[\d\s().-]{7,}\d", text))
    section_hits = len(re.findall(r"\b(experience|education|skills|profil|formation|competences|projects)\b", text.lower()))
    return alpha + (emails * 200) + (phones * 120) + (section_hits * 80) + (len(lines) * 3)


def _extract_text_from_pdf_ocr(file_path: str) -> str:
    """OCR fallback: render PDF pages to images and run Tesseract."""
    page_texts: List[str] = []
    max_pages = int(os.getenv("CV_OCR_MAX_PAGES", "8"))
    dpi = int(os.getenv("CV_OCR_DPI", "250"))
    lang = os.getenv("CV_OCR_LANG", "fra+eng")
    psm = os.getenv("CV_OCR_PSM", "6").strip()
    oem = os.getenv("CV_OCR_OEM", "1").strip()
    tesseract_config = f"--oem {oem} --psm {psm}"

    try:
        doc = fitz.open(file_path)
        page_count = min(len(doc), max_pages)
        for idx in range(page_count):
            page = doc.load_page(idx)
            text = _extract_page_ocr_text(page=page, dpi=dpi, lang=lang, tesseract_config=tesseract_config)
            if text and text.strip():
                page_texts.append(text.strip())
        doc.close()
    except Exception:
        return ""

    return "\n\n".join(page_texts).strip()


def _extract_text_from_pdf_ultra(file_path: str) -> str:
    """Ultra mode: page-wise OCR only on weak native-extraction pages."""
    max_pages = int(os.getenv("CV_OCR_MAX_PAGES", "8"))
    dpi = int(os.getenv("CV_OCR_DPI", "250"))
    lang = os.getenv("CV_OCR_LANG", "fra+eng")
    psm = os.getenv("CV_OCR_PSM", "6").strip()
    oem = os.getenv("CV_OCR_OEM", "1").strip()
    page_trigger_score = int(os.getenv("CV_OCR_PAGE_TRIGGER_SCORE", "120"))
    tesseract_config = f"--oem {oem} --psm {psm}"

    merged_pages: List[str] = []

    try:
        doc = fitz.open(file_path)
        page_count = min(len(doc), max_pages)
        for idx in range(page_count):
            page = doc.load_page(idx)
            native_text = (page.get_text() or "").strip()
            native_score = _score_extracted_text(native_text)

            selected_text = native_text
            if native_score < page_trigger_score:
                ocr_text = _extract_page_ocr_text(page=page, dpi=dpi, lang=lang, tesseract_config=tesseract_config)
                if ocr_text:
                    ocr_text = ocr_text.strip()
                    ocr_score = _score_extracted_text(ocr_text)
                    if ocr_score > native_score:
                        selected_text = ocr_text

            if selected_text:
                merged_pages.append(selected_text)

        doc.close()
    except Exception:
        return ""

    return "\n\n".join(merged_pages).strip()


def _extract_page_ocr_text(page: Any, dpi: int, lang: str, tesseract_config: str) -> str:
    """Run OCR on a single PDF page rendered as image."""
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    image = Image.open(io.BytesIO(pix.tobytes("png")))
    return pytesseract.image_to_string(image, lang=lang, config=tesseract_config)


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