#!/usr/bin/env python
"""End-to-end smoke test of the pipeline.

Demonstrates a full CV ↔ Job evaluation without requiring trained models
or fine-tuned LLMs: uses the default embedding-based semantic matcher
and rule-based explainer.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from ai_pipeline.pipeline.orchestrator import MatchingOrchestrator, MatchingRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


SAMPLE_CV = """Nom : Slocks
Email : slocks@example.com
Localisation : Rabat

Formation :
- Ingénieur en Informatique, ESISA (2024)

Expérience professionnelle (3 ans):
- Développeur Full-Stack chez TechCorp, 2022 - aujourd'hui
  Missions : développement de plateformes web, conception d'API REST.

Compétences techniques :
- Python, FastAPI, PostgreSQL
- React, TypeScript, Next.js
- Docker, Git, AWS
- Machine Learning, PyTorch, HuggingFace Transformers

Langues :
- Français : Natif
- Anglais : C1
"""

SAMPLE_JOB = """Poste : LLM Engineer
Niveau : Confirmé
Localisation : Paris

Description :
Nous recherchons un(e) LLM Engineer pour rejoindre notre équipe.

Compétences requises :
- Python
- PyTorch
- HuggingFace Transformers
- LoRA
- LangChain

Compétences appréciées :
- RAG
- LlamaIndex
- vLLM

Expérience minimum : 2 ans
Formation : Ingénieur en informatique ou équivalent
"""


def main() -> int:
    logger.info("Building orchestrator (this will load embedding model on first run)…")
    orch = MatchingOrchestrator()

    req = MatchingRequest(
        cv_text=SAMPLE_CV,
        job_text=SAMPLE_JOB,
        job_required_skills={"python", "pytorch", "huggingface transformers", "lora", "langchain"},
        job_nice_to_have_skills={"rag", "llamaindex", "vllm"},
        job_min_years=2,
        job_min_edu_level=3,  # Ingénieur
        job_required_languages={"fr": "B2", "en": "B2"},
        job_location="Paris",
        remote_ok=True,
        use_llm=False,
    )

    logger.info("Running pipeline…")
    resp = orch.match(req)

    print(json.dumps(resp.to_dict(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
