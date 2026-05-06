"""Context-aware recruiter chatbot endpoint."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional
from urllib import request

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.models.models import Candidate, CriteriaSkill, JobCriteria, MatchResult, Skill


router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    context: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    intent: str
    actions: List[str] = Field(default_factory=list)


class IdealProfileRequest(BaseModel):
    job_title: str
    job_description: str = ""
    required_skills: List[str] = Field(default_factory=list)


class IdealProfileResponse(BaseModel):
    title: str
    skills: List[Dict[str, Any]] = Field(default_factory=list)
    experience: str
    education: str
    languages: List[str] = Field(default_factory=list)
    explanation: str


def _detect_intent(message: str) -> str:
    lower = message.lower()
    if any(keyword in lower for keyword in ["bonjour", "salut", "hello", "hey", "bonsoir", "coucou"]):
        return "greeting"
    if any(keyword in lower for keyword in ["pourquoi", "why", "score", "explique", "justifie", "raison", "detail", "détail"]):
        return "explanation"
    if any(keyword in lower for keyword in ["compare", "compar", "vs", "versus", "meilleur", "entre", "différence", "difference"]):
        return "comparison"
    if any(keyword in lower for keyword in ["qui", "who", "trouve", "experience", "expérience", "cherche", "top", "liste", "montre", "candidats"]):
        return "exploration"
    if any(keyword in lower for keyword in ["augmente", "diminue", "baisse", "increase", "decrease", "modifie", "adjust", "poids", "weight"]):
        return "adjustment"
    return "general"


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _to_percent(score: Any) -> float:
    value = float(score or 0.0)
    if value <= 1.0:
        value *= 100.0
    return round(value, 2)


def _build_candidate_snapshot(candidate: Candidate, score: float, criteria_skills: List[CriteriaSkill]) -> Dict[str, Any]:
    candidate_skill_names = {
        item.skill.name.lower(): item.skill.name
        for item in candidate.candidate_skills
        if item.skill and item.skill.name
    }

    matched_skills: List[str] = []
    missing_skills: List[str] = []
    skill_breakdown: List[Dict[str, Any]] = []

    total_weight = sum(item.weight for item in criteria_skills) or 1
    for item in criteria_skills:
        if not item.skill or not item.skill.name:
            continue
        skill_name = item.skill.name
        present = skill_name.lower() in candidate_skill_names
        if present:
            matched_skills.append(skill_name)
        else:
            missing_skills.append(skill_name)

        contribution = (item.weight / total_weight) * (score if present else 0)
        skill_breakdown.append(
            {
                "skill": skill_name,
                "weight": item.weight,
                "present": present,
                "score": score if present else 0,
                "contribution": round(contribution, 2),
            }
        )

    coverage = (len(matched_skills) / max(1, len(criteria_skills))) * 100
    return {
        "candidate_id": candidate.id,
        "candidate_name": candidate.full_name,
        "candidate_email": candidate.email,
        "score": score,
        "coverage": round(coverage, 2),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "skill_breakdown": skill_breakdown,
        "summary": f"{candidate.full_name} couvre {len(matched_skills)}/{max(1, len(criteria_skills))} compétences clés.",
    }


def _hydrate_context(context: Dict[str, Any], db: Session) -> Dict[str, Any]:
    hydrated = dict(context or {})

    criteria_obj: Optional[JobCriteria] = None
    criteria_payload = hydrated.get("current_criteria")
    criteria_id = hydrated.get("current_criteria_id")

    if isinstance(criteria_payload, dict) and criteria_payload.get("id"):
        criteria_id = criteria_payload.get("id")

    if criteria_id:
        criteria_obj = db.query(JobCriteria).filter(JobCriteria.id == int(criteria_id)).first()

    if not criteria_obj:
        criteria_obj = db.query(JobCriteria).order_by(JobCriteria.created_at.desc()).first()

    criteria_skills: List[CriteriaSkill] = []
    if criteria_obj:
        criteria_skills = (
            db.query(CriteriaSkill)
            .filter(CriteriaSkill.criteria_id == criteria_obj.id)
            .all()
        )
        hydrated["current_criteria_id"] = criteria_obj.id
        hydrated["current_criteria"] = {
            "id": criteria_obj.id,
            "title": criteria_obj.title,
            "required_skills": [
                {"name": item.skill.name, "weight": item.weight}
                for item in criteria_skills
                if item.skill and item.skill.name
            ],
        }

    existing_top = hydrated.get("top_candidates")
    if isinstance(existing_top, list) and existing_top:
        return hydrated

    if not criteria_obj:
        hydrated["top_candidates"] = []
        return hydrated

    top_candidates: List[Dict[str, Any]] = []
    stored_results = (
        db.query(MatchResult)
        .filter(MatchResult.criteria_id == criteria_obj.id)
        .order_by(MatchResult.score.desc())
        .limit(10)
        .all()
    )

    if stored_results:
        for result in stored_results:
            candidate = db.query(Candidate).filter(Candidate.id == result.candidate_id).first()
            if not candidate:
                continue
            top_candidates.append(_build_candidate_snapshot(candidate, _to_percent(result.score), criteria_skills))
    else:
        candidates = db.query(Candidate).order_by(Candidate.created_at.desc()).limit(20).all()
        for candidate in candidates:
            score = 0.0
            if criteria_skills:
                skill_set = {
                    item.skill.name.lower()
                    for item in candidate.candidate_skills
                    if item.skill and item.skill.name
                }
                matched_weight = sum(
                    item.weight
                    for item in criteria_skills
                    if item.skill and item.skill.name and item.skill.name.lower() in skill_set
                )
                total_weight = sum(item.weight for item in criteria_skills) or 1
                score = (matched_weight / total_weight) * 100
            top_candidates.append(_build_candidate_snapshot(candidate, round(score, 2), criteria_skills))

        top_candidates.sort(key=lambda item: float(item.get("score", 0)), reverse=True)
        top_candidates = top_candidates[:10]

    hydrated["top_candidates"] = top_candidates
    return hydrated


def _pick_candidate_from_message(message: str, top_candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    normalized_message = _normalize_text(message)
    if not top_candidates:
        return None

    # First try strict full-name containment.
    for candidate in top_candidates:
        name = str(candidate.get("candidate_name", "")).strip()
        if name and _normalize_text(name) in normalized_message:
            return candidate

    # Then token overlap on at least 2 meaningful tokens.
    for candidate in top_candidates:
        name = str(candidate.get("candidate_name", "")).strip()
        if not name:
            continue
        tokens = [token for token in re.findall(r"[a-zA-ZÀ-ÿ]+", _normalize_text(name)) if len(token) >= 3]
        overlap = sum(1 for token in tokens if token in normalized_message)
        if overlap >= 2:
            return candidate

    return top_candidates[0]


def _format_breakdown(candidate: Dict[str, Any]) -> str:
    rows = []
    for item in (candidate.get("skill_breakdown") or [])[:8]:
        skill = item.get("skill") or "N/A"
        present = bool(item.get("present"))
        weight = item.get("weight", 0)
        contribution = item.get("contribution", 0)
        marker = "OK" if present else "MANQUANT"
        rows.append(f"- {skill}: {marker}, poids {weight}%, contribution {round(float(contribution), 2)}")
    return "\n".join(rows)


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
        "If data is missing, say what is missing and propose the next action.",
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

    message = str(context.get("message", ""))
    candidate = _pick_candidate_from_message(message, top_candidates) or top_candidates[0]
    skills = candidate.get("skill_breakdown") or []
    matched = [item.get("skill") for item in skills if item.get("present")]
    missing = [item.get("skill") for item in skills if not item.get("present")]
    score = round(float(candidate.get("score", 0)), 2)
    coverage = round(float(candidate.get("coverage", 0)), 2)
    breakdown_text = _format_breakdown(candidate)
    missing_text = ", ".join(missing[:5]) if missing else "Aucun écart critique détecté"
    matched_text = ", ".join(matched[:5]) if matched else "alignement partiel"

    return "\n".join([
        f"{candidate.get('candidate_name', 'Ce candidat')} a un score de {score}% (couverture {coverage}%).",
        f"Points forts: {matched_text}.",
        f"Points à renforcer: {missing_text}.",
        "Détail des contributions:",
        breakdown_text or "- Pas de détail de contribution disponible.",
        "Action recommandée: renforcer 1-2 compétences manquantes à plus fort poids pour gagner rapidement des points.",
    ])


def _compare_candidates(message: str, context: Dict[str, Any]) -> str:
    top_candidates = context.get("top_candidates") or []
    if len(top_candidates) < 2:
        return "Ajoutez au moins deux candidats dans le contexte pour lancer une comparaison."

    normalized_message = _normalize_text(message)
    selected: List[Dict[str, Any]] = []
    for candidate in top_candidates:
        name = str(candidate.get("candidate_name", "")).strip()
        if name and _normalize_text(name) in normalized_message:
            selected.append(candidate)

    if len(selected) < 2:
        selected = top_candidates[:3]

    selected = sorted(selected, key=lambda item: float(item.get("score", 0)), reverse=True)
    lines = ["Comparaison rapide:", "| Candidat | Score | Couverture | Compétences clés |", "|---|---:|---:|---|"]
    for candidate in selected:
        coverage = round(float(candidate.get("coverage", 0)), 2)
        lines.append(
            f"| {candidate.get('candidate_name', 'Candidat')} | {round(float(candidate.get('score', 0)), 2)}% | {coverage}% | {', '.join(candidate.get('matched_skills', [])[:4]) or 'N/A'} |"
        )
    winner = selected[0]
    runner_up = selected[1] if len(selected) > 1 else None
    if runner_up:
        gap = round(float(winner.get("score", 0)) - float(runner_up.get("score", 0)), 2)
        lines.append(
            f"Recommandation: {winner.get('candidate_name', 'Candidat 1')} est devant avec +{gap} points."
        )
    return "\n".join(lines)


def _explore_candidates(message: str, context: Dict[str, Any], db: Session) -> str:
    lower = message.lower()
    requested_skill = None
    top_candidates = context.get("top_candidates") or []

    for skill in db.query(Skill).order_by(Skill.name.asc()).all():
        if skill.name.lower() in lower:
            requested_skill = skill.name
            break

    if not requested_skill:
        match = re.search(r"(?:machine learning|data science|python|react|docker|sql|anglais)", lower)
        if match:
            requested_skill = match.group(0)

    min_score = None
    score_match = re.search(r"(?:au[-\s]?dessus de|sup[eé]rieur [aà]|>=?|plus de)\s*(\d{1,3})\s*%?", lower)
    if score_match:
        min_score = max(0, min(100, int(score_match.group(1))))

    if not requested_skill:
        if top_candidates:
                        names = ", ".join(str(candidate.get("candidate_name", "N/A")) for candidate in top_candidates[:5])
                        return f"Je peux déjà vous montrer les meilleurs candidats du contexte: {names}. Précisez une compétence pour une recherche ciblée."

        candidates = db.query(Candidate).order_by(Candidate.created_at.desc()).limit(5).all()
        names = ", ".join(candidate.full_name for candidate in candidates)
        return f"Voici les derniers candidats disponibles: {names}. Précisez une compétence pour une recherche ciblée."

    matching_candidates: List[str] = []
    if top_candidates:
        for candidate in top_candidates:
            candidate_name = str(candidate.get("candidate_name", "")).strip()
            matched_skills = [str(skill).lower() for skill in candidate.get("matched_skills", [])]
            haystack = " ".join([candidate_name, " ".join(matched_skills)]).lower()
            if requested_skill.lower() in haystack:
                if min_score is not None and float(candidate.get("score", 0)) < min_score:
                    continue
                matching_candidates.append(f"{candidate_name} ({round(float(candidate.get('score', 0)), 2)}%)")

    if not matching_candidates:
        for candidate in db.query(Candidate).order_by(Candidate.created_at.desc()).all():
            skill_names = [skill.skill.name.lower() for skill in candidate.candidate_skills if skill.skill and skill.skill.name]
            if requested_skill.lower() in skill_names or requested_skill.lower() in (candidate.raw_text or "").lower():
                if min_score is not None:
                    continue
                matching_candidates.append(candidate.full_name)

    if not matching_candidates:
        return f"Je n'ai trouvé aucun candidat avec de l'expérience clairement reliée à {requested_skill}."

    return f"Candidats avec {requested_skill}: {', '.join(matching_candidates[:10])}."


def _adjust_criteria(message: str, context: Dict[str, Any], db: Session) -> str:
    criteria_id = context.get("current_criteria_id")
    criteria_payload = context.get("current_criteria") or {}
    criteria = None
    if criteria_id:
        criteria = db.query(JobCriteria).filter(JobCriteria.id == int(criteria_id)).first()
    if not criteria and criteria_payload:
        criteria = criteria_payload
    if not criteria:
        return "Je peux ajuster les poids si vous fournissez la matrice de critères courante ou si elle existe déjà dans le contexte."

    lower = message.lower()
    criteria_items = []
    if isinstance(criteria, JobCriteria):
        criteria_items = db.query(CriteriaSkill).filter(CriteriaSkill.criteria_id == criteria.id).all()
    else:
        criteria_items = [
            type("CriteriaItem", (), {"skill": type("SkillRef", (), {"name": skill.get("name")})(), "weight": skill.get("weight", 0)})
            for skill in criteria.get("required_skills", [])
            if isinstance(skill, dict) and skill.get("name")
        ]

    target_skill = None
    for item in criteria_items:
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

    if isinstance(criteria, JobCriteria):
        target_skill.weight = new_weight
        db.commit()
        ordered = sorted(
            [item for item in criteria_items if item.skill and item.skill.name],
            key=lambda item: item.weight,
            reverse=True,
        )[:5]
        leaderboard = ", ".join(f"{item.skill.name} ({item.weight}%)" for item in ordered)
        return f"Le poids de {target_skill.skill.name} a été ajusté à {new_weight}%. Top priorités actuelles: {leaderboard}."

    ordered = sorted(criteria_items, key=lambda item: item.weight, reverse=True)[:5]
    leaderboard = ", ".join(f"{item.skill.name} ({item.weight}%)" for item in ordered)
    return f"Le poids de {target_skill.skill.name} passerait à {new_weight}% dans le contexte courant. Top priorités actuelles: {leaderboard}."


def _general_response(message: str, context: Dict[str, Any]) -> str:
    top_candidates = context.get("top_candidates") or []
    criteria = context.get("current_criteria") or {}
    criteria_title = criteria.get("title") or "votre matrice active"

    if top_candidates:
        best = max(top_candidates, key=lambda c: float(c.get("score", 0)))
        names = ", ".join(c.get("candidate_name", "N/A") for c in top_candidates[:5])
        return (
            f"Pour {criteria_title}, le meilleur candidat actuel est {best.get('candidate_name', 'N/A')} "
            f"avec {round(float(best.get('score', 0)), 2)}%.\n"
            f"Candidats disponibles: {names}.\n"
            "Je peux maintenant: 1) expliquer un score, 2) comparer des candidats, 3) explorer par compétence, 4) ajuster les poids."
        )

    return (
        "Je peux expliquer un score, comparer des candidats, explorer la base ou ajuster des critères. "
        "Essayez: 'Pourquoi ce candidat a 85 % ?', 'Compare Ahmed et Sara', ou 'Augmente le poids de Python'."
    )


def _greeting_response(context: Dict[str, Any]) -> str:
    top_candidates = context.get("top_candidates") or []
    criteria = context.get("current_criteria") or {}
    criteria_title = criteria.get("title") or "la matrice active"

    if top_candidates:
        best = max(top_candidates, key=lambda c: float(c.get("score", 0)))
        return (
            f"Bonjour. Je suis prêt à vous aider sur {criteria_title}. "
            f"Le meilleur candidat actuel est {best.get('candidate_name', 'N/A')} avec {round(float(best.get('score', 0)), 2)}%. "
            "Si vous voulez, je peux expliquer ce score, comparer des candidats ou ajuster les poids."
        )

    return (
        f"Bonjour. Je suis prêt à vous aider sur {criteria_title}. "
        "Dites-moi ce que vous voulez analyser et je m’en charge."
    )


def _suggest_actions(intent: str, context: Dict[str, Any]) -> List[str]:
    top_candidates = context.get("top_candidates") or []
    criteria = context.get("current_criteria") or {}
    criteria_title = criteria.get("title") or "la matrice active"

    actions: List[str] = []
    if intent == "explanation" and top_candidates:
        actions.append("Comparer avec le candidat suivant")
        actions.append("Montrer les compétences manquantes")
    elif intent == "comparison" and len(top_candidates) >= 2:
        actions.append("Expliquer le score du vainqueur")
        actions.append("Voir les 3 meilleurs candidats")
    elif intent == "exploration":
        actions.append("Lister les candidats les mieux scorés")
        actions.append("Filtrer par autre compétence")
    elif intent == "adjustment":
        actions.append(f"Recalculer {criteria_title}")
        actions.append("Suggérer une pondération plus équilibrée")

    if not actions:
        if top_candidates:
            actions.append("Expliquer le meilleur score")
            actions.append("Comparer les deux meilleurs candidats")
        else:
            actions.append("Importer ou calculer un matching")
            actions.append("Poser une question sur un candidat précis")

    return actions[:3]


def _build_ideal_profile_fallback(payload: IdealProfileRequest) -> IdealProfileResponse:
    description = f"{payload.job_title} {payload.job_description} {' '.join(payload.required_skills)}".lower()

    skill_weights: Dict[str, int] = {}
    canonical_names = {
        "react": "React",
        "typescript": "TypeScript",
        "javascript": "JavaScript",
        "python": "Python",
        "node": "Node.js",
        "node.js": "Node.js",
        "aws": "AWS",
        "docker": "Docker",
        "kubernetes": "Kubernetes",
        "sql": "SQL",
        "mongodb": "MongoDB",
        "machine learning": "Machine Learning",
        "data science": "Data Science",
    }
    for skill in payload.required_skills:
        normalized = skill.strip()
        if normalized:
            canonical = canonical_names.get(normalized.lower(), normalized)
            skill_weights[canonical] = max(skill_weights.get(canonical, 0), 30)

    keyword_weights = {
        "react": 30,
        "typescript": 30,
        "javascript": 25,
        "python": 25,
        "node": 25,
        "aws": 20,
        "docker": 20,
        "kubernetes": 20,
        "sql": 15,
        "mongodb": 15,
        "machine learning": 30,
        "data science": 30,
    }
    for keyword, weight in keyword_weights.items():
        if keyword in description:
            canonical = canonical_names.get(keyword, keyword.title())
            skill_weights[canonical] = max(skill_weights.get(canonical, 0), weight)

    years = "3+ years"
    year_match = re.search(r"(\d{1,2})\+?\s*(?:ans|years?|yrs?)", description)
    if year_match:
        years = f"{year_match.group(1)}+ years"
    elif any(term in description for term in ["senior", "lead", "principal"]):
        years = "5+ years"

    education = "Bachelor's degree"
    if any(term in description for term in ["master", "msc", "m.sc", "ingénieur", "engineer"]):
        education = "Master's degree"
    if any(term in description for term in ["phd", "doctorat", "doctorate"]):
        education = "PhD or equivalent"

    languages: List[str] = []
    for language in ["English", "French", "Spanish", "German"]:
        if language.lower() in description:
            languages.append(language)
    if not languages:
        languages = ["English"]

    ordered_skills = [
        {"name": name, "weight": weight}
        for name, weight in sorted(skill_weights.items(), key=lambda item: item[1], reverse=True)
    ][:10]

    explanation = (
        f"Profil idéal généré pour {payload.job_title}. "
        f"Compétences prioritaires: {', '.join(item['name'] for item in ordered_skills[:5]) or 'non précisées'}. "
        f"Expérience attendue: {years}. "
        f"Niveau d'études: {education}."
    )

    return IdealProfileResponse(
        title=payload.job_title,
        skills=ordered_skills,
        experience=years,
        education=education,
        languages=languages,
        explanation=explanation,
    )


@router.post("", response_model=ChatResponse)
def chat(request_payload: ChatRequest, db: Session = Depends(get_db)):
    local_context = _hydrate_context(request_payload.context, db)
    local_context["message"] = request_payload.message

    intent = _detect_intent(request_payload.message)
    if intent == "greeting":
        response_text = _greeting_response(local_context)
    else:
        prompt = _build_prompt(request_payload.message, local_context, intent)
        llm_response = _call_anthropic(prompt)

        if llm_response:
            response_text = llm_response
        else:
            if intent == "explanation":
                response_text = _explain_score(local_context)
            elif intent == "comparison":
                response_text = _compare_candidates(request_payload.message, local_context)
            elif intent == "exploration":
                response_text = _explore_candidates(request_payload.message, local_context, db)
            elif intent == "adjustment":
                response_text = _adjust_criteria(request_payload.message, local_context, db)
            else:
                response_text = _general_response(request_payload.message, local_context)

    return ChatResponse(response=response_text, intent=intent, actions=_suggest_actions(intent, local_context))


@router.post("/ideal-profile", response_model=IdealProfileResponse)
def ideal_profile(request_payload: IdealProfileRequest, db: Session = Depends(get_db)):
    """Generate an ideal candidate profile for a job description."""

    llm_prompt = "\n".join([
        "You are an expert recruitment assistant.",
        f"Job title: {request_payload.job_title}",
        f"Job description: {request_payload.job_description}",
        f"Required skills: {', '.join(request_payload.required_skills)}",
        "Return only valid JSON with keys: title, skills (array of {name, weight}), experience, education, languages (array), explanation.",
        "Be concise and realistic.",
    ])
    llm_response = _call_anthropic(llm_prompt)
    if llm_response:
        try:
            data = json.loads(llm_response)
            if isinstance(data, dict):
                return IdealProfileResponse(
                    title=str(data.get("title") or request_payload.job_title),
                    skills=list(data.get("skills") or []),
                    experience=str(data.get("experience") or "3+ years"),
                    education=str(data.get("education") or "Bachelor's degree"),
                    languages=list(data.get("languages") or ["English"]),
                    explanation=str(data.get("explanation") or "Profil idéal généré par LLM."),
                )
        except Exception:
            pass

    return _build_ideal_profile_fallback(request_payload)
