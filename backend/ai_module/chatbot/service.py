"""
Chatbot service — recruiter assistant powered by Anthropic Claude.

All API calls go through `app.services.llm_service.LLMService`, which reads
credentials and the model name from `settings`. This keeps the model in sync
across the application and avoids the older hardcoded `claude-3-5-sonnet`.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.services.llm_service import ChatMessage, LLMService, LLMUnavailable


logger = logging.getLogger(__name__)


class ChatbotService:
    """
    Conversational layer with built-in recruiter prompts.

    Handles four intents:
    1. Explanation — "Why does this candidate have score X?"
    2. Comparison — "Compare these candidates"
    3. Exploration — "Find candidates with skill X"
    4. Adjustment  — "Change weight of skill X"
    """

    SYSTEM_PROMPT = (
        "Tu es un consultant expert en recrutement pour AI Talent Finder. "
        "Aide les recruteurs à prendre des décisions éclairées en :"
        "\n1. Expliquant les scores et les résultats de matching"
        "\n2. Comparant les profils des candidats"
        "\n3. Aidant à explorer la base de candidats"
        "\n4. Suggérant des ajustements de critères"
        "\n\nReste professionnel, concis et factuel. Cite des chiffres et des "
        "exemples concrets. Utilise des listes à puces ou des tableaux quand utile."
    )

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        # `api_key` and `model` remain for backwards compatibility with callers
        # that still pass them; otherwise we fall back to settings.
        self.llm = LLMService(api_key=api_key, model=model)
        self.conversation_history: List[ChatMessage] = []

    # ------------------------------------------------------------------ Helpers

    def add_context(self, context: Dict) -> str:
        """Format current recruiter state as a readable preamble."""
        lines = ["CONTEXTE ACTUEL :"]

        criteria = context.get("criteria") or {}
        if criteria:
            lines.append(f"\nCritère : {criteria.get('title', 'Sans titre')}")
            skills = criteria.get("skills") or {}
            if skills:
                lines.append("Compétences requises :")
                for skill, weight in skills.items():
                    lines.append(f"  - {skill}: {weight}%")

        top_candidates = context.get("top_candidates") or []
        if top_candidates:
            lines.append("\nMeilleurs candidats :")
            for cand in top_candidates[:5]:
                lines.append(
                    f"  - {cand.get('name', 'Inconnu')} (score {float(cand.get('score', 0)):.1f}%)"
                )

        return "\n".join(lines)

    # ------------------------------------------------------------------ Intents

    def explain_score(self, candidate_name: str, score: float, breakdown: Dict) -> str:
        message = [f"Explique pourquoi {candidate_name} a un score de matching de {score:.1f}%.", "", "Détail du score :"]
        for skill, points in breakdown.items():
            message.append(f"- {skill}: {points}")
        return self._send_message("\n".join(message))

    def compare_candidates(self, candidates: List[Dict]) -> str:
        message = ["Compare ces candidats pour le poste :", ""]
        for cand in candidates:
            message.append(f"- {cand.get('name', 'Candidat')} : score {float(cand.get('score', 0)):.1f}%")
            if cand.get("skills"):
                message.append(f"  Compétences : {', '.join(cand['skills'][:5])}")
        message.append("\nMets en avant les forces, les faiblesses et ta recommandation.")
        return self._send_message("\n".join(message))

    def generate_ideal_profile(self, job_description: str) -> Dict:
        """Ask Claude to extract a structured ideal-candidate profile (JSON)."""
        prompt = (
            "À partir de cette description de poste, génère un profil de candidat idéal.\n\n"
            f"Description :\n{job_description}\n\n"
            "Réponds uniquement avec un JSON ayant cette forme :\n"
            "{\n"
            '  "skills": {"<nom>": <poids 0-100>, ...},\n'
            '  "soft_skills": ["..."],\n'
            '  "experience_years": <int>,\n'
            '  "education": "...",\n'
            '  "languages": ["..."],\n'
            '  "explanation": "..."\n'
            "}"
        )
        try:
            return self.llm.complete_json(prompt, system=self.SYSTEM_PROMPT)
        except LLMUnavailable as exc:
            logger.warning("Profile generation skipped: %s", exc)
            return {
                "skills": {},
                "soft_skills": [],
                "experience_years": 0,
                "education": "",
                "languages": [],
                "explanation": "LLM indisponible — profil par défaut.",
            }

    def chat(self, user_input: str, context: Optional[Dict] = None) -> str:
        """Main conversational entry point."""
        full_message = user_input
        if context:
            full_message = f"{self.add_context(context)}\n\n{user_input}"
        return self._send_message(full_message)

    def reset_conversation(self) -> None:
        self.conversation_history = []

    # ------------------------------------------------------------------ Internals

    def _send_message(self, user_message: str) -> str:
        self.conversation_history.append(ChatMessage(role="user", content=user_message))
        try:
            reply = self.llm.complete(self.conversation_history, system=self.SYSTEM_PROMPT)
        except LLMUnavailable as exc:
            self.conversation_history.pop()
            logger.warning("Chatbot fallback (LLM unavailable): %s", exc)
            return "Je ne peux pas contacter le moteur LLM pour le moment. Vérifiez la configuration LLM_API_KEY."
        self.conversation_history.append(ChatMessage(role="assistant", content=reply))
        return reply
