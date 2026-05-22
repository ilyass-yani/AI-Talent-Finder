#!/usr/bin/env python3
import os,sys
import numpy as np
import faiss
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
import pandas as pd

os.makedirs('models/faiss', exist_ok=True)
csv_path = 'data/training_pairs.csv'
if not os.path.exists(csv_path):
    print('ERROR: data/training_pairs.csv not found')
    sys.exit(1)

df = pd.read_csv(csv_path)
if 'cv_text' in df.columns:
    texts = df['cv_text'].fillna('').astype(str).tolist()[:2000]
else:
    texts = df.iloc[:,0].fillna('').astype(str).tolist()[:2000]

print('Building TF-IDF matrix for', len(texts), 'documents')
vec = TfidfVectorizer(max_features=20000, ngram_range=(1,2))
X_tfidf = vec.fit_transform(texts)
print('TF-IDF shape', X_tfidf.shape)

n_components = 384 if X_tfidf.shape[1] >= 384 else min(128, X_tfidf.shape[1])
print('SVD components', n_components)
svd = TruncatedSVD(n_components=n_components, random_state=42)
X = svd.fit_transform(X_tfidf)
X = X.astype('float32')
print('Dense vectors shape', X.shape)

# Normalize for cosine similarity
faiss.normalize_L2(X)

dim = X.shape[1]
index = faiss.IndexFlatIP(dim)
index.add(X)
faiss.write_index(index, 'models/faiss/index.index')
np.savez('models/faiss/meta.npz', texts=np.array(texts, dtype=object))
print('INDEX_SAVED_TFIDF')

# quick search test
query_vec = X[0:1]
D, I = index.search(query_vec, 5)
print('Top ids', I[0][:5])
print('Top scores', D[0][:5])
print('SEARCH_OK')
