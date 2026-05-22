#!/usr/bin/env python3
"""Quality gate for CV extraction completeness.

Goal:
- Provide a measurable extraction quality score instead of claiming 100%.
- Evaluate identity/career/education/skills/enrichment coverage field-by-field.
- Fail fast when the global score is under a configurable threshold.

Usage:
  cd backend
  python scripts/run_extraction_quality_gate.py --threshold 95
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.cv_extractor import CVExtractionService


@dataclass
class GoldSample:
    name: str
    text: str
    expected_min_counts: Dict[str, int]


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE_PATH = SCRIPT_ROOT / "tests" / "fixtures" / "extraction_gold_samples.json"
REPORTS_DIR = SCRIPT_ROOT / "reports"


def _safe_len(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    return 1 if value else 0


def _extract_field_counts(structured: Dict[str, Any]) -> Dict[str, int]:
    return {
        "full_name": 1 if structured.get("full_name") else 0,
        "email": 1 if structured.get("email") else 0,
        "phone": 1 if structured.get("phone") else 0,
        "job_titles": _safe_len(structured.get("job_titles")),
        "companies": _safe_len(structured.get("companies")),
        "experiences": _safe_len(structured.get("experiences")),
        "education": _safe_len(structured.get("education")),
        "skills": _safe_len(structured.get("skills")),
        "languages": _safe_len(structured.get("languages")),
        "soft_skills": _safe_len(structured.get("soft_skills")),
        "projects": _safe_len(structured.get("projects")),
        "certifications": _safe_len(structured.get("certifications")),
        "linkedin_urls": _safe_len(structured.get("linkedin_urls")),
        "github_urls": _safe_len(structured.get("github_urls")),
        "portfolio_urls": _safe_len(structured.get("portfolio_urls")),
        "profile_summary": 1 if structured.get("profile_summary") else 0,
        "interests": _safe_len(structured.get("interests")),
    }


def _field_score(found: int, expected: int) -> float:
    if expected <= 0:
        return 100.0
    return min((found / expected) * 100.0, 100.0)


def _category_score(found: Dict[str, int], expected: Dict[str, int], fields: List[str]) -> float:
    if not fields:
        return 100.0
    return round(sum(_field_score(found.get(f, 0), expected.get(f, 0)) for f in fields) / len(fields), 2)


def _build_gold_samples() -> List[GoldSample]:
    return [
        GoldSample(
            name="Senior backend engineer",
            text="""
Yassine El Amrani

yassine.elamrani@gmail.com | +33 6 12 34 56 78
LinkedIn: https://www.linkedin.com/in/yassine-elamrani
GitHub: https://github.com/yelamrani
Portfolio: https://yelamrani.dev

PROFIL
Ingénieur backend Python orienté microservices et architecture scalable.

EXPERIENCES PROFESSIONNELLES
Senior Backend Engineer - NovaTech (2022 - 2026)
- Conception d'APIs FastAPI et pipelines Kafka
- Mise en place CI/CD et monitoring

Software Engineer - DataFlow Labs (2019 - 2022)
- Développement Python, PostgreSQL, Redis

FORMATION
Master Informatique - Université de Lille (2019)

COMPETENCES
Python, FastAPI, Docker, Kubernetes, PostgreSQL, Redis, AWS

LANGUES
Français, Anglais

CERTIFICATIONS
AWS Certified Developer Associate

PROJETS
Moteur de matching CV / Job avec scoring explicable
""".strip(),
            expected_min_counts={
                "full_name": 1,
                "email": 1,
                "phone": 1,
                "job_titles": 2,
                "companies": 2,
                "experiences": 1,
                "education": 1,
                "skills": 6,
                "languages": 2,
                "projects": 1,
                "certifications": 1,
                "linkedin_urls": 1,
                "github_urls": 1,
                "portfolio_urls": 1,
                "profile_summary": 1,
            },
        ),
        GoldSample(
            name="OCR noisy profile",
            text="""
SAMIRA BEN  YOUSSEF
samira.ben@gmail.com
+33 7 88 11 22 33

EXPERIENCE PROFESSIONELLE
2023 - PRESNT | DATA SCIENTIST | BLUE METRICS
Build modeles ML, NLP, dashboards

2020 - 2023 | DATA ANALYST | RETAIL INSIGHTS
SQL reporting, Power BI, A/B tests

FORMATION
Master Data Science - Univ Paris Saclay

SKILLS
Pythn, Pandas, Numpy, Scikit Learn, SQL, Power BI, Communication

PROJECTS
Churn prediction and recommendation pipeline
""".strip(),
            expected_min_counts={
                "full_name": 1,
                "email": 1,
                "phone": 1,
                "job_titles": 1,
                "companies": 1,
                "experiences": 1,
                "education": 1,
                "skills": 4,
                "projects": 1,
            },
        ),
        GoldSample(
            name="Minimal profile",
            text="""
Ines M.
ines.m@example.com
Python, SQL, Docker
""".strip(),
            expected_min_counts={
                "full_name": 1,
                "email": 1,
                "skills": 2,
            },
        ),
    ]


def _load_external_gold_samples(path: Optional[Path]) -> List[GoldSample]:
    fixture_path = path or DEFAULT_FIXTURE_PATH
    if not fixture_path.exists():
        return []

    try:
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    except Exception:
        return []

    raw_samples = payload.get("samples", []) if isinstance(payload, dict) else []
    samples: List[GoldSample] = []
    for raw in raw_samples:
        if not isinstance(raw, dict):
            continue

        name = str(raw.get("name", "")).strip()
        text = str(raw.get("text", "")).strip()
        expected = raw.get("expected_min_counts", {})

        if not name or not text or not isinstance(expected, dict):
            continue

        normalized_expected: Dict[str, int] = {}
        for key, value in expected.items():
            try:
                normalized_expected[str(key)] = int(value)
            except Exception:
                continue

        samples.append(GoldSample(name=name, text=text, expected_min_counts=normalized_expected))

    return samples


def _write_kpi_markdown(report: Dict[str, Any], output_path: Path) -> None:
    lines: List[str] = []
    lines.append("# Extraction KPI Report")
    lines.append("")
    lines.append(f"- Generated at: {report.get('generated_at')}")
    lines.append(f"- Threshold: {report.get('threshold')}")
    lines.append(f"- Global score: {report.get('global_score')}/100")
    lines.append(f"- Gate status: {'PASS' if report.get('passed') else 'FAIL'}")
    lines.append("")
    lines.append("## Sample Scores")
    lines.append("")
    lines.append("| Sample | Score | Identity | Career | Education | Skills | Enrichment | Missing fields |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---|")

    for sample in report.get("samples", []):
        category_scores = sample.get("category_scores", {}) if isinstance(sample, dict) else {}
        missing_fields = sample.get("missing_fields", []) if isinstance(sample, dict) else []
        missing_summary = ", ".join(str(item.get("field")) for item in missing_fields if isinstance(item, dict))
        lines.append(
            f"| {sample.get('sample', '')} | {sample.get('quality_score', 0):.2f} | "
            f"{category_scores.get('identity', 0):.1f} | {category_scores.get('career', 0):.1f} | "
            f"{category_scores.get('education', 0):.1f} | {category_scores.get('skills', 0):.1f} | "
            f"{category_scores.get('enrichment', 0):.1f} | {missing_summary or '-'} |"
        )

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("- `>= 95`: production-grade extraction completeness target reached.")
    lines.append("- `90-94.99`: very strong, improve edge-case handling.")
    lines.append("- `< 90`: extraction quality needs focused improvements before release.")
    lines.append("")
    lines.append("## Pipeline Coverage")
    lines.append("")
    lines.append("Extraction -> Feature Engineering -> Matching -> Scoring -> Final Decision")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_quality_gate(threshold: float, fixtures_path: Optional[Path] = None) -> int:
    service = CVExtractionService()

    category_fields = {
        "identity": ["full_name", "email", "phone"],
        "career": ["job_titles", "companies", "experiences"],
        "education": ["education", "languages"],
        "skills": ["skills", "soft_skills"],
        "enrichment": ["projects", "certifications", "linkedin_urls", "github_urls", "portfolio_urls", "profile_summary", "interests"],
    }
    category_weights = {
        "identity": 0.30,
        "career": 0.25,
        "education": 0.15,
        "skills": 0.20,
        "enrichment": 0.10,
    }

    samples = _build_gold_samples() + _load_external_gold_samples(fixtures_path)
    if not samples:
        print("No samples found. Provide built-in or fixture samples.")
        return 1
    sample_reports: List[Dict[str, Any]] = []
    aggregate_score = 0.0

    print("=" * 84)
    print("Extraction Quality Gate")
    print("=" * 84)

    for idx, sample in enumerate(samples, start=1):
        result = service.extract_from_text(sample.text)
        structured = result.structured
        found = _extract_field_counts(structured)

        category_scores: Dict[str, float] = {}
        weighted_score = 0.0
        for category, fields in category_fields.items():
            score = _category_score(found, sample.expected_min_counts, fields)
            category_scores[category] = score
            weighted_score += score * category_weights[category]

        weighted_score = round(weighted_score, 2)
        aggregate_score += weighted_score

        missing_fields = []
        for field_name, expected_min in sample.expected_min_counts.items():
            if found.get(field_name, 0) < expected_min:
                missing_fields.append(
                    {
                        "field": field_name,
                        "expected_min": expected_min,
                        "found": found.get(field_name, 0),
                    }
                )

        sample_reports.append(
            {
                "sample": sample.name,
                "quality_score": weighted_score,
                "quality_from_service": float(result.quality_score),
                "category_scores": category_scores,
                "missing_fields": missing_fields,
                "counts": found,
                "expected_min_counts": sample.expected_min_counts,
            }
        )

        print(f"[{idx}] {sample.name}: {weighted_score:.2f}/100")
        print(
            "    categories: "
            f"identity={category_scores['identity']:.1f}, "
            f"career={category_scores['career']:.1f}, "
            f"education={category_scores['education']:.1f}, "
            f"skills={category_scores['skills']:.1f}, "
            f"enrichment={category_scores['enrichment']:.1f}"
        )
        if missing_fields:
            concise = ", ".join(f"{m['field']}({m['found']}/{m['expected_min']})" for m in missing_fields[:6])
            print(f"    missing: {concise}")

    global_score = round(aggregate_score / max(1, len(samples)), 2)
    passed = global_score >= threshold

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "threshold": threshold,
        "global_score": global_score,
        "passed": passed,
        "samples": sample_reports,
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "extraction_quality_gate.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    kpi_path = REPORTS_DIR / "extraction_kpi.md"
    _write_kpi_markdown(report, kpi_path)

    print("-" * 84)
    print(f"Global score: {global_score:.2f}/100")
    print(f"Threshold: {threshold:.2f}")
    print(f"Gate status: {'PASS' if passed else 'FAIL'}")
    print(f"Report saved: {report_path}")
    print(f"KPI markdown saved: {kpi_path}")
    print("=" * 84)

    return 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CV extraction completeness quality gate")
    parser.add_argument("--threshold", type=float, default=95.0, help="Minimum global score to pass")
    parser.add_argument(
        "--fixtures",
        type=str,
        default=str(DEFAULT_FIXTURE_PATH),
        help="Optional JSON fixture path with anonymized gold samples",
    )
    args = parser.parse_args()
    fixtures_path = Path(args.fixtures) if args.fixtures else None
    return run_quality_gate(args.threshold, fixtures_path)


if __name__ == "__main__":
    raise SystemExit(main())
