#!/usr/bin/env python3
"""
Cross-platform wrapper to regenerate IA artifacts (datasets, models, reports).
Run from repo root:
  PYTHONPATH=. python backend/scripts/regenerate_ia_artifacts.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = [
    "backend/scripts/prepare_training_data.py",
    "backend/scripts/build_final_matching_artifacts.py",
    "backend/scripts/benchmark_models.py",
]


def _run(script_path: Path) -> None:
    env = os.environ.copy()
    current = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT) if not current else f"{str(ROOT)}{os.pathsep}{current}"
    subprocess.run([sys.executable, str(script_path)], cwd=str(ROOT), env=env, check=True)


def main() -> None:
    print("[regenerate] Starting IA artifact regeneration")
    for rel in SCRIPTS:
        script_path = ROOT / rel
        if script_path.exists():
            print(f"[regenerate] Running {rel}")
            _run(script_path)
        else:
            print(f"[regenerate] Skipping {rel} (not found)")
    print("[regenerate] Finished")


if __name__ == "__main__":
    main()
