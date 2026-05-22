from pathlib import Path

import fitz

from app.services import cv_extractor


def test_extract_text_from_pdf_prefers_ocr_when_native_text_is_empty(tmp_path: Path, monkeypatch):
    pdf_path = tmp_path / "scanned_cv.pdf"

    doc = fitz.open()
    doc.new_page()
    doc.save(str(pdf_path))
    doc.close()

    monkeypatch.setattr(cv_extractor, "FITZ_AVAILABLE", True)
    monkeypatch.setattr(cv_extractor, "TESSERACT_AVAILABLE", True)
    monkeypatch.setattr(cv_extractor, "PIL_AVAILABLE", True)
    monkeypatch.setattr(cv_extractor, "_extract_text_from_pdf_ocr", lambda *_args, **_kwargs: "SAMIRA BEN YOUSEF\nPython\nFastAPI\nDocker")
    monkeypatch.setattr(
        cv_extractor,
        "_score_extracted_text",
        lambda text: 1000 if "SAMIRA" in text else 0,
    )

    extracted_text = cv_extractor.extract_text_from_pdf(str(pdf_path))

    assert "SAMIRA BEN YOUSEF" in extracted_text
    assert "FastAPI" in extracted_text
    assert "Docker" in extracted_text