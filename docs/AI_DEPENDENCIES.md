# AI Dependencies and Fallback Modes

This document lists optional AI dependencies, environment variables and how the application falls back when they are unavailable.

## Optional dependencies

- `transformers` - local LLM or HF models
- `sentence_transformers` and `faiss` - embeddings and vector DB
- `pytesseract` + Tesseract binary - OCR for scanned PDFs
- `tika` - alternate PDF/text extraction
- `torch` - model runtime for local inference

Install optional groups:

- `pip install -r backend/requirements-faiss-optional.txt`
- `pip install -r backend/requirements-train.txt`

## Important environment variables

- `ANTHROPIC_API_KEY` - recruiter chatbot LLM (if set, chat uses Anthropic API)
- `OPENAI_API_KEY` - OpenAI LLM/embeddings
- `HUGGINGFACE_API_KEY` - HF model access
- `TESSERACT_CMD` - path to Tesseract binary (if installed)
- `DATABASE_URL` - production DB connection string
- `AI_FEATURES_STRICT` - fail startup if required AI features are missing
- `AI_FEATURES_REQUIRED` - comma-separated list of required AI features (used with strict mode)
- `USE_AI_PROFILE_GENERATOR` - enable HF profile generator (default: true)
- `HF_CV_NER_MODEL` - override HF NER model for CV parsing
- `HF_PROFILE_MODEL` - override HF model for profile generation
- `SKILL_NORMALIZATION_THRESHOLD` - embedding similarity threshold for skill normalization
- `LOCAL_LLM_BASE_URL` - base URL for a local OpenAI-compatible LLM server
- `LOCAL_LLM_MODEL` - model name sent to the local LLM server (optional)
- `LOCAL_LLM_MAX_TOKENS` - max tokens for local LLM responses (optional)
- `LOCAL_LLM_TIMEOUT` - timeout in seconds for local LLM calls (optional)

Known feature keys for `AI_FEATURES_REQUIRED`:

- `cv_text_extraction`
- `cv_ocr`
- `ner_hf`
- `semantic_matching`
- `export`
- `chat_llm`
- `profile_generator`

## Fallback behaviors

- If `OPENAI_API_KEY` and HF keys are missing, the system will try local small models (if installed). If those are missing too features relying on LLM will be disabled and deterministic fallbacks used.
- If OCR binaries or libraries are missing, scanned PDFs will not be processed; extraction will rely on plain-text or heuristics and `raw_text` may be minimal. Recruiter visibility logic has been relaxed to still show candidates when some structured signals exist.
- If embeddings/FAISS are unavailable, semantic search/matching will fall back to bag-of-words or simpler TF-IDF approaches (see `backend/app/services/` for code branches).
- If `USE_AI_PROFILE_GENERATOR=false` or HF model deps are missing, profile generation falls back to rule-based extraction.
- If `LOCAL_LLM_BASE_URL` is set, the chatbot can use a local LLM when Anthropic is unavailable.

For a full fallback matrix, see `backend/IA_FALLBACK_MODES.md`.

## How to verify environment quickly

Run:

```bash
PYTHONPATH=. python3 backend/scripts/check_ia_environment.py
```

This prints which optional packages and environment variables are present and gives quick recommendations.

## Health endpoints

- `GET /health` basic liveness endpoint
- `GET /health/deps` AI capability summary (features, missing deps, keys)

## Regenerating artifacts

See `backend/scripts/regenerate_ia_artifacts.sh` or the cross-platform `backend/scripts/regenerate_ia_artifacts.py` wrapper.

## Contact

If a specific host or API is used (Railway, Vercel), ensure secrets are set in the platform dashboard and redeploy to pick up changes.
