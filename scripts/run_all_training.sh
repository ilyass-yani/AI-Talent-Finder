#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONDA="$HOME/miniconda3/bin/conda"
ENV=faiss-py310
export PYTHONPATH="$REPO_ROOT/backend"
export KMP_DUPLICATE_LIB_OK=TRUE

echo "Running classical training..."
$CONDA run -n $ENV bash -lc "cd $REPO_ROOT/backend && python scripts/train_classical_models.py --data $REPO_ROOT/data/training_pairs.csv --out $REPO_ROOT/models/classical_real"

echo "Running siamese training..."
$CONDA run -n $ENV bash -lc "cd $REPO_ROOT/backend && python scripts/train_siamese.py --data $REPO_ROOT/data/training_pairs.csv --out $REPO_ROOT/models/siamese_real"

echo "Running finetune (LoRA) preparatory step on tiny model..."
$CONDA run -n $ENV bash -lc "cd $REPO_ROOT && python backend/scripts/finetune_lora.py --model sshleifer/tiny-random-gpt2 --data data/finetune_sample.jsonl --out models/finetuned_test"

echo "All training steps completed."
