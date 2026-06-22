"""
CV Extraction Service - Étape 5 Optimization
Combines PDF text extraction + NER structured data extraction
"""

try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except Exception:
    fitz = None
    FITZ_AVAILABLE = False
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
    try:
        from PIL import ImageOps
        PIL_IMAGEOPS_AVAILABLE = True
    except Exception:
        ImageOps = None
        PIL_IMAGEOPS_AVAILABLE = False
except Exception:
    PIL_AVAILABLE = False
    PIL_IMAGEOPS_AVAILABLE = False

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

try:
    from ai_module.nlp.gliner_extractor import get_gliner_extractor as _get_gliner
    GLINER_AVAILABLE = True
except ImportError:
    GLINER_AVAILABLE = False

from ai_module.nlp.cv_cleaner import CVCleaner

try:
    from ai_module.nlp.enhanced_skill_extractor import EnhancedSkillExtractor
    ENHANCED_SKILL_EXTRACTOR_AVAILABLE = True
except Exception:
    EnhancedSkillExtractor = None
    ENHANCED_SKILL_EXTRACTOR_AVAILABLE = False


logger = logging.getLogger(__name__)


class _FallbackSkillExtractor:
    def extract_skills_hybrid(self, text: str, threshold: int = 80) -> List[Dict]:
        return []


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
        if ENHANCED_SKILL_EXTRACTOR_AVAILABLE and EnhancedSkillExtractor is not None:
            try:
                self.skill_extractor = EnhancedSkillExtractor(load_ner=False)  # Separate NER
            except Exception as e:
                print(f"⚠️ Skill extractor not available: {e}")
                self.skill_extractor = _FallbackSkillExtractor()
        else:
            self.skill_extractor = _FallbackSkillExtractor()
        self.debug_enabled = os.getenv("CV_EXTRACTION_DEBUG", "0") == "1"
        # Set USE_GLINER=false to disable GLiNER without redeploying code.
        self._use_gliner = (
            GLINER_AVAILABLE
            and os.getenv("USE_GLINER", "true").strip().lower() not in ("false", "0", "no")
        )
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

        # Optional: force OCR/YELLOW as source of truth (bypass native text/NER)
        # Set env `CV_FORCE_OCR=true` to prefer OCR processing for all pages.
        force_ocr = os.getenv("CV_FORCE_OCR", "false").lower() == "true"
        if force_ocr and FITZ_AVAILABLE and TESSERACT_AVAILABLE and PIL_AVAILABLE:
            try:
                ocr_text = _extract_text_from_pdf_ocr(file_path)
                if ocr_text:
                    raw_text = ocr_text
            except Exception:
                # keep previous raw_text on failure
                pass
        
        # Step 2: Structured extraction (NER) can be disabled when forcing OCR.
        structured_data = {}
        quality_score = 0
        # If OCR is forced we still keep skill extraction from text but avoid
        # relying on NER structured parsing as the primary source.
        if not force_ocr and self.ner_available:
            structured_data, quality_score = self._extract_structured_data(raw_text)
        else:
            # Fallback: no structured NER; skills will be extracted from OCR text
            if force_ocr:
                logger.info("CVExtractionService: force OCR enabled, skipping NER structured parsing")
        
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
        """Extract structured data via NER cascade: GLiNER -> regex -> BERT.

        Returns:
            Tuple of (structured_dict, quality_score)
        """
        if not self.ner_available or not text:
            return {}, 0

        try:
            normalized_text = self._normalize_text_for_extraction(text)

            if self.debug_enabled:
                logger.info("TEXT EXTRACTED (preview): %s", normalized_text[:1000])

            # --- Step 1: regex extractor (full breadth: skills, phone, email, …) ---
            structured = self.ner_extractor.extract_structured_profile(normalized_text)
            quality = self._compute_quality_score(structured)

            # --- Step 2: GLiNER cascade (principal for name / companies / education) ---
            # GLiNER overrides the regex results for high-precision identity fields.
            # Falls back to regex values when GLiNER returns nothing for a field.
            gliner_data = self._run_gliner(normalized_text)
            if gliner_data:
                structured = self._apply_gliner_override(structured, gliner_data)

            # --- Step 3: BERT NER enrichment (fills gaps not covered by regex+GLiNER) ---
            hf_structured: Dict = {}
            hf_quality = 0.0
            if self.hf_parser is not None and self.hf_parser.available:
                hf_structured, hf_quality = self.hf_parser.extract_structured_profile(normalized_text)
            if hf_structured:
                structured = self._merge_structured_profiles(base=structured, hf=hf_structured)

            # --- Step 4: postprocess & score ---
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
                    "gliner_used": bool(gliner_data),
                }
                logger.info("ENTITIES SUMMARY: %s", entity_counts)

            return structured, quality
        except Exception as e:
            print(f"Warning: Structured extraction failed: {e}")
            return {}, 0

    def _run_gliner(self, text: str) -> Dict:
        """Run GLiNER and return its dict, or {} on any failure / disabled."""
        if not self._use_gliner:
            return {}
        try:
            extractor = _get_gliner()
            # Trigger lazy model load on first call
            extractor._load_model()
            if not extractor.available:
                return {}
            return extractor.extract(text)
        except Exception as exc:
            logger.warning("GLiNER run error: %s", exc)
            return {}

    def _apply_gliner_override(self, structured: Dict, gliner: Dict) -> Dict:
        """Override regex-extracted identity fields with GLiNER results.

        GLiNER is higher precision for name / companies / education / job_titles.
        Regex is kept for everything else (skills, phone, email, languages, etc.).
        A GLiNER field only overrides when GLiNER actually found something
        (non-empty), so the regex value is kept as fallback when GLiNER is silent.
        """
        result = dict(structured)

        if gliner.get("full_name"):
            result["full_name"] = gliner["full_name"]
            result["name"] = gliner["full_name"]

        if gliner.get("companies"):
            result["companies"] = gliner["companies"]

        if gliner.get("education"):
            result["education"] = gliner["education"]

        if gliner.get("job_titles"):
            result["job_titles"] = gliner["job_titles"]

        # Tag the extraction metadata so we know GLiNER ran
        meta = result.get("extraction_metadata")
        if not isinstance(meta, dict):
            meta = {}
        meta["gliner_model"] = os.getenv("GLINER_MODEL", "urchade/gliner_multi-v2.1")
        result["extraction_metadata"] = meta

        return result

    def _merge_structured_profiles(self, base: Dict, hf: Dict) -> Dict:
        """Merge legacy and HF structured outputs while preserving richer fields."""
        merged = dict(base or {})

        # Fill scalar identity fields only when missing in base.
        for key in ["full_name", "name", "email", "phone", "linkedin_url", "profile_summary"]:
            if not merged.get(key) and hf.get(key):
                merged[key] = hf[key]

        # Merge list fields with de-duplication while preserving order.
        # GLiNER-owned fields (companies, education, job_titles) are NOT merged
        # with the BERT/legacy output when GLiNER already produced a result:
        # BERT introduces wordpiece artifacts (##cence, ##P) and fragments
        # (Esp, Li) that would pollute the clean GLiNER lists.
        gliner_owned = ("companies", "education", "job_titles", "interests")
        list_keys = [
            "emails", "phones", "companies", "job_titles", "education", "skills",
            "languages", "soft_skills", "interests", "certifications", "projects",
            "experiences", "linkedin_urls", "github_urls", "portfolio_urls", "locations",
        ]
        for key in list_keys:
            base_list = merged.get(key) if isinstance(merged.get(key), list) else []
            hf_list = hf.get(key) if isinstance(hf.get(key), list) else []
            # Keep the clean GLiNER list untouched for its owned fields.
            if key in gliner_owned and base_list:
                continue

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

        # Clean interests (generic): drop form labels (/ or |), the candidate's
        # own name (case-insensitive), and CV section headers that leaked in.
        _name_norm = (cleaned.get("full_name") or cleaned.get("name") or "").strip().lower()
        _section_words = {
            "intitule du poste", "intitule du poste / stage", "intitule",
            "profil", "profile", "contact", "langues", "languages",
            "competences", "competence", "skills", "formation", "formations",
            "experience", "experiences", "education", "centres d interet",
            "objectif", "objectifs", "references", "projets", "certifications",
        }
        _src = cleaned.get("interests") if isinstance(cleaned.get("interests"), list) else []
        _clean_int = []
        _seen_int = set()
        for _it in _src:
            _v = str(_it or "").strip()
            if not _v or "/" in _v or "|" in _v:
                continue
            _low = _v.lower()
            if _name_norm and _low == _name_norm:
                continue
            if _low in _section_words:
                continue
            if _low in _seen_int:
                continue
            _seen_int.add(_low)
            _clean_int.append(_v)
        cleaned["interests"] = _clean_int

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

    # BOM and zero-width Unicode chars to strip from extracted text / names.
    # Using explicit codepoints is more robust than embedding literal Unicode chars.
    _ZERO_WIDTH_CHARS = (
        "﻿"  # BOM / Zero-width no-break space
        "￾"  # Reversed BOM
        "​"  # Zero-width space
        "‌"  # Zero-width non-joiner
        "‍"  # Zero-width joiner
        "⁠"  # Word joiner
        "­"  # Soft hyphen
    )

    def _clean_name(self, name: Any) -> Optional[str]:
        value = str(name or "").strip()
        # Strip BOM and zero-width chars — if not removed, capitalize() treats the
        # invisible char as the first character and lowercases the real first letter.
        value = value.strip(self._ZERO_WIDTH_CHARS).strip()
        if not value or len(value) < 4:
            return None
        if "@" in value or "http" in value.lower():
            return None
        if any(ch.isdigit() for ch in value):
            return None
        words = [w.strip(self._ZERO_WIDTH_CHARS) for w in re.split(r"\s+", value) if w]
        words = [w for w in words if w]
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
        # Strip BOM and zero-width chars from the start (and end) of the text.
        # Using the same _ZERO_WIDTH_CHARS constant for consistency.
        normalized = text.strip(self._ZERO_WIDTH_CHARS)
        normalized = normalized.replace("\r", "\n")
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


def _reflow_blocks_by_column(page_blocks: Any, page_width: float) -> tuple:
    """Reorder PyMuPDF text blocks into logical reading order, column by column.

    PyMuPDF's get_text("blocks") returns layout blocks, but sorting them by
    (y, x) reads straight across a multi-column page, interleaving a left
    sidebar (contact / languages / skills) with the main column. This detects a
    vertical separator from the spatial distribution of the blocks and emits the
    left column fully before the right column, restoring readable order.

    The separator is found from the actual content span, not the page midpoint,
    so a narrow sidebar (e.g. 35% of the width, on the left OR the right) is
    handled. Single-column pages fall back to a plain top-to-bottom sort.

    Returns:
        (reflowed_text, is_two_column)
    """
    blocks = []
    for b in (page_blocks or []):
        if len(b) >= 5 and isinstance(b[4], str):
            text = b[4].strip()
            if text:
                blocks.append((float(b[0]), float(b[1]), float(b[2]), float(b[3]), text))

    def _emit(ordered_blocks: List) -> str:
        return "\n".join(b[4] for b in ordered_blocks)

    if not blocks:
        return "", False

    # Too few blocks to reason about columns reliably -> plain reading order.
    if len(blocks) < 4:
        return _emit(sorted(blocks, key=lambda b: (b[1], b[0]))), False

    xs0 = min(b[0] for b in blocks)
    xs1 = max(b[2] for b in blocks)
    span = xs1 - xs0
    if span <= 0:
        if page_width and page_width > 0:
            span = page_width
            xs0 = 0.0
        else:
            return _emit(sorted(blocks, key=lambda b: (b[1], b[0]))), False

    # A block "straddles" a candidate separator when it clearly crosses it
    # (full-width headers do this); the margin ignores blocks that only graze it.
    margin = span * 0.02
    straddle_budget = max(1, int(len(blocks) * 0.08))

    best = None  # (straddlers, balance, separator, left, right)
    for i in range(15, 86):
        sep = xs0 + span * (i / 100.0)
        left, right = [], []
        for b in blocks:
            center = (b[0] + b[2]) / 2.0
            (left if center < sep else right).append(b)
        if len(left) < 2 or len(right) < 2:
            continue
        straddlers = sum(1 for b in blocks if b[0] < sep - margin and b[2] > sep + margin)
        balance = abs(len(left) - len(right))
        candidate = (straddlers, balance, sep, left, right)
        if best is None or candidate[:2] < best[:2]:
            best = candidate

    if best is not None:
        straddlers, _balance, _sep, left, right = best
        minority = min(len(left), len(right))
        # Genuine two-column layout: a near-clean vertical gutter (few straddlers)
        # and a minority column substantial enough to not be a stray element.
        if straddlers <= straddle_budget and minority >= max(2, int(len(blocks) * 0.15)):
            left_sorted = sorted(left, key=lambda b: (b[1], b[0]))
            right_sorted = sorted(right, key=lambda b: (b[1], b[0]))
            return _emit(left_sorted) + "\n" + _emit(right_sorted), True

    return _emit(sorted(blocks, key=lambda b: (b[1], b[0]))), False


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF using multiple strategies and keep the best result."""
    # If caller passed a plain text file, just read and return it.
    try:
        if str(file_path).lower().endswith(".txt"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
                return fh.read()
    except Exception:
        pass
    candidates: List[str] = []
    two_column_detected = False

    if FITZ_AVAILABLE:
        try:
            doc = fitz.open(file_path)
            text_parts_default = []
            reflow_parts = []
            for page in doc:
                text_parts_default.append(page.get_text())
                reflowed, is_two_col = _reflow_blocks_by_column(
                    page.get_text("blocks"), page.rect.width
                )
                if reflowed:
                    reflow_parts.append(reflowed)
                two_column_detected = two_column_detected or is_two_col
            doc.close()

            default_text = "\n".join(text_parts_default).strip()
            reflow_text = "\n".join(reflow_parts).strip()

            if two_column_detected and reflow_text:
                # On a multi-column layout the column-aware reflow is the only
                # correct reading order: the default (y, x) extraction interleaves
                # the sidebar with the main column. Use the reflow exclusively so
                # nothing downstream can re-select the scrambled variant.
                candidates.append(reflow_text)
            else:
                if default_text:
                    candidates.append(default_text)
                if reflow_text and reflow_text != default_text:
                    candidates.append(reflow_text)
        except Exception as e:
            print(f"❌ PDF extraction failed: {e}")

    # pdfplumber's default extraction also reads line-by-line across columns, so
    # skip it when a multi-column layout was detected to avoid reintroducing the
    # interleaved variant as a competing candidate.
    if PDFPLUMBER_AVAILABLE and not two_column_detected:
        try:
            with pdfplumber.open(file_path) as pdf:
                pages = [page.extract_text() or "" for page in pdf.pages]
                candidates.append("\n".join(pages).strip())
        except Exception:
            pass

    candidates = [text for text in candidates if text and text.strip()]
    if candidates:
        best_text = max(candidates, key=_score_extracted_text)
        best_score = _score_extracted_text(best_text)
    else:
        best_text = ""
        best_score = 0

    # OCR-first by default: favor OCR output whenever it produces usable text,
    # while keeping native extraction as a fallback for digitally born PDFs.
    ocr_mode = os.getenv("CV_OCR_MODE", "ocr_first").strip().lower()
    ocr_threshold = int(os.getenv("CV_OCR_TRIGGER_SCORE", "700"))

    # Full-page OCR (Tesseract PSM 6) reads line-by-line straight across columns,
    # so on a multi-column CV it glues the sidebar onto the main column (this is
    # what produced names like "Espagnol Cd"). When the PDF has a strong native
    # text layer — and especially when we already detected and reflowed columns —
    # the column-aware native text is authoritative and OCR must not override it.
    native_is_strong = best_score >= ocr_threshold
    protect_native = two_column_detected or native_is_strong

    should_try_ocr = (
        ocr_mode in {"ocr_first", "aggressive", "ultra"}
        or (ocr_mode == "auto" and best_score < ocr_threshold)
    )

    if should_try_ocr and not protect_native and FITZ_AVAILABLE and TESSERACT_AVAILABLE and PIL_AVAILABLE:
        ocr_text = _extract_text_from_pdf_ocr(file_path)
        if ocr_text:
            ocr_score = _score_extracted_text(ocr_text)
            if ocr_mode == "ocr_first":
                # Prefer OCR when it yields a meaningful result, but fall back
                # to native extraction if OCR is clearly weak.
                if ocr_score >= max(200, best_score * 0.75):
                    return ocr_text
            elif ocr_score > best_score:
                best_text = ocr_text
                best_score = ocr_score
        # Aggressive / ultra modes use an extra 'YELLOW' preprocessing pass
        # (image autocontrast / binarization heuristics) to improve OCR on
        # poor-quality scans when plain OCR is weak.
        if ocr_mode in {"aggressive", "ultra"}:
            yellow_text = _extract_text_with_yellow(file_path)
            if yellow_text:
                yellow_score = _score_extracted_text(yellow_text)
                if ocr_mode == "aggressive":
                    if yellow_score >= max(150, best_score * 0.6):
                        return yellow_text
                elif yellow_score > best_score:
                    return yellow_text

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
    dpi = int(os.getenv("CV_OCR_DPI", "250"))
    lang = os.getenv("CV_OCR_LANG", "fra+eng")
    psm = os.getenv("CV_OCR_PSM", "6").strip()
    oem = os.getenv("CV_OCR_OEM", "1").strip()
    tesseract_config = f"--oem {oem} --psm {psm}"

    try:
        doc = fitz.open(file_path)
        page_count = _resolve_ocr_page_count(len(doc))
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
    dpi = int(os.getenv("CV_OCR_DPI", "250"))
    lang = os.getenv("CV_OCR_LANG", "fra+eng")
    psm = os.getenv("CV_OCR_PSM", "6").strip()
    oem = os.getenv("CV_OCR_OEM", "1").strip()
    page_trigger_score = int(os.getenv("CV_OCR_PAGE_TRIGGER_SCORE", "120"))
    tesseract_config = f"--oem {oem} --psm {psm}"

    merged_pages: List[str] = []

    try:
        doc = fitz.open(file_path)
        page_count = _resolve_ocr_page_count(len(doc))
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


def _extract_text_with_yellow(file_path: str) -> str:
    """A lightweight 'YELLOW' extractor: render pages, apply simple PIL
    preprocessing (grayscale, autocontrast, optional resize), then OCR.
    This helps on low-contrast scans without requiring OpenCV.
    """
    if not (FITZ_AVAILABLE and TESSERACT_AVAILABLE and PIL_AVAILABLE):
        return ""

    page_texts: List[str] = []
    dpi = int(os.getenv("CV_OCR_DPI", "250"))
    lang = os.getenv("CV_OCR_LANG", "fra+eng")
    psm = os.getenv("CV_OCR_PSM", "6").strip()
    oem = os.getenv("CV_OCR_OEM", "1").strip()
    tesseract_config = f"--oem {oem} --psm {psm}"

    try:
        doc = fitz.open(file_path)
        page_count = _resolve_ocr_page_count(len(doc))
        for idx in range(page_count):
            page = doc.load_page(idx)
            zoom = dpi / 72.0
            matrix = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            image = Image.open(io.BytesIO(pix.tobytes("png")))

            try:
                if PIL_IMAGEOPS_AVAILABLE and ImageOps is not None:
                    image = ImageOps.autocontrast(image)
                image = image.convert("L")
                # Light sharpening by resizing up can help OCR on tiny fonts
                w, h = image.size
                if max(w, h) < 1200:
                    image = image.resize((int(w * 1.5), int(h * 1.5)))
            except Exception:
                pass

            text = pytesseract.image_to_string(image, lang=lang, config=tesseract_config)
            if text and text.strip():
                page_texts.append(text.strip())

        doc.close()
    except Exception:
        return ""

    return "\n\n".join(page_texts).strip()


def _resolve_ocr_page_count(total_pages: int) -> int:
    """Resolve how many pages OCR should process.

    CV_OCR_MAX_PAGES:
    - unset/0/negative => process all pages
    - positive integer => process up to that number of pages
    """
    raw_value = os.getenv("CV_OCR_MAX_PAGES", "0").strip()
    try:
        max_pages = int(raw_value)
    except Exception:
        max_pages = 0

    if max_pages <= 0:
        return max(0, total_pages)

    return min(total_pages, max_pages)


def save_text_as_txt(text: str, output_dir: str, base_name: str) -> str:
    """Save text as .txt file"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    txt_name = Path(base_name).with_suffix(".txt").name
    txt_path = output_path / txt_name
    txt_path.write_text(text, encoding="utf-8")
    return str(txt_path)


# ---------------------------------------------------------------------------
# Module-level singleton — BERT and embedding models are loaded once per
# process. Calling CVExtractionService() on every request was reloading
# 199 weight files each time (~3-5 s per upload).
# ---------------------------------------------------------------------------
_cv_extraction_service: Optional[CVExtractionService] = None


def get_cv_extraction_service() -> CVExtractionService:
    """Return the shared CVExtractionService instance, creating it if needed."""
    global _cv_extraction_service
    if _cv_extraction_service is None:
        _cv_extraction_service = CVExtractionService()
    return _cv_extraction_service


# Convenience function for backward compatibility
def extract_and_structure_cv(pdf_path: str) -> CVExtractionResult:
    """Extract CV and get complete structured data"""
    return get_cv_extraction_service().extract_from_pdf(pdf_path)