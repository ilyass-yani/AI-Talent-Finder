"""
Fallback tests for CV extraction when NER or skills extraction is unavailable.
"""
from app.services.cv_extractor import CVExtractionService, _FallbackSkillExtractor


def test_extract_from_text_without_ner():
    service = CVExtractionService()
    service.ner_available = False

    text = "John Doe\nEmail: john@example.com\nSkills: Python, FastAPI, PostgreSQL, Docker"
    result = service.extract_from_text(text)

    assert result.quality_score == 0
    assert result.structured == {}

    if type(service.skill_extractor).__name__ == "_FallbackSkillExtractor":
        assert result.skills == []
    else:
        assert any(skill.get("name") == "Python" for skill in result.skills)


def test_extract_from_text_skill_extractor_fallback():
    service = CVExtractionService()
    service.ner_available = False
    service.skill_extractor = _FallbackSkillExtractor()

    result = service.extract_from_text("Just some text without skills")
    assert result.skills == []


if __name__ == "__main__":
    test_extract_from_text_without_ner()
    test_extract_from_text_skill_extractor_fallback()
    print("ner fallback tests: OK")
