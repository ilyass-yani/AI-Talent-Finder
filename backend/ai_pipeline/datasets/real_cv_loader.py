"""Loader de CVs réels depuis les PDFs de dataset.

Extrait les textes de CV des 4 PDFs fournis :
  - dataset_cvs_cybersecurite_50.pdf    (50 pages, 1 CV/page, sans couverture)
  - dataset_cv_finance (1).pdf          (51 pages : 1 couverture + 50 CVs)
  - dataset_cv_informatique (1).pdf     (51 pages : 1 couverture + 50 CVs)
  - dataset_cv_sante (1).pdf            (51 pages : 1 couverture + 50 CVs)

Usage :
    from ai_pipeline.datasets.real_cv_loader import RealCVLoader
    loader = RealCVLoader("/chemin/vers/cvs/")
    records = loader.load_all()   # List[CVRecord]
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration des PDFs disponibles
# ---------------------------------------------------------------------------
# Chaque entrée : (nom_fichier, domaine, a_page_couverture)
PDF_CONFIGS: List[tuple] = [
    ("dataset_cvs_cybersecurite_50.pdf",  "cybersecurite", False),
    ("dataset_cv_finance (1).pdf",         "finance",        True),
    ("dataset_cv_informatique (1).pdf",    "informatique",   True),
    ("dataset_cv_sante (1).pdf",           "sante",          True),
]


@dataclass
class CVRecord:
    """Un CV extrait d'un PDF."""
    text: str
    domain: str           # cybersecurite | finance | informatique | sante
    page_idx: int         # index de page dans le PDF source
    pdf_source: str       # nom du fichier PDF
    char_count: int = 0
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        self.char_count = len(self.text)

    def is_valid(self, min_chars: int = 100) -> bool:
        """Un CV est valide s'il contient assez de texte."""
        return self.char_count >= min_chars and self.text.strip() != ""


class RealCVLoader:
    """Charge tous les CVs réels depuis un répertoire de PDFs."""

    def __init__(self, pdf_dir: str | Path) -> None:
        self.pdf_dir = Path(pdf_dir)
        if not self.pdf_dir.exists():
            raise FileNotFoundError(f"Répertoire introuvable : {self.pdf_dir}")

    # -----------------------------------------------------------------------
    # Extraction bas niveau
    # -----------------------------------------------------------------------
    def _extract_page_text(self, page) -> str:
        """Extrait et nettoie le texte d'une page PDF."""
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            logger.warning("Échec extraction page : %s", exc)
            return ""

        # Supprimer les caractères de contrôle invisibles (ex. \x00 dans les PDFs Canva)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", text)
        # Normaliser les espaces multiples sauf les sauts de ligne
        text = re.sub(r"[ \t]{2,}", " ", text)
        # Supprimer les lignes entièrement vides doublées
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _is_cover_page(self, text: str) -> bool:
        """Détecte si la page est une couverture (peu de contenu)."""
        stripped = text.strip()
        if len(stripped) < 80:
            return True
        # Couvertures typiques : "Dataset CVs — FINANCE\n 50 Curriculum Vitae…"
        if re.search(r"Dataset\s+CVs?\s*[—-]", stripped, re.IGNORECASE):
            return True
        return False

    def _load_pdf(
        self,
        pdf_path: Path,
        domain: str,
        skip_cover: bool,
    ) -> List[CVRecord]:
        """Extrait tous les CVs d'un PDF. Retourne une liste de CVRecord."""
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ImportError(
                "pypdf est requis. Installez avec : pip install pypdf"
            )

        records: List[CVRecord] = []
        reader = PdfReader(str(pdf_path))
        logger.info(
            "Lecture de %s (%d pages, domaine=%s)",
            pdf_path.name,
            len(reader.pages),
            domain,
        )

        for page_idx, page in enumerate(reader.pages):
            text = self._extract_page_text(page)

            # Sauter la page de couverture si nécessaire
            if skip_cover and page_idx == 0 and self._is_cover_page(text):
                logger.debug("Page couverture ignorée : page 0 de %s", pdf_path.name)
                continue

            record = CVRecord(
                text=text,
                domain=domain,
                page_idx=page_idx,
                pdf_source=pdf_path.name,
            )

            if not record.is_valid():
                logger.debug(
                    "Page %d ignorée (trop courte : %d chars)",
                    page_idx,
                    record.char_count,
                )
                continue

            records.append(record)

        logger.info(
            "  → %d CVs valides extraits de %s", len(records), pdf_path.name
        )
        return records

    # -----------------------------------------------------------------------
    # API publique
    # -----------------------------------------------------------------------
    def load_domain(self, domain: str) -> List[CVRecord]:
        """Charge tous les CVs d'un domaine donné."""
        domain = domain.lower()
        results: List[CVRecord] = []
        for filename, dom, has_cover in PDF_CONFIGS:
            if dom != domain:
                continue
            pdf_path = self.pdf_dir / filename
            if not pdf_path.exists():
                logger.warning("PDF introuvable : %s", pdf_path)
                continue
            results.extend(self._load_pdf(pdf_path, dom, skip_cover=has_cover))
        return results

    def load_all(self, min_chars: int = 100) -> List[CVRecord]:
        """Charge tous les CVs des 4 PDFs. Filtre les pages trop courtes."""
        all_records: List[CVRecord] = []
        for filename, domain, has_cover in PDF_CONFIGS:
            pdf_path = self.pdf_dir / filename
            if not pdf_path.exists():
                logger.warning("PDF manquant, ignoré : %s", pdf_path)
                continue
            records = self._load_pdf(pdf_path, domain, skip_cover=has_cover)
            all_records.extend(records)

        logger.info(
            "Total CVs chargés : %d (sur 4 domaines)",
            len(all_records),
        )
        return all_records

    def stats(self) -> Dict[str, int]:
        """Retourne le nombre de CVs par domaine."""
        records = self.load_all()
        dist: Dict[str, int] = {}
        for r in records:
            dist[r.domain] = dist.get(r.domain, 0) + 1
        return dist
