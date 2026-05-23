"""Normalisation des données structurées : dates, expérience, diplômes, langues."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple


# ----------------------------------------------------------------------- #
# Expérience
# ----------------------------------------------------------------------- #

_YEARS_RE = re.compile(
    r"(\d{1,2})(?:\s*\+\s*|\s*-\s*\d{1,2})?\s*"
    r"(?:years?|ans?|yrs?|année|années)",
    re.IGNORECASE,
)

_MONTHS_RE = re.compile(r"(\d{1,3})\s*(?:months?|mois)", re.IGNORECASE)


def parse_experience_years(text: str) -> float:
    """Extrait la durée d'expérience en années depuis un texte libre.

    Gère :
        '5 years', '5+ years', '5-7 ans', '5 ans 3 mois', '18 months'
    """
    if not text:
        return 0.0

    years = 0.0
    matches = _YEARS_RE.findall(text)
    if matches:
        try:
            years = float(matches[0])
        except ValueError:
            pass

    months_matches = _MONTHS_RE.findall(text)
    if months_matches:
        try:
            months = float(months_matches[0])
            years += months / 12.0
        except ValueError:
            pass

    return round(years, 2)


def parse_date_range(text: str) -> Tuple[Optional[date], Optional[date]]:
    """Extrait (start, end) depuis '2020-2023', 'Jan 2020 – Present', etc."""
    if not text:
        return None, None

    text = text.replace("–", "-").replace("—", "-")
    # Cas 'Present' / 'Actuel' / 'Now'
    is_current = bool(re.search(r"\b(present|now|current|actuel|en cours)\b",
                                text, re.IGNORECASE))

    # Range simple AAAA-AAAA
    year_range = re.search(r"\b(19|20)(\d{2})\s*-\s*(?:(19|20)(\d{2})|present|actuel)",
                           text, re.IGNORECASE)
    if year_range:
        start_year = int(year_range.group(1) + year_range.group(2))
        if year_range.group(3) and year_range.group(4):
            end_year = int(year_range.group(3) + year_range.group(4))
            return date(start_year, 1, 1), date(end_year, 12, 31)
        return date(start_year, 1, 1), date.today() if is_current else None

    # Date isolée
    single_year = re.search(r"\b(19|20)\d{2}\b", text)
    if single_year:
        year = int(single_year.group(0))
        return date(year, 1, 1), None

    return None, None


def compute_experience_months(start: Optional[date], end: Optional[date]) -> int:
    if not start:
        return 0
    end = end or date.today()
    return max(0, (end.year - start.year) * 12 + (end.month - start.month))


# ----------------------------------------------------------------------- #
# Niveau d'étude
# ----------------------------------------------------------------------- #

EDUCATION_LEVELS: Dict[str, int] = {
    # FR
    "bac": 0, "baccalauréat": 0,
    "bac+2": 1, "dut": 1, "bts": 1, "deust": 1,
    "licence": 2, "bachelor": 2, "bac+3": 2, "ba": 2, "bs": 2, "b.sc": 2, "b.s": 2, "b.a": 2,
    "master 1": 3, "maîtrise": 3, "bac+4": 3, "m1": 3,
    "master": 4, "master 2": 4, "ingénieur": 4, "bac+5": 4, "m2": 4,
    "msc": 4, "m.sc": 4, "ms": 4, "m.s": 4, "mba": 4, "mphil": 4,
    "doctorat": 5, "phd": 5, "ph.d": 5, "doctorate": 5, "thèse": 5,
}


def normalize_education_level(degree: str) -> int:
    """Renvoie un niveau d'étude normalisé (0=bac, 5=doctorat)."""
    if not degree:
        return -1
    lower = degree.lower().strip()
    # match exact ou contient
    for key, level in sorted(EDUCATION_LEVELS.items(), key=lambda x: -len(x[0])):
        if key in lower:
            return level
    return -1


# ----------------------------------------------------------------------- #
# Langues
# ----------------------------------------------------------------------- #

LANGUAGE_LEVELS: Dict[str, int] = {
    # CECRL
    "a1": 1, "a2": 2, "b1": 3, "b2": 4, "c1": 5, "c2": 6,
    "native": 6, "natif": 6, "natale": 6, "mother tongue": 6,
    "fluent": 5, "courant": 5, "couramment": 5,
    "advanced": 4, "avancé": 4, "professional": 4, "professionnel": 4,
    "intermediate": 3, "intermédiaire": 3, "good": 3,
    "basic": 2, "basique": 2, "élémentaire": 2,
    "beginner": 1, "débutant": 1, "notions": 1,
}


def normalize_language_level(text: str) -> int:
    if not text:
        return 0
    lower = text.lower()
    for key, level in LANGUAGE_LEVELS.items():
        if key in lower:
            return level
    return 0


# ----------------------------------------------------------------------- #
# Aggregator
# ----------------------------------------------------------------------- #

@dataclass
class NormalizedCandidate:
    skills: List[str]
    experience_years: float
    education_level: int
    languages: Dict[str, "object"]  # CECRL string (e.g. "B2") or int (0-6)
    raw: Dict
    location: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None

    # ---- Aliases for orchestrator compatibility ----
    @property
    def years_experience(self) -> float:
        return self.experience_years

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "email": self.email,
            "location": self.location,
            "skills": self.skills,
            "experience_years": self.experience_years,
            "education_level": self.education_level,
            "languages": self.languages,
        }


class DataNormalizer:
    """Pipeline complet de normalisation d'un dict candidat brut."""

    def __init__(self, skill_normalizer=None) -> None:
        if skill_normalizer is None:
            from ai_pipeline.preprocessing.skill_normalizer import SkillNormalizer
            skill_normalizer = SkillNormalizer()
        self.skill_normalizer = skill_normalizer

    # ----------------------------------------------------------------- #
    # Text-based entry point (used by the orchestrator)
    # ----------------------------------------------------------------- #
    def normalize_from_text(self, text: str) -> NormalizedCandidate:
        """Normalize directly from free-form CV text (no structured input)."""
        if not text:
            text = ""

        # Skills via dictionary lookup
        skills = self.skill_normalizer.extract_skills(text) if hasattr(
            self.skill_normalizer, "extract_skills"
        ) else []

        # Years of experience
        exp_years = parse_experience_years(text)

        # Education level — take the highest mentioned
        edu_level = 0
        for line in text.split("\n"):
            level = normalize_education_level(line)
            edu_level = max(edu_level, level)

        # Languages — match known language names in CECRL/native forms.
        # Stored as Dict[str, str] (the orchestrator expects level strings).
        languages: Dict[str, str] = {}
        for lang_name, key in (
            ("français", "fr"), ("francais", "fr"), ("french", "fr"),
            ("anglais", "en"), ("english", "en"),
            ("arabe", "ar"), ("arabic", "ar"),
            ("espagnol", "es"), ("spanish", "es"),
            ("allemand", "de"), ("german", "de"),
        ):
            m = re.search(
                rf"{lang_name}\s*[:\-–]\s*([A-Za-z0-9+]+)",
                text,
                re.IGNORECASE,
            )
            if m:
                languages[key] = m.group(1).strip().upper()

        # Email + location (best-effort)
        email = None
        m = re.search(r"[\w\.\-]+@[\w\.\-]+\.\w+", text)
        if m:
            email = m.group(0)

        location = None
        m = re.search(r"(?:Localisation|Location|Address|Adresse)\s*:\s*([^\n]+)", text, re.IGNORECASE)
        if m:
            location = m.group(1).strip()

        return NormalizedCandidate(
            skills=skills,
            experience_years=exp_years,
            education_level=edu_level,
            languages=languages,  # type: ignore[arg-type]
            raw={"raw_text": text},
            location=location,
            email=email,
        )

    def normalize_candidate(self, candidate: Dict) -> NormalizedCandidate:
        raw_skills = candidate.get("skills") or candidate.get("competences") or []
        if isinstance(raw_skills, str):
            raw_skills = re.split(r"[,;/]\s*", raw_skills)

        skills = self.skill_normalizer.normalize_list(raw_skills)

        # Expérience
        exp_years = candidate.get("experience_years")
        if not exp_years:
            for key in ("experience", "summary", "raw_text"):
                if candidate.get(key):
                    exp_years = parse_experience_years(candidate[key])
                    if exp_years > 0:
                        break
        exp_years = float(exp_years) if exp_years else 0.0

        # Education
        edu_text = candidate.get("education")
        if isinstance(edu_text, list):
            edu_text = " ".join(str(e) for e in edu_text)
        edu_level = normalize_education_level(edu_text or "")

        # Langues
        languages: Dict[str, int] = {}
        for entry in candidate.get("languages") or []:
            if isinstance(entry, dict):
                name = entry.get("name") or entry.get("language")
                level = entry.get("level") or entry.get("proficiency") or ""
            else:
                name, _, level = str(entry).partition(":")
            if name:
                normalized_name = self.skill_normalizer.normalize(name.strip())
                languages[normalized_name] = normalize_language_level(str(level))

        return NormalizedCandidate(
            skills=skills,
            experience_years=exp_years,
            education_level=edu_level,
            languages=languages,
            raw=candidate,
        )


if __name__ == "__main__":
    norm = DataNormalizer()
    sample = {
        "skills": ["python", "ml", "react.js", "PostgreSQL", "Docker"],
        "experience": "5+ years of software engineering experience",
        "education": "Master of Science in Computer Science",
        "languages": [
            {"name": "english", "level": "fluent"},
            {"name": "french", "level": "native"},
            {"name": "arabic", "level": "intermediate"},
        ],
    }
    result = norm.normalize_candidate(sample)
    print(f"Skills:        {result.skills}")
    print(f"Experience:    {result.experience_years} years")
    print(f"Education:     level {result.education_level}")
    print(f"Languages:     {result.languages}")
