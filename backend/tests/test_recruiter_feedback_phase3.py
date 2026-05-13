from __future__ import annotations

from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.models import User, Candidate, JobCriteria, RecruiterFeedback
from ai_module.feedback.recruiter_feedback import RecruiterFeedbackEngine


def _build_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _seed_feedback(session):
    recruiter = User(email="recruiter@example.com", hashed_password="x", full_name="Recruiter")
    candidate = Candidate(full_name="Alice Smith", email="alice@example.com", raw_text="Python FastAPI Docker")
    criteria = JobCriteria(recruiter_id=1, title="Senior Python Developer", description="Need Python and Docker")
    session.add_all([recruiter, candidate, criteria])
    session.flush()

    session.add_all([
        RecruiterFeedback(
            criteria_id=criteria.id,
            candidate_id=candidate.id,
            recruiter_id=recruiter.id,
            model_predicted_score=62.0,
            model_predicted_decision="review",
            recruiter_decision="accepted",
            recruiter_score_override=85.0,
            feedback_reason="Strong interview",
            is_override=True,
            created_at=datetime.utcnow(),
        ),
        RecruiterFeedback(
            criteria_id=criteria.id,
            candidate_id=candidate.id,
            recruiter_id=recruiter.id,
            model_predicted_score=45.0,
            model_predicted_decision="rejected",
            recruiter_decision="rejected",
            recruiter_score_override=None,
            feedback_reason="Missing key skill",
            is_override=False,
            created_at=datetime.utcnow(),
        ),
    ])
    session.commit()


def test_feedback_engine_metrics_and_export(tmp_path):
    session = _build_session()
    _seed_feedback(session)

    engine = RecruiterFeedbackEngine(session)

    stats = engine.get_override_statistics()
    assert stats["total_feedback"] == 2
    assert stats["override_count"] == 1
    assert stats["override_rate"] == 50.0

    readiness = engine.get_retraining_readiness(min_samples=2, min_override_rate=25.0)
    assert readiness["ready"] is True

    summary = engine.summarize_by_criteria()
    assert summary[next(iter(summary))]["total"] == 2

    dataset = engine.prepare_retraining_dataset(min_samples=2)
    assert dataset is not None
    assert dataset[0]["cv_text"] == "Python FastAPI Docker"

    export_path = tmp_path / "feedback.jsonl"
    result = engine.export_retraining_jsonl(export_path, min_samples=2)
    assert result is not None
    assert export_path.exists()
    assert export_path.read_text(encoding="utf-8").strip() != ""