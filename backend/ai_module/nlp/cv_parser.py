"""HF-based CV parser using token classification NER with safe fallbacks.

This parser is designed as a lightweight modern replacement layer that can be
used before legacy extractors. It focuses on high-signal entities and keeps the
output schema close to the existing extraction pipeline.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

try:
    from transformers import pipeline

    HF_NER_AVAILABLE = True
except Exception:
    HF_NER_AVAILABLE = False


class HFResumeNERParser:
    """NER parser powered by Hugging Face token classification models.

    Default model can be overridden with env var `HF_CV_NER_MODEL`.
    Recommended values:
    - dslim/bert-base-NER
    - Davlan/bert-base-multilingual-cased-ner-hrl
    """

    EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")

    def __init__(self, model_name: str = "dslim/bert-base-NER") -> None:
        self.model_name = model_name
        self.ner = None
        if HF_NER_AVAILABLE:
            try:
                self.ner = pipeline(
                    "ner",
                    model=self.model_name,
                    aggregation_strategy="simple",
                )
            except Exception:
                self.ner = None

    @property
    def available(self) -> bool:
        return self.ner is not None

    def extract_structured_profile(self, text: str) -> Tuple[Dict, float]:
        """Extract minimal structured profile and quality score [0..100]."""
        if not text:
            return {}, 0.0

        entities = self._extract_entities(text)

        emails = self.EMAIL_RE.findall(text)
        phones = [p.strip() for p in self.PHONE_RE.findall(text)]

        person_names = entities.get("PER", [])
        organizations = entities.get("ORG", [])
        locations = entities.get("LOC", [])
        misc = entities.get("MISC", [])

        profile = {
            "full_name": person_names[0] if person_names else None,
            "name": person_names[0] if person_names else None,
            "emails": list(dict.fromkeys(emails)),
            "email": emails[0] if emails else None,
            "phones": list(dict.fromkeys(phones)),
            "phone": phones[0] if phones else None,
            "companies": list(dict.fromkeys(organizations[:10])),
            "job_titles": list(dict.fromkeys(misc[:10])),
            "education": [],
            "skills": [],
            "locations": list(dict.fromkeys(locations[:10])),
            "extraction_metadata": {
                "model": self.model_name,
                "total_entities": sum(len(v) for v in entities.values()),
                "entity_groups": {k: len(v) for k, v in entities.items()},
            },
        }

        quality = 0.0
        if profile["full_name"]:
            quality += 20
        if profile["email"]:
            quality += 20
        if profile["phone"]:
            quality += 10
        if profile["companies"]:
            quality += 20
        if profile["job_titles"]:
            quality += 15
        if profile["locations"]:
            quality += 10
        if profile["extraction_metadata"]["total_entities"] > 0:
            quality += 5

        return profile, min(100.0, quality)

    def close(self) -> None:
        """Release the underlying Hugging Face pipeline."""
        self.ner = None

    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        groups: Dict[str, List[str]] = {"PER": [], "ORG": [], "LOC": [], "MISC": []}
        if not self.ner:
            return groups

        try:
            # Keep runtime bounded on long CVs.
            chunks = [text[i : i + 1600] for i in range(0, min(len(text), 9600), 1600)]
            for chunk in chunks:
                for entity in self.ner(chunk):
                    label = str(entity.get("entity_group", "MISC"))
                    word = str(entity.get("word", "")).strip()
                    score = float(entity.get("score", 0.0))
                    if not word or score < 0.60:
                        continue
                    if label not in groups:
                        label = "MISC"
                    if word not in groups[label]:
                        groups[label].append(word)
        except Exception:
            return groups

        return groups
