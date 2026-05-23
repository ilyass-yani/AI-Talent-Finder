"""Construction du dataset d'instructions pour fine-tuning LLM.

À partir des paires (CV, Job, label) issues du training, on génère :
    - un prompt d'entrée (system + user)
    - une réponse cible JSON (matched_skills, missing, score, decision, ...)

Le dataset final est au format `Dataset` HuggingFace, prêt pour SFTTrainer.

Format de sortie pour chaque exemple :
    {
        "text": "<full conversation au format chat-template>",
        "prompt": "<system + user>",
        "completion": "<JSON cible>",
    }
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import pandas as pd

from ai_pipeline.llm.prompts import build_matching_prompt
from ai_pipeline.preprocessing.skill_normalizer import SkillNormalizer


@dataclass
class TrainingExample:
    cv_text: str
    job_text: str
    cv_skills: List[str]
    job_skills: List[str]
    label: int  # 0 = pas compatible, 1 = compatible
    score: Optional[float] = None
    job_title: Optional[str] = None
    cv_years: Optional[float] = None
    job_years: Optional[float] = None


class MatchingDatasetBuilder:
    """Construit un dataset d'instructions pour LLM."""

    def __init__(self, skill_normalizer: Optional[SkillNormalizer] = None) -> None:
        self.skill_normalizer = skill_normalizer or SkillNormalizer()

    # ------------------------------------------------------------------ #
    # Construction des targets
    # ------------------------------------------------------------------ #

    def build_target(self, example: TrainingExample) -> Dict:
        """Construit le JSON cible à partir d'un exemple labellisé.

        Heuristique pour générer matched/missing/strengths/weaknesses/rationale
        de manière cohérente avec le label.
        """
        cv_norm = set(self.skill_normalizer.normalize_list(example.cv_skills))
        job_norm = set(self.skill_normalizer.normalize_list(example.job_skills))

        matched = sorted(cv_norm & job_norm)
        missing = sorted(job_norm - cv_norm)
        extra = sorted(cv_norm - job_norm)

        # Score : utiliser celui fourni, sinon le calculer depuis le label
        if example.score is not None:
            score = float(example.score)
        elif example.label == 1:
            # On varie le score pour éviter la corrélation parfaite
            base = 0.78 + random.uniform(0, 0.18) if matched else 0.6
            score = min(0.97, base)
        else:
            score = 0.15 + random.uniform(0, 0.25)

        # Decision cohérente
        if score >= 0.75:
            decision = "accepted"
        elif score >= 0.5:
            decision = "review"
        else:
            decision = "rejected"

        # Strengths / weaknesses
        strengths = self._gen_strengths(matched, example)
        weaknesses = self._gen_weaknesses(missing, example)
        rationale = self._gen_rationale(example, matched, missing, score)

        return {
            "score": round(score, 3),
            "decision": decision,
            "matched_skills": matched[:10],
            "missing_skills": missing[:10],
            "strengths": strengths,
            "weaknesses": weaknesses,
            "rationale": rationale,
        }

    @staticmethod
    def _gen_strengths(matched: List[str], example: TrainingExample) -> List[str]:
        result = []
        if matched:
            result.append(
                f"Maîtrise des compétences clés : {', '.join(matched[:3])}"
            )
        if example.cv_years and example.job_years and example.cv_years >= example.job_years:
            result.append(
                f"Expérience suffisante ({example.cv_years} ans pour {example.job_years} requis)"
            )
        if len(matched) >= 3:
            result.append("Profil techniquement polyvalent")
        elif example.label == 1:
            result.append("Bonne adéquation globale avec le poste")
        return result[:3] or ["Profil à examiner plus en détail"]

    @staticmethod
    def _gen_weaknesses(missing: List[str], example: TrainingExample) -> List[str]:
        result = []
        if missing:
            result.append(
                f"Compétences manquantes : {', '.join(missing[:3])}"
            )
        if example.cv_years and example.job_years and example.cv_years < example.job_years:
            gap = example.job_years - example.cv_years
            result.append(f"Manque {gap:.0f} an(s) d'expérience par rapport à la cible")
        if len(missing) > 3:
            result.append(f"{len(missing)} compétences requises non présentes")
        return result[:3] or ["Aucune faiblesse majeure identifiée"]

    @staticmethod
    def _gen_rationale(
        example: TrainingExample,
        matched: List[str],
        missing: List[str],
        score: float,
    ) -> str:
        n_matched = len(matched)
        n_missing = len(missing)
        if score >= 0.75:
            return (
                f"Candidat retenu : {n_matched} compétences correspondent au profil "
                f"recherché. L'expérience et le profil global sont en adéquation avec le poste."
            )
        if score >= 0.5:
            return (
                f"Profil à revoir : {n_matched} compétences en commun mais {n_missing} "
                f"manquent. Un entretien permettrait de vérifier le potentiel d'apprentissage."
            )
        return (
            f"Profil non adapté : seulement {n_matched} compétences correspondent, "
            f"avec {n_missing} compétences requises absentes du CV."
        )

    # ------------------------------------------------------------------ #
    # Format final pour SFT
    # ------------------------------------------------------------------ #

    def example_to_text(
        self,
        example: TrainingExample,
        tokenizer=None,
        target_json: Optional[Dict] = None,
    ) -> Dict[str, str]:
        """Convertit un exemple en texte pour SFT (chat-template ou raw)."""
        target = target_json or self.build_target(example)
        prompts = build_matching_prompt(
            cv_text=example.cv_text,
            job_text=example.job_text,
            cv_skills=example.cv_skills,
            job_skills=example.job_skills,
            cv_years=example.cv_years,
            job_years=example.job_years,
            job_title=example.job_title,
        )

        completion = json.dumps(target, ensure_ascii=False, indent=2)

        if tokenizer is not None and hasattr(tokenizer, "apply_chat_template"):
            messages = [
                {"role": "system", "content": prompts["system"]},
                {"role": "user", "content": prompts["user"]},
                {"role": "assistant", "content": completion},
            ]
            try:
                text = tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=False,
                )
                return {
                    "text": text,
                    "prompt": tokenizer.apply_chat_template(
                        messages[:-1], tokenize=False, add_generation_prompt=True,
                    ),
                    "completion": completion,
                }
            except Exception:
                pass

        # Fallback : format raw "### Instruction / ### Response"
        text = (
            f"### System\n{prompts['system']}\n\n"
            f"### Instruction\n{prompts['user']}\n\n"
            f"### Response\n{completion}"
        )
        return {
            "text": text,
            "prompt": f"### System\n{prompts['system']}\n\n### Instruction\n{prompts['user']}\n\n### Response\n",
            "completion": completion,
        }

    # ------------------------------------------------------------------ #
    # Pipelines de bout en bout
    # ------------------------------------------------------------------ #

    def from_csv(
        self,
        csv_path: str | Path,
        text_col: str = "cv_text",
        job_col: str = "job_text",
        label_col: str = "label",
        cv_skills_col: Optional[str] = None,
        job_skills_col: Optional[str] = None,
        score_col: str = "heuristic_score",
        max_examples: Optional[int] = None,
    ) -> List[TrainingExample]:
        """Charge un CSV (compatible avec data/training_pairs.csv) et le transforme."""
        df = pd.read_csv(csv_path)
        if max_examples:
            df = df.sample(min(max_examples, len(df)), random_state=42)

        examples: List[TrainingExample] = []
        for row in df.itertuples(index=False):
            cv_text = getattr(row, text_col, "")
            job_text = getattr(row, job_col, "")
            label = int(getattr(row, label_col, 0))
            score = float(getattr(row, score_col, None)) if hasattr(row, score_col) and getattr(row, score_col) is not None else None

            # Si les skills ne sont pas dans des colonnes dédiées, on tente
            # de les extraire heuristiquement du texte (à enrichir).
            cv_skills = _extract_skills_heuristic(cv_text)
            job_skills = _extract_skills_heuristic(job_text)

            examples.append(TrainingExample(
                cv_text=cv_text,
                job_text=job_text,
                cv_skills=cv_skills,
                job_skills=job_skills,
                label=label,
                score=score,
                job_title=str(getattr(row, "job_title", "")) or None,
            ))
        return examples

    def to_huggingface_dataset(
        self,
        examples: Sequence[TrainingExample],
        tokenizer=None,
    ):
        """Convertit en Dataset HuggingFace."""
        from datasets import Dataset

        rows = [self.example_to_text(ex, tokenizer=tokenizer) for ex in examples]
        return Dataset.from_list(rows)

    def save_jsonl(self, examples: Sequence[TrainingExample], output_path: str | Path) -> None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            for ex in examples:
                rendered = self.example_to_text(ex)
                f.write(json.dumps({
                    "prompt": rendered["prompt"],
                    "completion": rendered["completion"],
                    "label": ex.label,
                }, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------- #
# Extracteur de skills heuristique (très basique, pour fallback)
# ---------------------------------------------------------------------- #

_COMMON_SKILLS_REGEX = None


def _extract_skills_heuristic(text: str) -> List[str]:
    """Extrait les skills connus du dictionnaire depuis un texte libre."""
    if not text:
        return []
    global _COMMON_SKILLS_REGEX
    if _COMMON_SKILLS_REGEX is None:
        import re
        from ai_pipeline.preprocessing.skill_normalizer import CANONICAL_SKILLS
        all_aliases = []
        for canonical, aliases in CANONICAL_SKILLS.items():
            all_aliases.append(canonical)
            all_aliases.extend(aliases)
        all_aliases = sorted(set(all_aliases), key=len, reverse=True)
        # Échapper pour regex
        escaped = [re.escape(a) for a in all_aliases]
        _COMMON_SKILLS_REGEX = re.compile(
            r"(?<![A-Za-z])(" + "|".join(escaped) + r")(?![A-Za-z])",
            re.IGNORECASE,
        )

    found = _COMMON_SKILLS_REGEX.findall(text)
    norm = SkillNormalizer()
    return norm.normalize_list(found)


if __name__ == "__main__":
    builder = MatchingDatasetBuilder()
    ex = TrainingExample(
        cv_text="Senior Python developer, 5 years of FastAPI and ML experience.",
        job_text="Looking for senior backend engineer with Python and ML.",
        cv_skills=["Python", "FastAPI", "ML", "Docker"],
        job_skills=["Python", "Machine Learning", "PostgreSQL"],
        label=1,
        score=0.82,
        cv_years=5,
        job_years=3,
        job_title="Senior Backend Engineer",
    )
    target = builder.build_target(ex)
    print(json.dumps(target, ensure_ascii=False, indent=2))
