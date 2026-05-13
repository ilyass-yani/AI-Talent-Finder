from pathlib import Path
import sys

backend_root = Path(__file__).resolve().parents[1]
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from ai_module.chatbot.conversation_memory import ConversationMemory
from ai_module.nlp.multilingual_skill_extractor import MultilingualSkillExtractor
from scripts.prepare_ner_annotations import prepare_annotations, normalize_spans, spans_to_bio
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.models import User, Candidate, JobCriteria, RecruiterFeedback
from ai_module.feedback.recruiter_feedback import RecruiterFeedbackEngine


class FakeRedisClient:
    def __init__(self):
        self.lists = {}
        self.hashes = {}

    def ping(self):
        return True

    def rpush(self, key, value):
        self.lists.setdefault(key, []).append(value)

    def ltrim(self, key, start, end):
        self.lists[key] = self.lists.get(key, [])[start : end + 1 if end != -1 else None]

    def expire(self, key, ttl):
        return None

    def hset(self, key, mapping):
        self.hashes.setdefault(key, {}).update(mapping)

    def hget(self, key, field):
        return self.hashes.get(key, {}).get(field)

    def delete(self, *keys):
        for key in keys:
            self.lists.pop(key, None)
            self.hashes.pop(key, None)

    def lrange(self, key, start, end):
        return self.lists.get(key, [])[start : end + 1 if end != -1 else None]

    def keys(self, pattern):
        prefix = pattern[:-1] if pattern.endswith("*") else pattern
        return [key for key in self.lists if key.startswith(prefix)]


if __name__ == "__main__":
    memory = ConversationMemory(client=FakeRedisClient())
    memory.add_message("a", "user", "bonjour")
    memory.add_message("a", "assistant", "salut")
    memory.add_message("b", "user", "hola")
    assert [item["content"] for item in memory.get_history("a")] == ["bonjour", "salut"]
    assert [item["content"] for item in memory.get_history("b")] == ["hola"]
    assert set(memory.list_sessions()) == {"a", "b"}

    extractor = MultilingualSkillExtractor()
    french = extractor.extract_skills(
        "Développeur Python avec expérience en apprentissage automatique, Docker, communication et français courant."
    )
    assert {"Python", "Machine Learning", "Docker", "Communication", "French"}.issubset({item["name"] for item in french})

    spanish = extractor.extract_skills("Ingeniero de datos con aprendizaje automático, SQL, Docker y español fluido.")
    assert {"Machine Learning", "SQL", "Docker", "Spanish"}.issubset({item["name"] for item in spanish})

    template = prepare_annotations([{"text": "Python developer at ACME"}], mode="template")
    assert template[0]["tokens"] == ["Python", "developer", "at", "ACME"]
    assert template[0]["ner_tags"] == ["O", "O", "O", "O"]

    spans = normalize_spans([
        {"start": 7, "end": 13, "label": "SKILL"},
        {"start": 27, "end": 31, "label": "ORG"},
    ])
    bio = spans_to_bio("Senior Python developer at ACME", spans)
    assert bio["ner_tags"][1] == "B-SKILL"
    assert bio["ner_tags"][4] == "B-ORG"

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

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
            is_override=False,
            created_at=datetime.utcnow(),
        ),
    ])
    session.commit()

    feedback = RecruiterFeedbackEngine(session)
    stats = feedback.get_override_statistics()
    assert stats["total_feedback"] == 2
    assert stats["override_count"] == 1
    assert stats["override_rate"] == 50.0
    assert feedback.get_retraining_readiness(min_samples=2, min_override_rate=25.0)["ready"] is True
    assert feedback.summarize_by_criteria()[criteria.id]["total"] == 2
    assert feedback.prepare_retraining_dataset(min_samples=2)

    print("phase2 smoke ok")
