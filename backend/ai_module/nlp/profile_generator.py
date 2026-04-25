"""Profile generation from job descriptions using Flan-T5 + safe fallback rules."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from ai_module.nlp.cv_cleaner import CVCleaner

try:
    from transformers import pipeline

    HF_AVAILABLE = True
except Exception:
    HF_AVAILABLE = False


class ProfileGenerator:
    """Generate an ideal profile from free text."""

    USE_AI_MODEL = os.getenv("USE_AI_PROFILE_GENERATOR", "true").lower() == "true"
    HF_MODEL_NAME = os.getenv("HF_PROFILE_MODEL", "google/flan-t5-base")
    _model_cache: Dict[str, Any] = {}

    TECH_SKILLS = [
        "python", "fastapi", "django", "sql", "postgresql", "mysql", "docker", "kubernetes",
        "aws", "azure", "gcp", "javascript", "typescript", "react", "nodejs", "flask", "git",
        "devops", "api", "microservices", "data", "etl", "pandas", "numpy", "machine learning",
        "nlp", "cloud", "linux", "scikit-learn", "xgboost", "faiss",
    ]

    SOFT_SKILLS = [
        "communication", "teamwork", "collaboration", "leadership", "problem solving", "adaptability",
        "creativity", "organization", "autonomy", "critical thinking", "time management", "planning",
    ]

    LANGUAGES = [
        "english", "french", "spanish", "german", "italian", "portuguese", "arabic", "mandarin", "japanese",
    ]

    EDUCATION_LEVELS = {
        "phd": "PhD or equivalent",
        "doctorate": "PhD or equivalent",
        "master": "Master's degree",
        "msc": "Master's degree",
        "bachelor": "Bachelor's degree",
        "licence": "Bachelor's degree",
        "engineering": "Engineering degree",
    }

    EXPERIENCE_PATTERNS = [
        r"(?P<years>[0-9]{1,2})\s*\+?\s*(?:years|yrs|ans)",
        r"minimum\s+of\s+(?P<years>[0-9]{1,2})\s*\+?\s*(?:years|yrs|ans)",
    ]

    @classmethod
    def _load_ai_model(cls, model_name: Optional[str] = None) -> Optional[Any]:
        if not HF_AVAILABLE:
            return None

        key = model_name or cls.HF_MODEL_NAME
        if key in cls._model_cache:
            return cls._model_cache[key]

        try:
            model = pipeline("text2text-generation", model=key)
            cls._model_cache[key] = model
            return model
        except Exception as exc:
            print(f"Failed to load profile generation model '{key}': {exc}")
            return None

    @classmethod
    def clear_cache(cls) -> None:
        """Release cached generation models."""
        cls._model_cache.clear()

    @classmethod
    def _build_prompt(cls, text: str) -> str:
        return (
            "Generate an ideal candidate profile in valid JSON with keys: "
            "ideal_skills (array of {name, weight, level}), ideal_experience_years (int), "
            "ideal_education (string), ideal_languages (array), industries (array). "
            "Keep it concise and role-specific.\n\n"
            f"Job description:\n{text}\n"
        )

    @classmethod
    def _parse_ai_json(cls, output: str) -> Optional[Dict[str, Any]]:
        output = output.strip()
        start = output.find("{")
        end = output.rfind("}")
        if start < 0 or end <= start:
            return None

        snippet = output[start : end + 1]
        try:
            data = json.loads(snippet)
            if isinstance(data, dict):
                return data
        except Exception:
            return None
        return None

    @classmethod
    def _generate_with_ai(cls, text: str, model_name: Optional[str] = None) -> Dict[str, Any]:
        model = cls._load_ai_model(model_name)
        if not model:
            return cls._generate_with_rules(text)

        prompt = cls._build_prompt(CVCleaner.clean_text(text))
        try:
            result = model(prompt, max_new_tokens=256, do_sample=False)
            generated = result[0].get("generated_text", "") if result else ""
            parsed = cls._parse_ai_json(generated)
            if parsed is None:
                return cls._generate_with_rules(text)
            return cls._sanitize_profile(parsed, fallback_text=text)
        except Exception as exc:
            print(f"AI profile generation failed: {exc}")
            return cls._generate_with_rules(text)

    @classmethod
    def _sanitize_profile(cls, profile: Dict[str, Any], fallback_text: str) -> Dict[str, Any]:
        fallback = cls._generate_with_rules(fallback_text)

        skills = profile.get("ideal_skills")
        if not isinstance(skills, list) or not skills:
            skills = fallback["ideal_skills"]

        cleaned_skills: List[Dict[str, Any]] = []
        for item in skills[:12]:
            if isinstance(item, dict):
                name = str(item.get("name", "")).strip()
                if not name:
                    continue
                cleaned_skills.append(
                    {
                        "name": name,
                        "weight": int(item.get("weight", 80) or 80),
                        "level": str(item.get("level", "Intermediate") or "Intermediate"),
                    }
                )
            elif isinstance(item, str) and item.strip():
                cleaned_skills.append({"name": item.strip(), "weight": 80, "level": "Intermediate"})

        if not cleaned_skills:
            cleaned_skills = fallback["ideal_skills"]

        return {
            "ideal_skills": cleaned_skills,
            "ideal_experience_years": int(profile.get("ideal_experience_years") or fallback["ideal_experience_years"]),
            "ideal_education": str(profile.get("ideal_education") or fallback["ideal_education"]),
            "ideal_languages": profile.get("ideal_languages") if isinstance(profile.get("ideal_languages"), list) else fallback["ideal_languages"],
            "industries": profile.get("industries") if isinstance(profile.get("industries"), list) else fallback["industries"],
        }

    @classmethod
    def _generate_with_rules(cls, text: str) -> Dict[str, Any]:
        cleaned = CVCleaner.clean_text(text)
        technical = cls._find_keywords(cleaned, cls.TECH_SKILLS)
        soft = cls._find_keywords(cleaned, cls.SOFT_SKILLS)
        languages = [lang.title() for lang in cls._find_keywords(cleaned, cls.LANGUAGES)]

        experience_years = cls._extract_years(cleaned)
        education = cls._extract_education(cleaned)

        # Prioritize technical skills first, then selected soft skills.
        ordered = technical + [s for s in soft if s not in technical]
        if not ordered:
            ordered = ["communication", "problem solving", "teamwork"]

        ideal_skills = []
        for skill in ordered[:10]:
            level = cls._profile_level(cleaned, skill)
            weight = 90 if skill in technical else 70
            ideal_skills.append({"name": skill.title(), "weight": weight, "level": level})

        industries = cls._extract_industries(cleaned)

        return {
            "ideal_skills": ideal_skills,
            "ideal_experience_years": experience_years,
            "ideal_education": education,
            "ideal_languages": languages,
            "industries": industries,
        }

    @classmethod
    def generate_from_text(cls, text: str, model_name: Optional[str] = None) -> Dict[str, Any]:
        if cls.USE_AI_MODEL and HF_AVAILABLE:
            return cls._generate_with_ai(text, model_name)
        return cls._generate_with_rules(text)

    @classmethod
    def _find_keywords(cls, text: str, words: List[str]) -> List[str]:
        found = []
        lower_text = text.lower()
        for word in words:
            pattern = rf"\b{re.escape(word.lower())}\b"
            if re.search(pattern, lower_text):
                found.append(word)
        return found

    @classmethod
    def _extract_years(cls, text: str) -> int:
        lower = text.lower()
        for pattern in cls.EXPERIENCE_PATTERNS:
            match = re.search(pattern, lower)
            if match and match.group("years"):
                try:
                    return int(match.group("years"))
                except ValueError:
                    continue

        if "senior" in lower or "lead" in lower:
            return 5
        if "mid-level" in lower or "mid level" in lower:
            return 3
        if "junior" in lower:
            return 1
        return 2

    @classmethod
    def _extract_education(cls, text: str) -> str:
        lower = text.lower()
        for key, label in cls.EDUCATION_LEVELS.items():
            if key in lower:
                return label
        return "Bachelor's degree or equivalent"

    @classmethod
    def _extract_industries(cls, text: str) -> List[str]:
        lower = text.lower()
        mapping = {
            "fintech": "Fintech",
            "health": "Healthcare",
            "ecommerce": "E-commerce",
            "retail": "Retail",
            "saas": "SaaS",
            "bank": "Banking",
            "insurance": "Insurance",
        }
        industries = [label for token, label in mapping.items() if token in lower]
        return industries

    @classmethod
    def _profile_level(cls, text: str, skill: str) -> str:
        lower = text.lower()
        if any(prefix in lower for prefix in ["senior", "expert", "advanced", "lead"]):
            return "Advanced"
        if any(prefix in lower for prefix in ["junior", "entry", "beginner"]):
            return "Beginner"
        return "Intermediate"
