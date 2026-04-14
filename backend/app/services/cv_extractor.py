import fitz  # PyMuPDF
from pathlib import Path


def extract_text_from_pdf(file_path: str) -> str:
    doc = fitz.open(file_path)
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts).strip()


def save_text_as_txt(text: str, output_dir: str, base_name: str) -> str:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    txt_name = Path(base_name).with_suffix(".txt").name
    txt_path = output_path / txt_name
    txt_path.write_text(text, encoding="utf-8")
    return str(txt_path)