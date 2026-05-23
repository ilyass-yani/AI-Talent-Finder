from pathlib import Path
import json
import re
from typing import List, Dict, Any


_BASE_DIR = Path(__file__).resolve().parents[2]
_DATA_DIR = _BASE_DIR / "ai_module" / "data"
_SKILLS_FILE = _DATA_DIR / "skills_dictionary.json"
_MAPPINGS_FILE = _DATA_DIR / "skill_mappings.json"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


_SKILLS_DICT = _load_json(_SKILLS_FILE)
_MAPPINGS = {k.lower(): v for k, v in _load_json(_MAPPINGS_FILE).items()}


def normalize_skill(skill: str) -> str:
    """Normalize a single skill string to a canonical form.

    Steps:
    - lower + strip
    - basic punctuation cleanup
    - map via `skill_mappings.json` if available
    - if present in `skills_dictionary.json`, return the canonical spelling
    - otherwise return title-cased fallback
    """
    if not skill:
        return ""
    s = skill.strip()
    s = s.replace("\n", " ")
    s = re.sub(r"[\(\)\[\]\\/\\]", " ", s)
    s = re.sub(r"[\.,;:]$", "", s)
    s_clean = re.sub(r"\s+", " ", s).strip()
    key = s_clean.lower()

    # direct mapping
    if key in _MAPPINGS:
        return _MAPPINGS[key]

    # search in skills dictionary (case-insensitive)
    for cat, items in _SKILLS_DICT.items():
        for item in items:
            if item.lower() == key:
                return item

    # fuzzy-ish normalization: common replacements
    replacements = {
        "\bjs\b": "JavaScript",
        "\bnodejs\b": "Node.js",
        "\breactjs\b": "React",
        "\bdevops\b": "DevOps",
    }
    for pattern, repl in replacements.items():
        if re.search(pattern, key):
            return repl

    # fallback: title case acronyms preserved
    if key.isupper() or len(key) <= 3:
        return s_clean.upper()
    return s_clean.title()


def normalize_skills_list(skills: List[str]) -> List[str]:
    seen = set()
    out = []
    for sk in skills:
        norm = normalize_skill(sk)
        if not norm:
            continue
        if norm not in seen:
            seen.add(norm)
            out.append(norm)
    return out


_YEARS_RE = re.compile(r"(\d{1,2})(?:\+)?\s*(?:years|ans|yrs|year)", re.IGNORECASE)


def parse_experience_years(text: str) -> int:
    if not text:
        return 0
    m = _YEARS_RE.search(text)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return 0
    return 0


def clean_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Return a cleaned/normalized copy of a candidate dict.

    Expected keys handled: `skills` (list or comma string), `experience`, `summary`.
    Adds `normalized_skills` and `experience_years` when possible.
    """
    out = dict(candidate)

    skills = out.get("skills") or out.get("competences") or []
    if isinstance(skills, str):
        # split on commas/semicolons/slash
        skills_list = re.split(r"[,;/\\]\s*", skills)
    elif isinstance(skills, (list, tuple)):
        skills_list = list(skills)
    else:
        skills_list = []

    out["normalized_skills"] = normalize_skills_list([s for s in skills_list if s])

    # experience years
    years = out.get("experience_years") or 0
    if not years:
        years = parse_experience_years(out.get("experience") or out.get("summary") or "")
    try:
        out["experience_years"] = int(years)
    except Exception:
        out["experience_years"] = years

    # dedupe and basic cleanup for education
    edu = out.get("education")
    if isinstance(edu, str):
        out["education"] = edu.strip()

    return out


__all__ = [
    "normalize_skill",
    "normalize_skills_list",
    "parse_experience_years",
    "clean_candidate",
]


if __name__ == "__main__":
    # quick smoke test
    sample = {
        "skills": "react.js, JS, python, ml, AWS, docker-compose",
        "experience": "5+ years in web development",
        "education": "Bachelor in Computer Science",
    }
    print(clean_candidate(sample))
