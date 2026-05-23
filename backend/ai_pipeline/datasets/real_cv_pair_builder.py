"""Constructeur de paires d'entraînement à partir de CVs réels.

Remplace ``SyntheticGenerator`` pour le pipeline d'entraînement.

Stratégie de labeling :
  - ``compatible``   : CV et offre du même domaine          (score 0.75–0.95)
  - ``partial``      : CV d'un domaine adjacent/transversal (score 0.40–0.65)
  - ``incompatible`` : CV d'un domaine sans rapport         (score 0.05–0.35)

Les offres d'emploi (``job_text``) sont générées à partir de templates
réalistes par domaine, enrichis des compétences détectées dans les CVs.

Usage :
    builder = RealCVPairBuilder(pdf_dir="/chemin/cvs")
    examples = builder.build(n_per_cv=3, augment=True)
    builder.save_jsonl(examples, "data/real_cv_pairs.jsonl")
"""
from __future__ import annotations

import json
import logging
import random
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .real_cv_loader import CVRecord, RealCVLoader

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Templates d'offres d'emploi par domaine
# ---------------------------------------------------------------------------
DOMAIN_JOB_TEMPLATES: Dict[str, List[Dict]] = {
    "cybersecurite": [
        {
            "title": "Analyste SOC",
            "required": ["SIEM", "Splunk", "IDS/IPS", "Wireshark", "ISO 27001"],
            "nice": ["OSINT", "Threat Intelligence", "ElasticSearch", "Snort"],
            "description": (
                "Nous recherchons un Analyste SOC pour surveiller les incidents "
                "de sécurité, analyser les alertes et répondre aux cybermenaces. "
                "Vous participerez à la veille sécurité et à la gestion des vulnérabilités."
            ),
        },
        {
            "title": "Pentester / Ethical Hacker",
            "required": ["Kali Linux", "Metasploit", "Burp Suite", "Nmap", "OWASP"],
            "nice": ["CEH", "OSCP", "Python", "Reverse Engineering"],
            "description": (
                "Réalisation de tests d'intrusion sur des infrastructures web et réseaux. "
                "Rédaction de rapports de vulnérabilité et recommandations. "
                "Collaboration avec les équipes de développement pour corriger les failles."
            ),
        },
        {
            "title": "Consultant Cybersécurité GRC",
            "required": ["ISO 27001", "RGPD", "Analyse de risques", "Audit sécurité"],
            "nice": ["NIST", "PCI-DSS", "SOC 2", "Gestion des conformités"],
            "description": (
                "Accompagnement des clients dans leur démarche de conformité et gestion "
                "des risques cybersécurité. Réalisation d'audits, rédaction de politiques "
                "de sécurité et formation des équipes."
            ),
        },
        {
            "title": "Ingénieur Sécurité Cloud",
            "required": ["AWS Security", "Azure Security", "IAM", "SIEM", "Docker"],
            "nice": ["Kubernetes", "Terraform", "CIS Benchmarks", "Zero Trust"],
            "description": (
                "Conception et implémentation d'architectures sécurisées sur le cloud. "
                "Mise en place de politiques IAM, surveillance des environnements cloud "
                "et réponse aux incidents."
            ),
        },
    ],
    "finance": [
        {
            "title": "Analyste Financier",
            "required": ["Analyse financière", "Modélisation Excel", "IFRS", "SAP"],
            "nice": ["Bloomberg", "Python Finance", "VBA", "CFA"],
            "description": (
                "Réalisation d'analyses financières, modélisation de valorisation "
                "d'entreprises et reporting financier. Production de synthèses pour "
                "la direction générale et les investisseurs."
            ),
        },
        {
            "title": "Gestionnaire de Risques",
            "required": ["Gestion des risques", "Scoring crédit", "KYC", "Bâle III"],
            "nice": ["ACCA", "VaR", "Stress testing", "Audit interne"],
            "description": (
                "Identification et évaluation des risques financiers et opérationnels. "
                "Mise en place de dispositifs de contrôle interne et reporting "
                "réglementaire (Bâle III, IFRS 9)."
            ),
        },
        {
            "title": "Contrôleur de Gestion",
            "required": ["Contrôle budgétaire", "SAP FI/CO", "Reporting", "Excel"],
            "nice": ["Power BI", "Oracle Hyperion", "CIMA", "Consolidation"],
            "description": (
                "Pilotage budgétaire et élaboration des tableaux de bord financiers. "
                "Analyse des écarts, projections et support aux décisions stratégiques "
                "de la direction financière."
            ),
        },
        {
            "title": "Auditeur Interne",
            "required": ["Audit interne", "Contrôle interne", "IFRS", "Gestion ALM"],
            "nice": ["CIA", "ACCA", "CFA Level 1", "SAP"],
            "description": (
                "Planification et réalisation des missions d'audit interne. "
                "Évaluation du système de contrôle interne, identification des risques "
                "et formulation de recommandations d'amélioration."
            ),
        },
    ],
    "informatique": [
        {
            "title": "Développeur Full-Stack",
            "required": ["JavaScript", "TypeScript", "React", "Node.js", "SQL", "Git"],
            "nice": ["Next.js", "Docker", "GraphQL", "PostgreSQL"],
            "description": (
                "Développement de fonctionnalités front-end et back-end pour nos "
                "applications web. Participation aux revues de code, rédaction des "
                "tests unitaires et déploiement CI/CD."
            ),
        },
        {
            "title": "Ingénieur DevOps",
            "required": ["Docker", "Kubernetes", "CI/CD", "Linux", "Terraform"],
            "nice": ["AWS", "Prometheus", "Grafana", "Ansible", "GitLab CI"],
            "description": (
                "Mise en place et maintenance de pipelines CI/CD. Gestion des "
                "infrastructures cloud, monitoring, automatisation et amélioration "
                "continue de la fiabilité des systèmes."
            ),
        },
        {
            "title": "Data Engineer",
            "required": ["Python", "SQL", "Spark", "Airflow", "PostgreSQL"],
            "nice": ["dbt", "Kafka", "Snowflake", "BigQuery", "MLflow"],
            "description": (
                "Conception et développement de pipelines de données. Ingestion, "
                "transformation et stockage de données volumineuses. Collaboration "
                "avec les équipes Data Science pour la mise en production des modèles."
            ),
        },
        {
            "title": "Ingénieur QA / Test",
            "required": ["Tests automatisés", "Selenium", "JUnit", "Python", "CI/CD"],
            "nice": ["Cypress", "k6", "ISTQB", "BDD", "Jira"],
            "description": (
                "Définition et exécution des stratégies de test (fonctionnel, performance, "
                "sécurité). Automatisation des tests et intégration dans les pipelines CI/CD. "
                "Reporting des défauts et suivi qualité."
            ),
        },
    ],
    "sante": [
        {
            "title": "Médecin / Praticien Hospitalier",
            "required": ["Diagnostic clinique", "Protocoles OMS", "Urgences", "PMSI"],
            "nice": ["BLS", "ATLS", "Télémédecine", "DMP"],
            "description": (
                "Prise en charge des patients en consultation et hospitalisation. "
                "Établissement des diagnostics, prescription des traitements et "
                "coordination avec les équipes paramédicales."
            ),
        },
        {
            "title": "Pharmacien Hospitalier",
            "required": ["Dispensation hospitalière", "Pharmacovigilance", "Gestion de stock médicaments"],
            "nice": ["DU Pharmacie Hospitalière", "Bonne Pratiques Officinales", "Stérilisation"],
            "description": (
                "Gestion de la pharmacie hospitalière, dispensation des médicaments "
                "et dispositifs médicaux. Conseil auprès des équipes soignantes "
                "et suivi de la pharmacovigilance."
            ),
        },
        {
            "title": "Infirmier(ère) de Bloc Opératoire",
            "required": ["Bloc opératoire", "Hygiène hospitalière", "IBODE", "Stérilisation"],
            "nice": ["IADE", "Réanimation", "Urgences", "Triage"],
            "description": (
                "Assistance chirurgicale au bloc opératoire, préparation et gestion "
                "des instruments. Respect des protocoles d'hygiène et de stérilisation. "
                "Prise en charge péri-opératoire des patients."
            ),
        },
        {
            "title": "Kinésithérapeute / Rééducateur",
            "required": ["Rééducation fonctionnelle", "Kinésithérapie", "Bilan clinique"],
            "nice": ["Ostéopathie", "Électrothérapie", "Rhumatologie", "Pédiatrie"],
            "description": (
                "Évaluation et traitement des patients nécessitant une rééducation "
                "fonctionnelle. Élaboration de programmes de soins personnalisés et "
                "suivi de l'évolution clinique."
            ),
        },
    ],
}

# Domaines adjacents (pour les paires ``partial``)
ADJACENT_DOMAINS: Dict[str, List[str]] = {
    "cybersecurite": ["informatique"],
    "informatique":  ["cybersecurite"],
    "finance":       ["informatique"],   # fintech, data analyst finance
    "sante":         ["finance"],        # contrôle de gestion hospitalier
}

# Template texte pour une offre d'emploi
_JOB_TEMPLATE = """\
Poste : {title}
Domaine : {domain_label}
Localisation : {location}

Description du poste :
{description}

Compétences requises :
{required_block}

Compétences appréciées :
{nice_block}

Profil recherché :
- Formation : {edu_level}
- Expérience : {min_years} an(s) minimum
- Langues : Français courant, Anglais professionnel apprécié
"""

DOMAIN_LABELS = {
    "cybersecurite": "Cybersécurité / Sécurité SI",
    "finance":       "Finance / Audit / Contrôle de gestion",
    "informatique":  "Informatique / Développement / DevOps",
    "sante":         "Santé / Médical / Paramédical",
}

LOCATIONS = ["Casablanca", "Rabat", "Marrakech", "Paris", "Lyon", "Toulouse"]
EDU_LEVELS = ["Bac+2 ou équivalent", "Licence / Bac+3", "Master / Bac+5", "Ingénieur"]


@dataclass
class RealCVExample:
    cv_text: str
    job_text: str
    label: str      # compatible | partial | incompatible
    score: float
    cv_domain: str
    job_domain: str
    pdf_source: str
    page_idx: int
    archetype: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


class RealCVPairBuilder:
    """Construit les paires (cv, offre, label) depuis les CVs réels."""

    def __init__(
        self,
        pdf_dir: str | Path,
        seed: int = 42,
    ) -> None:
        self.loader = RealCVLoader(pdf_dir)
        self.rng = random.Random(seed)

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------
    def _bullet(self, items: List[str]) -> str:
        return "\n".join(f"- {it}" for it in items)

    def _make_job_text(self, domain: str, template: Dict) -> str:
        required = list(template["required"])
        nice = self.rng.sample(
            template["nice"], k=min(3, len(template["nice"]))
        )
        return _JOB_TEMPLATE.format(
            title=template["title"],
            domain_label=DOMAIN_LABELS.get(domain, domain),
            location=self.rng.choice(LOCATIONS),
            description=template["description"],
            required_block=self._bullet(required),
            nice_block=self._bullet(nice),
            edu_level=self.rng.choice(EDU_LEVELS),
            min_years=self.rng.randint(0, 4),
        )

    def _pick_job(self, domain: str) -> Tuple[str, str]:
        """Retourne (job_text, archetype_title) pour un domaine."""
        tmpl = self.rng.choice(DOMAIN_JOB_TEMPLATES[domain])
        return self._make_job_text(domain, tmpl), tmpl["title"]

    def _score(self, label: str) -> float:
        base = {"compatible": 0.85, "partial": 0.52, "incompatible": 0.18}[label]
        return round(max(0.05, min(0.97, base + self.rng.uniform(-0.10, 0.10))), 3)

    def _get_incompatible_domain(self, cv_domain: str) -> str:
        """Choisit un domaine sans rapport avec le CV."""
        all_domains = list(DOMAIN_JOB_TEMPLATES.keys())
        adjacent = ADJACENT_DOMAINS.get(cv_domain, [])
        candidates = [d for d in all_domains if d != cv_domain and d not in adjacent]
        return self.rng.choice(candidates) if candidates else self.rng.choice(
            [d for d in all_domains if d != cv_domain]
        )

    def _get_partial_domain(self, cv_domain: str) -> Optional[str]:
        """Retourne un domaine adjacent (pour label=partial) ou None."""
        adjacent = ADJACENT_DOMAINS.get(cv_domain, [])
        valid = [d for d in adjacent if d in DOMAIN_JOB_TEMPLATES]
        return self.rng.choice(valid) if valid else None

    # -----------------------------------------------------------------------
    # Builder principal
    # -----------------------------------------------------------------------
    def build(
        self,
        n_per_cv: int = 3,
        augment: bool = True,
    ) -> List[RealCVExample]:
        """
        Construit les paires d'entraînement.

        Args:
            n_per_cv: Nombre de paires à générer par CV
                      (>= 1 compatible + partials + incompatibles selon n_per_cv)
            augment: Si True, applique de l'augmentation textuelle légère
                     (shuffle des sections du cv_text)

        Returns:
            Liste de RealCVExample prêts pour l'entraînement.
        """
        cv_records = self.loader.load_all()
        if not cv_records:
            raise RuntimeError(
                "Aucun CV chargé. Vérifiez le chemin vers les PDFs."
            )

        logger.info("Construction des paires depuis %d CVs réels…", len(cv_records))
        examples: List[RealCVExample] = []

        for cv in cv_records:
            cv_text = cv.text
            if augment:
                cv_text = self._augment_cv(cv_text)

            # --- 1. Paire compatible (même domaine) ---
            job_text, arch = self._pick_job(cv.domain)
            examples.append(
                RealCVExample(
                    cv_text=cv_text,
                    job_text=job_text,
                    label="compatible",
                    score=self._score("compatible"),
                    cv_domain=cv.domain,
                    job_domain=cv.domain,
                    pdf_source=cv.pdf_source,
                    page_idx=cv.page_idx,
                    archetype=arch,
                )
            )

            # --- 2. Paire(s) selon n_per_cv ---
            if n_per_cv >= 2:
                # Paire partial (domaine adjacent)
                partial_domain = self._get_partial_domain(cv.domain)
                if partial_domain:
                    job_text_p, arch_p = self._pick_job(partial_domain)
                    examples.append(
                        RealCVExample(
                            cv_text=cv_text,
                            job_text=job_text_p,
                            label="partial",
                            score=self._score("partial"),
                            cv_domain=cv.domain,
                            job_domain=partial_domain,
                            pdf_source=cv.pdf_source,
                            page_idx=cv.page_idx,
                            archetype=arch_p,
                        )
                    )
                else:
                    # Pas de domaine adjacent → on génère une 2ème incompatible
                    incompat_domain = self._get_incompatible_domain(cv.domain)
                    job_text_i, arch_i = self._pick_job(incompat_domain)
                    examples.append(
                        RealCVExample(
                            cv_text=cv_text,
                            job_text=job_text_i,
                            label="incompatible",
                            score=self._score("incompatible"),
                            cv_domain=cv.domain,
                            job_domain=incompat_domain,
                            pdf_source=cv.pdf_source,
                            page_idx=cv.page_idx,
                            archetype=arch_i,
                        )
                    )

            if n_per_cv >= 3:
                # Paire incompatible (domaine sans rapport)
                incompat_domain = self._get_incompatible_domain(cv.domain)
                job_text_i2, arch_i2 = self._pick_job(incompat_domain)
                examples.append(
                    RealCVExample(
                        cv_text=cv_text,
                        job_text=job_text_i2,
                        label="incompatible",
                        score=self._score("incompatible"),
                        cv_domain=cv.domain,
                        job_domain=incompat_domain,
                        pdf_source=cv.pdf_source,
                        page_idx=cv.page_idx,
                        archetype=arch_i2,
                    )
                )

            # --- 3. Paires supplémentaires si n_per_cv > 3 ---
            for _ in range(max(0, n_per_cv - 3)):
                domain_choice = self.rng.choice(list(DOMAIN_JOB_TEMPLATES.keys()))
                if domain_choice == cv.domain:
                    label = "compatible"
                elif domain_choice in ADJACENT_DOMAINS.get(cv.domain, []):
                    label = "partial"
                else:
                    label = "incompatible"
                jt, ar = self._pick_job(domain_choice)
                examples.append(
                    RealCVExample(
                        cv_text=cv_text,
                        job_text=jt,
                        label=label,
                        score=self._score(label),
                        cv_domain=cv.domain,
                        job_domain=domain_choice,
                        pdf_source=cv.pdf_source,
                        page_idx=cv.page_idx,
                        archetype=ar,
                    )
                )

        self.rng.shuffle(examples)
        dist = {}
        for ex in examples:
            dist[ex.label] = dist.get(ex.label, 0) + 1
        logger.info(
            "Paires construites : %d total | distribution : %s",
            len(examples),
            dist,
        )
        return examples

    def _augment_cv(self, text: str) -> str:
        """Augmentation légère : mélange aléatoire de blocs de compétences."""
        lines = text.split("\n")
        # Repérer les runs de bullet points et les mélanger
        out: List[str] = []
        buffer: List[str] = []
        for line in lines:
            if re.match(r"\s*[•\-\*]\s+", line):
                buffer.append(line)
            else:
                if buffer and self.rng.random() < 0.4:
                    self.rng.shuffle(buffer)
                out.extend(buffer)
                buffer = []
                out.append(line)
        if buffer:
            out.extend(buffer)
        return "\n".join(out)

    # -----------------------------------------------------------------------
    # Sérialisation
    # -----------------------------------------------------------------------
    def save_jsonl(
        self, examples: List[RealCVExample], path: str | Path
    ) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            for ex in examples:
                fh.write(json.dumps(ex.to_dict(), ensure_ascii=False) + "\n")
        logger.info("Sauvegardé → %s (%d exemples)", path, len(examples))

    def save_csv(
        self, examples: List[RealCVExample], path: str | Path
    ) -> None:
        import csv

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "cv_text", "job_text", "label", "score",
            "cv_domain", "job_domain", "archetype", "pdf_source", "page_idx",
        ]
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for ex in examples:
                row = ex.to_dict()
                writer.writerow({k: row[k] for k in fieldnames})
        logger.info("Sauvegardé → %s (%d exemples)", path, len(examples))
