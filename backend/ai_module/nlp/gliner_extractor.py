"""GLiNER-based CV entity extractor.

Uses urchade/gliner_multi-v2.1 as the principal NER layer for high-precision
extraction of person names, companies, schools, job titles and interests.

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

Post-processing guarantees
---------------------------
* BERT tokenizer artifacts (spans starting with '##') are discarded.
* Spans with fewer than 3 alphabetic characters are discarded (noise).
* Single non-acronym words of 3 or fewer total characters are discarded.
* Company spans that match school/university keywords are moved to education.
* Interests that match the candidate name or a CV section header are removed.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_MODEL_NAME: str = os.getenv("GLINER_MODEL", "urchade/gliner_multi-v2.1")

# Labels sent to GLiNER.  Zero-shot model supports any labels.
_LABELS: List[str] = [
    "person name",
    "company",
    "school",
    "job title",
    "interest",
]

# Characters to strip from the ends of extracted spans.
_STRIP_CHARS = " \t\n.,;:()[]\"'"

# Patterns that indicate a span is NOT a person name.
_EMAIL_LIKE_RE = re.compile(
    r"@|\.(?:com|fr|net|org|io|be|de|es|uk|ca|eu)\b", re.IGNORECASE
)

# Trailing date / location suffixes commonly attached to company spans.
_COMPANY_SUFFIX_RE = re.compile(
    r"\s*[\(\[\-]\s*(?:19|20)\d{2}.*$"
    r"|\s+\-\s+[A-Z][A-Za-z\s]{0,30}$",
    re.IGNORECASE,
)

# Normalized CV section header names.
# Used to reject section titles that leak into entity lists.
# All values must be in their _normalize_key() form (lowercase, no accents,
# no extra spaces) so comparisons are accent-agnostic.
_SECTION_HEADERS: frozenset = frozenset({
    "contact",
    "langues", "languages",
    "competences", "competence", "skills",
    "experience", "experiences",
    "formation", "formations",
    "education",
    "profil", "profile",
    "interets", "interet",
    "centres d interet", "centres d interets",
    "certifications", "certification",
    "loisirs", "activites", "activite",
    "intitule", "intitule du poste", "intitule du stage",
    "objectif", "objectifs",
    "references", "recommandations",
    "publications",
    "projets", "projet", "realisations",
    "informations", "informations personnelles",
    "qualites", "atouts", "valeurs",
    "stage", "stages", "alternance",
})

# Normalized keywords that identify school / university entries.
# Checked as WORD tokens (not substrings) against the normalized span to
# avoid false positives (e.g. a company name that happens to contain 'school').
_SCHOOL_KEYWORDS: frozenset = frozenset({
    "universite",
    "ecole", "ecoles",
    "institut", "institute",
    "school",
    "faculte", "facultes",
    "iut", "bts", "esup",
    "lycee", "lycees",
    "college",
    "academy", "academie",
    "insa", "supinfo", "epitech",
})


# ---------------------------------------------------------------------------
# Module-level span-level filters (no class state needed)
# ---------------------------------------------------------------------------

def _is_noise_span(span: str) -> bool:
    """Return True if *span* is an artifact or too-short fragment to keep.

    Filtered cases:
    - BERT wordpiece tokenizer artifacts: prefix '##' (e.g. '##cence Pro ...')
    - Fewer than 3 alphabetic characters (e.g. 'Li' = 2 alpha)
    - Single non-acronym word of 3 or fewer total chars (e.g. 'Esp')
      All-uppercase 2-3 char words are valid acronyms (IBM, SAP) and pass.
    """
    if span.startswith("##"):
        return True
    alpha_count = sum(1 for c in span if c.isalpha())
    if alpha_count < 3:
        return True
    # Single short word: keep only if it is a pure uppercase acronym
    words = span.split()
    if len(words) == 1 and len(span) <= 3 and not span.isupper():
        return True
    return False


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class GLiNERExtractor:
    """Singleton GLiNER extractor.  Instantiate once; reuse everywhere."""

    _model = None
    _load_attempted: bool = False
    _available: bool = False

    # ------------------------------------------------------------------
    # Singleton / lazy-load (do not touch this block per project rules)
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
            full_name  : str | None
            companies  : List[str]
            education  : List[str]
            job_titles : List[str]
            interests  : List[str]

        Returns {} on failure so the caller can fall through to the regex
        extractor.
        """
        if not self._load_model():
            return {}
        if not text or not text.strip():
            return {}

        try:
            # Truncate to ~6 000 chars (identity info is in the first half of
            # the CV; processing the full text risks OOM on long documents).
            truncated = text[:6000]
            raw_entities = self.__class__._model.predict_entities(
                truncated,
                _LABELS,
                threshold=0.45,
            )
            return self._clean_entities(raw_entities)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "GLiNER extraction error: %s: %s", type(exc).__name__, exc
            )
            return {}

    # ------------------------------------------------------------------
    # Post-processing / cleaning  (the only section touched by this fix)
    # ------------------------------------------------------------------

    def _clean_entities(self, entities: List[Dict]) -> Dict:
        """Group, filter and clean the raw GLiNER entity spans.

        Pipeline:
        1. Discard noise spans (## artifacts, < 3 alpha chars, short non-acronyms).
        2. Detect company spans that look like schools and redirect them to the
           education pool.
        3. Deduplicate and cap each list.
        4. Filter interests: remove the candidate name and CV section headers.
        """
        grouped: Dict[str, List[str]] = {
            "person name": [],
            "company": [],
            "school": [],
            "job title": [],
            "interest": [],
        }

        # --- Step 1: group spans, discarding noise immediately ---------------
        for ent in entities:
            label = ent.get("label", "")
            raw = (ent.get("text") or "").strip(_STRIP_CHARS)
            if label not in grouped or not raw:
                continue
            if _is_noise_span(raw):
                logger.debug("GLiNER noise filtered: %r (%s)", raw, label)
                continue
            grouped[label].append(raw)

        # --- Step 2: separate school-like entries from company list ----------
        extra_schools: List[str] = []
        real_companies: List[str] = []
        for span in grouped["company"]:
            if self._is_school_like(span):
                extra_schools.append(span)
            else:
                real_companies.append(span)

        # Combined school pool: GLiNER-labeled schools + redirected companies
        all_schools = grouped["school"] + extra_schools

        # --- Step 3: build clean field lists ---------------------------------
        full_name = self._best_person_name(grouped["person name"])
        companies = self._clean_company_list(real_companies, all_schools)
        education = self._dedup(all_schools)
        job_titles = self._dedup(grouped["job title"])
        interests = self._clean_interests(grouped["interest"], full_name)

        return {
            "full_name": full_name,
            "companies": companies[:8],
            "education": education[:6],
            "job_titles": job_titles[:5],
            "interests": interests[:8],
        }

    # --- helpers ---------------------------------------------------------

    def _best_person_name(self, candidates: List[str]) -> Optional[str]:
        """Return the most plausible person name from GLiNER person-name spans."""
        valid = []
        for name in candidates:
            name = name.strip(_STRIP_CHARS)
            if not name:
                continue
            if _EMAIL_LIKE_RE.search(name):
                continue
            if "http" in name.lower() or "//" in name:
                continue
            norm = self._normalize_key(name)
            if norm in _SECTION_HEADERS:
                continue
            words = [w for w in name.split() if w]
            if not 1 <= len(words) <= 5:
                continue
            if not any(w[0].isalpha() for w in words):
                continue
            valid.append(name)

        if not valid:
            return None
        # Prefer multi-word names (more complete) over single tokens.
        valid.sort(key=lambda n: -len(n.split()))
        return valid[0]

    def _clean_company_list(
        self, companies: List[str], schools: List[str]
    ) -> List[str]:
        """Clean and deduplicate companies.

        A company span is rejected when:
        - It still looks like a school (cross-check after redirect pass).
        - Its normalized key duplicates an already-kept entry.
        """
        school_keys = {self._normalize_key(s) for s in schools}
        seen: set = set()
        result: List[str] = []
        for raw in companies:
            cleaned = _COMPANY_SUFFIX_RE.sub("", raw).strip(_STRIP_CHARS)
            if not cleaned:
                continue
            if self._is_school_like(cleaned):
                continue
            key = self._normalize_key(cleaned)
            if key in school_keys or key in seen:
                continue
            seen.add(key)
            result.append(cleaned)
        return result

    def _clean_interests(
        self, interests: List[str], full_name: Optional[str]
    ) -> List[str]:
        """Filter interests: reject the candidate name, section headers, and
        form-label patterns (strings containing '/' or '|').
        """
        name_key = self._normalize_key(full_name) if full_name else None
        seen: set = set()
        result: List[str] = []
        for raw in interests:
            span = raw.strip(_STRIP_CHARS)
            if not span:
                continue
            # Reject form labels (e.g. 'INTITULE DU POSTE / STAGE')
            if "/" in span or "|" in span:
                continue
            key = self._normalize_key(span)
            # Reject if it matches the candidate name
            if name_key and key == name_key:
                continue
            # Reject exact section header matches
            if key in _SECTION_HEADERS:
                continue
            # Reject if any word token is an unambiguous section header
            tokens = set(re.split(r"\W+", key))
            tokens.discard("")
            if tokens & _SECTION_HEADERS:
                continue
            if key in seen:
                continue
            seen.add(key)
            result.append(span)
        return result

    def _dedup(self, items: List[str]) -> List[str]:
        """Deduplicate a list of spans preserving first-seen order."""
        seen: set = set()
        result: List[str] = []
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
    def _is_school_like(span: str) -> bool:
        """Return True if *span* looks like a school / university entry.

        Detection: check whether any word token in the normalized span matches
        a known education keyword.  Word-based (not substring) to avoid false
        positives from company names that contain those letters incidentally.
        """
        norm = GLiNERExtractor._normalize_key(span)
        tokens = set(re.split(r"\W+", norm))
        tokens.discard("")
        return bool(tokens & _SCHOOL_KEYWORDS)

    @staticmethod
    def _normalize_key(text: str) -> str:
        """Lowercase and accent-strip *text*, collapse internal whitespace."""
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
