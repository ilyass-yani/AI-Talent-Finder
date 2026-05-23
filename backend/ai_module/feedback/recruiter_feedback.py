"""Phase 3: Recruiter Feedback Loop - Capture decisions and learn from overrides."""

from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import json
from pathlib import Path
from sqlalchemy.orm import Session

try:
    import pandas as pd
except ImportError:
    pd = None


@dataclass
class FeedbackRecord:
    """Single feedback data point from recruiter decision."""
    criteria_id: int
    candidate_id: int
    recruiter_id: int
    model_predicted_score: float  # 0-100
    model_predicted_decision: str  # "accepted" | "review" | "rejected"
    recruiter_decision: str  # "accepted" | "rejected" | "no_action"
    recruiter_score_override: Optional[float] = None
    feedback_reason: Optional[str] = None
    is_override: bool = False
    hire_outcome: Optional[str] = None
    hire_date: Optional[datetime] = None
    feedback_id: Optional[int] = None


class RecruiterFeedbackEngine:
    """Manage recruiter feedback, detect overrides, and prepare retraining data."""

    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db

    def record_feedback(
        self,
        criteria_id: int,
        candidate_id: int,
        recruiter_id: int,
        model_predicted_score: float,
        model_predicted_decision: str,
        recruiter_decision: str,
        recruiter_score_override: Optional[float] = None,
        feedback_reason: Optional[str] = None,
    ) -> "FeedbackRecord":
        """
        Record a recruiter decision vs model prediction.
        
        Returns FeedbackRecord for further processing.
        """
        # Check if recruiter overrode model decision
        is_override = recruiter_decision != model_predicted_decision
        
        record = FeedbackRecord(
            criteria_id=criteria_id,
            candidate_id=candidate_id,
            recruiter_id=recruiter_id,
            model_predicted_score=model_predicted_score,
            model_predicted_decision=model_predicted_decision,
            recruiter_decision=recruiter_decision,
            recruiter_score_override=recruiter_score_override,
            feedback_reason=feedback_reason,
            is_override=is_override,
        )
        
        # Persist to database if available
        if self.db:
            self._persist_feedback(record)
        
        return record

    def _persist_feedback(self, record: FeedbackRecord) -> None:
        """Store feedback record to database."""
        try:
            from app.models.models import RecruiterFeedback as FeedbackModel
            
            db_feedback = FeedbackModel(
                criteria_id=record.criteria_id,
                candidate_id=record.candidate_id,
                recruiter_id=record.recruiter_id,
                model_predicted_score=record.model_predicted_score,
                model_predicted_decision=record.model_predicted_decision,
                recruiter_decision=record.recruiter_decision,
                recruiter_score_override=record.recruiter_score_override,
                feedback_reason=record.feedback_reason,
                is_override=record.is_override,
                hire_outcome=record.hire_outcome,
                hire_date=record.hire_date,
            )
            self.db.add(db_feedback)
            self.db.commit()
            self.db.refresh(db_feedback)
            record.feedback_id = db_feedback.id
        except Exception as e:
            print(f"Warning: Could not persist feedback: {e}")

    def get_override_statistics(self) -> Dict[str, float]:
        """Get statistics on recruiter overrides (for quality monitoring)."""
        try:
            from app.models.models import RecruiterFeedback as FeedbackModel
            
            total = self.db.query(FeedbackModel).count()
            if total == 0:
                return {"total_feedback": 0, "override_rate": 0.0, "override_count": 0}
            
            overrides = self.db.query(FeedbackModel).filter(FeedbackModel.is_override == True).count()
            
            return {
                "total_feedback": total,
                "override_count": overrides,
                "override_rate": round(overrides / total * 100, 2),
            }
        except Exception:
            return {"total_feedback": 0, "override_rate": 0.0, "override_count": 0}

    def get_feedback_distribution(self, criteria_id: Optional[int] = None) -> Dict[str, int]:
        """Get distribution of recruiter decisions."""
        try:
            from app.models.models import RecruiterFeedback as FeedbackModel
            
            query = self.db.query(FeedbackModel)
            if criteria_id:
                query = query.filter(FeedbackModel.criteria_id == criteria_id)
            
            results = query.all()
            distribution = {
                "accepted": 0,
                "rejected": 0,
                "no_action": 0,
            }
            
            for fb in results:
                decision = fb.recruiter_decision.lower()
                if decision in distribution:
                    distribution[decision] += 1
            
            return distribution
        except Exception:
            return {"accepted": 0, "rejected": 0, "no_action": 0}

    def prepare_retraining_dataset(self, min_samples: int = 50) -> Optional[List[Dict]]:
        """
        Prepare dataset for model retraining using recruiter feedback.
        
        Only retrain if we have enough feedback samples with meaningful overrides.
        """
        try:
            from app.models.models import RecruiterFeedback as FeedbackModel, Candidate, JobCriteria
            
            # Get all feedback records
            feedback_records = self.db.query(FeedbackModel).all()
            
            if len(feedback_records) < min_samples:
                print(f"Insufficient feedback: {len(feedback_records)} < {min_samples}")
                return None
            
            # Build retraining pairs (candidate text + feedback label)
            retraining_data = []
            for fb in feedback_records:
                try:
                    candidate = self.db.query(Candidate).filter(
                        Candidate.id == fb.candidate_id
                    ).first()
                    criteria = self.db.query(JobCriteria).filter(
                        JobCriteria.id == fb.criteria_id
                    ).first()
                    
                    if not candidate or not criteria:
                        continue
                    
                    # Use recruiter decision as ground truth label (not model prediction)
                    label = 1 if fb.recruiter_decision == "accepted" else 0
                    score = fb.recruiter_score_override or fb.model_predicted_score
                    
                    retraining_data.append({
                        "candidate_id": fb.candidate_id,
                        "criteria_id": fb.criteria_id,
                        "cv_text": candidate.raw_text or "",
                        "job_title": criteria.title,
                        "job_description": criteria.description or "",
                        "label": label,  # 1=accepted, 0=rejected
                        "score": score / 100.0,  # Normalize to 0-1
                        "is_override": fb.is_override,
                        "feedback_reason": fb.feedback_reason,
                        "created_at": fb.created_at.isoformat() if fb.created_at else None,
                    })
                except Exception as e:
                    print(f"Error processing feedback {fb.id}: {e}")
                    continue
            
            print(f"Prepared {len(retraining_data)} samples for retraining")
            return retraining_data
        except Exception as e:
            print(f"Error preparing retraining dataset: {e}")
            return None

    def get_misclassified_cases(self, override_only: bool = True) -> List[Dict]:
        """Return cases where model was wrong (recruiter overrode)."""
        try:
            from app.models.models import RecruiterFeedback as FeedbackModel, Candidate, JobCriteria
            
            query = self.db.query(FeedbackModel)
            if override_only:
                query = query.filter(FeedbackModel.is_override == True)
            
            results = []
            for fb in query.limit(100).all():  # Limit to avoid huge lists
                try:
                    candidate = self.db.query(Candidate).filter(
                        Candidate.id == fb.candidate_id
                    ).first()
                    criteria = self.db.query(JobCriteria).filter(
                        JobCriteria.id == fb.criteria_id
                    ).first()
                    
                    if candidate and criteria:
                        results.append({
                            "feedback_id": fb.id,
                            "candidate": candidate.full_name,
                            "job": criteria.title,
                            "model_decision": fb.model_predicted_decision,
                            "model_score": fb.model_predicted_score,
                            "recruiter_decision": fb.recruiter_decision,
                            "recruiter_score": fb.recruiter_score_override or fb.model_predicted_score,
                            "reason": fb.feedback_reason,
                            "created_at": fb.created_at.isoformat() if fb.created_at else None,
                        })
                except Exception:
                    continue
            
            return results
        except Exception as e:
            print(f"Error fetching misclassified cases: {e}")
            return []

    def get_metrics_summary(self) -> Dict:
        """Get comprehensive feedback metrics for monitoring."""
        stats = self.get_override_statistics()
        distribution = self.get_feedback_distribution()
        
        return {
            "total_feedback": stats.get("total_feedback", 0),
            "override_rate": f"{stats.get('override_rate', 0)}%",
            "distribution": distribution,
            "misclassified_count": stats.get("override_count", 0),
        }

    def get_retraining_readiness(self, min_samples: int = 50, min_override_rate: float = 10.0) -> Dict[str, object]:
        """Return whether the collected feedback is sufficient for retraining."""
        stats = self.get_override_statistics()
        total_feedback = int(stats.get("total_feedback", 0))
        override_rate = float(stats.get("override_rate", 0.0))

        ready = total_feedback >= min_samples and override_rate >= min_override_rate
        reasons = []
        if total_feedback < min_samples:
            reasons.append(f"Need at least {min_samples} samples")
        if override_rate < min_override_rate:
            reasons.append(f"Need override rate >= {min_override_rate}% to learn from disagreement")

        return {
            "ready": ready,
            "total_feedback": total_feedback,
            "override_rate": override_rate,
            "min_samples": min_samples,
            "min_override_rate": min_override_rate,
            "reasons": reasons,
        }

    def export_retraining_jsonl(self, output_path: str | Path, min_samples: int = 50) -> Optional[str]:
        """Export the retraining dataset as JSONL for offline training jobs."""
        dataset = self.prepare_retraining_dataset(min_samples=min_samples)
        if not dataset:
            return None

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for record in dataset:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return str(path)

    def summarize_by_criteria(self) -> Dict[int, Dict[str, int]]:
        """Aggregate feedback counts per criteria id."""
        try:
            from app.models.models import RecruiterFeedback as FeedbackModel

            summary: Dict[int, Dict[str, int]] = {}
            for feedback in self.db.query(FeedbackModel).all():
                bucket = summary.setdefault(int(feedback.criteria_id), {"accepted": 0, "rejected": 0, "no_action": 0, "total": 0})
                decision = str(feedback.recruiter_decision).lower()
                if decision in bucket:
                    bucket[decision] += 1
                bucket["total"] += 1
            return summary
        except Exception:
            return {}
