"""Regression test for multi-column CV text extraction.

Verifies that extract_text_from_pdf() reads a 2-column CV column-by-column
(left sidebar fully, then main column) instead of interleaving rows across the
two columns, and that it does not regress on a 1-column CV.

Run:  python scripts/test_cv_column_extraction.py
Exit code 0 = all checks passed, 1 = at least one failure.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.abspath(os.path.join(HERE, ".."))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

# Keep the run deterministic and offline: OCR-first must NOT clobber the
# column-aware native text. The native_is_strong / two_column guards should
# already protect it, but pin the mode so the test does not depend on whether a
# Tesseract binary is installed on the machine running it.
os.environ.setdefault("CV_OCR_MODE", "auto")

from app.services.cv_extractor import extract_text_from_pdf, _reflow_blocks_by_column  # noqa: E402

import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("_make_test_cvs", os.path.join(HERE, "_make_test_cvs.py"))
_mk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_mk)

FIXTURES = os.path.join(BACKEND, "tests", "fixtures")
TWO_COL = os.path.join(FIXTURES, "cv_two_column.pdf")
ONE_COL = os.path.join(FIXTURES, "cv_one_column.pdf")

_failures = []


def check(cond, msg):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {msg}")
    if not cond:
        _failures.append(msg)


def _idx(text, needle):
    return text.find(needle)


def test_two_column():
    print("\n=== 2-column CV (Raphael MARTIN) ===")
    text = extract_text_from_pdf(TWO_COL)
    print("---- extracted ----")
    print(text)
    print("-------------------")

    # 1. The name must be intact and contiguous (not "Espagnol ... MARTIN").
    check("Raphael MARTIN" in text, "name 'Raphael MARTIN' is contiguous")

    # 2. All three companies present as recognizable tokens.
    for company in ("DIOR", "ORANGE", "DANONE"):
        check(company in text, f"company '{company}' present")

    # 3. Main column is contiguous: name -> title -> profile, with NO sidebar
    #    block injected between them (the interleaving symptom).
    i_name = _idx(text, "Raphael MARTIN")
    i_title = _idx(text, "Commercial Senior")
    check(i_name >= 0 and i_title > i_name, "title follows name")
    between = text[i_name:i_title]
    for sidebar in ("CONTACT", "LANGUES", "Espagnol", "COMPETENCES", "Negociation"):
        check(sidebar not in between, f"sidebar '{sidebar}' NOT injected between name and title")

    # 4. Experiences stay in order within the main column.
    i_dior = _idx(text, "DIOR")
    i_orange = _idx(text, "ORANGE")
    i_danone = _idx(text, "DANONE")
    check(0 <= i_dior < i_orange < i_danone, "experiences in order DIOR < ORANGE < DANONE")

    # 5. Education present.
    check("Sorbonne" in text and "ESUP" in text, "education (Sorbonne / ESUP) present")


def test_one_column():
    print("\n=== 1-column CV (Sophie BERNARD) — regression guard ===")
    text = extract_text_from_pdf(ONE_COL)
    print("---- extracted ----")
    print(text)
    print("-------------------")
    check("Sophie BERNARD" in text, "name 'Sophie BERNARD' present")
    i_name = _idx(text, "Sophie BERNARD")
    i_cap = _idx(text, "CAPGEMINI")
    i_atos = _idx(text, "ATOS")
    check(0 <= i_name < i_cap, "name precedes experiences")
    check(0 <= i_cap < i_atos, "experiences in order CAPGEMINI < ATOS")
    check("INSA Lyon" in text, "education (INSA Lyon) present")


def test_reflow_unit():
    print("\n=== unit: _reflow_blocks_by_column flags ===")
    import fitz
    doc = fitz.open(TWO_COL)
    _, is_two = _reflow_blocks_by_column(doc[0].get_text("blocks"), doc[0].rect.width)
    doc.close()
    check(is_two, "2-column layout detected on cv_two_column.pdf")

    doc = fitz.open(ONE_COL)
    _, is_two = _reflow_blocks_by_column(doc[0].get_text("blocks"), doc[0].rect.width)
    doc.close()
    check(not is_two, "1-column layout NOT misdetected as 2-column")


if __name__ == "__main__":
    if not os.path.exists(TWO_COL) or not os.path.exists(ONE_COL):
        _mk.make_two_column_cv(TWO_COL)
        _mk.make_one_column_cv(ONE_COL)

    test_reflow_unit()
    test_two_column()
    test_one_column()

    print()
    if _failures:
        print(f"RESULT: {len(_failures)} check(s) FAILED")
        for f in _failures:
            print("  - " + f)
        sys.exit(1)
    print("RESULT: all checks passed")
    sys.exit(0)
