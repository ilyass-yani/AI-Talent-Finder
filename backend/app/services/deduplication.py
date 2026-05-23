"""Deduplication and data cleaning service."""

from typing import List, Dict, Any
import hashlib


def compute_fingerprint(candidate: Dict[str, Any]) -> str:
    """Compute hash fingerprint for deduplication.

    Uses: email, phone, full_name + normalized_skills
    """
    email = (candidate.get("email") or "").lower().strip()
    phone = (candidate.get("phone") or "").replace(" ", "").replace("-", "")
    name = (candidate.get("full_name") or "").lower().strip()
    skills = sorted(candidate.get("normalized_skills", []))

    fingerprint_str = f"{email}|{phone}|{name}|{''.join(skills)}"
    return hashlib.md5(fingerprint_str.encode()).hexdigest()


def deduplicate_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate candidates by fingerprint.

    Returns list with duplicates removed (keeps first occurrence).
    """
    seen = {}
    result = []
    for candidate in candidates:
        fp = compute_fingerprint(candidate)
        if fp not in seen:
            seen[fp] = True
            result.append(candidate)
    return result


def merge_duplicate_candidates(
    candidates: List[Dict[str, Any]], group_threshold: float = 0.9
) -> List[Dict[str, Any]]:
    """Merge near-duplicate candidates with high similarity.

    Uses fingerprint similarity. If similarity >= threshold, merges entries
    (keeps more complete record).
    """
    # For now: simple dedupe by fingerprint
    # Can be extended to fuzzy matching
    return deduplicate_candidates(candidates)


__all__ = ["compute_fingerprint", "deduplicate_candidates", "merge_duplicate_candidates"]
