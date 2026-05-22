# Extraction KPI Report

- Generated at: 2026-05-19T12:00:19.047779+00:00
- Threshold: 95.0
- Global score: 98.89/100
- Gate status: PASS

## Sample Scores

| Sample | Score | Identity | Career | Education | Skills | Enrichment | Missing fields |
|---|---:|---:|---:|---:|---:|---:|---|
| Senior backend engineer | 100.00 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | - |
| OCR noisy profile | 100.00 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | - |
| Minimal profile | 100.00 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | - |
| Anonymized Product Manager | 93.33 | 100.0 | 100.0 | 100.0 | 66.7 | 100.0 | skills |
| Anonymized DevOps Engineer | 100.00 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | - |
| Anonymized OCR-like Analyst | 100.00 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | - |

## Interpretation

- `>= 95`: production-grade extraction completeness target reached.
- `90-94.99`: very strong, improve edge-case handling.
- `< 90`: extraction quality needs focused improvements before release.

## Pipeline Coverage

Extraction -> Feature Engineering -> Matching -> Scoring -> Final Decision
