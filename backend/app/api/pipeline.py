import json

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Dict, Any, Optional

from app.services.cv_extractor import CVExtractionService
from app.services.feature_engineering import PairFeatureMeta, build_pair_features, fit_pair_vectorizer
from app.services.matching_service import MatchingService
from app.services.scoring import compute_match_score, apply_business_rules
from app.scoring.decision import combine_scores, decision_from_score
import joblib
import pickle
from pathlib import Path
import numpy as _np

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


def _load_bert_first_model_bundle():
    """Load the BERT-first pairwise scoring bundle if it exists."""
    models_dir = Path("models/classical_from_tfidf_bertfirst")
    if not models_dir.exists():
        return None

    meta_path = models_dir / "pair_feature_meta.joblib"
    if not meta_path.exists():
        return None

    try:
        meta = joblib.load(meta_path)
    except Exception:
        return None

    model = None
    for filename in ("xgboost.model", "random_forest.joblib", "logistic.joblib"):
        model_path = models_dir / filename
        if model_path.exists():
            try:
                model = joblib.load(model_path)
            except Exception:
                try:
                    import xgboost as xgb

                    model = xgb.Booster()
                    model.load_model(str(model_path))
                except Exception:
                    model = None
            if model is not None:
                break

    if model is None:
        return None

    return {"model": model, "meta": meta}


@router.post("/run")
def run_pipeline(payload: Dict[str, Any]):
    """Run full pipeline: extraction -> features -> matching -> scoring -> decision.

    Accepts either `candidate` (raw_text or fields) or `candidate_id` (not implemented),
    and `job` (job_text + metadata).
    """
    candidate = payload.get("candidate")
    job = payload.get("job")
    mode = payload.get("mode", "semantic")

    if not candidate or not job:
        raise HTTPException(status_code=400, detail="Both 'candidate' and 'job' are required in payload")

    # Extraction (if raw text provided)
    extractor = CVExtractionService()
    if isinstance(candidate, dict) and candidate.get("raw_text"):
        extraction = extractor.extract_from_text(candidate.get("raw_text"))
    else:
        # If structured candidate provided, build a lightweight extraction result
        extraction = extractor.extract_from_text(candidate.get("raw_text", ""))

    cv_text = extraction.raw_text or ""
    job_text = job.get("job_text") or job.get("description") or ""

    # Feature engineering: fit a small TF-IDF meta on-the-fly when needed
    meta = fit_pair_vectorizer([cv_text], [job_text])
    features = build_pair_features(cv_text, job_text, meta)

    # Matching
    matcher = MatchingService()
    if mode == "semantic":
        sim = matcher.semantic_similarity(cv_text, job_text)
    elif mode == "vector":
        # Keep the vector mode aligned with the BERT-first matching stack.
        sim = matcher.semantic_similarity(cv_text, job_text)
    elif mode == "continuous":
        cont = matcher.continuous_similarity(job_text, cv_text)
        sim = cont.get("max", cont.get("mean", 0.0))
    else:
        sim = matcher.deep_match_score(job_text, cv_text)

    # Scoring and decision
    cv_skills = extraction.structured.get("skills", []) if extraction.structured else []
    job_skills = job.get("skills", [])
    cv_years = extraction.structured.get("years_experience", 0) if extraction.structured else 0
    job_years = job.get("years_experience", 0)

    score = compute_match_score(
        cv_skills=cv_skills,
        job_skills=job_skills,
        cv_years=cv_years,
        job_years=job_years,
        similarity_score=float(sim),
    )
    # Try to augment with ML model score (if trained models present)
    ml_score_pct = None
    model_bundle = _load_bert_first_model_bundle()
    if model_bundle is not None:
        try:
            clf = model_bundle["model"]
            meta = model_bundle["meta"]
            X = build_pair_features(cv_text, job_text, meta)
            try:
                prob = clf.predict_proba(X)[:, 1].ravel()[0]
                ml_score_pct = float(prob * 100.0)
            except Exception:
                try:
                    pred = clf.predict(X).ravel()[0]
                    ml_score_pct = float(pred * 100.0)
                except Exception:
                    ml_score_pct = None
        except Exception:
            ml_score_pct = None

    # ml_score_pct None -> use compute_match_score result (skills + experience)
    if ml_score_pct is None:
        ml_score_pct = float(score * 100.0)

    # combine similarity (0..1) -> convert to 0..100
    sim_pct = float(sim) * 100.0 if sim is not None else 0.0
    final_score = combine_scores(sim_pct, ml_score_pct, w_sim=0.5, w_ml=0.5)
    decision_label, decision_meta = decision_from_score(final_score)

    return {
        "extraction": {
            "quality_score": extraction.quality_score,
            "structured": extraction.structured,
        },
        "similarity": float(sim),
        "ml_score": ml_score_pct,
        "final_score": final_score,
        "decision": {"label": decision_label, "meta": decision_meta},
    }


def np_dot_cosine(a, b):
    import numpy as _np
    na = _np.linalg.norm(a)
    nb = _np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(_np.dot(a, b) / (na * nb))



@router.post("/run-full")
async def run_full(cv: UploadFile = File(...), job_json: str = Form(...)):
    """Minimal endpoint: upload a CV file and a job JSON, return pipeline decision.

    This endpoint saves the uploaded CV to a temporary path, runs the existing
    `run_pipeline` function by providing extracted raw text, and returns the same
    output shape as `/run`.
    """
    try:
        job = json.loads(job_json)
    except Exception:
        raise HTTPException(status_code=400, detail="'job_json' must be valid JSON")

    if not isinstance(job, dict):
        raise HTTPException(status_code=400, detail="'job_json' must decode to an object")

    from uuid import uuid4
    tmp_path = Path('/tmp')
    tmp_path.mkdir(parents=True, exist_ok=True)
    suffix = Path(cv.filename).suffix or '.pdf'
    dest = tmp_path / f"uploaded_cv_{uuid4().hex}{suffix}"
    content = await cv.read()
    try:
        dest.write_bytes(content)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {exc}")

    extractor = CVExtractionService()
    try:
        extraction = extractor.extract_from_pdf(str(dest))
    except Exception:
        # fallback: try text extraction
        text = content.decode('utf-8', errors='ignore')
        extraction = extractor.extract_from_text(text)

    payload = {"candidate": {"raw_text": extraction.raw_text or ""}, "job": job}
    decision_payload = run_pipeline(payload)

    matcher = MatchingService()
    job_text = job.get("job_text") or job.get("description") or ""
    top_k = int(job.get("top_k", 5))
    top_k_results = matcher.search_top_k_candidates(job_text=job_text, top_k=top_k)

    return {
        "decision": decision_payload,
        "top_k": {
            "job_text": job_text,
            "top_k": top_k,
            "results": top_k_results,
        },
    }


@router.post("/top-k")
def top_k_candidates(payload: Dict[str, Any]):
    """Return the top-K CV candidates for a job description using FAISS.

    Expected payload:
        {
            "job_text": "...",
            "top_k": 5,
            "index_dir": "models/faiss_index"
        }
    """
    job_text = payload.get("job_text") or payload.get("description") or ""
    top_k = int(payload.get("top_k", 5))
    index_dir = payload.get("index_dir", "models/faiss_index")

    if not job_text.strip():
        raise HTTPException(status_code=400, detail="'job_text' is required")

    matcher = MatchingService()
    results = matcher.search_top_k_candidates(job_text=job_text, top_k=top_k, index_dir=index_dir)

    return {
        "job_text": job_text,
        "top_k": top_k,
        "index_dir": index_dir,
        "results": results,
    }
