"""SHAP explainer for the ML matching model.

Wraps SHAP TreeExplainer / KernelExplainer around a trained scikit-learn or
XGBoost matching model.  Returns per-feature contributions in a format
suitable for charting in the frontend.

SHAP is imported lazily so the package stays importable without it.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ShapExplanation:
    feature_names: List[str]
    shap_values: List[float]
    base_value: float
    prediction: float
    top_positive: List[Dict[str, Any]] = field(default_factory=list)
    top_negative: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_names": self.feature_names,
            "shap_values": self.shap_values,
            "base_value": self.base_value,
            "prediction": self.prediction,
            "top_positive": self.top_positive,
            "top_negative": self.top_negative,
        }


class ShapExplainer:
    """SHAP wrapper for a fitted matching model."""

    def __init__(
        self,
        model: Any,
        feature_names: List[str],
        background_data: Optional[np.ndarray] = None,
    ) -> None:
        self.model = model
        self.feature_names = feature_names
        self.background_data = background_data
        self._explainer = None

    def _load_explainer(self) -> None:
        if self._explainer is not None:
            return
        import shap  # type: ignore

        model_class = type(self.model).__name__.lower()
        if any(
            name in model_class
            for name in ("randomforest", "xgb", "gradientboosting", "lgbm", "catboost", "tree")
        ):
            self._explainer = shap.TreeExplainer(self.model)
        elif self.background_data is not None:
            self._explainer = shap.KernelExplainer(
                self.model.predict_proba if hasattr(self.model, "predict_proba") else self.model.predict,
                self.background_data,
            )
        else:
            # Linear model fast path
            self._explainer = shap.LinearExplainer(self.model, np.zeros((1, len(self.feature_names))))

    def explain(self, x: np.ndarray, top_k: int = 5) -> ShapExplanation:
        """Explain a single instance ``x`` of shape ``(n_features,)``."""
        self._load_explainer()
        x = np.asarray(x).reshape(1, -1)
        shap_vals = self._explainer.shap_values(x)

        # For binary classification, take the positive-class explanation
        if isinstance(shap_vals, list):
            shap_vals = shap_vals[1] if len(shap_vals) > 1 else shap_vals[0]
        shap_vals = np.asarray(shap_vals).flatten()

        base = self._explainer.expected_value
        if isinstance(base, (list, np.ndarray)):
            base = float(np.asarray(base).flatten()[-1])
        else:
            base = float(base)

        pred = float(base + shap_vals.sum())

        # Top positive/negative contributions
        idx_sorted = np.argsort(shap_vals)
        neg_idx = idx_sorted[:top_k]
        pos_idx = idx_sorted[-top_k:][::-1]

        top_pos = [
            {"feature": self.feature_names[i], "shap_value": float(shap_vals[i]), "value": float(x[0, i])}
            for i in pos_idx
            if shap_vals[i] > 0
        ]
        top_neg = [
            {"feature": self.feature_names[i], "shap_value": float(shap_vals[i]), "value": float(x[0, i])}
            for i in neg_idx
            if shap_vals[i] < 0
        ]

        return ShapExplanation(
            feature_names=self.feature_names,
            shap_values=shap_vals.tolist(),
            base_value=base,
            prediction=pred,
            top_positive=top_pos,
            top_negative=top_neg,
        )
