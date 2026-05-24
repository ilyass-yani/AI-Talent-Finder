"""Shared feature engineering helpers for CV/job matching.

This module keeps the baseline model, API inference, smoke tests and demos on
the same feature recipe.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer

from app.services.normalization import normalize_text


@dataclass
class PairFeatureMeta:
    tfidf: TfidfVectorizer
    svd: TruncatedSVD
    bow: Optional[CountVectorizer] = None


def _tokenize(text: str) -> set[str]:
    return {token for token in normalize_text(text).lower().split() if token}


def _safe_cosine(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    left_norm = np.linalg.norm(left, axis=1)
    right_norm = np.linalg.norm(right, axis=1)
    denominator = np.where(left_norm * right_norm == 0, 1e-9, left_norm * right_norm)
    return np.sum(left * right, axis=1) / denominator


def _extra_pair_features(candidate_text: str, job_text: str) -> np.ndarray:
    candidate_tokens = _tokenize(candidate_text)
    job_tokens = _tokenize(job_text)

    intersection = candidate_tokens & job_tokens
    union = candidate_tokens | job_tokens

    overlap_ratio = len(intersection) / max(1, len(union))
    candidate_ratio = len(intersection) / max(1, len(candidate_tokens))
    job_ratio = len(intersection) / max(1, len(job_tokens))

    candidate_length = len(candidate_text.split())
    job_length = len(job_text.split())
    length_ratio = min(candidate_length, job_length) / max(1, max(candidate_length, job_length))
    length_gap = abs(candidate_length - job_length) / max(1, max(candidate_length, job_length))

    return np.array([
        overlap_ratio,
        candidate_ratio,
        job_ratio,
        length_ratio,
        length_gap,
        float(candidate_length),
        float(job_length),
    ], dtype=float)


def fit_pair_vectorizer(candidate_texts: Iterable[str], job_texts: Iterable[str], max_features: int = 20000, svd_components: int = 200) -> PairFeatureMeta:
    candidate_texts = [normalize_text(text) for text in candidate_texts]
    job_texts = [normalize_text(text) for text in job_texts]
    combined = candidate_texts + job_texts

    tfidf = TfidfVectorizer(max_features=max_features, ngram_range=(1, 2))
    tfidf.fit(combined)

    candidate_matrix = tfidf.transform(candidate_texts)
    svd = TruncatedSVD(n_components=min(svd_components, max(1, candidate_matrix.shape[1] - 1)))
    svd.fit(candidate_matrix)

    return PairFeatureMeta(tfidf=tfidf, svd=svd)


def fit_pair_bow_vectorizer(candidate_texts: Iterable[str], job_texts: Iterable[str], max_features: int = 20000, svd_components: int = 200) -> PairFeatureMeta:
    """Classic feature engineering using a Bag-of-Words corpus representation."""
    candidate_texts = [normalize_text(text) for text in candidate_texts]
    job_texts = [normalize_text(text) for text in job_texts]
    combined = candidate_texts + job_texts

    bow = CountVectorizer(max_features=max_features, ngram_range=(1, 2), binary=False)
    bow.fit(combined)

    candidate_matrix = bow.transform(candidate_texts)
    svd = TruncatedSVD(n_components=min(svd_components, max(1, candidate_matrix.shape[1] - 1)))
    svd.fit(candidate_matrix)

    # Keep tfidf field populated for backward compatibility in callers.
    tfidf = TfidfVectorizer(max_features=max_features, ngram_range=(1, 2))
    tfidf.fit(combined)

    return PairFeatureMeta(bow=bow, tfidf=tfidf, svd=svd)


def _build_pair_features_from_matrix(candidate_text: str, job_text: str, matrix_builder, svd: TruncatedSVD) -> np.ndarray:
    x_candidate = matrix_builder([candidate_text])
    x_job = matrix_builder([job_text])

    x_candidate_red = svd.transform(x_candidate)
    x_job_red = svd.transform(x_job)
    # Keep the feature vector shape stable, but make BERT the primary similarity signal.
    semantic_similarity = np.array([build_bert_similarity_feature(candidate_text, job_text)], dtype=float)
    extra = _extra_pair_features(candidate_text, job_text).reshape(1, -1)

    return np.hstack([
        x_candidate_red,
        x_job_red,
        np.abs(x_candidate_red - x_job_red),
        x_candidate_red * x_job_red,
        semantic_similarity.reshape(-1, 1),
        extra,
    ])


def build_pair_features(candidate_text: str, job_text: str, meta: PairFeatureMeta) -> np.ndarray:
    candidate_text = normalize_text(candidate_text)
    job_text = normalize_text(job_text)

    matrix_builder = meta.tfidf.transform
    if meta.bow is not None:
        matrix_builder = meta.bow.transform

    return _build_pair_features_from_matrix(candidate_text, job_text, matrix_builder, meta.svd)


def build_bert_similarity_feature(candidate_text: str, job_text: str) -> float:
    """Recommended feature: semantic similarity from sentence-transformers (BERT family).

    Returns a value in [0, 1]. Falls back to 0.0 if the model is unavailable.
    """
    try:
        from ai_module.matching.semantic_matcher import SemanticSkillMatcher

        return float(SemanticSkillMatcher.semantic_similarity(candidate_text, job_text))
    except Exception:
        return 0.0


def build_pair_features_dataframe(df):
    meta = fit_pair_vectorizer(df["cv_text"].tolist(), df["job_text"].tolist())
    matrix = np.vstack([
        build_pair_features(row.cv_text, row.job_text, meta) for row in df.itertuples(index=False)
    ])
    return matrix, meta