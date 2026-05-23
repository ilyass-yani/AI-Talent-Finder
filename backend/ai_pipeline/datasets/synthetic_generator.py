"""Synthetic training data generator for CV ↔ Job matching.

Generates ``(cv, job, label, metadata)`` quadruples by:
  1. Sampling a job archetype (Backend, Data Scientist, Frontend, etc.)
     from a curated template library
  2. Sampling a CV that is either ``compatible``, ``partial``, or
     ``incompatible`` with the job
  3. Filling in templates with realistic skills, experience, education

The result is balanced across classes and ready to feed into
:class:`ai_pipeline.llm.dataset_builder.MatchingDatasetBuilder` for
LLM fine-tuning.
"""
from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


# --------------------------------------------------------------------------- #
# Job archetypes
# --------------------------------------------------------------------------- #
JOB_ARCHETYPES: Dict[str, Dict] = {
    "backend_python": {
        "titles": ["Backend Python Developer", "Software Engineer Python", "Python Backend Engineer"],
        "required": ["Python", "FastAPI", "PostgreSQL", "Docker", "Git", "REST API"],
        "nice": ["Redis", "Kubernetes", "AWS", "GCP", "Celery"],
        "seniority": ["Junior", "Confirmé", "Senior"],
        "min_years": {"Junior": 0, "Confirmé": 2, "Senior": 5},
    },
    "data_scientist": {
        "titles": ["Data Scientist", "Machine Learning Engineer", "AI Engineer"],
        "required": ["Python", "Machine Learning", "Pandas", "Scikit-learn", "SQL", "PyTorch"],
        "nice": ["TensorFlow", "MLflow", "Spark", "Airflow", "Kubeflow"],
        "seniority": ["Junior", "Confirmé", "Senior"],
        "min_years": {"Junior": 0, "Confirmé": 2, "Senior": 5},
    },
    "frontend_react": {
        "titles": ["Frontend Developer", "React Developer", "Senior Frontend Engineer"],
        "required": ["JavaScript", "TypeScript", "React", "HTML", "CSS", "Git"],
        "nice": ["Next.js", "Tailwind CSS", "GraphQL", "Jest"],
        "seniority": ["Junior", "Confirmé", "Senior"],
        "min_years": {"Junior": 0, "Confirmé": 2, "Senior": 5},
    },
    "fullstack": {
        "titles": ["Full-Stack Engineer", "Fullstack Developer"],
        "required": ["JavaScript", "TypeScript", "React", "Node.js", "PostgreSQL", "Docker"],
        "nice": ["AWS", "Next.js", "Redis", "GraphQL"],
        "seniority": ["Junior", "Confirmé", "Senior"],
        "min_years": {"Junior": 0, "Confirmé": 2, "Senior": 5},
    },
    "devops": {
        "titles": ["DevOps Engineer", "Site Reliability Engineer", "Cloud Engineer"],
        "required": ["Linux", "Docker", "Kubernetes", "Terraform", "AWS", "CI/CD"],
        "nice": ["Ansible", "Prometheus", "Grafana", "GitLab CI"],
        "seniority": ["Confirmé", "Senior"],
        "min_years": {"Junior": 1, "Confirmé": 3, "Senior": 6},
    },
    "llm_engineer": {
        "titles": ["LLM Engineer", "Generative AI Engineer", "NLP Engineer"],
        "required": ["Python", "PyTorch", "HuggingFace Transformers", "LoRA", "LangChain"],
        "nice": ["RAG", "LlamaIndex", "vLLM", "QLoRA", "FAISS"],
        "seniority": ["Confirmé", "Senior"],
        "min_years": {"Junior": 1, "Confirmé": 2, "Senior": 4},
    },
}

# Random pools for unrelated skills (used to create incompatible candidates)
UNRELATED_SKILL_POOL = [
    "COBOL", "Fortran", "Salesforce", "SAP", "Photoshop", "Illustrator",
    "AutoCAD", "Revit", "Excel", "Word", "PowerPoint", "Comptabilité",
    "Marketing", "SEO", "Copywriting", "WordPress",
]

EDU_LEVELS = ["BTS", "Licence", "Master", "Ingénieur", "Doctorat"]
LANGUAGES = {"fr": ["B2", "C1", "C2", "Natif"], "en": ["B1", "B2", "C1", "C2"]}


@dataclass
class SyntheticExample:
    cv_text: str
    job_text: str
    label: str  # "compatible" | "partial" | "incompatible"
    score: float
    cv_skills: List[str] = field(default_factory=list)
    job_skills: List[str] = field(default_factory=list)
    archetype: str = ""
    seniority: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Templates
# --------------------------------------------------------------------------- #
_JOB_TEMPLATE = """Poste : {title}
Niveau : {seniority}
Localisation : {location}

Description :
Nous recherchons un(e) {title} pour rejoindre notre équipe.
Vos missions incluront le développement, la maintenance et l'amélioration
de nos systèmes.

Compétences requises :
{required_block}

Compétences appréciées :
{nice_block}

Expérience minimum : {min_years} ans
Formation : {edu_level} en informatique ou équivalent
"""

_CV_TEMPLATE = """Nom : {name}
Email : {email}
Localisation : {location}

Formation :
- {edu_level} en Informatique, École supérieure ({edu_year})

Expérience professionnelle ({years} ans):
- {role} chez {company}, {start_year} - aujourd'hui
  Missions : développement de fonctionnalités, code review, déploiement.

Compétences techniques :
{skills_block}

Langues :
- Français : {fr_level}
- Anglais : {en_level}
"""

LOCATIONS = ["Paris", "Lyon, France", "Casablanca", "Rabat", "Marseille", "Bordeaux"]


# --------------------------------------------------------------------------- #
# Generator
# --------------------------------------------------------------------------- #
class SyntheticGenerator:
    def __init__(self, seed: int = 42) -> None:
        self.rng = random.Random(seed)

    # -------- helpers ---------------------------------------------------- #
    def _bullet(self, items: List[str]) -> str:
        return "\n".join(f"- {it}" for it in items)

    def _sample_job(self, archetype: str) -> Dict:
        spec = JOB_ARCHETYPES[archetype]
        seniority = self.rng.choice(spec["seniority"])
        required = list(spec["required"])
        nice = self.rng.sample(spec["nice"], k=min(3, len(spec["nice"])))
        min_years = spec["min_years"][seniority]
        edu_level = self.rng.choice(["Licence", "Master", "Ingénieur"])

        job_text = _JOB_TEMPLATE.format(
            title=self.rng.choice(spec["titles"]),
            seniority=seniority,
            location=self.rng.choice(LOCATIONS),
            required_block=self._bullet(required),
            nice_block=self._bullet(nice),
            min_years=min_years,
            edu_level=edu_level,
        )
        return {
            "text": job_text,
            "skills": required + nice,
            "seniority": seniority,
            "min_years": min_years,
            "edu_level": edu_level,
        }

    def _sample_cv(self, archetype: str, kind: str, job: Dict) -> Dict:
        """Generate a CV that is compatible / partial / incompatible with `job`."""
        spec = JOB_ARCHETYPES[archetype]
        if kind == "compatible":
            cv_skills = list(spec["required"]) + self.rng.sample(spec["nice"], 2)
            years = job["min_years"] + self.rng.randint(1, 4)
        elif kind == "partial":
            keep_n = max(1, len(spec["required"]) // 2)
            cv_skills = self.rng.sample(spec["required"], keep_n)
            cv_skills += self.rng.sample(UNRELATED_SKILL_POOL, 2)
            years = max(0, job["min_years"] - self.rng.randint(0, 1))
        else:  # incompatible
            cv_skills = self.rng.sample(UNRELATED_SKILL_POOL, 5)
            years = self.rng.randint(0, 2)

        cv_text = _CV_TEMPLATE.format(
            name=self.rng.choice(["Karim Benali", "Yasmine Idrissi", "Marc Dupont", "Sarah Cohen", "Slocks ESISA"]),
            email="candidat@example.com",
            location=self.rng.choice(LOCATIONS),
            edu_level=self.rng.choice(EDU_LEVELS),
            edu_year=2024 - self.rng.randint(0, 10),
            years=years,
            role=self.rng.choice(spec["titles"]),
            company=self.rng.choice(["TechCorp", "DataSoft", "AI Labs", "WebStudio", "NovaTech"]),
            start_year=2024 - max(years, 1),
            skills_block=self._bullet(cv_skills),
            fr_level=self.rng.choice(LANGUAGES["fr"]),
            en_level=self.rng.choice(LANGUAGES["en"]),
        )
        return {"text": cv_text, "skills": cv_skills, "years": years}

    # -------- public API ------------------------------------------------- #
    def generate(
        self,
        n: int = 1000,
        class_balance: Optional[Dict[str, float]] = None,
    ) -> List[SyntheticExample]:
        balance = class_balance or {"compatible": 0.4, "partial": 0.3, "incompatible": 0.3}
        out: List[SyntheticExample] = []
        for _ in range(n):
            archetype = self.rng.choice(list(JOB_ARCHETYPES.keys()))
            kind = self.rng.choices(
                list(balance.keys()), weights=list(balance.values()), k=1
            )[0]
            job = self._sample_job(archetype)
            cv = self._sample_cv(archetype, kind, job)

            score = {"compatible": 0.85, "partial": 0.55, "incompatible": 0.25}[kind]
            score += self.rng.uniform(-0.1, 0.1)
            score = max(0.05, min(0.95, score))

            out.append(
                SyntheticExample(
                    cv_text=cv["text"],
                    job_text=job["text"],
                    label=kind,
                    score=round(score, 3),
                    cv_skills=cv["skills"],
                    job_skills=job["skills"],
                    archetype=archetype,
                    seniority=job["seniority"],
                )
            )
        return out

    def save_jsonl(self, examples: List[SyntheticExample], path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            for ex in examples:
                fh.write(json.dumps(ex.to_dict(), ensure_ascii=False) + "\n")

    def save_csv(self, examples: List[SyntheticExample], path: str | Path) -> None:
        import csv

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["cv_text", "job_text", "label", "score", "archetype", "seniority"])
            for ex in examples:
                w.writerow([ex.cv_text, ex.job_text, ex.label, ex.score, ex.archetype, ex.seniority])
