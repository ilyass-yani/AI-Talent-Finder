#!/usr/bin/env bash
set -euo pipefail

# Wrapper to regenerate IA artifacts (datasets, models, reports)
# Run from repo root: PYTHONPATH=. ./backend/scripts/regenerate_ia_artifacts.sh

echo "[regenerate] Starting IA artifact regeneration"

SCRIPTS=(
  "backend/scripts/prepare_training_data.py"
  "backend/scripts/build_final_matching_artifacts.py"
  "backend/scripts/benchmark_models.py"
)

for s in "${SCRIPTS[@]}"; do
  if [ -f "$s" ]; then
    echo "[regenerate] Running $s"
    PYTHONPATH=. python3 "$s"
  else
    echo "[regenerate] Skipping $s (not found)"
  fi
done

echo "[regenerate] Finished"
