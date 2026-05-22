from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import joblib
import numpy as np

from app.services.feature_engineering import fit_pair_vectorizer, build_pair_features

router = APIRouter(prefix="/api/models", tags=["models"])


class PredictRequest(BaseModel):
    candidate_text: str
    job_text: str
    model: Optional[str] = "logistic"  # logistic | random_forest | xgboost


_MODEL_CACHE = {}


def _load_model(name: str):
    base = os.path.join("models", "classical")
    if name == "logistic":
        path = os.path.join(base, "logistic.joblib")
    elif name == "random_forest":
        path = os.path.join(base, "random_forest.joblib")
    elif name == "xgboost":
        path = os.path.join(base, "xgboost.model")
    else:
        raise FileNotFoundError("Unknown model")

    if not os.path.exists(path):
        raise FileNotFoundError(f"Model not found: {path}")

    if name in _MODEL_CACHE:
        return _MODEL_CACHE[name]

    if name == "xgboost":
        try:
            import xgboost as xgb
            model = xgb.Booster()
            model.load_model(path)
        except Exception as e:
            raise
    else:
        model = joblib.load(path)

    _MODEL_CACHE[name] = model
    return model


@router.post("/predict")
def predict(req: PredictRequest):
    # Build feature meta
    meta_path = os.path.join("models", "classical", "pair_feature_meta.joblib")
    if not os.path.exists(meta_path):
        raise HTTPException(status_code=404, detail="Featurization meta not found; train models first")

    meta = joblib.load(meta_path)
    X = build_pair_features(req.candidate_text, req.job_text, meta)
    X = X.reshape(1, -1)

    try:
        model = _load_model(req.model)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if req.model == "xgboost":
        import xgboost as xgb
        dmat = xgb.DMatrix(X)
        score = float(model.predict(dmat)[0])
    else:
        score = float(model.predict_proba(X)[0, 1])

    return {"model": req.model, "score": score}
