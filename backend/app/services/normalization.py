"""Text and skill normalization helpers used across extraction, matching and training."""

from __future__ import annotations

import re


_WHITESPACE_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[\t\r\n]+")
_SKILL_ALIASES = {
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "ai": "Artificial Intelligence",
    "artificial intelligence": "Artificial Intelligence",
    "nlp": "Natural Language Processing",
    "natural language processing": "Natural Language Processing",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "sql": "SQL",
    "python": "Python",
    "fastapi": "FastAPI",
    "docker": "Docker",
    "aws": "AWS",
    "devops": "DevOps",
    "react": "React",
    "node js": "Node.js",
    "nodejs": "Node.js",
    "pandas": "Pandas",
    "scikit learn": "Scikit-Learn",
}


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    text = str(value).replace("\u00a0", " ")
    text = _PUNCT_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def normalize_skill_name(value: str | None) -> str:
    text = normalize_text(value)
    if not text:
        return ""

    text = text.replace("/", " ")
    text = _WHITESPACE_RE.sub(" ", text)
    normalized = text.strip().lower()
    return _SKILL_ALIASES.get(normalized, text.title())


def normalize_company_name(value: str | None) -> str:
    text = normalize_text(value)
    return text.strip(" ,.-")


def normalize_job_title(value: str | None) -> str:
    text = normalize_text(value)
    return text[:120]


def compact_join(values: list[str] | tuple[str, ...] | None) -> str:
    if not values:
        return ""
    return normalize_text(" ".join(normalize_text(item) for item in values if normalize_text(item)))