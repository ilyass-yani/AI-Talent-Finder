#!/usr/bin/env bash
# Helper to launch LoRA/QLoRA finetuning with `accelerate`.
# Usage: ./backend/scripts/run_finetune_gpu.sh --model <HF_MODEL> --data <DATA.jsonl> --out <OUT_DIR> [--method qlora|lora] [--epochs N]

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="${script_dir}/.."

MODEL="mistralai/Mistral-7B-Instruct-v0.1"
DATA="data/finetune_sample.jsonl"
OUT="models/finetune_gpu"
METHOD="qlora"
EPOCHS=3
BATCH=4

while [[ $# -gt 0 ]]; do
  case $1 in
    --model) MODEL="$2"; shift 2;;
    --data) DATA="$2"; shift 2;;
    --out) OUT="$2"; shift 2;;
    --method) METHOD="$2"; shift 2;;
    --epochs) EPOCHS="$2"; shift 2;;
    --batch) BATCH="$2"; shift 2;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

echo "Running finetune: model=${MODEL}, data=${DATA}, out=${OUT}, method=${METHOD}, epochs=${EPOCHS}, batch=${BATCH}"

# Example accelerate launch
# Ensure you have run `accelerate config` or placed a YAML at ~/.cache/huggingface/accelerate/default_config.yaml
accelerate launch backend/scripts/finetune_lora.py --model "${MODEL}" --data "${DATA}" --out "${OUT}" --method "${METHOD}" --epochs ${EPOCHS} --batch-size ${BATCH} --trust-remote-code --dry-run

echo "Dry-run completed. Remove --dry-run to perform actual fine-tuning."
