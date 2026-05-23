"""Feature engineering pour PAIRES (CV, Job) — l'entrée des modèles ML.

Combine 3 familles de features :
    1. Features sémantiques     : cosine, distance euclidienne
    2. Features lexicales       : overlap tokens, Jaccard, longueur
    3. Features métier          : skill overlap, gap d'expérience, gap d'éducation

Sortie : un vecteur de features par paire (CV, Job), utilisable par LR/RF/XGB.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

from ai_pipeline.feature_engineering.classical_features import ClassicalFeatureExtractor
from ai_pipeline.feature_engineering.semantic_features import SemanticFeatureExtractor
from ai_pipeline.preprocessing.skill_normalizer import SkillNormalizer


# ----------------------------------------------------------------------- #
# Helpers
# ----------------------------------------------------------------------- #

def _safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def _tokenize(text: str) -> set:
    if not text:
        return set()
    return {tok for tok in text.lower().split() if tok}


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def _overlap_coefficient(a: set, b: set) -> float:
    """|A ∩ B| / min(|A|, |B|) — meilleur que Jaccard pour ensembles asymétriques."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


# ----------------------------------------------------------------------- #
# Pair feature builder
# ----------------------------------------------------------------------- #

@dataclass
class PairExample:
    """Une paire (CV, Job) avec contexte structuré pour calcul des features."""
    cv_text: str
    job_text: str
    cv_skills: List[str] = field(default_factory=list)
    job_skills: List[str] = field(default_factory=list)
    cv_years_experience: float = 0.0
    job_required_years: float = 0.0
    cv_education_level: int = -1
    job_required_education_level: int = -1
    cv_languages: Dict[str, int] = field(default_factory=dict)
    job_required_languages: Dict[str, int] = field(default_factory=dict)


class PairFeatureBuilder:
    """Construit le vecteur de features pour une paire CV/Job.

    Sortie typique : ~30-50 features (selon options).

    Pipeline :
        - encode CV et job avec sentence-transformer → cosine sémantique
        - encode aussi avec TF-IDF → cosine lexical
        - extrait les features métier (skills, exp, edu, langues)
        - calcule les interactions (différences, produits)
    """

    def __init__(
        self,
        use_semantic: bool = True,
        use_classical: bool = True,
        semantic_extractor: Optional[SemanticFeatureExtractor] = None,
        classical_extractor: Optional[ClassicalFeatureExtractor] = None,
    ) -> None:
        self.use_semantic = use_semantic
        self.use_classical = use_classical
        self.semantic = semantic_extractor
        self.classical = classical_extractor
        self.skill_normalizer = SkillNormalizer()

    # ------------------------------------------------------------------ #
    # Fit (sur le corpus, pour TF-IDF)
    # ------------------------------------------------------------------ #

    def fit(self, examples: Sequence[PairExample]) -> "PairFeatureBuilder":
        if self.use_classical:
            corpus = [ex.cv_text for ex in examples] + [ex.job_text for ex in examples]
            if self.classical is None:
                self.classical = ClassicalFeatureExtractor(svd_components=128)
            self.classical.fit(corpus)
        return self

    # ------------------------------------------------------------------ #
    # Build features pour une paire
    # ------------------------------------------------------------------ #

    def build(self, example: PairExample) -> np.ndarray:
        features: List[float] = []
        names: List[str] = []  # pour debug, on garde les noms

        # ---------- 1. SEMANTIC ----------
        if self.use_semantic and self.semantic is not None:
            cv_emb = self.semantic.encode_single(example.cv_text)
            job_emb = self.semantic.encode_single(example.job_text)
            sem_cosine = SemanticFeatureExtractor.cosine_similarity(cv_emb, job_emb)
            sem_l2 = float(np.linalg.norm(cv_emb - job_emb))
            features.extend([sem_cosine, sem_l2])
            names.extend(["sem_cosine", "sem_l2"])

        # ---------- 2. LEXICAL / TF-IDF ----------
        if self.use_classical and self.classical is not None:
            cv_vec = self.classical.transform([example.cv_text])[0]
            job_vec = self.classical.transform([example.job_text])[0]
            n_cv = np.linalg.norm(cv_vec)
            n_job = np.linalg.norm(job_vec)
            tfidf_cosine = float(np.dot(cv_vec, job_vec) / max(n_cv * n_job, 1e-9))
            features.append(tfidf_cosine)
            names.append("tfidf_cosine")

        # ---------- 3. TOKEN OVERLAP ----------
        cv_tokens = _tokenize(example.cv_text)
        job_tokens = _tokenize(example.job_text)
        features.extend([
            _jaccard(cv_tokens, job_tokens),
            _overlap_coefficient(cv_tokens, job_tokens),
            _safe_div(len(cv_tokens & job_tokens), len(cv_tokens)),
            _safe_div(len(cv_tokens & job_tokens), len(job_tokens)),
            _safe_div(len(cv_tokens), len(job_tokens) or 1),  # length ratio
        ])
        names.extend(["jaccard", "overlap", "cv_coverage", "job_coverage", "length_ratio"])

        # ---------- 4. SKILL FEATURES ----------
        cv_skills_norm = set(self.skill_normalizer.normalize_list(example.cv_skills))
        job_skills_norm = set(self.skill_normalizer.normalize_list(example.job_skills))
        skill_matched = cv_skills_norm & job_skills_norm
        skill_missing = job_skills_norm - cv_skills_norm
        skill_extra = cv_skills_norm - job_skills_norm

        features.extend([
            float(len(skill_matched)),
            float(len(skill_missing)),
            float(len(skill_extra)),
            _safe_div(len(skill_matched), len(job_skills_norm) or 1),  # skill coverage
            _jaccard(cv_skills_norm, job_skills_norm),
            _overlap_coefficient(cv_skills_norm, job_skills_norm),
        ])
        names.extend([
            "n_skills_matched", "n_skills_missing", "n_skills_extra",
            "skill_coverage", "skill_jaccard", "skill_overlap",
        ])

        # ---------- 5. EXPERIENCE ----------
        cv_years = float(example.cv_years_experience)
        job_years = float(example.job_required_years)
        exp_diff = cv_years - job_years
        exp_ratio = _safe_div(cv_years, job_years) if job_years > 0 else 1.0
        features.extend([
            cv_years,
            job_years,
            exp_diff,
            max(0.0, exp_diff),       # surplus d'expérience
            max(0.0, -exp_diff),      # déficit d'expérience
            min(1.0, exp_ratio),
            1.0 if cv_years >= job_years else 0.0,
        ])
        names.extend([
            "cv_years", "job_years", "exp_diff",
            "exp_surplus", "exp_deficit", "exp_ratio", "exp_meets",
        ])

        # ---------- 6. EDUCATION ----------
        edu_diff = example.cv_education_level - example.job_required_education_level
        features.extend([
            float(example.cv_education_level),
            float(example.job_required_education_level),
            float(edu_diff),
            1.0 if edu_diff >= 0 else 0.0,
        ])
        names.extend([
            "cv_edu_level", "job_edu_level", "edu_diff", "edu_meets",
        ])

        # ---------- 7. LANGUES ----------
        cv_langs = set(example.cv_languages.keys())
        req_langs = set(example.job_required_languages.keys())
        lang_matched = cv_langs & req_langs
        features.extend([
            float(len(lang_matched)),
            _safe_div(len(lang_matched), len(req_langs) or 1),
        ])
        names.extend(["n_lang_matched", "lang_coverage"])

        # ---------- 8. SOFT INTERACTION ----------
        if self.use_semantic and self.semantic is not None:
            features.append(sem_cosine * float(len(skill_matched)) / max(1, len(job_skills_norm)))
            names.append("sem_x_skill")

        self.last_feature_names = names
        return np.array(features, dtype=np.float32)

    def build_batch(self, examples: Sequence[PairExample]) -> np.ndarray:
        return np.vstack([self.build(ex) for ex in examples])

    @property
    def n_features(self) -> int:
        return len(getattr(self, "last_feature_names", []))


if __name__ == "__main__":
    builder = PairFeatureBuilder(use_semantic=False, use_classical=False)
    example = PairExample(
        cv_text="Senior Python developer with 5 years of experience.",
        job_text="Looking for a Python engineer with 3+ years.",
        cv_skills=["Python", "FastAPI", "Docker", "AWS"],
        job_skills=["Python", "FastAPI", "Kubernetes"],
        cv_years_experience=5.0,
        job_required_years=3.0,
        cv_education_level=4,
        job_required_education_level=2,
        cv_languages={"English": 5, "French": 6},
        job_required_languages={"English": 4},
    )
    feat = builder.build(example)
    print(f"Features ({len(feat)}):")
    for name, value in zip(builder.last_feature_names, feat):
        print(f"  {name:25s} = {value:.4f}")
