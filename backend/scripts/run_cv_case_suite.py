#!/usr/bin/env python3
"""
Run a representative CV case suite for extraction quality checks.
Usage:
  PYTHONPATH=. python backend/scripts/run_cv_case_suite.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

from app.services.cv_extractor import CVExtractionService

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASES = ROOT / "backend" / "tests" / "fixtures" / "cv_cases.json"


def _load_cases(path: Path) -> List[Dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload.get("cases", []))


def _to_lower_set(values: List[str]) -> set[str]:
    return {str(v).strip().lower() for v in values if str(v).strip()}


def _score_expected(found: List[str], expected: List[str]) -> float:
    if not expected:
        return 1.0
    found_lower = _to_lower_set(found)
    expected_lower = _to_lower_set(expected)
    if not expected_lower:
        return 1.0
    matched = sum(1 for skill in expected_lower if skill in found_lower)
    return matched / max(1, len(expected_lower))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--min-skill-match", type=float, default=0.5)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    cases_path = Path(args.cases)
    if not cases_path.exists():
        raise SystemExit(f"Cases file not found: {cases_path}")

    service = CVExtractionService()
    failures = 0

    cases = _load_cases(cases_path)
    print(f"Running {len(cases)} CV cases from {cases_path}")
    for case in cases:
        case_id = case.get("id", "unknown")
        print("\n---")
        print(f"Case: {case_id}")

        text = case.get("text")
        pdf_path = case.get("pdf_path")
        requires_ocr = bool(case.get("requires_ocr"))

        if pdf_path:
            pdf_path = str(pdf_path)
            pdf_full = (ROOT / pdf_path).resolve()
            if not pdf_full.exists():
                print(f"PDF missing: {pdf_full}")
                if requires_ocr:
                    print("Skipping OCR-required case (no PDF provided).")
                continue
            result = service.extract_from_pdf(str(pdf_full))
        elif text:
            result = service.extract_from_text(str(text))
        else:
            print("No text or PDF provided for this case.")
            continue

        expected_skills = case.get("expected_skills", [])
        expected_languages = case.get("expected_languages", [])
        found_skills = [item.get("name") for item in result.skills if isinstance(item, dict)]
        found_languages = []
        if isinstance(result.structured, dict):
            found_languages = result.structured.get("languages") or []

        skill_match = _score_expected(found_skills, expected_skills)
        lang_match = _score_expected(found_languages, expected_languages)

        print(f"Quality score: {result.quality_score:.1f}")
        print(f"Skills extracted: {len(found_skills)}")
        print(f"Expected skills coverage: {skill_match:.2f}")
        if expected_languages:
            print(f"Expected language coverage: {lang_match:.2f}")

        if skill_match < args.min_skill_match:
            failures += 1
            print("WARN: skill coverage below threshold")

    print("\nDone.")
    if failures and args.strict:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
