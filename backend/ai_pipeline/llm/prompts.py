"""Templates de prompts pour le fine-tuning et l'inférence LLM.

Le prompt impose au modèle de sortir un JSON structuré, qu'on parse facilement.
C'est la stratégie standard pour transformer un LLM en classifier/scorer.
"""

from __future__ import annotations

import json
import re
from typing import Dict, List, Optional


MATCHING_SYSTEM_PROMPT = """Tu es un expert en recrutement IT et un analyste RH avec 15 ans d'expérience.
Ta mission : analyser la compatibilité entre un CV et une offre d'emploi, et produire un score motivé.

Tu réponds EXCLUSIVEMENT en JSON valide, sans markdown, sans texte autour.
Le JSON doit suivre ce schéma exact :

{
  "score": <float entre 0 et 1>,
  "decision": "<accepted | review | rejected>",
  "matched_skills": [<liste des compétences en commun>],
  "missing_skills": [<compétences requises non présentes>],
  "strengths": [<3 points forts du candidat>],
  "weaknesses": [<3 faiblesses ou risques>],
  "rationale": "<2-3 phrases d'explication>"
}

Règles :
- score >= 0.75 → decision = "accepted"
- 0.5  <= score < 0.75 → decision = "review"
- score <  0.5 → decision = "rejected"
- Sois rigoureux, neutre, factuel."""


MATCHING_USER_PROMPT = """## Offre d'emploi

**Titre** : {job_title}
**Compétences requises** : {job_skills}
**Années d'expérience requises** : {job_years}
**Niveau d'études requis** : {job_education}

**Description** :
{job_description}

---

## CV du candidat

**Compétences** : {cv_skills}
**Années d'expérience** : {cv_years}
**Niveau d'études** : {cv_education}

**Résumé du CV** :
{cv_summary}

---

Analyse cette paire et produis le JSON de matching."""


def build_matching_prompt(
    cv_text: str,
    job_text: str,
    cv_skills: Optional[List[str]] = None,
    job_skills: Optional[List[str]] = None,
    cv_years: Optional[float] = None,
    job_years: Optional[float] = None,
    cv_education: Optional[str] = None,
    job_education: Optional[str] = None,
    job_title: Optional[str] = None,
) -> Dict[str, str]:
    """Construit (system, user) prompt pour matching.

    Returns:
        dict avec 'system' et 'user' (à utiliser dans le format chat-template)
    """
    user_prompt = MATCHING_USER_PROMPT.format(
        job_title=job_title or "Non spécifié",
        job_skills=", ".join(job_skills) if job_skills else "Non spécifié",
        job_years=job_years if job_years is not None else "Non spécifié",
        job_education=job_education or "Non spécifié",
        job_description=_truncate(job_text, 1500),
        cv_skills=", ".join(cv_skills) if cv_skills else "Non spécifié",
        cv_years=cv_years if cv_years is not None else "Non spécifié",
        cv_education=cv_education or "Non spécifié",
        cv_summary=_truncate(cv_text, 2000),
    )
    return {"system": MATCHING_SYSTEM_PROMPT, "user": user_prompt}


def _truncate(text: str, max_chars: int) -> str:
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + " […]"


# ---------------------------------------------------------------------- #
# Parsing de la réponse du LLM
# ---------------------------------------------------------------------- #

def parse_matching_response(text: str) -> Optional[Dict]:
    """Parse la réponse JSON du LLM, robuste aux extras de formatage.

    Le LLM peut parfois renvoyer :
        - du markdown autour : ```json ... ```
        - du texte d'intro avant le JSON
        - des fautes de syntaxe mineures

    On essaie d'extraire le premier JSON valide.
    """
    if not text:
        return None

    text = text.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)

    # Trouver le premier { et le dernier } qui matchent
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Tenter d'extraire le JSON entre la première { et la dernière }
    first = text.find("{")
    last = text.rfind("}")
    if first >= 0 and last > first:
        candidate = text[first:last + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            # Tenter de réparer les virgules manquantes simples
            repaired = re.sub(r",\s*}", "}", candidate)
            repaired = re.sub(r",\s*]", "]", repaired)
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                return None

    return None


def validate_matching_output(payload: Dict) -> Dict:
    """Valide et normalise la sortie du LLM (clamp score, decision cohérente)."""
    if not isinstance(payload, dict):
        return {"score": 0.0, "decision": "rejected", "_invalid": True}

    score = payload.get("score", 0.0)
    try:
        score = float(score)
        score = max(0.0, min(1.0, score))
    except (TypeError, ValueError):
        score = 0.0

    # Decision cohérente avec score
    if score >= 0.75:
        decision = "accepted"
    elif score >= 0.5:
        decision = "review"
    else:
        decision = "rejected"

    return {
        "score": round(score, 4),
        "decision": decision,
        "matched_skills": _ensure_list(payload.get("matched_skills")),
        "missing_skills": _ensure_list(payload.get("missing_skills")),
        "strengths": _ensure_list(payload.get("strengths")),
        "weaknesses": _ensure_list(payload.get("weaknesses")),
        "rationale": str(payload.get("rationale", "")).strip()[:500],
    }


def _ensure_list(value) -> List[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


if __name__ == "__main__":
    p = build_matching_prompt(
        cv_text="Python developer with 5 years experience in FastAPI",
        job_text="Looking for senior Python engineer",
        cv_skills=["Python", "FastAPI", "Docker"],
        job_skills=["Python", "FastAPI", "Kubernetes"],
        cv_years=5, job_years=3,
        job_title="Senior Python Engineer",
    )
    print("=== SYSTEM ===")
    print(p["system"])
    print("\n=== USER ===")
    print(p["user"])
