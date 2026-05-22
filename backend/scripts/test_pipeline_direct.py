"""Run pipeline logic directly using service classes to avoid importing FastAPI."""
import json
from app.services.cv_extractor import CVExtractionService
from app.services.feature_engineering import fit_pair_vectorizer, build_pair_features
from app.services.matching_service import MatchingService
from app.services.scoring import compute_match_score, apply_business_rules


def main():
    candidate_raw = "John Doe\nExperience: 5 years Python, AWS, Docker. Skills: Python, AWS, Docker."
    job_text = "Senior Python developer with AWS experience"

    extractor = CVExtractionService()
    extraction = extractor.extract_from_text(candidate_raw)

    cv_text = extraction.raw_text

    meta = fit_pair_vectorizer([cv_text], [job_text])
    features = build_pair_features(cv_text, job_text, meta)

    matcher = MatchingService()
    sim = matcher.semantic_similarity(cv_text, job_text)

    cv_skills = extraction.structured.get("skills", []) if extraction.structured else []
    job_skills = ["Python", "AWS"]
    cv_years = extraction.structured.get("years_experience", 0) if extraction.structured else 0
    job_years = 3

    score = compute_match_score(
        cv_skills=cv_skills,
        job_skills=job_skills,
        cv_years=cv_years,
        job_years=job_years,
        similarity_score=float(sim),
    )

    decision = apply_business_rules({
        "score": score,
        "cv_skills": cv_skills,
        "job_skills": job_skills,
        "cv_years": cv_years,
        "job_years": job_years,
    })

    out = {
        "extraction_quality": extraction.quality_score,
        "similarity": sim,
        "score": score,
        "decision": decision,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
