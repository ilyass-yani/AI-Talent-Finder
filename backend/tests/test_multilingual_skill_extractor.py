from ai_module.nlp.multilingual_skill_extractor import MultilingualSkillExtractor


def test_extracts_french_skills_and_languages():
    extractor = MultilingualSkillExtractor()
    text = (
        "Développeur Python avec expérience en apprentissage automatique, "
        "Docker, communication et français courant."
    )

    skills = extractor.extract_skills(text)
    names = {item["name"] for item in skills}

    assert "Python" in names
    assert "Machine Learning" in names
    assert "Docker" in names
    assert "Communication" in names
    assert "French" in names


def test_extracts_spanish_skills():
    extractor = MultilingualSkillExtractor()
    text = "Ingeniero de datos con aprendizaje automático, SQL, Docker y español fluido."

    skills = extractor.extract_skills(text)
    names = {item["name"] for item in skills}

    assert "Machine Learning" in names
    assert "SQL" in names
    assert "Docker" in names
    assert "Spanish" in names