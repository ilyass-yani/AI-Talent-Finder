"""Context-aware recruiter chatbot endpoint."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib import error, request

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.models.models import Candidate, CriteriaSkill, JobCriteria, Skill


router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    context: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    intent: str
    actions: List[str] = Field(default_factory=list)


def _detect_intent(message: str) -> str:
    lower = message.lower()
    if any(keyword in lower for keyword in ["pourquoi", "why", "score", "explique"]):
        return "explanation"
    if any(keyword in lower for keyword in ["compare", "compar", "vs", "versus"]):
        return "comparison"
    if any(keyword in lower for keyword in ["qui", "who", "trouve", "experience", "expérience"]):
        return "exploration"
    if any(keyword in lower for keyword in ["augmente", "diminue", "baisse", "increase", "decrease", "modifie", "adjust"]):
        return "adjustment"
    return "general"


def _build_prompt(message: str, context: Dict[str, Any], intent: str) -> str:
    criteria = context.get("current_criteria") or {}
    top_candidates = context.get("top_candidates") or []
    history = context.get("history") or []

    return "\n".join([
        "You are an expert recruiting assistant for AI Talent Finder.",
        f"Intent: {intent}",
        f"User message: {message}",
        f"Current criteria: {json.dumps(criteria, ensure_ascii=False)}",
        f"Top candidates: {json.dumps(top_candidates, ensure_ascii=False)}",
        f"Conversation history: {json.dumps(history, ensure_ascii=False)}",
        "Respond in French, be concise and useful, and mention scores and skills explicitly when relevant.",
    ])


def _call_anthropic(prompt: str) -> Optional[str]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    payload = json.dumps({
        "model": model,
        "max_tokens": 700,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
        parts = data.get("content", [])
        texts = [part.get("text", "") for part in parts if isinstance(part, dict)]
        return "\n".join(part for part in texts if part).strip() or None
    except Exception:
        return None


def _explain_score(context: Dict[str, Any]) -> str:
    top_candidates = context.get("top_candidates") or []
    if not top_candidates:
        return "Je n'ai pas encore de candidat ou de détail de score à expliquer. Lancez d'abord un matching."

    candidate = top_candidates[0]
    skills = candidate.get("skill_breakdown") or []
    matched = [item.get("skill") for item in skills if item.get("present")]
    missing = [item.get("skill") for item in skills if not item.get("present")]
    score = candidate.get("score", 0)
    return (
        f"{candidate.get('candidate_name', 'Ce candidat')} obtient {round(float(score), 2)}% grâce à {', '.join(matched[:5]) or 'un bon alignement'}"
        + (f". Les écarts principaux sont: {', '.join(missing[:5])}." if missing else ".")
    )


def _compare_candidates(message: str, context: Dict[str, Any]) -> str:
    top_candidates = context.get("top_candidates") or []
    if len(top_candidates) < 2:
        return "Ajoutez au moins deux candidats dans le contexte pour lancer une comparaison."

    selected = top_candidates[:3]
    lines = ["Comparaison rapide:"]
    for candidate in selected:
        lines.append(
            f"- {candidate.get('candidate_name', 'Candidat')} | score {round(float(candidate.get('score', 0)), 2)}% | compétences clés: {', '.join(candidate.get('matched_skills', [])[:4]) or 'N/A'}"
        )
    return "\n".join(lines)


def _explore_candidates(message: str, db: Session) -> str:
    lower = message.lower()
    requested_skill = None

    for skill in db.query(Skill).order_by(Skill.name.asc()).all():
        if skill.name.lower() in lower:
            requested_skill = skill.name
            break

    if not requested_skill:
        match = re.search(r"(?:machine learning|data science|python|react|docker|sql|anglais)", lower)
        if match:
            requested_skill = match.group(0)

    if not requested_skill:
        candidates = db.query(Candidate).order_by(Candidate.created_at.desc()).limit(5).all()
        names = ", ".join(candidate.full_name for candidate in candidates)
        return f"Voici les derniers candidats disponibles: {names}. Précisez une compétence pour une recherche ciblée."

    matching_candidates: List[str] = []
    for candidate in db.query(Candidate).order_by(Candidate.created_at.desc()).all():
        skill_names = [skill.skill.name.lower() for skill in candidate.candidate_skills if skill.skill and skill.skill.name]
        if requested_skill.lower() in skill_names or requested_skill.lower() in (candidate.raw_text or "").lower():
            matching_candidates.append(candidate.full_name)

    if not matching_candidates:
        return f"Je n'ai trouvé aucun candidat avec de l'expérience clairement reliée à {requested_skill}."

    return f"Candidats avec {requested_skill}: {', '.join(matching_candidates[:10])}."


def _adjust_criteria(message: str, context: Dict[str, Any], db: Session) -> str:
    criteria_id = context.get("current_criteria_id")
    if not criteria_id:
        return "Je peux ajuster les poids si vous fournissez l'identifiant de la matrice de critères courante."

    criteria = db.query(JobCriteria).filter(JobCriteria.id == int(criteria_id)).first()
    if not criteria:
        return "La matrice de critères n'a pas été trouvée."

    lower = message.lower()
    target_skill = None
    for item in db.query(CriteriaSkill).filter(CriteriaSkill.criteria_id == criteria.id).all():
        if item.skill and item.skill.name.lower() in lower:
            target_skill = item
            break

    if not target_skill:
        return "Je n'ai pas trouvé la compétence à ajuster. Précisez le nom de la compétence."

    new_weight = None
    match = re.search(r"(\d{1,3})\s*%", lower)
    if match:
        new_weight = max(0, min(100, int(match.group(1))))
    elif any(keyword in lower for keyword in ["augmente", "increase", "raise", "hausse"]):
        new_weight = min(100, target_skill.weight + 10)
    elif any(keyword in lower for keyword in ["diminue", "baisse", "decrease", "lower"]):
        new_weight = max(0, target_skill.weight - 10)

    if new_weight is None:
        return "Indiquez un nouveau poids ou demandez une hausse/baisse de 10 points."

    target_skill.weight = new_weight
    db.commit()
    return f"Le poids de {target_skill.skill.name} a été ajusté à {new_weight}%."


@router.post("", response_model=ChatResponse)
def chat(request_payload: ChatRequest, db: Session = Depends(get_db)):
    intent = _detect_intent(request_payload.message)
    prompt = _build_prompt(request_payload.message, request_payload.context, intent)
    llm_response = _call_anthropic(prompt)

    if llm_response:
      response_text = llm_response
    else:
      if intent == "explanation":
          response_text = _explain_score(request_payload.context)
      elif intent == "comparison":
          response_text = _compare_candidates(request_payload.message, request_payload.context)
      elif intent == "exploration":
          response_text = _explore_candidates(request_payload.message, db)
      elif intent == "adjustment":
          response_text = _adjust_criteria(request_payload.message, request_payload.context, db)
      else:
          response_text = (
              "Je peux expliquer un score, comparer des candidats, explorer la base ou ajuster des critères. "
              "Essayez: 'Pourquoi ce candidat a 85 % ?', 'Compare Ahmed et Sara', ou 'Augmente le poids de Python'."
          )

    return ChatResponse(response=response_text, intent=intent, actions=[])
