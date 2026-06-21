"""Regression test for GLiNER-based CV extraction.

Verifies that on the 2-column CV fixture (Raphael MARTIN):
  - full_name is extracted correctly even when the name appears deep in the
    reflowed text (the position-scoring weakness of the regex extractor).
  - DIOR / ORANGE / DANONE are extracted as companies.

Also checks that the 1-column CV (Sophie BERNARD) does not regress.

Finally, verifies that USE_GLINER=false falls back to the regex extractor
without crashing.

test_cleanup_logic() is a pure unit test for the GLiNER post-processing
pipeline.  It uses synthetic (mock) entity output so it runs without the
GLiNER package being installed.

Run:
    cd backend
    python scripts/test_gliner_extraction.py

Exit code 0 = all checks passed, 1 = at least one failure.
"""
from __future__ import annotations

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.abspath(os.path.join(HERE, ".."))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

# Regenerate fixtures on demand
spec = importlib.util.spec_from_file_location(
    "_make_test_cvs", os.path.join(HERE, "_make_test_cvs.py")
)
_mk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_mk)

FIXTURES = os.path.join(BACKEND, "tests", "fixtures")
TWO_COL = os.path.join(FIXTURES, "cv_two_column.pdf")
ONE_COL = os.path.join(FIXTURES, "cv_one_column.pdf")

_failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {msg}")
    if not cond:
        _failures.append(msg)


# ---------------------------------------------------------------------------
# Check GLiNER availability before running model-dependent tests
# ---------------------------------------------------------------------------

def _gliner_importable() -> bool:
    try:
        import gliner  # noqa: F401
        return True
    except ImportError:
        return False


GLINER_PRESENT = _gliner_importable()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _name_matches(extracted: str | None, first: str, last: str) -> bool:
    """Case-insensitive check that both first and last name tokens appear."""
    if not extracted:
        return False
    lower = extracted.lower()
    return first.lower() in lower and last.lower() in lower


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_cleanup_logic():
    """Post-processing unit test: uses synthetic (mock) GLiNER output.

    Does NOT require the GLiNER package to be installed -- it calls
    _clean_entities() directly.  Validates:
      - '##' BERT artifacts are removed
      - fragments with < 3 alpha chars ('Li') and short non-acronyms ('Esp')
        are removed
      - school-like company spans (ESUP, Universite Sorbonne) are moved to
        education, not kept in companies
      - interests do not contain the candidate name or a section header
    """
    print("\n=== GLiNER cleanup unit test (no model needed) ===")

    from ai_module.nlp.gliner_extractor import GLiNERExtractor

    extractor = GLiNERExtractor()

    # Simulate raw GLiNER output that mirrors the observed 2-column CV problem.
    # ASCII apostrophes and no accented literals (to keep this file ASCII-safe).
    mock_entities = [
        # --- person name ---
        {"label": "person name", "text": "Raphael MARTIN"},

        # --- companies: 3 real + 4 pollutants ---
        {"label": "company", "text": "DIOR"},
        {"label": "company", "text": "ORANGE"},
        {"label": "company", "text": "DANONE"},
        {"label": "company", "text": "ESUP"},                 # school, not company
        {"label": "company", "text": "Universite Sorbonne"},  # school, not company
        {"label": "company", "text": "Esp"},                  # short non-acronym fragment
        {"label": "company", "text": "Li"},                   # < 3 alpha chars
        {
            "label": "company",
            "text": "##cence Pro Commerce et Distribution E",  # BERT ## artifact
        },

        # --- schools (GLiNER-labeled) ---
        {"label": "school", "text": "Universite Sorbonne"},
        {"label": "school", "text": "ESUP"},

        # --- interests: 1 valid + 2 pollutants ---
        {"label": "interest", "text": "Raphael MARTIN"},         # candidate name
        {"label": "interest", "text": "INTITULE DU POSTE / STAGE"},  # form label with /
        {"label": "interest", "text": "Voyage"},                 # valid interest
    ]

    result = extractor._clean_entities(mock_entities)
    print(f"  full_name  : {result.get('full_name')!r}")
    print(f"  companies  : {result.get('companies')}")
    print(f"  education  : {result.get('education')}")
    print(f"  job_titles : {result.get('job_titles')}")
    print(f"  interests  : {result.get('interests')}")

    companies = result.get("companies", [])
    education = result.get("education", [])
    interests = result.get("interests", [])
    full_name = result.get("full_name")

    # full_name must not regress
    check(
        _name_matches(full_name, "Raphael", "Martin"),
        f"cleanup: full_name is Raphael MARTIN (got {full_name!r})",
    )

    # --- companies ---
    for co in ("DIOR", "ORANGE", "DANONE"):
        check(co in companies, f"cleanup: '{co}' kept in companies (got {companies})")

    check(
        "ESUP" not in companies,
        f"cleanup: 'ESUP' NOT in companies (got {companies})",
    )
    check(
        not any("Sorbonne" in c or "sorbonne" in c.lower() for c in companies),
        f"cleanup: 'Universite Sorbonne' NOT in companies (got {companies})",
    )
    check(
        not any(c.startswith("##") for c in companies),
        f"cleanup: no '##' artifacts in companies (got {companies})",
    )
    check(
        not any(c in ("Esp", "Li") for c in companies),
        f"cleanup: short fragments not in companies (got {companies})",
    )

    # --- education ---
    check(
        any("Sorbonne" in e or "sorbonne" in e.lower() for e in education),
        f"cleanup: 'Universite Sorbonne' in education (got {education})",
    )
    check(
        any("ESUP" in e or "esup" in e.lower() for e in education),
        f"cleanup: 'ESUP' in education (got {education})",
    )

    # --- interests ---
    check(
        "Voyage" in interests,
        f"cleanup: valid interest 'Voyage' kept (got {interests})",
    )
    check(
        not any((full_name or "").lower() == i.lower() for i in interests),
        f"cleanup: candidate name NOT in interests (got {interests})",
    )
    check(
        not any("INTITULE" in i.upper() or "/" in i for i in interests),
        f"cleanup: form label NOT in interests (got {interests})",
    )

    # --- word-concatenation fix ---
    # Simulate the real artifact observed in production: 'Voyageen sac a dos'
    # (two adjacent PDF text blocks merged without a space separator).
    from ai_module.nlp.gliner_extractor import GLiNERExtractor as _G
    _ext = _G()
    fused_cases = [
        ("Voyageen sac a dos",      "Voyage en sac a dos"),
        ("Theatreet concerts",      "Theatre et concerts"),
        ("Cuisinedu jour",          "Cuisine du jour"),
        ("Randonnee",               "Randonnee"),     # single word -- must be unchanged
        ("Benevola",                "Benevola"),      # ends in 'la' but no following space
        ("Voyage en sac a dos",     "Voyage en sac a dos"),  # already correct
    ]
    for fused, expected in fused_cases:
        got = _ext._fix_concatenated_words(fused)
        check(
            got == expected,
            f"concat fix: {fused!r} -> {got!r} (expected {expected!r})",
        )
    # End-to-end: verify the full pipeline repairs the concat artifact
    fused_mock_extra = [
        {"label": "person name", "text": "Test User"},
        {"label": "interest", "text": "Voyageen sac a dos"},
        {"label": "interest", "text": "Randonnee"},
    ]
    fused_result = _ext._clean_entities(fused_mock_extra)
    check(
        any("Voyage" in i and " en" in i for i in fused_result.get("interests", [])),
        f"concat e2e: 'Voyageen sac a dos' repaired in pipeline "
        f"(interests={fused_result.get('interests')})",
    )
    check(
        "Randonnee" in fused_result.get("interests", []),
        f"concat e2e: 'Randonnee' unchanged (interests={fused_result.get('interests')})",
    )


def test_gliner_unit():
    """Unit test: GLiNERExtractor on raw CV text (no PDF parsing)."""
    print("\n=== GLiNER unit test (raw text) ===")
    if not GLINER_PRESENT:
        print("  [SKIP] gliner package not installed -- skipping unit test")
        return

    from ai_module.nlp.gliner_extractor import GLiNERExtractor

    extractor = GLiNERExtractor()
    if not extractor._load_model():
        print("  [SKIP] GLiNER model could not be loaded (network / RAM) -- skipping")
        return

    sample_text = """Raphael MARTIN
Commercial Senior

EXPERIENCES
Responsable Commercial - DIOR (2020-2024)
Charge d affaires - ORANGE (2016-2020)
Commercial - DANONE (2014-2016)

FORMATION
Master Commerce - Universite Sorbonne (2014)
Licence Gestion - ESUP (2012)
"""
    result = extractor.extract(sample_text)
    print(f"  GLiNER raw output: {result}")

    check(
        _name_matches(result.get("full_name"), "Raphael", "MARTIN"),
        f"GLiNER unit: full_name contains 'Raphael MARTIN' (got {result.get('full_name')!r})",
    )
    for co in ("DIOR", "ORANGE", "DANONE"):
        companies_lower = [c.upper() for c in result.get("companies", [])]
        check(
            any(co in c for c in companies_lower),
            f"GLiNER unit: company '{co}' extracted (companies={result.get('companies')})",
        )


def test_pipeline_two_column():
    """Integration: full pipeline on cv_two_column.pdf."""
    print("\n=== Pipeline integration — 2-column CV (Raphael MARTIN) ===")

    # Force-enable GLiNER for this test (it may be disabled via env)
    os.environ["USE_GLINER"] = "true"

    # Re-import to pick up the env var (singleton may already be created,
    # but _use_gliner is set per-instance so we create a fresh one)
    from app.services.cv_extractor import CVExtractionService, extract_text_from_pdf

    # Check text extraction first (column reflow)
    text = extract_text_from_pdf(TWO_COL)
    check("Raphael MARTIN" in text, "text extraction: 'Raphael MARTIN' in reflowed text")

    if not GLINER_PRESENT:
        print("  [SKIP] gliner not installed -- pipeline GLiNER checks skipped")
        print("  Running regex-only pipeline check ...")
        svc = CVExtractionService()
        result = svc.extract_from_text(text)
        candidate = svc.to_candidate_dict(result)
        name = candidate.get("full_name") or candidate.get("extracted_name")
        print(f"  Regex-only full_name: {name!r}")
        print(f"  Regex-only companies: {candidate.get('extracted_companies')!r}")
        return

    svc = CVExtractionService()
    result = svc.extract_from_text(text)
    candidate = svc.to_candidate_dict(result)

    name = candidate.get("full_name") or candidate.get("extracted_name")
    print(f"  Extracted full_name: {name!r}")
    check(
        _name_matches(name, "Raphael", "Martin"),
        f"pipeline 2-col: full_name ~ 'Raphael MARTIN' (got {name!r})",
    )

    import json
    companies_raw = candidate.get("extracted_companies") or "[]"
    if isinstance(companies_raw, list):
        companies = companies_raw
    else:
        try:
            companies = json.loads(companies_raw)
        except Exception:
            companies = []
    companies_str = " ".join(str(c).upper() for c in companies)
    print(f"  Extracted companies: {companies}")
    for co in ("DIOR", "ORANGE", "DANONE"):
        check(co in companies_str, f"pipeline 2-col: company '{co}' in extracted_companies")


def test_pipeline_one_column():
    """Regression: 1-column CV must still work correctly."""
    print("\n=== Pipeline integration — 1-column CV (Sophie BERNARD) — regression ===")

    from app.services.cv_extractor import CVExtractionService, extract_text_from_pdf

    text = extract_text_from_pdf(ONE_COL)
    check("Sophie BERNARD" in text, "text extraction: 'Sophie BERNARD' in text")

    svc = CVExtractionService()
    result = svc.extract_from_text(text)
    candidate = svc.to_candidate_dict(result)

    name = candidate.get("full_name") or candidate.get("extracted_name")
    print(f"  Extracted full_name: {name!r}")
    check(
        _name_matches(name, "Sophie", "Bernard"),
        f"pipeline 1-col: full_name ~ 'Sophie BERNARD' (got {name!r})",
    )


def test_fallback_without_gliner():
    """Verify USE_GLINER=false falls back to regex without crashing."""
    print("\n=== Fallback: USE_GLINER=false ===")

    os.environ["USE_GLINER"] = "false"

    # Must import AFTER setting the env var so a fresh instance picks it up
    from app.services.cv_extractor import CVExtractionService

    svc = CVExtractionService()
    check(not svc._use_gliner, "USE_GLINER=false: _use_gliner is False on service instance")

    sample = "Jean DUPONT\nIngenieur Logiciel\njean.dupont@example.com"
    try:
        result = svc.extract_from_text(sample)
        candidate = svc.to_candidate_dict(result)
        check(True, "USE_GLINER=false: extract_from_text does not crash")
    except Exception as exc:
        check(False, f"USE_GLINER=false: extract_from_text crashed ({exc})")

    # Restore
    os.environ["USE_GLINER"] = "true"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not os.path.exists(TWO_COL) or not os.path.exists(ONE_COL):
        print("Generating test fixtures ...")
        _mk.make_two_column_cv(TWO_COL)
        _mk.make_one_column_cv(ONE_COL)

    test_cleanup_logic()
    test_gliner_unit()
    test_pipeline_two_column()
    test_pipeline_one_column()
    test_fallback_without_gliner()

    print()
    if _failures:
        print(f"RESULT: {len(_failures)} check(s) FAILED")
        for f in _failures:
            print("  - " + f)
        sys.exit(1)
    print("RESULT: all checks passed")
    sys.exit(0)
