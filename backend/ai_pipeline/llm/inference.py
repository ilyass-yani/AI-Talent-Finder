"""LLM inference for CV ↔ Job matching using a fine-tuned LoRA adapter.

This module wraps a (Q)LoRA-fine-tuned causal language model and exposes a
high-level :meth:`MatchingLLM.score` API that returns a structured matching
result (score, decision, matched/missing skills, rationale).

The base model is loaded once (optionally in 4-bit via bitsandbytes) and the
LoRA adapter is attached on top.  Generation is deterministic by default
(``temperature=0``) to make scoring reproducible.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import LLMConfig
from .prompts import (
    MATCHING_SYSTEM_PROMPT,
    build_matching_prompt,
    parse_matching_response,
)

logger = logging.getLogger(__name__)


@dataclass
class InferenceResult:
    """Structured output of a single CV↔Job inference call."""

    score: float
    decision: str
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    rationale: str = ""
    raw_output: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "decision": self.decision,
            "matched_skills": self.matched_skills,
            "missing_skills": self.missing_skills,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "rationale": self.rationale,
        }


class MatchingLLM:
    """Wrapper around a fine-tuned causal LM for CV/Job matching."""

    def __init__(
        self,
        config: LLMConfig,
        adapter_path: Optional[str] = None,
        load_in_4bit: bool = True,
        device_map: str = "auto",
    ) -> None:
        self.config = config
        self.adapter_path = adapter_path
        self.load_in_4bit = load_in_4bit
        self.device_map = device_map
        self._model = None
        self._tokenizer = None

    # ------------------------------------------------------------------ #
    # Lazy loading
    # ------------------------------------------------------------------ #
    def _load(self) -> None:
        if self._model is not None:
            return

        # Imports are deferred so the rest of the package stays importable
        # in environments without torch/transformers installed.
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        logger.info("Loading base model: %s", self.config.base_model)

        quant_config = None
        if self.load_in_4bit:
            try:
                from transformers import BitsAndBytesConfig

                quant_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_compute_dtype=torch.bfloat16,
                )
            except Exception:  # pragma: no cover - bitsandbytes may be absent
                logger.warning("bitsandbytes unavailable, falling back to fp16/bf16.")
                quant_config = None

        self._tokenizer = AutoTokenizer.from_pretrained(
            self.config.base_model, trust_remote_code=True
        )
        if self._tokenizer.pad_token is None:
            self._tokenizer.pad_token = self._tokenizer.eos_token

        dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
        self._model = AutoModelForCausalLM.from_pretrained(
            self.config.base_model,
            quantization_config=quant_config,
            device_map=self.device_map,
            torch_dtype=dtype,
            trust_remote_code=True,
        )

        if self.adapter_path:
            logger.info("Attaching LoRA adapter from %s", self.adapter_path)
            from peft import PeftModel

            self._model = PeftModel.from_pretrained(self._model, self.adapter_path)

        self._model.eval()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def score(
        self,
        cv_text: str,
        job_text: str,
        max_new_tokens: int = 512,
        temperature: float = 0.0,
    ) -> InferenceResult:
        """Score a single (CV, Job) pair and return structured output."""
        self._load()
        import torch

        user_prompt = build_matching_prompt(cv_text=cv_text, job_text=job_text)

        # Use the model's chat template when available (Qwen/Mistral/Llama all
        # ship one), otherwise fall back to a simple concatenation.
        if hasattr(self._tokenizer, "apply_chat_template"):
            messages = [
                {"role": "system", "content": MATCHING_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
            input_text = self._tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        else:
            input_text = f"{MATCHING_SYSTEM_PROMPT}\n\n{user_prompt}\n\nAssistant:"

        inputs = self._tokenizer(
            input_text,
            return_tensors="pt",
            truncation=True,
            max_length=self.config.max_length,
        ).to(self._model.device)

        gen_kwargs = {
            "max_new_tokens": max_new_tokens,
            "do_sample": temperature > 0.0,
            "pad_token_id": self._tokenizer.pad_token_id,
        }
        if temperature > 0.0:
            gen_kwargs["temperature"] = temperature
            gen_kwargs["top_p"] = 0.9

        with torch.no_grad():
            output_ids = self._model.generate(**inputs, **gen_kwargs)

        generated = output_ids[0, inputs["input_ids"].shape[1] :]
        raw_output = self._tokenizer.decode(generated, skip_special_tokens=True)

        parsed = parse_matching_response(raw_output)
        return InferenceResult(
            score=float(parsed.get("score", 0.0)),
            decision=str(parsed.get("decision", "à revoir")),
            matched_skills=list(parsed.get("matched_skills", [])),
            missing_skills=list(parsed.get("missing_skills", [])),
            strengths=list(parsed.get("strengths", [])),
            weaknesses=list(parsed.get("weaknesses", [])),
            rationale=str(parsed.get("rationale", "")),
            raw_output=raw_output,
        )

    def batch_score(
        self,
        pairs: List[Dict[str, str]],
        max_new_tokens: int = 512,
        temperature: float = 0.0,
    ) -> List[InferenceResult]:
        """Score a list of ``{"cv": str, "job": str}`` dicts sequentially."""
        return [
            self.score(p["cv"], p["job"], max_new_tokens, temperature) for p in pairs
        ]

    def unload(self) -> None:
        """Free GPU memory."""
        import gc

        self._model = None
        self._tokenizer = None
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
