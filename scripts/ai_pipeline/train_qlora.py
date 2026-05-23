#!/usr/bin/env python
"""QLoRA fine-tuning (4-bit NF4) for low-VRAM training.

Usage:
    python scripts/train_qlora.py \
        --data data/training_pairs.csv \
        --model Qwen/Qwen2.5-1.5B-Instruct \
        --output models/qlora_matching
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from ai_pipeline.config import LLMConfig
from ai_pipeline.llm.dataset_builder import MatchingDatasetBuilder
from ai_pipeline.llm.lora_trainer import QLoRATrainer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="QLoRA 4-bit fine-tuning")
    p.add_argument("--data", required=True)
    p.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    p.add_argument("--output", default="models/qlora_matching")
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--batch-size", type=int, default=2)
    p.add_argument("--grad-accum", type=int, default=8)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--lora-r", type=int, default=16)
    p.add_argument("--lora-alpha", type=int, default=32)
    p.add_argument("--max-length", type=int, default=2048)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    config = LLMConfig(
        base_model=args.model,
        max_length=args.max_length,
        lora_r=args.lora_r,
        lora_alpha=args.lora_alpha,
        num_epochs=args.epochs,
        per_device_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        output_dir=args.output,
        use_qlora=True,
    )

    builder = MatchingDatasetBuilder()
    examples = builder.from_csv(args.data)
    logger.info("Loaded %d examples", len(examples))

    logger.info("QLoRA 4-bit NF4 + bfloat16 compute + double quantization")
    trainer = QLoRATrainer(config=config)
    trainer.prepare_model()
    trainer.train(examples)
    trainer.save()
    logger.info("QLoRA adapter saved → %s", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
