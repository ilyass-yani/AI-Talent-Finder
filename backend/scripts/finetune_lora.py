"""Finetune causal LLMs with LoRA, QLoRA, or DoRA.

Supported base families:
- Mistral
- Qwen
- Llama

Dataset formats supported:
- JSONL with prompt/completion
- JSONL with instruction/input/output
- JSONL with text (already formatted for causal LM)

This script is intentionally split into small helpers so it can be dry-run
validated without a GPU, while still providing a real training path when the
required libraries and hardware are available.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, List, Sequence


DEFAULT_TARGET_MODULES = {
    "mistral": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    "qwen": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    "llama": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
}


@dataclass
class FinetuneConfig:
    model: str
    data: str
    output_dir: str
    method: str
    max_length: int
    epochs: int
    batch_size: int
    learning_rate: float
    gradient_accumulation_steps: int
    warmup_ratio: float
    test_split: float
    seed: int
    dry_run: bool
    target_family: str
    target_modules: list[str]
    use_gradient_checkpointing: bool
    trust_remote_code: bool


class DependencyError(RuntimeError):
    pass


def _check_dependencies() -> list[str]:
    missing = []
    for pkg in ("transformers", "peft", "accelerate", "datasets"):
        try:
            __import__(pkg)
        except Exception:
            missing.append(pkg)
    return missing


def _optional_import(name: str):
    try:
        module = __import__(name)
        return module
    except Exception:
        return None


def _infer_family(model_name: str) -> str:
    lowered = model_name.lower()
    if "mistral" in lowered:
        return "mistral"
    if "qwen" in lowered:
        return "qwen"
    if "llama" in lowered:
        return "llama"
    return "llama"


def _build_target_modules(model_name: str, explicit: Sequence[str] | None = None) -> list[str]:
    if explicit:
        return [module.strip() for module in explicit if module.strip()]
    family = _infer_family(model_name)
    return list(DEFAULT_TARGET_MODULES.get(family, DEFAULT_TARGET_MODULES["llama"]))


def _read_jsonl(path: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except Exception as exc:
                raise ValueError(f"Invalid JSONL row: {line[:120]}") from exc
            if isinstance(payload, dict):
                records.append(payload)
    if not records:
        raise ValueError("The dataset is empty")
    return records


def _normalize_example(example: dict[str, Any]) -> str:
    if "text" in example and str(example["text"]).strip():
        return str(example["text"]).strip()

    if "prompt" in example and "completion" in example:
        prompt = str(example["prompt"]).strip()
        completion = str(example["completion"]).strip()
        return f"{prompt}\n{completion}".strip()

    if "instruction" in example and "output" in example:
        instruction = str(example["instruction"]).strip()
        input_text = str(example.get("input", "")).strip()
        output = str(example["output"]).strip()
        pieces = [f"### Instruction\n{instruction}"]
        if input_text:
            pieces.append(f"### Input\n{input_text}")
        pieces.append(f"### Response\n{output}")
        return "\n\n".join(pieces).strip()

    raise ValueError(
        "Unsupported dataset row. Expected one of: text, prompt/completion, instruction/output."
    )


def load_training_texts(path: str) -> list[str]:
    records = _read_jsonl(path)
    texts = [_normalize_example(record) for record in records]
    return [text for text in texts if text.strip()]


def _tokenize_texts(tokenizer, texts: Sequence[str], max_length: int):
    tokenized = tokenizer(
        list(texts),
        padding=False,
        truncation=True,
        max_length=max_length,
        return_attention_mask=True,
    )
    return tokenized


def _format_training_metadata(config: FinetuneConfig, dataset_size: int) -> dict[str, Any]:
    payload = asdict(config)
    payload["dataset_size"] = dataset_size
    return payload


def _resolve_dtype(dtype_name: str):
    dtype_name = dtype_name.lower().strip()
    if dtype_name in {"bf16", "bfloat16"}:
        return "bfloat16"
    if dtype_name in {"fp16", "float16"}:
        return "float16"
    return "auto"


def _build_peft_config(method: str, target_modules: Sequence[str], use_dora: bool):
    from peft import LoraConfig, TaskType

    method = method.lower().strip()
    if method not in {"lora", "qlora", "dora"}:
        raise ValueError("method must be one of: lora, qlora, dora")

    config_kwargs = {
        "r": 16,
        "lora_alpha": 32,
        "target_modules": list(target_modules),
        "lora_dropout": 0.05,
        "bias": "none",
        "task_type": TaskType.CAUSAL_LM,
    }
    if method == "dora" or use_dora:
        config_kwargs["use_dora"] = True
    return LoraConfig(**config_kwargs)


class CausalLMDataset:
    def __init__(self, encodings: dict[str, list[list[int]]]):
        self.encodings = encodings

    def __len__(self) -> int:
        return len(self.encodings["input_ids"])

    def __getitem__(self, idx: int) -> dict[str, list[int]]:
        item = {key: value[idx] for key, value in self.encodings.items()}
        item["labels"] = item["input_ids"].copy()
        return item


class DataCollatorForCausalLM:
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer

    def __call__(self, features: list[dict[str, Any]]) -> dict[str, Any]:
        import torch

        batch = self.tokenizer.pad(features, padding=True, return_tensors="pt")
        labels = batch["input_ids"].clone()
        labels[batch["attention_mask"] == 0] = -100
        batch["labels"] = labels
        return batch


def build_trainer(config: FinetuneConfig, training_texts: Sequence[str]):
    missing = _check_dependencies()
    if missing:
        raise DependencyError(
            "Missing dependencies for finetuning: " + ", ".join(missing) +
            ". Install: pip install -r backend/requirements-extras.txt"
        )

    transformers = __import__("transformers", fromlist=[
        "AutoModelForCausalLM", "AutoTokenizer", "Trainer", "TrainingArguments"
    ])
    peft_module = __import__("peft", fromlist=["get_peft_model", "prepare_model_for_kbit_training"])

    AutoModelForCausalLM = transformers.AutoModelForCausalLM
    AutoTokenizer = transformers.AutoTokenizer
    Trainer = transformers.Trainer
    TrainingArguments = transformers.TrainingArguments
    get_peft_model = peft_module.get_peft_model
    prepare_model_for_kbit_training = peft_module.prepare_model_for_kbit_training

    target_modules = config.target_modules
    dtype = _resolve_dtype(os.getenv("FINETUNE_DTYPE", "auto"))
    tokenizer = AutoTokenizer.from_pretrained(config.model, use_fast=True, trust_remote_code=config.trust_remote_code)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model_kwargs: dict[str, Any] = {"trust_remote_code": config.trust_remote_code}
    if config.method == "qlora":
        model_kwargs.update({"load_in_4bit": True})
    elif dtype != "auto":
        model_kwargs["torch_dtype"] = dtype

    model = AutoModelForCausalLM.from_pretrained(config.model, **model_kwargs)
    if config.use_gradient_checkpointing:
        model.gradient_checkpointing_enable()

    if config.method in {"qlora", "dora"}:
        model = prepare_model_for_kbit_training(model)

    # Auto-detect reasonable target modules when explicit ones are not present
    # or when the provided ones don't match the model's state dict keys.
    sd_keys = list(model.state_dict().keys())
    need_auto_detect = False
    if not target_modules:
        need_auto_detect = True
    else:
        # check if any provided target module appears in the model's keys
        found_any = False
        for m in target_modules:
            for k in sd_keys:
                if m in k:
                    found_any = True
                    break
            if found_any:
                break
        if not found_any:
            need_auto_detect = True

    if need_auto_detect:
        # Try to find common projection / attention module name patterns in the
        # model's state_dict keys. This makes the script robust to tiny test
        # models that do not follow Mistral/Qwen/Llama naming exactly.
        hits = []
        patterns = ['q_proj', 'k_proj', 'v_proj', 'o_proj', 'c_attn', 'attn', 'qkv', 'W_pack', 'Wq', 'Wk', 'Wv', 'gate_proj', 'up_proj', 'down_proj']
        for p in patterns:
            for k in sd_keys:
                if p in k:
                    hits.append(k.rsplit('.', 1)[0])
        # de-duplicate while preserving order
        seen = set()
        detected = []
        for h in hits:
            if h not in seen:
                seen.add(h)
                detected.append(h)
        if detected:
            target_modules = detected[:8]
        else:
            # Fallback: pick up to 8 named modules that are Linear layers
            try:
                import torch.nn as nn
                candidates = [name for name, mod in model.named_modules() if isinstance(mod, nn.Linear) and name]
                target_modules = candidates[:8]
            except Exception:
                target_modules = []

    peft_config = _build_peft_config(config.method, target_modules, config.method == "dora")
    model = get_peft_model(model, peft_config)

    tokenized = _tokenize_texts(tokenizer, training_texts, config.max_length)
    dataset = CausalLMDataset(tokenized)

    training_args = TrainingArguments(
        output_dir=config.output_dir,
        num_train_epochs=config.epochs,
        per_device_train_batch_size=config.batch_size,
        per_device_eval_batch_size=config.batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        learning_rate=config.learning_rate,
        warmup_ratio=config.warmup_ratio,
        logging_steps=10,
        save_strategy="epoch",
        evaluation_strategy="no",
        fp16=os.getenv("FINETUNE_FP16", "0") == "1",
        bf16=os.getenv("FINETUNE_BF16", "0") == "1",
        report_to=[],
        remove_unused_columns=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=DataCollatorForCausalLM(tokenizer),
    )
    return trainer, tokenizer, model


def run_finetuning(config: FinetuneConfig) -> dict[str, Any]:
    training_texts = load_training_texts(config.data)
    if len(training_texts) < 2:
        raise ValueError("Need at least 2 training rows for finetuning")

    os.makedirs(config.output_dir, exist_ok=True)
    metadata = _format_training_metadata(config, len(training_texts))
    metadata_path = Path(config.output_dir) / "finetune_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    if config.dry_run:
        return {"status": "dry_run", "metadata": metadata}

    trainer, tokenizer, model = build_trainer(config, training_texts)
    trainer.train()
    trainer.save_model(config.output_dir)
    tokenizer.save_pretrained(config.output_dir)

    if hasattr(model, "save_pretrained"):
        model.save_pretrained(config.output_dir)

    return {"status": "completed", "metadata": metadata, "output_dir": config.output_dir}


def parse_args(argv: Iterable[str] | None = None) -> FinetuneConfig:
    parser = argparse.ArgumentParser(description="Finetune Mistral/Qwen/Llama with LoRA, QLoRA, or DoRA")
    parser.add_argument("--model", required=True, help="HF model id or local path")
    parser.add_argument("--data", required=True, help="JSONL dataset path")
    parser.add_argument("--out", default="models/finetuned_adapter", help="Output directory for adapter weights")
    parser.add_argument("--method", choices=["lora", "qlora", "dora"], default="lora")
    parser.add_argument("--max-length", type=int, default=2048)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=4)
    parser.add_argument("--warmup-ratio", type=float, default=0.03)
    parser.add_argument("--test-split", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--target-family", choices=["mistral", "qwen", "llama", "auto"], default="auto")
    parser.add_argument("--target-modules", nargs="*", default=[])
    parser.add_argument("--use-gradient-checkpointing", action="store_true")
    parser.add_argument("--trust-remote-code", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Validate config and dataset without loading the base model")

    args = parser.parse_args(list(argv) if argv is not None else None)
    target_family = args.target_family if args.target_family != "auto" else _infer_family(args.model)
    target_modules = _build_target_modules(args.model, args.target_modules)

    return FinetuneConfig(
        model=args.model,
        data=args.data,
        output_dir=args.out,
        method=args.method,
        max_length=args.max_length,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        warmup_ratio=args.warmup_ratio,
        test_split=args.test_split,
        seed=args.seed,
        dry_run=args.dry_run,
        target_family=target_family,
        target_modules=target_modules,
        use_gradient_checkpointing=args.use_gradient_checkpointing,
        trust_remote_code=args.trust_remote_code,
    )


def main(argv: Iterable[str] | None = None) -> int:
    config = parse_args(argv)
    try:
        result = run_finetuning(config)
    except DependencyError as exc:
        print(str(exc))
        return 1
    except Exception as exc:
        print(f"Finetuning failed: {exc}")
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())