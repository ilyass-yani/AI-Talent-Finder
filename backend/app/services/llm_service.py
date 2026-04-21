"""
Centralized Anthropic Claude wrapper.

A single client + model are configured from `app.core.config.settings` so the
chatbot, profile generator, and any future LLM consumer agree on credentials
and model name. Callers never instantiate `Anthropic()` directly.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Iterable, List, Optional

from anthropic import Anthropic, APIError

from app.core.config import settings


logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """One turn in a Claude conversation."""
    role: str  # "user" | "assistant"
    content: str


class LLMUnavailable(RuntimeError):
    """Raised when no API key is configured or the provider is unreachable."""


class LLMService:
    """Thin wrapper around the Anthropic SDK."""

    DEFAULT_SYSTEM_PROMPT = (
        "Tu es un assistant expert en recrutement pour AI Talent Finder. "
        "Tes réponses doivent être concises, factuelles et orientées action. "
        "Utilise des listes à puces ou des tableaux pour comparer des candidats. "
        "Si on te demande un objet structuré, réponds uniquement avec un JSON valide."
    )

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> None:
        self.api_key = api_key or settings.effective_llm_api_key
        self.model = model or settings.llm_model
        self.max_tokens = max_tokens

        if not self.api_key:
            self._client: Optional[Anthropic] = None
            logger.warning("LLMService initialized without API key — calls will raise LLMUnavailable.")
        else:
            self._client = Anthropic(api_key=self.api_key)

    @property
    def is_ready(self) -> bool:
        return self._client is not None

    def complete(
        self,
        messages: Iterable[ChatMessage],
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.4,
    ) -> str:
        """Send a message list to Claude and return the assistant text."""
        if self._client is None:
            raise LLMUnavailable("LLM_API_KEY (or ANTHROPIC_API_KEY) is not configured.")

        payload = [{"role": m.role, "content": m.content} for m in messages]

        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature,
                system=system or self.DEFAULT_SYSTEM_PROMPT,
                messages=payload,
            )
        except APIError as exc:
            logger.exception("Anthropic API error: %s", exc)
            raise LLMUnavailable(f"Anthropic call failed: {exc}") from exc

        # Claude returns a list of content blocks; we only consume text.
        parts: List[str] = []
        for block in response.content or []:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return "\n".join(parts).strip()

    def complete_text(self, prompt: str, system: Optional[str] = None) -> str:
        """Single-turn convenience: send one user prompt, get one reply."""
        return self.complete([ChatMessage(role="user", content=prompt)], system=system)

    def complete_json(self, prompt: str, system: Optional[str] = None) -> dict:
        """Ask the model for JSON and parse it. Strips ```json fences if present."""
        raw = self.complete_text(prompt, system=system)
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        snippet = match.group(0) if match else raw
        try:
            return json.loads(snippet)
        except json.JSONDecodeError as exc:
            logger.warning("LLM returned non-JSON payload (%s); raw=%s", exc, raw[:200])
            return {"_raw": raw, "_error": str(exc)}


_default_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Module-level singleton — instantiated lazily so missing key only warns once."""
    global _default_service
    if _default_service is None:
        _default_service = LLMService()
    return _default_service
