"""Phase 3: Feedback Loop API Endpoints - Expose feedback capture and analysis."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.models.models import User, RecruiterFeedback, Candidate, JobCriteria

# Import Phase 3 modules (with fallback)
try:
    from ai_module.feedback.recruiter_feedback import RecruiterFeedbackEngine, FeedbackRecord
    _FEEDBACK_ENGINE_AVAILABLE = True
except ImportError:
    _FEEDBACK_ENGINE_AVAILABLE = False

try:
    from ai_module.feedback.recommendations_engine import SkillRecommendationsEngine
    _RECOMMENDATIONS_AVAILABLE = True
except ImportError:
    _RECOMMENDATIONS_AVAILABLE = False

try:
    from ai_module.feedback.bias_detector import BiasDetector
    _BIAS_DETECTOR_AVAILABLE = True
except ImportError:
    _BIAS_DETECTOR_AVAILABLE = False


# ============================================================================
# SCHEMAS
# ============================================================================

class RecordFeedbackRequest(BaseModel):
    """Record recruiter decision for a match result."""
    criteria_id: int
    candidate_id: int
    model_predicted_score: float  # 0-100
    model_predicted_decision: str  # "accepted" | "review" | "rejected"
    recruiter_decision: str  # "accepted" | "rejected" | "no_action"
    recruiter_score_override: Optional[float] = None
    feedback_reason: Optional[str] = None


class FeedbackStatsResponse(BaseModel):
    """Statistics on recruiter feedback."""
    total_feedback: int
    override_rate: str
    override_count: int
    distribution: Dict[str, int]


class SkillRecommendationResponse(BaseModel):
    """Skill recommendation."""
    skill_name: str
    frequency: int
    trending_score: float
    category: str
    reason: str
    average_proficiency: str


class BiasAlertResponse(BaseModel):
    """Bias alert."""
    alert_type: str
    severity: str
    message: str
    affected_group: str
    recommendation: str


class BiasReportResponse(BaseModel):
    """Bias detection report."""
    analysis_date: str
    total_records: int
    alerts: List[Dict]
    disparities: Dict
    recommendations: List[str]


# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(prefix="/api/feedback", tags=["feedback-phase3"])


def _default_retraining_export_path() -> Path:
    backend_root = Path(__file__).resolve().parents[2]
    return backend_root / "reports" / "retraining" / "retraining_feedback.jsonl"


# ============================================================================
# FEEDBACK LOOP ENDPOINTS
# ============================================================================

@router.post("/record-decision", response_model=Dict[str, Any])
async def record_recruiter_decision(
    request: RecordFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Record recruiter's actual decision vs model prediction.
    
    Phase 3: Captures feedback for continuous learning.
    """
    if not _FEEDBACK_ENGINE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Feedback engine not available",
        )

    # Validate references
    candidate = db.query(Candidate).filter(Candidate.id == request.candidate_id).first()
    criteria = db.query(JobCriteria).filter(JobCriteria.id == request.criteria_id).first()

    if not candidate or not criteria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate or criteria not found",
        )

    # Record feedback
    engine = RecruiterFeedbackEngine(db)
    feedback = engine.record_feedback(
        criteria_id=request.criteria_id,
        candidate_id=request.candidate_id,
        recruiter_id=current_user.id,
        model_predicted_score=request.model_predicted_score,
        model_predicted_decision=request.model_predicted_decision,
        recruiter_decision=request.recruiter_decision,
        recruiter_score_override=request.recruiter_score_override,
        feedback_reason=request.feedback_reason,
    )

    return {
        "status": "success",
        "feedback_id": feedback.feedback_id,
        "is_override": feedback.is_override,
        "message": (
            "Override recorded" if feedback.is_override else "Decision matches model"
        ),
    }


@router.get("/statistics", response_model=FeedbackStatsResponse)
async def get_feedback_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get statistics on recruiter overrides."""
    if not _FEEDBACK_ENGINE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Feedback engine not available",
        )

    engine = RecruiterFeedbackEngine(db)
    stats = engine.get_override_statistics()
    dist = engine.get_feedback_distribution()

    return FeedbackStatsResponse(
        total_feedback=stats.get("total_feedback", 0),
        override_rate=f"{stats.get('override_rate', 0)}%",
        override_count=stats.get("override_count", 0),
        distribution=dist,
    )


@router.get("/misclassified", response_model=List[Dict])
async def get_misclassified_cases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    override_only: bool = True,
):
    """Get cases where model was wrong (recruiter overrode)."""
    if not _FEEDBACK_ENGINE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Feedback engine not available",
        )

    engine = RecruiterFeedbackEngine(db)
    return engine.get_misclassified_cases(override_only=override_only)


# ============================================================================
# RECOMMENDATIONS ENDPOINTS
# ============================================================================

@router.get("/recommendations/skills", response_model=List[SkillRecommendationResponse])
async def recommend_skills(
    job_title: str,
    current_skills: str = "",  # Comma-separated
    missing_skills: str = "",  # Comma-separated
    top_k: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Recommend skills for a job position.
    
    Phase 3: Suggest trending skills to close gaps.
    """
    if not _RECOMMENDATIONS_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendations engine not available",
        )

    engine = SkillRecommendationsEngine(db)
    current = [s.strip() for s in current_skills.split(",") if s.strip()]
    missing = [s.strip() for s in missing_skills.split(",") if s.strip()]

    recommendations = engine.recommend_skills(job_title, current, missing, top_k)

    return [
        SkillRecommendationResponse(
            skill_name=rec.skill_name,
            frequency=rec.frequency,
            trending_score=rec.trending_score,
            category=rec.category,
            reason=rec.reason,
            average_proficiency=rec.average_proficiency,
        )
        for rec in recommendations
    ]


@router.get("/recommendations/complementary", response_model=List[Dict])
async def get_complementary_skills(
    primary_skills: str,  # Comma-separated
    job_domain: str = "backend",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get complementary skills to existing ones."""
    if not _RECOMMENDATIONS_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendations engine not available",
        )

    engine = SkillRecommendationsEngine(db)
    skills = [s.strip() for s in primary_skills.split(",") if s.strip()]
    return engine.get_complementary_skills(skills, job_domain)


@router.get("/recommendations/certifications", response_model=List[Dict])
async def get_certification_recommendations(
    job_title: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Suggest relevant certifications for job domain."""
    if not _RECOMMENDATIONS_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendations engine not available",
        )

    engine = SkillRecommendationsEngine(db)
    return engine.get_certification_recommendations(job_title)


@router.post("/recommendations/gap-analysis", response_model=Dict)
async def analyze_skill_gaps(
    candidate_skills: List[str],
    required_skills: List[str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Analyze which skills to prioritize learning."""
    if not _RECOMMENDATIONS_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendations engine not available",
        )

    engine = SkillRecommendationsEngine(db)
    return engine.analyze_skill_gaps(candidate_skills, required_skills)


# ============================================================================
# BIAS DETECTION ENDPOINTS
# ============================================================================

@router.post("/bias-analyze", response_model=BiasReportResponse)
async def analyze_bias(
    min_samples: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze recruiter decisions for bias indicators.
    
    Phase 3: Monitor fairness in hiring.
    """
    if not _BIAS_DETECTOR_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bias detector not available",
        )

    try:
        from app.models.models import RecruiterFeedback as FeedbackModel

        # Fetch feedback records
        feedback_records = db.query(FeedbackModel).all()

        # Convert to dicts for analysis
        feedback_dicts = [
            {
                "candidate_id": f.candidate_id,
                "recruiter_id": f.recruiter_id,
                "model_predicted_score": f.model_predicted_score,
                "recruiter_decision": f.recruiter_decision,
                "is_override": f.is_override,
            }
            for f in feedback_records
        ]

        detector = BiasDetector(db)
        report = detector.analyze_recruiter_decisions(feedback_dicts, min_samples)

        return BiasReportResponse(
            analysis_date=report.get("analysis_date", datetime.utcnow().isoformat()),
            total_records=report.get("total_records", 0),
            alerts=report.get("alerts", []),
            disparities=report.get("disparities", {}),
            recommendations=report.get("recommendations", []),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bias analysis failed: {str(e)}",
        )


@router.get("/bias-alerts-summary", response_model=Dict)
async def get_bias_alerts_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get summary of all detected bias alerts."""
    if not _BIAS_DETECTOR_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bias detector not available",
        )

    detector = BiasDetector(db)
    return detector.get_alerts_summary()


# ============================================================================
# MODEL RETRAINING ENDPOINTS
# ============================================================================

@router.post("/retrain-model", response_model=Dict[str, Any])
async def trigger_model_retraining(
    n_estimators: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger model retraining using collected feedback.
    
    Phase 3: Continuous improvement from recruiter decisions.
    """
    if not _FEEDBACK_ENGINE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Feedback engine not available",
        )

    try:
        from scripts.retrain_feedback_model import ModelRetrainingPipeline

        engine = RecruiterFeedbackEngine(db)
        retraining_data = engine.prepare_retraining_dataset(min_samples=20)

        if not retraining_data:
            return {
                "status": "skipped",
                "reason": "Insufficient feedback data",
                "samples": len(retraining_data) if retraining_data else 0,
            }

        pipeline = ModelRetrainingPipeline()
        X, y = pipeline.prepare_features(retraining_data)

        if X is None:
            return {
                "status": "error",
                "message": "Could not prepare features",
            }

        metrics = pipeline.train(X, y, n_estimators=n_estimators)
        
        # Check if training was skipped due to insufficient label variety
        if metrics.get("status") == "skipped":
            return {
                "status": "skipped",
                "reason": metrics.get("reason", "Training skipped"),
                "details": metrics.get("unique_labels", []),
                "message": (
                    "Cannot train with only one class of labels. "
                    "Please collect feedback with both 'accepted' and 'rejected' decisions."
                ),
            }
        
        if metrics.get("status") == "error":
            return {
                "status": "error",
                "message": metrics.get("message", "Unknown training error"),
            }
        
        save_msg = pipeline.save_model()

        return {
            "status": "success",
            "train_accuracy": metrics.get("train_accuracy", 0),
            "test_accuracy": metrics.get("test_accuracy", 0),
            "samples_used": metrics.get("samples", 0),
            "feature_importance": [
                {"feature": f, "importance": imp}
                for f, imp in metrics.get("feature_importance", [])[:5]
            ],
            "model_saved": save_msg,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retraining failed: {str(e)}",
        )


@router.get("/retraining-status", response_model=Dict)
async def get_retraining_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get status of model retraining."""
    if not _FEEDBACK_ENGINE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Feedback engine not available",
        )

    try:
        from app.models.models import RecruiterFeedback as FeedbackModel

        total = db.query(FeedbackModel).count()
        overrides = db.query(FeedbackModel).filter(FeedbackModel.is_override == True).count()

        return {
            "total_feedback_samples": total,
            "override_samples": overrides,
            "ready_for_retraining": total >= 20,
            "recommended_action": (
                "Ready to retrain" if total >= 20 else f"Collect {20 - total} more samples"
            ),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }


@router.get("/retraining-readiness", response_model=Dict[str, Any])
async def get_retraining_readiness(
    min_samples: int = 50,
    min_override_rate: float = 10.0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return whether the feedback store is ready for retraining."""
    if not _FEEDBACK_ENGINE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Feedback engine not available",
        )

    engine = RecruiterFeedbackEngine(db)
    return engine.get_retraining_readiness(min_samples=min_samples, min_override_rate=min_override_rate)


@router.post("/export-retraining-data", response_model=Dict[str, Any])
async def export_retraining_data(
    output_path: Optional[str] = None,
    min_samples: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export the retraining dataset to JSONL for offline jobs."""
    if not _FEEDBACK_ENGINE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Feedback engine not available",
        )

    engine = RecruiterFeedbackEngine(db)
    target_path = Path(output_path).expanduser().resolve() if output_path else _default_retraining_export_path()
    exported_path = engine.export_retraining_jsonl(output_path=target_path, min_samples=min_samples)
    if not exported_path:
        return {"status": "skipped", "reason": "Insufficient feedback data"}

    return {"status": "success", "output_path": exported_path}


@router.get("/criteria/{criteria_id}/summary", response_model=Dict[str, Any])
async def get_feedback_summary_by_criteria(
    criteria_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aggregate feedback decisions for one criteria."""
    if not _FEEDBACK_ENGINE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Feedback engine not available",
        )

    engine = RecruiterFeedbackEngine(db)
    summary = engine.summarize_by_criteria()
    return summary.get(criteria_id, {"accepted": 0, "rejected": 0, "no_action": 0, "total": 0})
