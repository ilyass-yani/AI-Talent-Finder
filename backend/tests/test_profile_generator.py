from pathlib import Path

import fitz
from ai_module.nlp.profile_generator import ProfileGenerator
from app.services.cv_extractor import extract_text_from_pdf, save_text_as_txt


def test_generate_profile_from_job_description():
    text = (
        "Senior Python developer with 5 years of experience in FastAPI, Docker, and SQL. "
        "Strong communication and teamwork skills are required. "
        "Bachelor degree in Computer Science. Fluent in English and French."
    )

    profile = ProfileGenerator.generate_from_text(text)

    assert profile["ideal_experience_years"] >= 5
    assert any(skill["name"].lower() == "python" for skill in profile["ideal_skills"])
    assert any(skill["name"].lower() == "fastapi" for skill in profile["ideal_skills"])
    assert "Bachelor" in profile["ideal_education"]
    assert "English" in profile["ideal_languages"]
    assert "French" in profile["ideal_languages"]


def test_extract_text_from_pdf_and_save_txt(tmp_path: Path):
    pdf_path = tmp_path / "sample_cv.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello world from CV extraction test")
    doc.save(str(pdf_path))
    doc.close()

    extracted_text = extract_text_from_pdf(str(pdf_path))
    assert "Hello world from CV extraction test" in extracted_text

    txt_dir = tmp_path / "txt"
    txt_path = save_text_as_txt(extracted_text, str(txt_dir), pdf_path.name)
    assert Path(txt_path).exists()
    assert Path(txt_path).read_text(encoding="utf-8").strip() == extracted_text.strip()
