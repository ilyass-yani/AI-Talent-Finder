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

- `OPENAI_API_KEY` - OpenAI LLM/embeddings
- `HUGGINGFACE_API_KEY` - HF model access
- `TESSERACT_CMD` - path to Tesseract binary (if installed)
- `DATABASE_URL` - production DB connection string

## Fallback behaviors

- If `OPENAI_API_KEY` and HF keys are missing, the system will try local small models (if installed). If those are missing too features relying on LLM will be disabled and deterministic fallbacks used.
- If OCR binaries or libraries are missing, scanned PDFs will not be processed; extraction will rely on plain-text or heuristics and `raw_text` may be minimal. Recruiter visibility logic has been relaxed to still show candidates when some structured signals exist.
- If embeddings/FAISS are unavailable, semantic search/matching will fall back to bag-of-words or simpler TF-IDF approaches (see `backend/app/services/` for code branches).

## How to verify environment quickly

Run:

```bash
PYTHONPATH=. python3 backend/scripts/check_ia_environment.py
```

This prints which optional packages and environment variables are present and gives quick recommendations.

## Regenerating artifacts

See `backend/scripts/regenerate_ia_artifacts.sh` for the standard regeneration wrapper.

## Contact

If a specific host or API is used (Railway, Vercel), ensure secrets are set in the platform dashboard and redeploy to pick up changes.
