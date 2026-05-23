"""BERT fine-tuner for CV ↔ Job sequence-pair classification.

Fine-tunes a BERT-family model (default: ``camembert-base`` for French)
on (CV, Job) text pairs to predict the matching label.  Uses HuggingFace
``Trainer`` for ease of use and built-in eval metrics.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BertFineTuneConfig:
    model_name: str = "camembert-base"
    num_labels: int = 3
    max_length: int = 384
    batch_size: int = 16
    eval_batch_size: int = 32
    epochs: int = 3
    learning_rate: float = 2e-5
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1
    output_dir: str = "models/bert_matching"
    label_mapping: Dict[str, int] = field(
        default_factory=lambda: {"incompatible": 0, "partial": 1, "compatible": 2}
    )


class BertMatchingFineTuner:
    """Fine-tune a BERT model for matching classification."""

    def __init__(self, config: Optional[BertFineTuneConfig] = None) -> None:
        self.config = config or BertFineTuneConfig()
        self._tokenizer = None
        self._model = None
        self._trainer = None

    # ------------------------------------------------------------------ #
    # Data prep
    # ------------------------------------------------------------------ #
    def _prepare_dataset(self, examples: List[Dict[str, Any]]):
        from datasets import Dataset  # type: ignore

        label_map = self.config.label_mapping

        def to_record(ex):
            return {
                "cv": ex["cv_text"],
                "job": ex["job_text"],
                "label": label_map.get(ex.get("label", "partial"), 1),
            }

        return Dataset.from_list([to_record(e) for e in examples])

    def _tokenize(self, ds):
        def _tok(batch):
            return self._tokenizer(
                batch["cv"],
                batch["job"],
                truncation=True,
                max_length=self.config.max_length,
                padding=False,
            )

        return ds.map(_tok, batched=True, remove_columns=["cv", "job"])

    # ------------------------------------------------------------------ #
    # Training
    # ------------------------------------------------------------------ #
    def train(
        self,
        train_examples: List[Dict[str, Any]],
        val_examples: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        import numpy as np
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            DataCollatorWithPadding,
            Trainer,
            TrainingArguments,
        )

        self._tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
        self._model = AutoModelForSequenceClassification.from_pretrained(
            self.config.model_name,
            num_labels=self.config.num_labels,
            id2label={v: k for k, v in self.config.label_mapping.items()},
            label2id=self.config.label_mapping,
        )

        train_ds = self._tokenize(self._prepare_dataset(train_examples))
        val_ds = (
            self._tokenize(self._prepare_dataset(val_examples)) if val_examples else None
        )

        def compute_metrics(eval_pred):
            from sklearn.metrics import accuracy_score, f1_score

            preds, labels = eval_pred
            preds = np.argmax(preds, axis=1)
            return {
                "accuracy": accuracy_score(labels, preds),
                "f1": f1_score(labels, preds, average="weighted"),
            }

        args = TrainingArguments(
            output_dir=self.config.output_dir,
            num_train_epochs=self.config.epochs,
            per_device_train_batch_size=self.config.batch_size,
            per_device_eval_batch_size=self.config.eval_batch_size,
            learning_rate=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
            warmup_ratio=self.config.warmup_ratio,
            eval_strategy="epoch" if val_ds else "no",
            save_strategy="epoch",
            load_best_model_at_end=val_ds is not None,
            metric_for_best_model="f1" if val_ds else None,
            logging_steps=50,
            report_to=[],
            fp16=False,
        )

        self._trainer = Trainer(
            model=self._model,
            args=args,
            train_dataset=train_ds,
            eval_dataset=val_ds,
            tokenizer=self._tokenizer,
            data_collator=DataCollatorWithPadding(self._tokenizer),
            compute_metrics=compute_metrics if val_ds else None,
        )

        logger.info("Starting BERT fine-tuning…")
        train_result = self._trainer.train()
        self._trainer.save_model(self.config.output_dir)
        self._tokenizer.save_pretrained(self.config.output_dir)

        metrics = dict(train_result.metrics or {})
        if val_ds is not None:
            metrics.update(self._trainer.evaluate())
        return metrics

    def predict(self, cv_text: str, job_text: str) -> Dict[str, Any]:
        if self._model is None or self._tokenizer is None:
            raise RuntimeError("Model not loaded. Call train() or load() first.")

        import torch

        enc = self._tokenizer(
            cv_text,
            job_text,
            truncation=True,
            max_length=self.config.max_length,
            return_tensors="pt",
        ).to(self._model.device)
        with torch.no_grad():
            logits = self._model(**enc).logits
        probs = logits.softmax(dim=-1).cpu().numpy()[0]
        idx = int(probs.argmax())
        inv_map = {v: k for k, v in self.config.label_mapping.items()}
        return {
            "label": inv_map[idx],
            "score": float(probs[idx]),
            "probabilities": {inv_map[i]: float(p) for i, p in enumerate(probs)},
        }

    @classmethod
    def load(cls, path: str | Path) -> "BertMatchingFineTuner":
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        instance = cls()
        instance.config.output_dir = str(path)
        instance._tokenizer = AutoTokenizer.from_pretrained(path)
        instance._model = AutoModelForSequenceClassification.from_pretrained(path)
        return instance
