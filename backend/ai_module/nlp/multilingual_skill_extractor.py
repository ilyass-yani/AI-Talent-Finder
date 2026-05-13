"""Multilingual skill extraction for FR/EN/ES CVs and job descriptions.

The extractor is intentionally lightweight: it uses a canonical skill map plus
language-specific aliases and heuristics, and only depends on `langdetect` when
available. It is designed to plug into the existing hybrid skill extractor
without introducing a hard dependency on external NLP services.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

try:
    from langdetect import detect  # type: ignore
    LANGDETECT_AVAILABLE = True
except Exception:
    detect = None
    LANGDETECT_AVAILABLE = False


@dataclass(frozen=True)
class MultilingualSkillMatch:
    name: str
    source: str
    confidence: float
    category: str = "tech"
    normalized_name: Optional[str] = None


class MultilingualSkillExtractor:
    """Extract skills in FR/EN/ES and map them to canonical skill names."""

    def __init__(self) -> None:
        self.alias_map: Dict[str, Dict[str, str]] = {
            "en": {
                "python": "Python",
                "machine learning": "Machine Learning",
                "deep learning": "Deep Learning",
                "data science": "Data Science",
                "data analysis": "Data Analysis",
                "communication": "Communication",
                "teamwork": "Teamwork",
                "problem solving": "Problem Solving",
                "sql": "SQL",
                "postgresql": "PostgreSQL",
                "docker": "Docker",
                "kubernetes": "Kubernetes",
                "react": "React",
                "typescript": "TypeScript",
                "javascript": "JavaScript",
                "fastapi": "FastAPI",
                "flask": "Flask",
                "english": "English",
                "spanish": "Spanish",
                "french": "French",
            },
            "fr": {
                "python": "Python",
                "apprentissage automatique": "Machine Learning",
                "apprentissage profond": "Deep Learning",
                "science des données": "Data Science",
                "analyse de données": "Data Analysis",
                "communication": "Communication",
                "travail d'équipe": "Teamwork",
                "resolution de problemes": "Problem Solving",
                "sql": "SQL",
                "postgresql": "PostgreSQL",
                "docker": "Docker",
                "kubernetes": "Kubernetes",
                "react": "React",
                "typescript": "TypeScript",
                "javascript": "JavaScript",
                "fastapi": "FastAPI",
                "flask": "Flask",
                "anglais": "English",
                "espagnol": "Spanish",
                "francais": "French",
            },
            "es": {
                "python": "Python",
                "aprendizaje automático": "Machine Learning",
                "aprendizaje profundo": "Deep Learning",
                "ciencia de datos": "Data Science",
                "análisis de datos": "Data Analysis",
                "comunicación": "Communication",
                "trabajo en equipo": "Teamwork",
                "resolución de problemas": "Problem Solving",
                "sql": "SQL",
                "postgresql": "PostgreSQL",
                "docker": "Docker",
                "kubernetes": "Kubernetes",
                "react": "React",
                "typescript": "TypeScript",
                "javascript": "JavaScript",
                "fastapi": "FastAPI",
                "flask": "Flask",
                "inglés": "English",
                "español": "Spanish",
                "francés": "French",
            },
        }
        self.category_map = {
            "Python": "tech",
            "Machine Learning": "tech",
            "Deep Learning": "tech",
            "Data Science": "tech",
            "Data Analysis": "tech",
            "SQL": "tech",
            "PostgreSQL": "tech",
            "Docker": "tech",
            "Kubernetes": "tech",
            "React": "tech",
            "TypeScript": "tech",
            "JavaScript": "tech",
            "FastAPI": "tech",
            "Flask": "tech",
            "Communication": "soft",
            "Teamwork": "soft",
            "Problem Solving": "soft",
            "English": "language",
            "Spanish": "language",
            "French": "language",
        }

    def detect_language(self, text: str) -> str:
        """Detect the most likely language of the input text."""
        if not text:
            return "en"

        if LANGDETECT_AVAILABLE:
            try:
                lang = detect(text)
                if lang in {"fr", "es", "en"}:
                    return lang
            except Exception:
                pass

        lowered = text.lower()
        if any(token in lowered for token in [" le ", " la ", " les ", " et ", " avec ", "français", "expérience"]):
            return "fr"
        if any(token in lowered for token in [" el ", " la ", " los ", " experiencia", "con ", "español"]):
            return "es"
        return "en"

    def extract_skills(self, text: str) -> List[Dict[str, object]]:
        """Return multilingual skill matches as canonical skill dictionaries."""
        if not text:
            return []

        lang = self.detect_language(text)
        aliases = self.alias_map.get(lang, self.alias_map["en"])
        lowered = self._normalize_text(text)

        matches: List[MultilingualSkillMatch] = []
        seen = set()

        for alias, canonical in aliases.items():
            alias_pattern = r"\b" + re.escape(self._normalize_text(alias)) + r"\b"
            if re.search(alias_pattern, lowered) and canonical.lower() not in seen:
                seen.add(canonical.lower())
                matches.append(
                    MultilingualSkillMatch(
                        name=canonical,
                        normalized_name=canonical,
                        source=f"MULTILINGUAL-{lang}",
                        confidence=0.88 if lang != "en" else 0.92,
                        category=self.category_map.get(canonical, "tech"),
                    )
                )

        return [match.__dict__ for match in matches]

    def _normalize_text(self, text: str) -> str:
        normalized = text.lower()
        normalized = normalized.replace("é", "e").replace("è", "e").replace("ê", "e")
        normalized = normalized.replace("à", "a").replace("ù", "u").replace("î", "i")
        normalized = normalized.replace("ç", "c").replace("á", "a").replace("í", "i")
        normalized = normalized.replace("ó", "o").replace("ú", "u").replace("ñ", "n")
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized