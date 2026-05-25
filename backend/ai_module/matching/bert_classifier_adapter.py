"""BERT classifier adapter for camembert-based candidate/job compatibility scoring.

The underlying model (CamembertForSequenceClassification) outputs 3 classes:
  0 = incompatible, 1 = partial, 2 = compatible

The adapter converts softmax probabilities to a continuous [0, 1] score via
weighted class expectation:  score = 0.0*P(incompatible) + 0.5*P(partial) + 1.0*P(compatible)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch

    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers/torch not installed — BertClassifierAdapter will be disabled.")


class BertClassifierAdapter:
    """Thin wrapper around a fine-tuned CamembertForSequenceClassification model."""

    # Class-level weights: incompatible=0, partial=0.5, compatible=1.0
    _CLASS_WEIGHTS = np.array([0.0, 0.5, 1.0], dtype=np.float32)

    def __init__(self, model_dir: str | Path):
        if not TRANSFORMERS_AVAILABLE:
            raise RuntimeError(
                "transformers and torch are required. "
                "Install them with: pip install transformers torch"
            )
        model_dir = Path(model_dir)
        if not model_dir.exists():
            raise FileNotFoundError(f"Model directory not found: {model_dir}")

        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        self._model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
        self._model.to(self._device)
        self._model.eval()
        self._max_length = 384
        logger.info("BertClassifierAdapter loaded from %s on %s", model_dir, self._device)

    @classmethod
    def load(cls, model_dir: str | Path) -> "BertClassifierAdapter":
        return cls(model_dir)

    def predict_score(self, candidate_text: str, job_text: str) -> float:
        """Return a compatibility score in [0, 1].

        Combines candidate and job text as a text-pair sequence and returns
        the soft-label expectation over (incompatible=0, partial=0.5, compatible=1.0).
        """
        if not TRANSFORMERS_AVAILABLE:
            return 0.0

        try:
            inputs = self._tokenizer(
                candidate_text,
                job_text,
                return_tensors="pt",
                truncation=True,
                max_length=self._max_length,
                padding=True,
            )
            inputs = {k: v.to(self._device) for k, v in inputs.items()}

            with torch.no_grad():
                logits = self._model(**inputs).logits

            probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]
            score = float(np.dot(probs, self._CLASS_WEIGHTS))
            return float(np.clip(score, 0.0, 1.0))

        except Exception as exc:
            logger.warning("BertClassifierAdapter.predict_score failed: %s", exc)
            return 0.0

    def predict_label(self, candidate_text: str, job_text: str) -> str:
        """Return the top predicted label: 'incompatible', 'partial', or 'compatible'."""
        if not TRANSFORMERS_AVAILABLE:
            return "incompatible"
        try:
            inputs = self._tokenizer(
                candidate_text,
                job_text,
                return_tensors="pt",
                truncation=True,
                max_length=self._max_length,
                padding=True,
            )
            inputs = {k: v.to(self._device) for k, v in inputs.items()}
            with torch.no_grad():
                logits = self._model(**inputs).logits
            label_id = int(torch.argmax(logits, dim=-1).item())
            id2label = {0: "incompatible", 1: "partial", 2: "compatible"}
            return id2label[label_id]
        except Exception as exc:
            logger.warning("BertClassifierAdapter.predict_label failed: %s", exc)
            return "incompatible"

    @property
    def available(self) -> bool:
        return TRANSFORMERS_AVAILABLE


_default_adapter: Optional[BertClassifierAdapter] = None


def get_default_adapter(model_dir: Optional[str | Path] = None) -> Optional[BertClassifierAdapter]:
    """Lazy-load a shared adapter instance. Returns None if unavailable."""
    global _default_adapter
    if _default_adapter is not None:
        return _default_adapter

    if model_dir is None:
        # Resolve relative to this file: backend/ai_module/matching/ -> backend/models/bert_matching/
        model_dir = Path(__file__).parent.parent.parent / "models" / "bert_matching"

    try:
        _default_adapter = BertClassifierAdapter.load(model_dir)
    except Exception as exc:
        logger.warning("Could not load default BertClassifierAdapter: %s", exc)
        return None

    return _default_adapter
