#!/usr/bin/env python3
"""Batch CV extraction helper.

Usage:
  PYTHONPATH=. python backend/scripts/run_extraction.py --input uploads/cvs --out data/extracted_sample.jsonl --mode ocr --limit 10
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import os
from app.services.cv_extractor import CVExtractionService


def iter_pdf_files(input_path: Path) -> Iterable[Path]:
    if input_path.is_file():
        yield input_path
        return
    for p in input_path.rglob("*.pdf"):
        yield p
    for p in input_path.rglob("*.txt"):
        yield p


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input file or directory (PDFs)")
    parser.add_argument("--out", required=True, help="Output JSONL path")
    parser.add_argument("--mode", choices=["ocr", "ner", "auto"], default="auto")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--dpi", type=int, help="Override OCR DPI (env CV_OCR_DPI)")
    parser.add_argument("--psm", type=str, help="Override Tesseract PSM (env CV_OCR_PSM)")
    parser.add_argument("--oem", type=str, help="Override Tesseract OEM (env CV_OCR_OEM)")
    args = parser.parse_args(list(argv) if argv is not None else None)

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input not found: {input_path}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Apply runtime OCR overrides
    if args.dpi:
        os.environ["CV_OCR_DPI"] = str(args.dpi)
    if args.psm:
        os.environ["CV_OCR_PSM"] = str(args.psm)
    if args.oem:
        os.environ["CV_OCR_OEM"] = str(args.oem)

    service = CVExtractionService()

    files = list(iter_pdf_files(input_path))
    files = files[: args.limit]

    with out_path.open("w", encoding="utf-8") as fh:
        for pdf in files:
            try:
                # Use text path for .txt files to avoid PDF parsing errors
                if str(pdf).lower().endswith(".txt"):
                    text = pdf.read_text(encoding="utf-8", errors="ignore")
                    res = service.extract_from_text(text)
                else:
                    res = service.extract_from_pdf(str(pdf))
                record = {
                    "file": str(pdf),
                    "quality_score": res.quality_score,
                    "raw_text_length": len(res.raw_text or ""),
                    "structured": res.structured,
                    "skills_count": len(res.skills or []),
                }
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                print(f"Processed: {pdf} -> score={res.quality_score:.1f} len={record['raw_text_length']}")
            except Exception as exc:
                print(f"Error processing {pdf}: {exc}")

    print(f"Wrote {out_path} ({len(files)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
