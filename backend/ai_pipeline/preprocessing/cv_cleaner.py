"""Nettoyage de CV bruts.

Pipeline :
    1. Suppression caractères de contrôle / artefacts OCR
    2. Normalisation des sauts de ligne et espaces
    3. Réparation des sections (mots collés)
    4. Suppression des en-têtes/pieds de page redondants
    5. Détection et marquage des sections (Education, Experience, Skills, ...)
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional


# Mots-clés multilingues pour détection de sections
SECTION_KEYWORDS = {
    "summary": [
        "summary", "profile", "objective", "about me", "professional summary",
        "résumé", "profil", "à propos", "objectif",
    ],
    "experience": [
        "experience", "work experience", "professional experience", "employment",
        "expérience", "expérience professionnelle", "parcours professionnel",
    ],
    "education": [
        "education", "academic", "qualifications",
        "formation", "éducation", "diplômes", "études",
    ],
    "skills": [
        "skills", "technical skills", "competencies", "expertise", "technologies",
        "compétences", "savoir-faire", "techniques",
    ],
    "languages": [
        "languages", "spoken languages",
        "langues", "langues parlées",
    ],
    "certifications": [
        "certifications", "certificates", "courses",
        "certifications", "certificats", "formations complémentaires",
    ],
    "projects": [
        "projects", "personal projects", "open source",
        "projets", "projets personnels",
    ],
}

# Patterns OCR communs à corriger
OCR_FIXES = {
    r"\bl\s*[\.]\s*([A-Z])": r"I.\1",
    r"\b0([A-Za-z])": r"O\1",      # 0pen -> Open
    r"([a-z])5\b": r"\1s",          # word5 -> words
    r"\s+([\.,;:!?])": r"\1",
    r"\(\s+": r"(",
    r"\s+\)": r")",
}

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
EXCESS_WHITESPACE = re.compile(r"[ \t\u00a0]+")
EXCESS_NEWLINES = re.compile(r"\n{3,}")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?:\+\d{1,3}[\s-]?)?(?:\(\d{1,4}\)[\s-]?)?\d{1,4}[\s-]?\d{2,4}[\s-]?\d{2,4}[\s-]?\d{0,4}")
URL_RE = re.compile(r"https?://[^\s)]+|www\.[^\s)]+")


@dataclass
class CleanedCV:
    """Résultat du nettoyage : texte propre + sections détectées + métadonnées."""
    raw_text: str
    clean_text: str
    sections: Dict[str, str]
    emails: List[str]
    phones: List[str]
    urls: List[str]
    char_count: int
    word_count: int
    line_count: int
    quality_score: float  # 0..1 — heuristique de qualité d'extraction


class CVCleaner:
    """Nettoyeur de CV bruts, robuste aux artefacts OCR et PDF."""

    def __init__(self, language: str = "auto") -> None:
        self.language = language

    # --------------------------------------------------------------------- #
    # API publique
    # --------------------------------------------------------------------- #

    def clean(self, raw_text: str) -> CleanedCV:
        if not raw_text:
            return CleanedCV("", "", {}, [], [], [], 0, 0, 0, 0.0)

        text = self._strip_control_chars(raw_text)
        text = self._normalize_unicode(text)
        text = self._fix_ocr_artifacts(text)
        text = self._normalize_whitespace(text)

        emails = self._extract_unique(EMAIL_RE, text)
        phones = self._extract_unique(PHONE_RE, text, min_len=8)
        urls = self._extract_unique(URL_RE, text)

        sections = self._segment_sections(text)
        quality = self._quality_score(text, sections, emails, phones)

        return CleanedCV(
            raw_text=raw_text,
            clean_text=text,
            sections=sections,
            emails=emails,
            phones=phones,
            urls=urls,
            char_count=len(text),
            word_count=len(text.split()),
            line_count=len(text.splitlines()),
            quality_score=quality,
        )

    def clean_text_only(self, raw_text: str) -> str:
        """Version légère qui ne renvoie que le texte propre."""
        return self.clean(raw_text).clean_text

    # --------------------------------------------------------------------- #
    # Étapes internes
    # --------------------------------------------------------------------- #

    @staticmethod
    def _strip_control_chars(text: str) -> str:
        return CONTROL_CHARS.sub(" ", text)

    @staticmethod
    def _normalize_unicode(text: str) -> str:
        # NFKC : compose et compatibilise (ligatures, espaces insécables, etc.)
        return unicodedata.normalize("NFKC", text)

    @staticmethod
    def _fix_ocr_artifacts(text: str) -> str:
        for pattern, replacement in OCR_FIXES.items():
            text = re.sub(pattern, replacement, text)
        return text

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        text = EXCESS_WHITESPACE.sub(" ", text)
        # Reconstituer les vrais sauts de paragraphe (2 \n max consécutifs)
        text = EXCESS_NEWLINES.sub("\n\n", text)
        # Trim chaque ligne
        text = "\n".join(line.strip() for line in text.splitlines())
        return text.strip()

    @staticmethod
    def _extract_unique(pattern: re.Pattern, text: str, min_len: int = 0) -> List[str]:
        seen: set = set()
        out: List[str] = []
        for match in pattern.findall(text):
            value = match.strip().rstrip(".,;:")
            if len(value) < min_len:
                continue
            if value.lower() not in seen:
                seen.add(value.lower())
                out.append(value)
        return out

    def _segment_sections(self, text: str) -> Dict[str, str]:
        """Découpe le CV en sections par mots-clés."""
        sections: Dict[str, List[str]] = {key: [] for key in SECTION_KEYWORDS}
        current_section: Optional[str] = None

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                if current_section:
                    sections[current_section].append("")
                continue

            detected = self._detect_section_header(stripped)
            if detected:
                current_section = detected
                continue

            if current_section:
                sections[current_section].append(stripped)

        return {key: "\n".join(lines).strip() for key, lines in sections.items() if lines}

    @staticmethod
    def _detect_section_header(line: str) -> Optional[str]:
        """Détecte si une ligne est un en-tête de section."""
        if len(line) > 50:
            return None  # trop long, pas un titre
        lower = line.lower().rstrip(":").strip()
        for section, keywords in SECTION_KEYWORDS.items():
            for kw in keywords:
                # match exact ou contient le mot-clé en début de ligne
                if lower == kw or lower.startswith(kw + " ") or lower.startswith(kw + ":"):
                    return section
        return None

    @staticmethod
    def _quality_score(
        text: str,
        sections: Dict[str, str],
        emails: List[str],
        phones: List[str],
    ) -> float:
        """Score heuristique 0..1 de qualité d'extraction du CV.

        Composantes :
            - longueur (CV trop court = OCR raté ou CV vide)
            - présence d'un email (signe d'extraction réussie)
            - présence de sections clés
            - ratio de caractères imprimables
        """
        score = 0.0

        length = len(text)
        if length >= 1500:
            score += 0.30
        elif length >= 500:
            score += 0.20
        elif length >= 200:
            score += 0.10

        if emails:
            score += 0.15
        if phones:
            score += 0.10

        important_sections = ["experience", "education", "skills"]
        sections_present = sum(1 for s in important_sections if sections.get(s))
        score += 0.15 * (sections_present / len(important_sections))

        printable = sum(1 for c in text if c.isprintable() or c in "\n\t")
        if length:
            score += 0.30 * (printable / length)

        return min(1.0, score)


if __name__ == "__main__":
    sample = """
    JOHN DOE
    john.doe@example.com  | +33 6 12 34 56 78  |  github.com/johndoe

    SUMMARY
    Senior software engineer with 7 years of experience in Python and ML.

    EXPERIENCE
    Senior Engineer — TechCorp (2020-Present)
    - Built ML pipelines for fraud detection
    - Led team of 4 engineers

    EDUCATION
    M.Sc. Computer Science — MIT (2018)

    SKILLS
    Python, FastAPI, PyTorch, Docker, AWS
    """
    cleaner = CVCleaner()
    result = cleaner.clean(sample)
    print(f"Quality: {result.quality_score:.2f}")
    print(f"Sections: {list(result.sections.keys())}")
    print(f"Emails: {result.emails}")
    print(f"Phones: {result.phones}")
