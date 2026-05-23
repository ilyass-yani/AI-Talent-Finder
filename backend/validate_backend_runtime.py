import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./ai_talent_finder.db")
os.environ.setdefault("USE_AI_PROFILE_GENERATOR", "false")

from fastapi.testclient import TestClient
from app.main import app
from ai_module.nlp.profile_generator import ProfileGenerator
from ai_module.matching.semantic_matcher import SemanticSkillMatcher
from ai_module.nlp.enhanced_skill_extractor import EnhancedSkillExtractor


def main() -> None:
    client = TestClient(app)

    r = client.get("/health")
    print("health", r.status_code, r.json())

    r = client.post(
        "/api/matching/generate-profile",
        json={
            "job_title": "Senior Python Developer",
            "description": "Senior Python FastAPI engineer, 5 years experience, bachelor degree, english and french.",
        },
    )
    print("generate_profile", r.status_code, sorted(r.json().keys()))

    r = client.post(
        "/api/matching/generate-and-match",
        json={
            "job_title": "Data Engineer",
            "description": "Need Python, SQL, ETL and cloud skills.",
        },
    )
    body = r.json()
    print("generate_and_match", r.status_code, "ideal_profile" in body, isinstance(body.get("matches"), list))

    p = ProfileGenerator.generate_from_text("Python lead with 6 years and master degree, english language")
    print("profile_ok", isinstance(p, dict), len(p.get("ideal_skills", [])))

    m = SemanticSkillMatcher.match_candidate_skills(
        ["Python", "FastAPI", "Docker"],
        [{"name": "Python", "weight": 100}, {"name": "Django", "weight": 70}],
    )
    print("semantic_ok", round(float(m.get("score", 0)), 2), m.get("total_matches"))

    ex = EnhancedSkillExtractor(load_ner=False)
    sk = ex.extract_skills_hybrid("Python FastAPI Docker Kubernetes communication leadership English")
    print("skill_extractor_ok", len(sk), sk[0]["name"] if sk else "none")


if __name__ == "__main__":
    main()
