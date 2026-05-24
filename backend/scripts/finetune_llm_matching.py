#!/usr/bin/env python3
"""
LLM Fine-tuning for CV-Job Matching
Fine-tunes Mistral / Qwen / LLaMA with LoRA, QLoRA, or DoRA
on the task of scoring CV compatibility with a job description.

The model is trained as an instruction-following LLM:
  INSTRUCTION: Given the CV below and the job description below,
               rate the compatibility from 0 to 100 and explain.
  INPUT: <cv_text> + <job_description>
  OUTPUT: Score: <0-100>. Reason: <explanation>

Supported base models (change via --model):
  - mistralai/Mistral-7B-Instruct-v0.3
  - Qwen/Qwen2-7B-Instruct
  - meta-llama/Meta-Llama-3-8B-Instruct

PEFT techniques (change via --peft):
  - lora   : LoRA (rank decomposition)
  - qlora  : QLoRA (LoRA + 4-bit quantization, memory efficient)
  - dora   : DoRA (Weight-Decomposed Low-Rank Adaptation)

Usage:
  # Synthetic data, QLoRA on Mistral
  python backend/scripts/finetune_llm_matching.py \\
      --model mistralai/Mistral-7B-Instruct-v0.3 \\
      --peft qlora \\
      --synthetic 500 \\
      --out models/llm_matching_mistral \\
      --epochs 3

  # From labeled JSONL
  python backend/scripts/finetune_llm_matching.py \\
      --model Qwen/Qwen2-7B-Instruct \\
      --peft lora \\
      --data data/matching_pairs.jsonl \\
      --out models/llm_matching_qwen

Requirements:
  pip install transformers peft trl bitsandbytes accelerate datasets
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional heavy imports (skip gracefully if dependencies are missing)
# ---------------------------------------------------------------------------
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    log.warning("PyTorch not available")

try:
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        TrainingArguments,
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    log.warning("transformers not available")

try:
    from peft import (
        LoraConfig,
        TaskType,
        get_peft_model,
        prepare_model_for_kbit_training,
    )
    PEFT_AVAILABLE = True
except ImportError:
    PEFT_AVAILABLE = False
    log.warning("peft not available")

try:
    from trl import SFTConfig, SFTTrainer
    TRL_AVAILABLE = True
except ImportError:
    TRL_AVAILABLE = False
    log.warning("trl not available")

try:
    from datasets import Dataset
    DATASETS_AVAILABLE = True
except ImportError:
    DATASETS_AVAILABLE = False
    log.warning("datasets not available")


# ---------------------------------------------------------------------------
# Prompt templates per model family
# ---------------------------------------------------------------------------

PROMPT_TEMPLATES = {
    "mistral": (
        "<s>[INST] {instruction}\n\n### CV:\n{cv}\n\n### Job Description:\n{job} [/INST] {response}</s>"
    ),
    "qwen": (
        "<|im_start|>system\nYou are an expert recruiter assistant.<|im_end|>\n"
        "<|im_start|>user\n{instruction}\n\n### CV:\n{cv}\n\n### Job Description:\n{job}<|im_end|>\n"
        "<|im_start|>assistant\n{response}<|im_end|>"
    ),
    "llama": (
        "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
        "You are an expert recruiter assistant.<|eot_id|>"
        "<|start_header_id|>user<|end_header_id|>\n"
        "{instruction}\n\n### CV:\n{cv}\n\n### Job Description:\n{job}<|eot_id|>"
        "<|start_header_id|>assistant<|end_header_id|>\n{response}<|eot_id|>"
    ),
    "default": (
        "### Instruction:\n{instruction}\n\n### CV:\n{cv}\n\n### Job Description:\n{job}\n\n### Response:\n{response}"
    ),
}

INSTRUCTION = (
    "Evaluate the compatibility between the candidate CV and the job description. "
    "Provide a compatibility score from 0 (no match) to 100 (perfect match) and a brief explanation. "
    "Format: Score: <number>. Reason: <explanation>"
)


def _detect_model_family(model_name: str) -> str:
    name_lower = model_name.lower()
    if "mistral" in name_lower:
        return "mistral"
    if "qwen" in name_lower:
        return "qwen"
    if "llama" in name_lower or "meta-llama" in name_lower:
        return "llama"
    return "default"


def format_prompt(cv: str, job: str, score: int, reason: str, model_family: str = "default") -> str:
    template = PROMPT_TEMPLATES.get(model_family, PROMPT_TEMPLATES["default"])
    response = f"Score: {score}. Reason: {reason}"
    return template.format(
        instruction=INSTRUCTION,
        cv=cv[:2000],    # truncate to keep within context window
        job=job[:1500],
        response=response,
    )


# ---------------------------------------------------------------------------
# Synthetic data (mirrors train_ml_matching.py but with richer outputs)
# ---------------------------------------------------------------------------

_CV_TEMPLATES = [
    "Software engineer with {exp} years of experience in {skills}. Worked at {company}. "
    "Degree in Computer Science.",
    "Data scientist with {exp} years, specializing in {skills}. MSc in AI.",
    "Full-stack developer ({exp} years), expert in {skills}. Led teams of 5+.",
    "DevOps engineer with {exp} years managing {skills} environments.",
    "ML engineer with {exp} years, deep expertise in {skills}.",
    "Backend engineer with {exp} years, building high-performance systems with {skills}.",
]

_JOB_TEMPLATES = [
    "We seek a developer with {exp_req}+ years in {skills}. {level} role in our {team} team.",
    "Data scientist needed — {exp_req}+ years of {skills} experience required.",
    "Full-stack engineer position. Required: {skills}. {exp_req}+ years.",
    "Cloud/DevOps role. Expertise in {skills} essential. {exp_req} years.",
    "ML engineer — deep knowledge of {skills}. {exp_req}+ years.",
    "Senior backend engineer. Stack: {skills}. {exp_req}+ years at scale.",
]

_SKILL_POOLS = {
    "python": ["Python", "FastAPI", "Django", "Pandas", "NumPy"],
    "data": ["Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "Spark"],
    "frontend": ["React", "TypeScript", "JavaScript", "Vue.js", "CSS"],
    "devops": ["Docker", "Kubernetes", "AWS", "Terraform", "CI/CD"],
    "java": ["Java", "Spring Boot", "Microservices", "Maven"],
}

_COMPANIES = ["Accenture", "Capgemini", "Thales", "Orange", "SNCF"]
_LEVELS = ["Junior", "Mid-level", "Senior", "Lead"]
_TEAMS = ["data", "platform", "product", "core backend"]


def _random_skills(pool_key: Optional[str] = None, n: int = 3) -> str:
    if pool_key and pool_key in _SKILL_POOLS:
        pool = _SKILL_POOLS[pool_key]
    else:
        pool_key = random.choice(list(_SKILL_POOLS.keys()))
        pool = _SKILL_POOLS[pool_key]
    return ", ".join(random.sample(pool, min(n, len(pool))))


def generate_synthetic_dataset(n: int = 300) -> List[Dict]:
    """Generate synthetic (cv, job, score, reason) records."""
    records = []
    pool_keys = list(_SKILL_POOLS.keys())

    for _ in range(n):
        match_type = random.choices(["full_match", "partial", "no_match"], weights=[0.4, 0.3, 0.3])[0]
        exp = random.randint(1, 12)

        if match_type == "full_match":
            key = random.choice(pool_keys)
            skills_cv = _random_skills(key, n=4)
            skills_job = _random_skills(key, n=3)
            exp_req = max(1, exp - random.randint(0, 2))
            score = random.randint(75, 100)
            reason = (
                f"The candidate's skills in {skills_cv} match the job requirements for {skills_job}. "
                f"Experience ({exp} years) meets the {exp_req}+ year requirement."
            )
        elif match_type == "partial":
            key_a = random.choice(pool_keys)
            key_b = random.choice([k for k in pool_keys if k != key_a])
            skills_cv = _random_skills(key_a, n=3) + ", " + _random_skills(key_b, n=1)
            skills_job = _random_skills(key_a, n=2) + ", " + _random_skills(key_b, n=2)
            exp_req = random.randint(1, 8)
            score = random.randint(40, 74)
            reason = (
                f"Partial skill overlap between candidate and job. "
                f"Candidate covers {skills_cv} but is missing some required {skills_job} skills."
            )
        else:
            key_a, key_b = random.sample(pool_keys, 2)
            skills_cv = _random_skills(key_a, n=4)
            skills_job = _random_skills(key_b, n=3)
            exp_req = random.randint(3, 10)
            score = random.randint(0, 39)
            reason = (
                f"Significant skill mismatch. Candidate specializes in {skills_cv} "
                f"while job requires {skills_job}."
            )

        cv = random.choice(_CV_TEMPLATES).format(
            exp=exp, skills=skills_cv, company=random.choice(_COMPANIES)
        )
        job = random.choice(_JOB_TEMPLATES).format(
            exp_req=exp_req,
            skills=skills_job,
            level=random.choice(_LEVELS),
            team=random.choice(_TEAMS),
        )

        records.append({"cv_text": cv, "job_text": job, "score": score, "reason": reason})

    random.shuffle(records)
    return records


def load_jsonl_dataset(path: Path) -> List[Dict]:
    records = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if "cv_text" in rec and "job_text" in rec and "score" in rec:
                    records.append(rec)
            except json.JSONDecodeError:
                continue
    return records


# ---------------------------------------------------------------------------
# LoRA / QLoRA / DoRA configuration
# ---------------------------------------------------------------------------

def get_peft_config(peft_type: str, model_name: str) -> "LoraConfig":
    name_lower = model_name.lower()

    # Target modules per architecture
    if "mistral" in name_lower or "llama" in name_lower:
        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    elif "qwen" in name_lower:
        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    else:
        target_modules = ["query_key_value", "dense", "dense_h_to_4h", "dense_4h_to_h"]

    use_dora = peft_type == "dora"

    config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,                   # LoRA rank
        lora_alpha=32,          # scaling factor
        lora_dropout=0.05,
        target_modules=target_modules,
        bias="none",
        use_dora=use_dora,      # DoRA: weight-decomposed adaptation
    )
    return config


def get_bnb_config() -> "BitsAndBytesConfig":
    """4-bit quantization config for QLoRA."""
    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16 if TORCH_AVAILABLE else None,
    )


# ---------------------------------------------------------------------------
# Main training routine
# ---------------------------------------------------------------------------

def finetune(
    model_name: str,
    peft_type: str,
    records: List[Dict],
    out_dir: Path,
    epochs: int = 3,
    batch_size: int = 4,
    grad_accum: int = 4,
    lr: float = 2e-4,
    max_seq_len: int = 1024,
    val_split: float = 0.1,
) -> None:
    if not all([TORCH_AVAILABLE, TRANSFORMERS_AVAILABLE, PEFT_AVAILABLE, TRL_AVAILABLE, DATASETS_AVAILABLE]):
        missing = []
        if not TORCH_AVAILABLE:
            missing.append("torch")
        if not TRANSFORMERS_AVAILABLE:
            missing.append("transformers")
        if not PEFT_AVAILABLE:
            missing.append("peft")
        if not TRL_AVAILABLE:
            missing.append("trl")
        if not DATASETS_AVAILABLE:
            missing.append("datasets")
        raise RuntimeError(f"Missing dependencies: {', '.join(missing)}. Run: pip install {' '.join(missing)}")

    model_family = _detect_model_family(model_name)
    log.info("Model family: %s | PEFT: %s | Records: %d", model_family, peft_type, len(records))

    # Split train / val
    random.shuffle(records)
    n_val = max(1, int(len(records) * val_split))
    val_records = records[:n_val]
    train_records = records[n_val:]

    # Format prompts
    def to_text(rec: Dict) -> str:
        return format_prompt(
            cv=rec["cv_text"],
            job=rec["job_text"],
            score=int(rec.get("score", 50)),
            reason=rec.get("reason", ""),
            model_family=model_family,
        )

    train_dataset = Dataset.from_dict({"text": [to_text(r) for r in train_records]})
    val_dataset = Dataset.from_dict({"text": [to_text(r) for r in val_records]})

    log.info("Train: %d | Val: %d", len(train_dataset), len(val_dataset))

    # Load tokenizer
    log.info("Loading tokenizer from %s…", model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # Load model
    log.info("Loading model (%s)…", peft_type)
    use_4bit = peft_type == "qlora"

    model_kwargs: Dict = {
        "trust_remote_code": True,
        "device_map": "auto" if TORCH_AVAILABLE and torch.cuda.is_available() else "cpu",
    }

    if use_4bit:
        model_kwargs["quantization_config"] = get_bnb_config()
        model_kwargs["torch_dtype"] = torch.bfloat16 if TORCH_AVAILABLE else None
    else:
        if TORCH_AVAILABLE and torch.cuda.is_available():
            model_kwargs["torch_dtype"] = torch.bfloat16

    model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)

    if use_4bit:
        model = prepare_model_for_kbit_training(model)

    # Apply PEFT
    peft_config = get_peft_config(peft_type, model_name)
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    # Training arguments
    out_dir.mkdir(parents=True, exist_ok=True)
    training_args = SFTConfig(
        output_dir=str(out_dir),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
        learning_rate=lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,
        weight_decay=0.01,
        fp16=TORCH_AVAILABLE and torch.cuda.is_available() and not use_4bit,
        bf16=TORCH_AVAILABLE and torch.cuda.is_available() and use_4bit,
        logging_steps=10,
        save_strategy="epoch",
        eval_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        max_seq_length=max_seq_len,
        dataset_text_field="text",
        report_to="none",
        dataloader_pin_memory=False,
    )

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        processing_class=tokenizer,
        peft_config=peft_config,
    )

    log.info("Starting training…")
    trainer.train()
    log.info("Training complete.")

    # Save adapter
    adapter_path = out_dir / "adapter"
    model.save_pretrained(str(adapter_path))
    tokenizer.save_pretrained(str(adapter_path))
    log.info("Adapter saved → %s", adapter_path)

    # Save metadata
    meta = {
        "base_model": model_name,
        "peft_type": peft_type,
        "model_family": model_family,
        "epochs": epochs,
        "n_train": len(train_dataset),
        "n_val": len(val_dataset),
        "adapter_path": str(adapter_path),
    }
    (out_dir / "finetune_meta.json").write_text(json.dumps(meta, indent=2))
    log.info("Metadata saved → %s/finetune_meta.json", out_dir)


# ---------------------------------------------------------------------------
# Inference helper (merge adapter + generate)
# ---------------------------------------------------------------------------

def predict_compatibility(
    cv_text: str,
    job_text: str,
    adapter_path: str,
    max_new_tokens: int = 150,
) -> Dict:
    """
    Load fine-tuned adapter and generate a compatibility score + reason.

    Returns dict: {score, reason, raw_output}
    """
    import re

    meta_path = Path(adapter_path).parent / "finetune_meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    base_model = meta.get("base_model", "")
    model_family = meta.get("model_family", "default")

    from peft import AutoPeftModelForCausalLM

    tokenizer = AutoTokenizer.from_pretrained(adapter_path, trust_remote_code=True)
    model = AutoPeftModelForCausalLM.from_pretrained(
        adapter_path,
        device_map="auto",
        torch_dtype=torch.bfloat16 if TORCH_AVAILABLE and torch.cuda.is_available() else torch.float32,
        trust_remote_code=True,
    )
    model.eval()

    # Build inference prompt (no response part)
    template = PROMPT_TEMPLATES.get(model_family, PROMPT_TEMPLATES["default"])
    prompt = template.split("{response}")[0].format(
        instruction=INSTRUCTION,
        cv=cv_text[:2000],
        job=job_text[:1500],
        response="",
    )

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=1.0,
            pad_token_id=tokenizer.eos_token_id,
        )

    raw_output = tokenizer.decode(output_ids[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

    # Parse Score: <number>. Reason: <text>
    score_match = re.search(r"Score\s*:\s*(\d{1,3})", raw_output, re.IGNORECASE)
    reason_match = re.search(r"Reason\s*:\s*(.+)", raw_output, re.IGNORECASE | re.DOTALL)

    score = int(score_match.group(1)) if score_match else -1
    reason = reason_match.group(1).strip() if reason_match else raw_output.strip()

    return {"score": score, "reason": reason, "raw_output": raw_output}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description="Fine-tune LLM (Mistral/Qwen/LLaMA) for CV-Job matching")
    parser.add_argument(
        "--model",
        default="mistralai/Mistral-7B-Instruct-v0.3",
        help="HuggingFace model ID",
    )
    parser.add_argument(
        "--peft",
        choices=["lora", "qlora", "dora"],
        default="qlora",
        help="PEFT technique",
    )

    data_group = parser.add_mutually_exclusive_group(required=True)
    data_group.add_argument("--synthetic", type=int, metavar="N", help="Use N synthetic pairs")
    data_group.add_argument("--data", type=str, metavar="JSONL", help="JSONL with {cv_text, job_text, score, reason}")

    parser.add_argument("--out", default="models/llm_matching", help="Output directory")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--grad-accum", type=int, default=4)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--max-seq-len", type=int, default=1024)
    parser.add_argument("--val-split", type=float, default=0.1)

    # Inference mode
    parser.add_argument("--infer", action="store_true", help="Run inference instead of training")
    parser.add_argument("--adapter", type=str, help="Path to saved adapter (for --infer)")
    parser.add_argument("--cv", type=str, help="CV text for inference")
    parser.add_argument("--job", type=str, help="Job description text for inference")

    args = parser.parse_args(argv)

    if args.infer:
        if not args.adapter or not args.cv or not args.job:
            parser.error("--infer requires --adapter, --cv, and --job")
        result = predict_compatibility(args.cv, args.job, args.adapter)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    out_dir = Path(args.out)

    if args.synthetic:
        log.info("Generating %d synthetic training records…", args.synthetic)
        records = generate_synthetic_dataset(n=args.synthetic)
    else:
        data_path = Path(args.data)
        log.info("Loading records from %s…", data_path)
        records = load_jsonl_dataset(data_path)

    if not records:
        log.error("No records loaded — aborting")
        return 1

    log.info("Total records: %d", len(records))

    finetune(
        model_name=args.model,
        peft_type=args.peft,
        records=records,
        out_dir=out_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        grad_accum=args.grad_accum,
        lr=args.lr,
        max_seq_len=args.max_seq_len,
        val_split=args.val_split,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
