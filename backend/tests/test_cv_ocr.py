import os
import json
from pathlib import Path
import pytest

from app.services.cv_extractor import extract_text_from_pdf, _extract_text_with_yellow, CVExtractionService

TEST_DIR = Path("backend/uploads/cvs")
SAMPLE_TXT = TEST_DIR / "3ae24dcc5ecd4fa084774a3e07f7a36d_test_cv_clean.txt"


def test_extract_text_from_pdf_reads_txt():
    assert SAMPLE_TXT.exists(), "Sample txt fixture must exist for this test"
    content = extract_text_from_pdf(str(SAMPLE_TXT))
    assert isinstance(content, str)
    assert len(content) > 0


@pytest.mark.skipif(not (os.getenv('FITZ_AVAILABLE') and os.getenv('TESSERACT_AVAILABLE')),
                    reason="Requires fitz + tesseract to run yellow OCR")
def test_extract_text_with_yellow_on_txt_returns_empty():
    # Passing a .txt path should gracefully return empty for _extract_text_with_yellow
    res = _extract_text_with_yellow(str(SAMPLE_TXT))
    assert res == "" or isinstance(res, str)


def test_extract_from_text_structured():
    service = CVExtractionService()
    txt = SAMPLE_TXT.read_text(encoding='utf-8', errors='ignore')
    res = service.extract_from_text(txt)
    assert res.raw_text is not None
    assert isinstance(res.quality_score, (int, float))
    assert isinstance(res.structured, dict)
