"""GLiNER-based CV entity extractor.

Uses urchade/gliner_multi-v2.1 as the principal NER layer for high-precision
extraction of person names, companies, schools and job titles.

Key design decisions
---------------------
* Singleton model: the 2.3 GB model is loaded once per process on the first
  call.  Subsequent calls are fast (~0.6 s per CV).
* Lazy loading: the model is NOT imported at module level.  It is loaded on
  the first call to GLiNERExtractor.extract() so the FastAPI startup is not
  slowed down and a missing / OOM situation does not crash the server.
* Graceful fallback: every failure path returns an empty dict so the caller
  (cv_extractor.py) can fall through to the regex extractor.
* ASCII apostrophes only -- never use curly/smart quotes in this file.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_MODEL_NAME: str = os.getenv("GLINER_MODEL", "urchade/gliner_multi-v2.1")

# Labels sent to GLiNER.  Adjust here if precision/recall balance shifts.
_LABELS: List[str] = ["person name", "company", "school", "job title"]

# Characters to strip from the ends of extracted spans.
_STRIP_CHARS = " \t\n.,;:()[]\"'"

# Patterns that indicate a span is NOT a person name.
_EMAIL_LIKE_RE = re.compile(r"@|\.(?:com|fr|net|org|io|be|de|es|uk|ca|eu)\b", re.IGNORECASE)

# Trailing date / location suffixes commonly attached to company spans.
_COMPANY_SUFFIX_RE = re.compile(
    r"\s*[\(\[\-]\s*(?:19|20)\d{2}.*$"
    r"|\s+\-\s+[A-Z][A-Za-z\s]{0,30}$",
    re.IGNORECASE,
)

_SECTION_HEADERS = frozenset({
    "contact", "langues", "languages", "competences", "skills",
    "experience", "experiences", "formation", "formations",
    "education", "profil", "profile", "interets", "certifications",
})


class GLiNERExtractor:
    """Singleton GLiNER extractor.  Instantiate once; reuse everywhere."""

    _model = None
    _load_attempted: bool = False
    _available: bool = False

    # ------------------------------------------------------------------
    # Singleton / lazy-load
    # ------------------------------------------------------------------

    @classmethod
    def _load_model(cls) -> bool:
        """Load the GLiNER model exactly once.  Thread-safe at Python GIL level."""
        if cls._load_attempted:
            return cls._available
        cls._load_attempted = True
        try:
            from gliner import GLiNER  # type: ignore  # noqa: PLC0415
            logger.info("Loading GLiNER model: %s ...", _MODEL_NAME)
            cls._model = GLiNER.from_pretrained(_MODEL_NAME)
            cls._available = True
            logger.info("GLiNER model loaded successfully.")
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "GLiNER not available (%s: %s) -- falling back to regex extractor.",
                type(exc).__name__,
                exc,
            )
            cls._available = False
        return cls._available

    @property
    def available(self) -> bool:
        return self.__class__._available

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, text: str) -> Dict:
        """Extract CV entities from *text* using GLiNER.

        Returns a dict with keys:
            full_name   : str | None
            companies   : List[str]
            education   : List[str]
            job_titles  : List[str]

        Returns {} on failure so the caller can use the fallback extractor.
        """
        if not self._load_model():
            return {}
        if not text or not text.strip():
            return {}

        try:
            # Truncate to ~6 000 chars (identity info is in the first half of the CV)
            truncated = text[:6000]
            raw_entities = self.__class__._model.predict_entities(
                truncated,
                _LABELS,
                threshold=0.45,
            )
            return self._clean_entities(raw_entities)
        except Exception as exc:  # noqa: BLE001
            logger.warning("GLiNER extraction error: %s: %s", type(exc).__name__, exc)
            return {}

    # ------------------------------------------------------------------
    # Internal cleaning
    # ------------------------------------------------------------------

    def _clean_entities(self, entities: List[Dict]) -> Dict:
        """Group and clean the raw GLiNER entity spans."""
        grouped: Dict[str, List[str]] = {
            "person name": [],
            "company": [],
            "school": [],
            "job title": [],
        }
        for ent in entities:
            label = ent.get("label", "")
            span = (ent.get("text") or "").strip(_STRIP_CHARS)
            if label in grouped and span:
                grouped[label].append(span)

        full_name = self._best_person_name(grouped["person name"])
        companies = self._clean_company_list(grouped["company"], grouped["school"])
        education = self._dedup(grouped["school"])
        job_titles = self._dedup(grouped["job title"])

        return {
            "full_name": full_name,
            "companies": companies[:8],
            "education": education[:6],
            "job_titles": job_titles[:5],
        }

    # --- helpers ---------------------------------------------------------

    def _best_person_name(self, candidates: List[str]) -> Optional[str]:
        """Return the most plausible person name from GLiNER person-name spans."""
        valid = []
        for name in candidates:
            name = name.strip(_STRIP_CHARS)
            if not name:
                continue
            # Reject email-like strings
            if _EMAIL_LIKE_RE.search(name):
                continue
            # Reject URL patterns
            if "http" in name.lower() or "//" in name:
                continue
            # Reject section headers
            if name.lower() in _SECTION_HEADERS:
                continue
            words = [w for w in name.split() if w]
            # Must be between 1 and 5 words
            if not 1 <= len(words) <= 5:
                continue
            # At least one word must start with a letter
            if not any(w[0].isalpha() for w in words):
                continue
            valid.append(name)

        if not valid:
            return None
        # Prefer the longest plausible name (more words = more specific)
        valid.sort(key=lambda n: -len(n.split()))
        return valid[0]

    def _clean_company_list(
        self, companies: List[str], schools: List[str]
    ) -> List[str]:
        """Clean and deduplicate companies; remove school overlaps."""
        school_keys = {self._normalize_key(s) for s in schools}
        seen = set()
        result = []
        for raw in companies:
            # Strip trailing date/location suffixes
            cleaned = _COMPANY_SUFFIX_RE.sub("", raw).strip(_STRIP_CHARS)
            if not cleaned or len(cleaned) < 2:
                continue
            # Skip if it looks like a school
            if self._normalize_key(cleaned) in school_keys:
                continue
            key = self._normalize_key(cleaned)
            if key in seen:
                continue
            seen.add(key)
            result.append(cleaned)
        return result

    def _dedup(self, items: List[str]) -> List[str]:
        seen = set()
        result = []
        for item in items:
            cleaned = item.strip(_STRIP_CHARS)
            if not cleaned:
                continue
            key = self._normalize_key(cleaned)
            if key in seen:
                continue
            seen.add(key)
            result.append(cleaned)
        return result

    @staticmethod
    def _normalize_key(text: str) -> str:
        """Lowercase, strip accents (via ASCII encoding), collapse spaces."""
        import unicodedata
        nfkd = unicodedata.normalize("NFKD", text)
        ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
        return re.sub(r"\s+", " ", ascii_only.lower().strip())


# ---------------------------------------------------------------------------
# Module-level singleton accessor
# ---------------------------------------------------------------------------

_instance: Optional[GLiNERExtractor] = None


def get_gliner_extractor() -> GLiNERExtractor:
    """Return the shared GLiNERExtractor instance (created once per process)."""
    global _instance
    if _instance is None:
        _instance = GLiNERExtractor()
    return _instance
