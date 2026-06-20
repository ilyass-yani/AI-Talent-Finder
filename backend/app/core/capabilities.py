from __future__ import annotations

import importlib.util
import logging
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_REQUIRED_FEATURES = [
    "cv_text_extraction",
    "semantic_matching",
]

_CAPABILITIES_CACHE: Optional[Dict[str, object]] = None


def _has_module(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _env_set(name: str) -> bool:
    return bool(os.getenv(name))


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _resolve_tesseract_path() -> Optional[str]:
    cmd = os.getenv("TESSERACT_CMD", "").strip()
    if cmd:
        found = shutil.which(cmd)
        return found
    return shutil.which("tesseract")


def _parse_required_features() -> List[str]:
    raw = os.getenv("AI_FEATURES_REQUIRED", "")
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _feature_status(
    required: Dict[str, bool],
    optional: Optional[Dict[str, bool]] = None,
    notes: str | None = None,
) -> Dict[str, object]:
    optional = optional or {}
    missing_required = [name for name, ok in required.items() if not ok]
    missing_optional = [name for name, ok in optional.items() if not ok]

    available = not missing_required
    status = "ok" if available else "missing"
    if available and missing_optional:
        status = "degraded"

    return {
        "available": available,
        "status": status,
        "required_missing": missing_required,
        "optional_missing": missing_optional,
        "notes": notes or "",
    }


def detect_capabilities() -> Dict[str, object]:
    use_ai_profile = _env_bool("USE_AI_PROFILE_GENERATOR", default=False)
    local_llm_enabled = bool(os.getenv("LOCAL_LLM_BASE_URL", "").strip())
    deps = {
        "fitz": _has_module("fitz"),
        "pdfplumber": _has_module("pdfplumber"),
        "pytesseract": _has_module("pytesseract"),
        "pillow": _has_module("PIL"),
        "transformers": _has_module("transformers"),
        "torch": _has_module("torch"),
        "sentence_transformers": _has_module("sentence_transformers"),
        "faiss": _has_module("faiss"),
        "numpy": _has_module("numpy"),
        "openpyxl": _has_module("openpyxl"),
        "reportlab": _has_module("reportlab"),
        "anthropic": _has_module("anthropic"),
    }

    tesseract_path = _resolve_tesseract_path()
    deps["tesseract_binary"] = bool(tesseract_path)

    api_keys = {
        "ANTHROPIC_API_KEY": _env_set("ANTHROPIC_API_KEY"),
        "OPENAI_API_KEY": _env_set("OPENAI_API_KEY"),
        "HUGGINGFACE_API_KEY": _env_set("HUGGINGFACE_API_KEY"),
        "HF_TOKEN_CHATBOT": _env_set("HF_TOKEN_CHATBOT"),
        "LOCAL_LLM_BASE_URL": _env_set("LOCAL_LLM_BASE_URL"),
    }

    features = {
        "cv_text_extraction": _feature_status(
            required={"fitz": deps["fitz"]},
            optional={"pdfplumber": deps["pdfplumber"]},
            notes="PyMuPDF is required for PDF text extraction.",
        ),
        "cv_ocr": _feature_status(
            required={
                "fitz": deps["fitz"],
                "pytesseract": deps["pytesseract"],
                "pillow": deps["pillow"],
                "tesseract_binary": deps["tesseract_binary"],
            },
            notes="OCR requires the Tesseract binary and PIL.",
        ),
        "ner_hf": _feature_status(
            required={"transformers": deps["transformers"], "torch": deps["torch"]},
            notes="If missing, regex-based NER is still available.",
        ),
        "semantic_matching": _feature_status(
            required={
                "sentence_transformers": deps["sentence_transformers"],
                "numpy": deps["numpy"],
                "torch": deps["torch"],
            },
            optional={"faiss": deps["faiss"]},
            notes="If missing, matching falls back to heuristic scoring.",
        ),
        "export": _feature_status(
            required={"openpyxl": deps["openpyxl"], "reportlab": deps["reportlab"]},
            notes="If missing, export endpoints are disabled.",
        ),
        "chat_llm": _feature_status(
            required={
                "llm_provider": (
                    api_keys["ANTHROPIC_API_KEY"]
                    or api_keys["HF_TOKEN_CHATBOT"]
                    or api_keys["LOCAL_LLM_BASE_URL"]
                )
            },
            notes="Disponible si un provider LLM est configure (Anthropic, HF Inference, ou LLM local). Sinon, reponses deterministes.",
        ),
        "profile_generator": _feature_status(
            required={"transformers": deps["transformers"], "torch": deps["torch"]}
            if use_ai_profile
            else {},
            notes="If disabled or missing deps, rule-based profile generation is used.",
        ),
    }

    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "strict": _env_set("AI_FEATURES_STRICT"),
        "required_features": _parse_required_features(),
        "dependencies": deps,
        "api_keys": api_keys,
        "flags": {
            "USE_AI_PROFILE_GENERATOR": use_ai_profile,
            "LOCAL_LLM_ENABLED": local_llm_enabled,
        },
        "features": features,
        "tesseract_path": tesseract_path,
        "tesseract_cmd": os.getenv("TESSERACT_CMD", "").strip() or None,
    }


def get_capabilities(force_refresh: bool = False) -> Dict[str, object]:
    global _CAPABILITIES_CACHE
    if _CAPABILITIES_CACHE is None or force_refresh:
        _CAPABILITIES_CACHE = detect_capabilities()
    return _CAPABILITIES_CACHE


def log_capabilities_summary(capabilities: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    cap = capabilities or get_capabilities()
    features = cap.get("features", {})

    status_counts = {"ok": 0, "degraded": 0, "missing": 0}
    for detail in features.values():
        status = str(detail.get("status", "missing"))
        status_counts[status] = status_counts.get(status, 0) + 1

    logger.info(
        "AI capabilities: ok=%s degraded=%s missing=%s",
        status_counts.get("ok", 0),
        status_counts.get("degraded", 0),
        status_counts.get("missing", 0),
    )

    for name, detail in sorted(features.items()):
        status = detail.get("status")
        if status == "ok":
            continue
        logger.warning(
            "AI capability %s: %s (required_missing=%s optional_missing=%s)",
            name,
            status,
            detail.get("required_missing"),
            detail.get("optional_missing"),
        )

    return cap


def assert_required_features(capabilities: Optional[Dict[str, object]] = None) -> None:
    cap = capabilities or get_capabilities()
    strict = bool(cap.get("strict"))
    if not strict:
        return

    required = list(cap.get("required_features") or [])
    if not required:
        required = list(_DEFAULT_REQUIRED_FEATURES)
        logger.warning(
            "AI_FEATURES_STRICT is enabled without AI_FEATURES_REQUIRED; using defaults: %s",
            ", ".join(required),
        )

    features = cap.get("features", {})
    missing = [name for name in required if not features.get(name, {}).get("available")]
    if not missing:
        return

    logger.error("Missing required AI features: %s", ", ".join(missing))
    raise RuntimeError(f"Missing required AI features: {', '.join(missing)}")