#!/usr/bin/env python3
"""Fine-tune a recruiter-domain NER model from annotated CV data.

Expected input formats:
- JSONL with tokens + ner_tags
- JSON with records containing `tokens` and `ner_tags`

This script is intentionally defensive: if `transformers` is unavailable,
it still validates and exports a prepared dataset snapshot for later training.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

try:
    from datasets import Dataset  # type: ignore
    from transformers import AutoModelForTokenClassification, AutoTokenizer, Trainer, TrainingArguments  # type: ignore

    TRANSFORMERS_AVAILABLE = True
except Exception:
    Dataset = None
    AutoModelForTokenClassification = None
    AutoTokenizer = None
    Trainer = None
    TrainingArguments = None
    TRANSFORMERS_AVAILABLE = False

LABEL_NAMES = ["O", "B-PER", "I-PER", "B-ORG", "I-ORG", "B-SKILL", "I-SKILL", "B-EDU", "I-EDU"]
DEFAULT_MODEL = "dslim/bert-base-NER"


def load_annotations(path: Path) -> List[Dict[str, Any]]:
    """Load token/label annotations from JSON or JSONL."""
    if not path.exists():
        raise FileNotFoundError(f"Annotation file not found: {path}")

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    if path.suffix.lower() == ".jsonl":
        records = []
        for line in text.splitlines():
            if line.strip():
                records.append(json.loads(line))
        return records

    payload = json.loads(text)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    raise ValueError("Unsupported annotation format")


def validate_records(records: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep only records with aligned tokens/labels."""
    valid_records: List[Dict[str, Any]] = []
    for record in records:
        tokens = record.get("tokens")
        ner_tags = record.get("ner_tags")
        if not isinstance(tokens, list) or not isinstance(ner_tags, list):
            continue
        if len(tokens) != len(ner_tags) or not tokens:
            continue
        valid_records.append({"tokens": [str(token) for token in tokens], "ner_tags": [str(tag) for tag in ner_tags]})
    return valid_records


def build_label_map(records: Sequence[Dict[str, Any]]) -> Tuple[Dict[str, int], Dict[int, str]]:
    labels = {"O"}
    for record in records:
        labels.update(str(tag) for tag in record.get("ner_tags", []))
    ordered_labels = ["O"] + sorted(label for label in labels if label != "O")
    label2id = {label: index for index, label in enumerate(ordered_labels)}
    id2label = {index: label for label, index in label2id.items()}
    return label2id, id2label


def tokenize_and_align_labels(examples: Dict[str, List[Any]], tokenizer, label2id: Dict[str, int]) -> Dict[str, Any]:
    tokenized_inputs = tokenizer(
        examples["tokens"],
        is_split_into_words=True,
        truncation=True,
        padding=False,
    )

    aligned_labels = []
    for batch_index, labels in enumerate(examples["ner_tags"]):
        word_ids = tokenized_inputs.word_ids(batch_index=batch_index)
        previous_word_id = None
        label_ids: List[int] = []
        for word_id in word_ids:
            if word_id is None:
                label_ids.append(-100)
            elif word_id != previous_word_id:
                label_ids.append(label2id.get(labels[word_id], label2id["O"]))
            else:
                label = labels[word_id]
                if label.startswith("B-"):
                    label = "I-" + label[2:]
                label_ids.append(label2id.get(label, label2id["O"]))
            previous_word_id = word_id
        aligned_labels.append(label_ids)

    tokenized_inputs["labels"] = aligned_labels
    return tokenized_inputs


def export_prepared_dataset(records: Sequence[Dict[str, Any]], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    export_path = output_dir / "recruiter_ner_prepared_dataset.json"
    export_path.write_text(json.dumps(list(records), indent=2, ensure_ascii=False), encoding="utf-8")
    return export_path


def train_model(records: Sequence[Dict[str, Any]], model_name: str, output_dir: Path, epochs: int) -> Path:
    if not TRANSFORMERS_AVAILABLE:
        raise RuntimeError("transformers/datasets are not available in this environment")

    label2id, id2label = build_label_map(records)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForTokenClassification.from_pretrained(
        model_name,
        num_labels=len(label2id),
        label2id=label2id,
        id2label=id2label,
    )

    dataset = Dataset.from_list(list(records))
    tokenized_dataset = dataset.map(lambda batch: tokenize_and_align_labels(batch, tokenizer, label2id), batched=True)

    output_dir.mkdir(parents=True, exist_ok=True)
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        learning_rate=2e-5,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        num_train_epochs=epochs,
        weight_decay=0.01,
        logging_steps=10,
        save_strategy="epoch",
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        tokenizer=tokenizer,
    )
    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Fine-tune recruiter NER model")
    parser.add_argument("--annotations", required=True, help="Path to JSON/JSONL annotation file")
    parser.add_argument("--output-dir", default="models/recruiter_ner", help="Training output directory")
    parser.add_argument("--model-name", default=DEFAULT_MODEL, help="Base HF model to fine-tune")
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs")
    parser.add_argument("--export-only", action="store_true", help="Prepare dataset without training")
    args = parser.parse_args()

    annotation_path = Path(args.annotations).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    records = validate_records(load_annotations(annotation_path))
    if not records:
        raise SystemExit("No valid annotation records found")

    export_path = export_prepared_dataset(records, output_dir)
    print(f"Prepared dataset exported to {export_path}")

    if args.export_only or not TRANSFORMERS_AVAILABLE:
        print("Training skipped: exporting only or transformers unavailable")
        return 0

    trained_dir = train_model(records, args.model_name, output_dir, args.epochs)
    print(f"Model trained and saved to {trained_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
