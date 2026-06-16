"""Runtime configuration store for the AI matching pipeline.

Backs the admin use case "Configurer les paramètres du pipeline IA". The
configuration is persisted in the ``system_settings`` table (key/value, JSON
encoded) and mirrored in a module-level cache so the hot scoring path does not
hit the database on every call.

Reads always succeed even without a database: if nothing has been configured,
the built-in defaults (identical to the historical hard-coded values) are used,
so existing behaviour is unchanged until an admin overrides a parameter.
"""

from __future__ import annotations

import json
import logging
from typing import Dict

logger = logging.getLogger(__name__)

PIPELINE_CONFIG_KEY = "pipeline_config"

# Defaults mirror the original hard-coded weights/thresholds in
# app/services/scoring.py so default behaviour is preserved.
DEFAULT_PIPELINE_CONFIG: Dict[str, float] = {
    "skill_weight": 0.50,
    "semantic_weight": 0.20,
    "experience_weight": 0.15,
    "education_weight": 0.10,
    "perfect_match_bonus": 0.05,
    "accept_threshold": 0.80,
    "review_threshold": 0.50,
}

# Bounds used to validate incoming admin updates.
_WEIGHT_KEYS = {
    "skill_weight",
    "semantic_weight",
    "experience_weight",
    "education_weight",
    "perfect_match_bonus",
}
_THRESHOLD_KEYS = {"accept_threshold", "review_threshold"}

# Module-level cache. Populated lazily / on startup; defaults until then.
_runtime_config: Dict[str, float] = dict(DEFAULT_PIPELINE_CONFIG)
_loaded_from_db = False


def get_runtime_pipeline_config() -> Dict[str, float]:
    """Return the current pipeline config from the in-memory cache (no DB hit)."""
    return dict(_runtime_config)


def load_pipeline_config(db) -> Dict[str, float]:
    """Load config from the database into the cache, merging over defaults."""
    global _runtime_config, _loaded_from_db
    try:
        from app.models.models import SystemSetting

        row = (
            db.query(SystemSetting)
            .filter(SystemSetting.key == PIPELINE_CONFIG_KEY)
            .first()
        )
        merged = dict(DEFAULT_PIPELINE_CONFIG)
        if row and row.value:
            stored = json.loads(row.value)
            merged.update({k: v for k, v in stored.items() if k in DEFAULT_PIPELINE_CONFIG})
        _runtime_config = merged
        _loaded_from_db = True
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("Could not load pipeline config from DB: %s", exc)
    return dict(_runtime_config)


def validate_pipeline_config(partial: Dict[str, float]) -> Dict[str, str]:
    """Validate a partial config update. Returns a dict of field -> error message."""
    errors: Dict[str, str] = {}
    for key, value in partial.items():
        if key not in DEFAULT_PIPELINE_CONFIG:
            errors[key] = "Paramètre inconnu"
            continue
        try:
            value = float(value)
        except (TypeError, ValueError):
            errors[key] = "Doit être un nombre"
            continue
        if not (0.0 <= value <= 1.0):
            errors[key] = "Doit être compris entre 0 et 1"

    # Cross-field rule: thresholds must keep accept >= review.
    merged = {**_runtime_config, **{k: float(v) for k, v in partial.items() if k in DEFAULT_PIPELINE_CONFIG}}
    if merged["accept_threshold"] < merged["review_threshold"]:
        errors["accept_threshold"] = "Le seuil d'acceptation doit être >= au seuil de revue"
    return errors


def update_pipeline_config(db, partial: Dict[str, float], updated_by: int | None = None) -> Dict[str, float]:
    """Persist a partial config update and refresh the cache.

    Caller is responsible for having validated ``partial`` first.
    """
    global _runtime_config
    from app.models.models import SystemSetting

    merged = dict(_runtime_config)
    merged.update({k: float(v) for k, v in partial.items() if k in DEFAULT_PIPELINE_CONFIG})

    row = (
        db.query(SystemSetting)
        .filter(SystemSetting.key == PIPELINE_CONFIG_KEY)
        .first()
    )
    if row is None:
        row = SystemSetting(key=PIPELINE_CONFIG_KEY)
        db.add(row)
    row.value = json.dumps(merged)
    row.updated_by = updated_by
    db.commit()

    _runtime_config = merged
    return dict(_runtime_config)


def reset_pipeline_config(db, updated_by: int | None = None) -> Dict[str, float]:
    """Reset config back to defaults (persisted)."""
    return update_pipeline_config(db, dict(DEFAULT_PIPELINE_CONFIG), updated_by=updated_by)
