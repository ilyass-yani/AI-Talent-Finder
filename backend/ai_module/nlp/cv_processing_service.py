"""
Unified CV Extraction & Parsing Service
Replaces: cv_extractor.py + enhanced_nlp_service.py
Handles: PDF extraction + HuggingFace NER parsing + data structuring
"""

import logging
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import uuid
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    from transformers import pipeline, AutoTokenizer
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    logger.warning("HuggingFace transformers not available")


class PDFExtractor:
    """Extract text and metadata from multiple CV file formats"""
    
    MAX_FILE_SIZE_MB = 50
    SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".docx", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
    
    @staticmethod
    def extract(file_path: str) -> Dict[str, Any]:
        """
        Extract content from supported document formats
        
        Returns:
            Dict with: text, pages, images_detected, metadata
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_size_mb = Path(file_path).stat().st_size / (1024 * 1024)
        if file_size_mb > PDFExtractor.MAX_FILE_SIZE_MB:
            raise ValueError(f"File too large: {file_size_mb:.1f}MB (max {PDFExtractor.MAX_FILE_SIZE_MB}MB)")

        suffix = Path(file_path).suffix.lower()
        if suffix not in PDFExtractor.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported CV format: {suffix}")

        if suffix == ".txt":
            return PDFExtractor._extract_text(file_path)
        if suffix == ".docx":
            return PDFExtractor._extract_docx(file_path)
        if suffix == ".pdf":
            return PDFExtractor._extract_pdf(file_path)
        return PDFExtractor._extract_image(file_path)

    @staticmethod
    def _extract_text(file_path: str) -> Dict[str, Any]:
        text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        return {
            "success": True,
            "text": text,
            "pages": 1,
            "images_detected": 0,
            "metadata": {"title": "", "author": "", "pages": 1, "has_images": False, "file_type": "txt"},
        }

    @staticmethod
    def _extract_docx(file_path: str) -> Dict[str, Any]:
        if not DOCX_AVAILABLE:
            raise RuntimeError("python-docx is not installed")

        document = Document(file_path)
        paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
        text = "\n".join(paragraphs).strip()
        return {
            "success": True,
            "text": text,
            "pages": 1,
            "images_detected": 0,
            "metadata": {"title": "", "author": "", "pages": 1, "has_images": False, "file_type": "docx"},
        }

    @staticmethod
    def _extract_image(file_path: str) -> Dict[str, Any]:
        if not (PIL_AVAILABLE and TESSERACT_AVAILABLE):
            raise RuntimeError("OCR dependencies are not available")

        try:
            image = Image.open(file_path)
            extracted_text = pytesseract.image_to_string(image, lang="eng+fra")
        except Exception:
            # Fallback to default OCR language if FR data is unavailable.
            image = Image.open(file_path)
            extracted_text = pytesseract.image_to_string(image)

        return {
            "success": True,
            "text": extracted_text,
            "pages": 1,
            "images_detected": 1,
            "metadata": {"title": "", "author": "", "pages": 1, "has_images": True, "file_type": "image"},
        }

    @staticmethod
    def _ocr_pdf_page(page) -> str:
        if not (PIL_AVAILABLE and TESSERACT_AVAILABLE):
            return ""

        try:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
            try:
                return pytesseract.image_to_string(image, lang="eng+fra")
            except Exception:
                return pytesseract.image_to_string(image)
        except Exception as exc:
            logger.warning(f"PDF OCR failed on page {page.number + 1}: {exc}")
            return ""

    @staticmethod
    def _extract_pdf(file_path: str) -> Dict[str, Any]:
        doc = fitz.open(file_path)
        text_parts = []
        image_count = 0

        try:
            for page_num, page in enumerate(doc):
                page_text = page.get_text().strip()
                if page_text:
                    text_parts.append(f"--- PAGE {page_num + 1} ---\n{page_text}")
                else:
                    ocr_text = PDFExtractor._ocr_pdf_page(page).strip()
                    if ocr_text:
                        text_parts.append(f"--- PAGE {page_num + 1} (OCR) ---\n{ocr_text}")

                image_count += len(page.get_images())

            metadata = {
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "pages": doc.page_count,
                "has_images": image_count > 0,
                "file_type": "pdf",
            }

            extracted_text = "\n\n".join(text_parts).strip()
            return {
                "success": True,
                "text": extracted_text,
                "pages": doc.page_count,
                "images_detected": image_count,
                "metadata": metadata,
            }

        finally:
            doc.close()


class TextNormalizer:
    """Normalize and clean extracted text"""
    
    @staticmethod
    def normalize(text: str) -> str:
        """Normalize whitespace while preserving structure"""
        # Replace multiple spaces/tabs
        text = re.sub(r'[ \t]+', ' ', text)
        # Preserve paragraph breaks
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        # Remove repeated bullet noise and OCR artifacts common in unknown CVs
        text = re.sub(r'\n[\s•·●▪-]{1,}\n', '\n', text)
        return text.strip()
    
    @staticmethod
    def format_for_parsing(text: str, metadata: Dict = None) -> str:
        """
        Format text for NER model input
        Adds context and structure
        """
        lines = []
        
        if metadata:
            if metadata.get("title"):
                lines.append(f"Title: {metadata['title']}")
            if metadata.get("author"):
                lines.append(f"Author: {metadata['author']}")
            lines.append("")
        
        lines.append(TextNormalizer.normalize(text))
        
        return "\n".join(lines)


class LanguageExtractor:
    """
    Extract programming and natural languages
    Handles both explicit and implicit mentions
    """
    
    LANGUAGE_PATTERNS = {
        # Programming languages
        "Python": [r"\bPython\b", r"\bPy\b"],
        "JavaScript": [r"\bJavaScript\b", r"\bJS\b", r"\b\.js\b"],
        "TypeScript": [r"\bTypeScript\b", r"\bTS\b"],
        "Java": [r"\bJava\b"],
        "C++": [r"\bC\+\+\b", r"\bCPP\b"],
        "C#": [r"\bC#\b", r"\bCSharp\b"],
        "PHP": [r"\bPHP\b"],
        "Go": [r"\bGo\b", r"\bGolang\b"],
        "Rust": [r"\bRust\b"],
        "Ruby": [r"\bRuby\b"],
        "SQL": [r"\bSQL\b", r"\bMySQL\b", r"\bPostgreSQL\b", r"\bPostgres\b"],
        "R": [r"\bR\b"],
        "Kotlin": [r"\bKotlin\b"],
        "Swift": [r"\bSwift\b"],
        "Bash": [r"\bBash\b"],
        
        # Frameworks/Tech
        "React": [r"\bReact\b"],
        "Vue": [r"\bVue\b"],
        "Angular": [r"\bAngular\b"],
        "Django": [r"\bDjango\b"],
        "FastAPI": [r"\bFastAPI\b"],
        "Docker": [r"\bDocker\b"],
        "Kubernetes": [r"\bKubernetes\b"],
        "AWS": [r"\bAWS\b"],
        "Docker": [r"\bDocker\b"],
        
        # Natural languages
        "French": [r"\bFrench\b", r"\b(Français|français)\b"],
        "English": [r"\bEnglish\b"],
        "Spanish": [r"\bSpanish\b"],
        "German": [r"\bGerman\b"],
        "Arabic": [r"\bArabic\b"],
        "Chinese": [r"\bChinese\b"],
        "Japanese": [r"\bJapanese\b"],
    }
    
    @staticmethod
    def extract(text: str) -> List[Dict[str, Any]]:
        """Extract languages from text"""
        languages = []
        found = set()
        
        for lang, patterns in LanguageExtractor.LANGUAGE_PATTERNS.items():
            if lang in found:
                continue
            
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    languages.append({
                        "language": lang,
                        "confidence": 0.9,
                        "type": "implicit"
                    })
                    found.add(lang)
                    break
        
        return languages


class HuggingFaceResumeParser:
    """Parse CV using HuggingFace NER model"""
    
    MODEL_ID = "AventIQ-AI/Resume-Parsing-NER-AI-Model"
    
    def __init__(self):
        """Initialize parser"""
        if not HF_AVAILABLE:
            logger.warning("HuggingFace not available, using fallback extraction")
            self.ner_pipeline = None
            return
        
        try:
            self.ner_pipeline = pipeline(
                "token-classification",
                model=self.MODEL_ID,
                aggregation_strategy="simple"
            )
            logger.info(f"Loaded HF model: {self.MODEL_ID}")
        except Exception as e:
            logger.error(f"Failed to load HF model: {str(e)}")
            self.ner_pipeline = None
    
    def parse(self, text: str) -> Dict[str, List[Dict]]:
        """Parse text using NER model"""
        if not self.ner_pipeline:
            return self._fallback_parse(text)
        
        try:
            # Limit input to avoid memory issues
            text_chunk = text[:512]
            entities = self.ner_pipeline(text_chunk)
            
            parsed = self._organize_entities(entities)
            parsed["languages"] = LanguageExtractor.extract(text)
            
            return parsed
        except Exception as e:
            logger.error(f"Parsing error: {str(e)}")
            return self._fallback_parse(text)
    
    def _organize_entities(self, ner_results: List[Dict]) -> Dict[str, List[Dict]]:
        """Organize NER results"""
        organized = {}
        
        for entity_result in ner_results:
            entity_type = entity_result.get("entity_group", "UNKNOWN").upper()
            entity_value = entity_result.get("word", "").strip()
            confidence = entity_result.get("score", 0.0)
            
            if not entity_value:
                continue
            
            if entity_type not in organized:
                organized[entity_type] = []
            
            if not any(e["value"].lower() == entity_value.lower() for e in organized[entity_type]):
                organized[entity_type].append({
                    "value": entity_value,
                    "confidence": round(confidence, 3)
                })
        
        return organized
    
    def _fallback_parse(self, text: str) -> Dict:
        """Fallback extraction without HF model"""
        logger.info("Using fallback extraction (no HF model)")
        
        result = {
            "languages": LanguageExtractor.extract(text),
            "emails": self._extract_emails(text),
            "phones": self._extract_phones(text)
        }
        
        return result
    
    @staticmethod
    def _extract_emails(text: str) -> List[Dict]:
        """Extract email addresses"""
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(pattern, text)
        return [{"value": m, "confidence": 1.0} for m in matches]
    
    @staticmethod
    def _extract_phones(text: str) -> List[Dict]:
        """Extract phone numbers"""
        pattern = r'\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}'
        matches = re.findall(pattern, text)
        return [{"value": m, "confidence": 0.8} for m in matches]


class CVExtractionPipeline:
    """Complete CV extraction and parsing pipeline"""
    
    def __init__(self, output_dir: Optional[str] = None):
        """Initialize pipeline"""
        self.pdf_extractor = PDFExtractor()
        self.parser = HuggingFaceResumeParser()
        self.output_dir = Path(output_dir) if output_dir else None
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def process(self, pdf_path: str) -> Dict[str, Any]:
        """
        Process PDF: extract → normalize → parse
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            Complete extraction result
        """
        logger.info(f"Starting CV processing: {Path(pdf_path).name}")
        
        try:
            # Step 1: Extract PDF
            extraction = self.pdf_extractor.extract(pdf_path)
            if not extraction["success"]:
                return {"success": False, "error": extraction.get("error", "Extraction failed")}
            
            # Step 2: Normalize text
            normalized_text = TextNormalizer.normalize(extraction["text"])
            formatted_text = TextNormalizer.format_for_parsing(
                normalized_text,
                extraction["metadata"]
            )
            
            # Step 3: Parse with NER
            parsed_entities = self.parser.parse(formatted_text)
            
            # Step 4: Structure output
            result = {
                "success": True,
                "file": Path(pdf_path).name,
                "source_type": extraction.get("metadata", {}).get("file_type", Path(pdf_path).suffix.lstrip(".")),
                "metadata": extraction["metadata"],
                "extraction": {
                    "pages": extraction["pages"],
                    "images_detected": extraction["images_detected"],
                    "text_length": len(normalized_text)
                },
                "parsed_entities": parsed_entities,
                "extracted_text": normalized_text,
                "timestamp": datetime.utcnow().isoformat()
            }

            safe_result = self._make_json_safe(result)
            
            # Step 5: Save if output_dir specified
            if self.output_dir:
                self._save_outputs(pdf_path, safe_result)
            
            logger.info(f"✓ CV processing completed: {len(parsed_entities)} entity types")
            return safe_result
        
        except Exception as e:
            logger.error(f"CV processing failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "file": Path(pdf_path).name
            }
    
    def _save_outputs(self, pdf_path: str, result: Dict):
        """Save extracted content and parsed entities"""
        base_name = Path(pdf_path).stem
        
        # Save normalized text
        txt_path = self.output_dir / f"{base_name}_extracted.txt"
        txt_path.write_text(result["extracted_text"], encoding='utf-8')
        logger.info(f"Saved: {txt_path}")
        
        # Save parsed result as JSON
        json_path = self.output_dir / f"{base_name}_parsed.json"
        safe_result = self._make_json_safe(result)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(safe_result, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved: {json_path}")

    @staticmethod
    def _make_json_safe(value: Any) -> Any:
        """Convert nested values to JSON-serializable Python types."""
        # dict
        if isinstance(value, dict):
            return {k: CVExtractionPipeline._make_json_safe(v) for k, v in value.items()}

        # list/tuple/set
        if isinstance(value, (list, tuple, set)):
            return [CVExtractionPipeline._make_json_safe(v) for v in value]

        # numpy scalar types (float32, int64, etc.) expose .item()
        if hasattr(value, "item") and callable(getattr(value, "item")):
            try:
                return value.item()
            except Exception:
                pass

        # datetime-like object
        if hasattr(value, "isoformat") and callable(getattr(value, "isoformat")):
            try:
                return value.isoformat()
            except Exception:
                pass

        return value


# Singleton instance for the application
_pipeline_instance = None

def get_cv_pipeline(output_dir: Optional[str] = None) -> CVExtractionPipeline:
    """Get or create CV pipeline instance"""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = CVExtractionPipeline(output_dir)
    elif output_dir:
        # Keep singleton but allow late configuration of output directory.
        _pipeline_instance.output_dir = Path(output_dir)
        _pipeline_instance.output_dir.mkdir(parents=True, exist_ok=True)
    return _pipeline_instance
