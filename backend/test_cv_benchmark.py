#!/usr/bin/env python3
"""
Multi-CV extraction benchmark.

Runs the CV extraction pipeline against several resume layouts and reports
coverage scores per section so we can track robustness across formats.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.cv_extractor import CVExtractionService


@dataclass
class BenchmarkSample:
    name: str
    text: str
    expected: Dict[str, int]


def _load_reference_text() -> str:
    """Best-effort loader for the existing test CV fixture."""
    fixture_path = Path(__file__).with_name("test_cv.txt")
    if not fixture_path.exists():
        return ""

    raw_bytes = fixture_path.read_bytes()
    for encoding in ("utf-16", "utf-16-le", "utf-8", "latin-1"):
        try:
            text = raw_bytes.decode(encoding)
            cleaned = text.strip()
            alpha_count = sum(1 for char in cleaned if char.isalpha())
            if len(cleaned) >= 20 and alpha_count >= 10 and "\x00" not in cleaned:
                return text
        except Exception:
            continue

    return ""


def _build_samples() -> List[BenchmarkSample]:
    return [
        BenchmarkSample(
            name="Structured English CV",
            text="""
JOHN SMITH
john.smith@example.com | +33 6 12 34 56 78 | linkedin.com/in/johnsmith

PROFESSIONAL SUMMARY
Senior Full Stack Developer with 8 years of experience in web development.

EXPERIENCE
Senior Developer - Tech Company Inc (2020-2024)
- Led team of 5 developers
- Built microservices using Python and FastAPI
- Managed PostgreSQL databases

Junior Developer - Startup LLC (2016-2020)
- Developed React frontend applications
- Worked with Node.js backend

EDUCATION
Bachelor of Science in Computer Science
University of Technology (2016)

SKILLS
Python, JavaScript, TypeScript, SQL, HTML/CSS, FastAPI, React, Docker
""".strip(),
            expected={"identity": 3, "experience": 2, "education": 2, "skills": 6, "enrichment": 1},
        ),
        BenchmarkSample(
            name="French CV with links",
            text="""
MARIE DUPONT
marie.dupont@gmail.com | 06 12 34 56 78 | Paris
linkedin.com/in/mariedupont | github.com/mdupont | mariedupont.dev

PROFIL
Chef de projet digital orientée produit et expérience client.

EXPÉRIENCES PROFESSIONNELLES
Responsable Marketing Digital - Entreprise X (2021 - Présent)
- Pilotage de campagnes multi-canaux
- Analyse des performances et reporting

Chef de projet CRM - Société Y (2018 - 2021)
- Mise en place d'automatisations marketing
- Coordination avec les équipes produit et design

FORMATION
Master Marketing Digital - Université de Lyon (2018)

COMPÉTENCES
Communication, Organisation, Gestion de projet, Leadership, Sens du contact

CERTIFICATIONS
Google Analytics Individual Qualification
HubSpot Inbound Marketing

PROJETS
Refonte du parcours d'onboarding client
""".strip(),
            expected={"identity": 3, "experience": 2, "education": 1, "skills": 4, "enrichment": 4},
        ),
        BenchmarkSample(
            name="OCR noisy CV",
            text="""
ALEXANDRE MARTIN
alex.martin@example.com

EXPERIENCE PROFESSIONNELLE
2022 - PRESENT | DATA ENGINEER | BLUE ANALYTICS
Built ETL pipelines on Airflow and Spark
Implemented data quality checks and dashboards

2020 - 2022 - BI ANALYST - RETAIL GROUP
Automated SQL reporting and Power BI models

FORMATION
2019 - Master Data Science - Paris School of AI

LANGUES
French English

COMPETENCES
Python, SQL, Airflow, Spark, Power BI, Communication

PROJECTS
Customer churn prediction using Python and scikit-learn
""".strip(),
            expected={"identity": 2, "experience": 2, "education": 1, "skills": 4, "enrichment": 2},
        ),
        BenchmarkSample(
            name="Minimal fallback CV",
            text="""
NOAH LEROY
noah.leroy@outlook.com

Some short CV text with little structure.
Python, SQL, Docker.
""".strip(),
            expected={"identity": 2, "experience": 0, "education": 0, "skills": 2, "enrichment": 0},
        ),
        BenchmarkSample(
            name="Ultra short CV",
            text="""
NADIA BENALI
nadia.benali@example.com
+33 6 98 76 54 32
Paris, France

Python | SQL | Data analysis
""".strip(),
            expected={"identity": 3, "experience": 0, "education": 0, "skills": 2, "enrichment": 1},
        ),
    ]


def _safe_len(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if value:
        return 1
    return 0


def _score_section(found: int, expected: int) -> float:
    if expected <= 0:
        return 100.0 if found == 0 else min(found * 25.0, 100.0)
    return min(found / expected, 1.0) * 100.0


def _build_section_scores(structured: Dict[str, Any]) -> Dict[str, float]:
    identity_found = sum(
        [
            1 if structured.get("full_name") else 0,
            1 if structured.get("email") else 0,
            1 if structured.get("phone") else 0,
        ]
    )
    experience_found = _safe_len(structured.get("experiences"))
    education_found = _safe_len(structured.get("education"))
    skills_found = _safe_len(structured.get("skills"))
    enrichment_found = sum(
        [
            _safe_len(structured.get("linkedin_urls")),
            _safe_len(structured.get("github_urls")),
            _safe_len(structured.get("portfolio_urls")),
            _safe_len(structured.get("certifications")),
            _safe_len(structured.get("projects")),
            _safe_len(structured.get("languages")),
            _safe_len(structured.get("soft_skills")),
            _safe_len(structured.get("interests")),
        ]
    )

    return {
        "identity": float(identity_found),
        "experience": float(experience_found),
        "education": float(education_found),
        "skills": float(skills_found),
        "enrichment": float(enrichment_found),
    }


def _overall_score(section_hits: Dict[str, float], expected: Dict[str, int]) -> float:
    weights = {
        "identity": 0.25,
        "experience": 0.30,
        "education": 0.15,
        "skills": 0.15,
        "enrichment": 0.15,
    }

    total = 0.0
    for section, weight in weights.items():
        total += weight * _score_section(int(section_hits[section]), expected.get(section, 0))

    return round(total, 1)


def _diagnose_missing_fields(sample: BenchmarkSample, structured: Dict[str, Any]) -> List[str]:
    """Return human-readable reasons for missing fields in a given sample."""
    reasons: List[str] = []
    lines = [line.strip() for line in sample.text.splitlines() if line.strip()]
    normalized_text = sample.text.lower()

    if not structured.get("full_name"):
        top_lines = lines[:5]
        has_name_like_line = any(
            2 <= len(re.findall(r"[A-Za-zÀ-ÿ'-]+", line)) <= 4 and not re.search(r"[@\d]", line)
            for line in top_lines
        )
        if has_name_like_line:
            reasons.append("Nom probable présent en haut du CV mais rejeté par les filtres de nom.")
        elif structured.get("email"):
            reasons.append("Nom absent mais un email est disponible: vérifier l'inférence depuis l'email.")
        else:
            reasons.append("Aucune ligne de nom claire détectée dans les premières lignes.")

    if not structured.get("phone"):
        has_phone_like_text = bool(
            re.search(r"\+?\d[\d\s().-]{7,}\d", sample.text)
        )
        if has_phone_like_text:
            reasons.append("Un numéro semble présent mais n'a pas passé la normalisation téléphone.")
        else:
            reasons.append("Aucun motif téléphone suffisamment clair détecté.")

    if not structured.get("experiences"):
        if any(keyword in normalized_text for keyword in ("experience", "experiences", "professionnelle", "work experience", "stage")):
            reasons.append("Section expérience détectée mais aucun bloc stable titre/entreprise/période n'a pu être construit.")
        else:
            reasons.append("Aucune section expérience ou ancre de période détectée.")

    if not structured.get("education") and any(keyword in normalized_text for keyword in ("formation", "education", "study", "universit", "school")):
        reasons.append("Section formation présente mais les lignes ne ressemblaient pas assez à de l'éducation.")

    if not structured.get("skills"):
        if any(token in normalized_text for token in ("python", "sql", "java", "react", "docker", "airflow", "spark")):
            reasons.append("Des mots-clés techniques existent mais la normalisation a raté l'extraction de compétences.")
        elif any(keyword in normalized_text for keyword in ("communication", "organisation", "leadership", "rigueur", "autonomie", "gestion de projet", "sens du contact")):
            reasons.append("Le CV contient surtout des compétences génériques/soft skills; vérifier si elles doivent être reportées dans skills ou seulement dans soft_skills.")
        else:
            reasons.append("Aucune compétence technique évidente détectée.")

    if not (
        structured.get("linkedin_urls")
        or structured.get("github_urls")
        or structured.get("portfolio_urls")
        or structured.get("projects")
        or structured.get("certifications")
    ):
        reasons.append("Aucun signal d'enrichissement (liens/projets/certifications) détecté.")

    return reasons


def run_benchmark(diagnostic: bool = False) -> int:
    service = CVExtractionService()
    samples = _build_samples()

    print("=" * 78)
    print("Multi-CV Extraction Benchmark")
    print("=" * 78)

    aggregate: List[float] = []

    for index, sample in enumerate(samples, start=1):
        result = service.extract_from_text(sample.text)
        structured = result.structured
        section_hits = _build_section_scores(structured)
        overall = _overall_score(section_hits, sample.expected)
        aggregate.append(overall)

        print(f"\n[{index}] {sample.name}")
        print(f"  Overall: {overall:.1f}/100")
        print(
            "  Sections: "
            f"identity={_score_section(int(section_hits['identity']), sample.expected['identity']):.1f}, "
            f"experience={_score_section(int(section_hits['experience']), sample.expected['experience']):.1f}, "
            f"education={_score_section(int(section_hits['education']), sample.expected['education']):.1f}, "
            f"skills={_score_section(int(section_hits['skills']), sample.expected['skills']):.1f}, "
            f"enrichment={_score_section(int(section_hits['enrichment']), sample.expected['enrichment']):.1f}"
        )
        print(
            "  Extracted: "
            f"name={bool(structured.get('full_name'))}, "
            f"email={bool(structured.get('email'))}, "
            f"phone={bool(structured.get('phone'))}, "
            f"experiences={len(structured.get('experiences', []))}, "
            f"education={len(structured.get('education', []))}, "
            f"skills={len(structured.get('skills', []))}, "
            f"links={len(structured.get('linkedin_urls', [])) + len(structured.get('github_urls', [])) + len(structured.get('portfolio_urls', []))}, "
            f"projects={len(structured.get('projects', []))}, "
            f"certifications={len(structured.get('certifications', []))}"
        )

        if diagnostic:
            reasons = _diagnose_missing_fields(sample, structured)
            if reasons:
                print("  Diagnostics:")
                for reason in reasons:
                    print(f"    - {reason}")

    average_score = round(sum(aggregate) / len(aggregate), 1) if aggregate else 0.0
    print("\n" + "=" * 78)
    print(f"Average overall score: {average_score:.1f}/100")
    print("=" * 78)

    return 0 if average_score >= 70.0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the CV extraction benchmark")
    parser.add_argument(
        "--diagnostic",
        action="store_true",
        help="Print human-readable reasons for missing fields",
    )
    args = parser.parse_args()
    raise SystemExit(run_benchmark(diagnostic=args.diagnostic))