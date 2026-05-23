"""Features classiques : TF-IDF, Bag-of-Words.

Sert de baseline et de complément aux embeddings sémantiques.
Léger, déterministe, interprétable.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import joblib
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer


@dataclass
class ClassicalFeatures:
    tfidf_vectorizer: TfidfVectorizer
    bow_vectorizer: Optional[CountVectorizer]
    svd: Optional[TruncatedSVD]
    feature_dim: int


class ClassicalFeatureExtractor:
    """Encode du texte en TF-IDF (+ SVD optionnelle pour densification).

    Recommandations :
        - n-grams (1, 2) : capture les bigrammes type "machine learning"
        - max_features=20000 : suffit pour un corpus de 10-50k CV/jobs
        - SVD à 200 dimensions : compromis vitesse / qualité
    """

    def __init__(
        self,
        max_features: int = 20000,
        ngram_range: Tuple[int, int] = (1, 2),
        min_df: int = 2,
        max_df: float = 0.95,
        svd_components: Optional[int] = 200,
        use_bow: bool = False,
    ) -> None:
        self.max_features = max_features
        self.ngram_range = ngram_range
        self.min_df = min_df
        self.max_df = max_df
        self.svd_components = svd_components
        self.use_bow = use_bow

        self._tfidf: Optional[TfidfVectorizer] = None
        self._bow: Optional[CountVectorizer] = None
        self._svd: Optional[TruncatedSVD] = None
        self._fitted = False

    # ------------------------------------------------------------------ #
    # Fit / Transform
    # ------------------------------------------------------------------ #

    def fit(self, texts: Iterable[str]) -> "ClassicalFeatureExtractor":
        text_list = [t if t else "" for t in texts]
        if not text_list:
            raise ValueError("Empty corpus")

        self._tfidf = TfidfVectorizer(
            max_features=self.max_features,
            ngram_range=self.ngram_range,
            min_df=self.min_df,
            max_df=self.max_df,
            sublinear_tf=True,        # log(1 + tf) — meilleur pour corpus inégaux
            strip_accents="unicode",
            lowercase=True,
        )
        tfidf_matrix = self._tfidf.fit_transform(text_list)

        if self.use_bow:
            self._bow = CountVectorizer(
                max_features=self.max_features // 2,
                ngram_range=(1, 1),
                min_df=self.min_df,
                max_df=self.max_df,
                lowercase=True,
            )
            self._bow.fit(text_list)

        if self.svd_components:
            n_components = min(self.svd_components, tfidf_matrix.shape[1] - 1)
            if n_components > 1:
                self._svd = TruncatedSVD(n_components=n_components, random_state=42)
                self._svd.fit(tfidf_matrix)

        self._fitted = True
        return self

    def transform(self, texts: Iterable[str]) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Call fit() first.")
        text_list = [t if t else "" for t in texts]
        tfidf_matrix = self._tfidf.transform(text_list)
        if self._svd is not None:
            return self._svd.transform(tfidf_matrix)
        return tfidf_matrix.toarray()

    def transform_sparse(self, texts: Iterable[str]):
        """Retourne la matrice sparse TF-IDF brute (avant SVD)."""
        if not self._fitted:
            raise RuntimeError("Call fit() first.")
        return self._tfidf.transform([t or "" for t in texts])

    def fit_transform(self, texts: Iterable[str]) -> np.ndarray:
        return self.fit(texts).transform(texts)

    # ------------------------------------------------------------------ #
    # Sérialisation
    # ------------------------------------------------------------------ #

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            "tfidf": self._tfidf,
            "bow": self._bow,
            "svd": self._svd,
            "config": {
                "max_features": self.max_features,
                "ngram_range": self.ngram_range,
                "min_df": self.min_df,
                "max_df": self.max_df,
                "svd_components": self.svd_components,
                "use_bow": self.use_bow,
            },
        }, path)

    @classmethod
    def load(cls, path: str | Path) -> "ClassicalFeatureExtractor":
        payload = joblib.load(Path(path))
        config = payload["config"]
        instance = cls(**config)
        instance._tfidf = payload["tfidf"]
        instance._bow = payload["bow"]
        instance._svd = payload["svd"]
        instance._fitted = True
        return instance

    # ------------------------------------------------------------------ #
    # Similarité directe
    # ------------------------------------------------------------------ #

    def cosine_sim(self, text_a: str, text_b: str) -> float:
        vec_a = self.transform([text_a])
        vec_b = self.transform([text_b])
        return float(_cosine(vec_a[0], vec_b[0]))


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


if __name__ == "__main__":
    corpus = [
        "Python developer with machine learning experience",
        "Senior Java engineer, microservices and Kubernetes",
        "Data scientist, deep learning, PyTorch, TensorFlow",
        "Frontend developer, React, TypeScript, Next.js",
    ]
    extractor = ClassicalFeatureExtractor(svd_components=4)
    extractor.fit(corpus)
    print("Shape:", extractor.transform(corpus).shape)
    print("Sim(0,2):", extractor.cosine_sim(corpus[0], corpus[2]))
    print("Sim(0,3):", extractor.cosine_sim(corpus[0], corpus[3]))
