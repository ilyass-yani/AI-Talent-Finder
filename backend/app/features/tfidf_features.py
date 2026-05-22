import os
import pickle
from typing import List, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD


def build_tfidf_corpus(texts: List[str], max_features: int = 20000) -> Tuple[TfidfVectorizer, np.ndarray]:
    vect = TfidfVectorizer(max_features=max_features, stop_words='english')
    X = vect.fit_transform(texts)
    return vect, X


def reduce_dimensionality(X, n_components: int = 128) -> Tuple[TruncatedSVD, np.ndarray]:
    n_features = X.shape[1] if hasattr(X, 'shape') else 0
    if n_features <= 0:
        svd = TruncatedSVD(n_components=1)
        Xr = svd.fit_transform(X)
        return svd, Xr

    n_comp = min(n_components, max(1, n_features - 1))
    svd = TruncatedSVD(n_components=n_comp)
    Xr = svd.fit_transform(X)
    return svd, Xr


def save_artifacts(output_dir: str, vect: TfidfVectorizer, svd: TruncatedSVD, Xr: np.ndarray):
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, 'tfidf_vectorizer.pkl'), 'wb') as fh:
        pickle.dump(vect, fh)
    with open(os.path.join(output_dir, 'svd.pkl'), 'wb') as fh:
        pickle.dump(svd, fh)
    np.save(os.path.join(output_dir, 'tfidf_svd.npy'), Xr)


def load_artifacts(output_dir: str):
    with open(os.path.join(output_dir, 'tfidf_vectorizer.pkl'), 'rb') as fh:
        vect = pickle.load(fh)
    with open(os.path.join(output_dir, 'svd.pkl'), 'rb') as fh:
        svd = pickle.load(fh)
    Xr = np.load(os.path.join(output_dir, 'tfidf_svd.npy'))
    return vect, svd, Xr
