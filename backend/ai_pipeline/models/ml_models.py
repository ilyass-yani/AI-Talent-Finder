"""Classical ML models for CV ↔ Job matching.

Wraps Logistic Regression, Random Forest, and XGBoost under a unified
interface so they can be swapped easily in scripts and benchmarks.
The features expected are the ones produced by
:class:`PairFeatureBuilder` (dense numeric vectors).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ModelMetrics:
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    roc_auc: float = 0.0
    confusion_matrix: List[List[int]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "roc_auc": self.roc_auc,
            "confusion_matrix": self.confusion_matrix,
        }


class BaseMLModel:
    """Common scikit-style fit/predict/save interface."""

    def __init__(self, feature_names: Optional[List[str]] = None) -> None:
        self.feature_names = feature_names or []
        self.model = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        raise NotImplementedError

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Model not fitted.")
        return self.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Model not fitted.")
        if hasattr(self.model, "predict_proba"):
            return self.model.predict_proba(X)
        scores = self.model.decision_function(X)
        return np.vstack([-scores, scores]).T

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> ModelMetrics:
        from sklearn.metrics import (
            accuracy_score,
            confusion_matrix,
            f1_score,
            precision_score,
            recall_score,
            roc_auc_score,
        )

        preds = self.predict(X)
        try:
            proba = self.predict_proba(X)[:, 1]
            auc = roc_auc_score(y, proba)
        except Exception:
            auc = 0.0
        return ModelMetrics(
            accuracy=float(accuracy_score(y, preds)),
            precision=float(precision_score(y, preds, average="weighted", zero_division=0)),
            recall=float(recall_score(y, preds, average="weighted", zero_division=0)),
            f1=float(f1_score(y, preds, average="weighted", zero_division=0)),
            roc_auc=float(auc),
            confusion_matrix=confusion_matrix(y, preds).tolist(),
        )

    def save(self, path: str | Path) -> None:
        import joblib

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": self.model, "feature_names": self.feature_names}, path)

    @classmethod
    def load(cls, path: str | Path) -> "BaseMLModel":
        import joblib

        data = joblib.load(path)
        instance = cls(feature_names=data.get("feature_names", []))
        instance.model = data["model"]
        return instance


class LogisticRegressionModel(BaseMLModel):
    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        from sklearn.linear_model import LogisticRegression

        self.model = LogisticRegression(
            max_iter=2000, class_weight="balanced", C=1.0, random_state=42
        )
        self.model.fit(X, y)


class RandomForestModel(BaseMLModel):
    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        from sklearn.ensemble import RandomForestClassifier

        self.model = RandomForestClassifier(
            n_estimators=300,
            max_depth=20,
            min_samples_split=4,
            class_weight="balanced",
            n_jobs=-1,
            random_state=42,
        )
        self.model.fit(X, y)


class XGBoostModel(BaseMLModel):
    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        try:
            from xgboost import XGBClassifier  # type: ignore
        except ImportError as exc:
            raise ImportError("xgboost is required: pip install xgboost") from exc

        # Handle class imbalance via scale_pos_weight
        pos = int((np.asarray(y) == 1).sum())
        neg = int((np.asarray(y) == 0).sum())
        spw = max(1.0, neg / max(pos, 1))

        self.model = XGBClassifier(
            n_estimators=500,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            scale_pos_weight=spw,
            eval_metric="auc",
            random_state=42,
            n_jobs=-1,
        )
        self.model.fit(X, y)


# Factory helper
def get_model(name: str, **kwargs) -> BaseMLModel:
    name = name.lower()
    if name in ("lr", "logreg", "logistic_regression"):
        return LogisticRegressionModel(**kwargs)
    if name in ("rf", "random_forest"):
        return RandomForestModel(**kwargs)
    if name in ("xgb", "xgboost"):
        return XGBoostModel(**kwargs)
    raise ValueError(f"Unknown model: {name}")
