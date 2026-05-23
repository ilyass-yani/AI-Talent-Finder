#!/usr/bin/env python
"""Construit le dataset d'entraînement depuis les CVs réels (PDFs).

Remplace ``scripts/ai_pipeline/generate_synthetic_data.py``.

Usage :
    # Depuis la racine du repo
    python scripts/ai_pipeline/build_dataset_from_real_cvs.py \\
        --pdf-dir data/cvs/ \\
        --output data/real_cv_pairs.jsonl \\
        --n-per-cv 3

    # Avec CSV en sortie
    python scripts/ai_pipeline/build_dataset_from_real_cvs.py \\
        --pdf-dir data/cvs/ \\
        --output data/real_cv_pairs.csv \\
        --format csv \\
        --n-per-cv 4 \\
        --no-augment

Notes :
    - Les PDFs attendus dans --pdf-dir :
        * dataset_cvs_cybersecurite_50.pdf
        * dataset_cv_finance (1).pdf
        * dataset_cv_informatique (1).pdf
        * dataset_cv_sante (1).pdf
    - Avec --n-per-cv 3 et 200 CVs → ~600 paires équilibrées
    - Ajoutez --hybrid pour mixer avec des données synthétiques (fallback)
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Ajout du backend au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from ai_pipeline.datasets.real_cv_pair_builder import RealCVPairBuilder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Génère un dataset d'entraînement depuis des CVs réels (PDF)."
    )
    p.add_argument(
        "--pdf-dir",
        required=True,
        help="Répertoire contenant les 4 PDFs de CVs.",
    )
    p.add_argument(
        "--output",
        default="data/real_cv_pairs.jsonl",
        help="Chemin du fichier de sortie (.jsonl ou .csv).",
    )
    p.add_argument(
        "--format",
        default="jsonl",
        choices=["jsonl", "csv"],
        help="Format de sortie (défaut : jsonl).",
    )
    p.add_argument(
        "--n-per-cv",
        type=int,
        default=3,
        help="Nombre de paires à générer par CV (défaut : 3).",
    )
    p.add_argument(
        "--no-augment",
        action="store_true",
        help="Désactive l'augmentation textuelle légère.",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Graine aléatoire pour la reproductibilité.",
    )
    p.add_argument(
        "--hybrid",
        action="store_true",
        help=(
            "Mode hybride : complète les données réelles avec des données "
            "synthétiques pour atteindre un minimum de paires."
        ),
    )
    p.add_argument(
        "--hybrid-min",
        type=int,
        default=1000,
        help="Nombre minimum de paires en mode --hybrid (défaut : 1000).",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    pdf_dir = Path(args.pdf_dir)

    if not pdf_dir.exists():
        logger.error("Répertoire PDF introuvable : %s", pdf_dir)
        return 1

    builder = RealCVPairBuilder(pdf_dir=pdf_dir, seed=args.seed)

    logger.info(
        "Chargement des CVs depuis %s (n_per_cv=%d, augment=%s)…",
        pdf_dir,
        args.n_per_cv,
        not args.no_augment,
    )

    try:
        examples = builder.build(
            n_per_cv=args.n_per_cv,
            augment=not args.no_augment,
        )
    except RuntimeError as exc:
        logger.error("Erreur lors de la construction des paires : %s", exc)
        return 1

    # --- Mode hybride : compléter avec du synthétique si besoin ---
    if args.hybrid and len(examples) < args.hybrid_min:
        logger.info(
            "Mode hybride : %d paires réelles < %d minimum. "
            "Complément avec données synthétiques…",
            len(examples),
            args.hybrid_min,
        )
        try:
            from ai_pipeline.datasets.synthetic_generator import SyntheticGenerator

            n_synthetic = args.hybrid_min - len(examples)
            gen = SyntheticGenerator(seed=args.seed)
            synthetic = gen.generate(n=n_synthetic)

            # Convertir SyntheticExample → même format dict pour la sérialisation
            import json
            from ai_pipeline.datasets.real_cv_pair_builder import RealCVExample

            for sx in synthetic:
                examples.append(
                    RealCVExample(
                        cv_text=sx.cv_text,
                        job_text=sx.job_text,
                        label=sx.label,
                        score=sx.score,
                        cv_domain=sx.archetype,
                        job_domain=sx.archetype,
                        pdf_source="synthetic",
                        page_idx=-1,
                        archetype=sx.archetype,
                    )
                )
            logger.info(
                "Après complément hybride : %d paires totales.", len(examples)
            )
        except ImportError:
            logger.warning(
                "SyntheticGenerator non disponible, mode hybride ignoré."
            )

    # --- Statistiques finales ---
    dist: dict = {}
    for ex in examples:
        dist[ex.label] = dist.get(ex.label, 0) + 1
    logger.info("Distribution finale : %s", dist)

    by_domain: dict = {}
    for ex in examples:
        by_domain[ex.cv_domain] = by_domain.get(ex.cv_domain, 0) + 1
    logger.info("CVs par domaine : %s", by_domain)

    # --- Sauvegarde ---
    out_path = Path(args.output)
    if args.format == "csv":
        builder.save_csv(examples, out_path)
    else:
        builder.save_jsonl(examples, out_path)

    logger.info(
        "✅ Dataset généré : %s (%d paires)", out_path, len(examples)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
