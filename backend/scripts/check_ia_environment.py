#!/usr/bin/env python3
"""
Check AI environment: optional deps, API keys, and fallback modes.
Run: PYTHONPATH=. python3 backend/scripts/check_ia_environment.py
"""

from __future__ import annotations

from typing import Dict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.capabilities import get_capabilities


def _section(title: str) -> None:
    print("\n" + title)
    print("=" * len(title))


def _print_feature(name: str, detail: Dict[str, object]) -> None:
    status = str(detail.get("status", "missing")).upper()
    print(f"{name}: {status}")
    required_missing = detail.get("required_missing") or []
    optional_missing = detail.get("optional_missing") or []
    notes = str(detail.get("notes") or "").strip()
    if required_missing:
        print(f"  missing required: {', '.join(required_missing)}")
    if optional_missing:
        print(f"  missing optional: {', '.join(optional_missing)}")
    if notes:
        print(f"  notes: {notes}")


def main() -> None:
    cap = get_capabilities(force_refresh=True)

    _section("AI environment quick-check")
    print(f"timestamp: {cap.get('timestamp')}")

    _section("Features")
    features = cap.get("features", {})
    for name in sorted(features.keys()):
        _print_feature(name, features[name])

    _section("Dependencies")
    dependencies = cap.get("dependencies", {})
    for name in sorted(dependencies.keys()):
        print(f"{name}: {'OK' if dependencies[name] else 'MISSING'}")

    tesseract_path = cap.get("tesseract_path")
    if tesseract_path:
        print(f"tesseract_path: {tesseract_path}")
    else:
        tcmd = cap.get("tesseract_cmd")
        if tcmd:
            print("tesseract_path: NOT FOUND (check TESSERACT_CMD)")
        else:
            print("tesseract_path: NOT FOUND")

    _section("API keys")
    api_keys = cap.get("api_keys", {})
    for name in sorted(api_keys.keys()):
        print(f"{name}: {'SET' if api_keys[name] else 'NOT SET'}")

    _section("Strict mode")
    required_features = cap.get("required_features") or []
    print(f"AI_FEATURES_STRICT: {'ON' if cap.get('strict') else 'OFF'}")
    print(
        "AI_FEATURES_REQUIRED: "
        + (", ".join(required_features) if required_features else "(not set)")
    )

    _section("Quick recommendations")
    print("- Install optional packages with `pip install -r backend/requirements-faiss-optional.txt`")
    print("- Set ANTHROPIC_API_KEY to enable LLM responses")
    print("- Install Tesseract system binary for OCR on scanned PDFs")

    print("\nDone.")


if __name__ == "__main__":
    main()
