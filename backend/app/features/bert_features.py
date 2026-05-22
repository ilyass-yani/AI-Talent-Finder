import os
from typing import List
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    SBT_AVAILABLE = True
except Exception:
    SentenceTransformer = None
    SBT_AVAILABLE = False


def compute_sentence_embeddings(texts: List[str], model_name: str = None):
    if not SBT_AVAILABLE:
        raise RuntimeError("sentence-transformers not available")
    model_name = model_name or os.getenv('SENTENCE_TRANSFORMER_MODEL', 'all-MiniLM-L6-v2')
    model = SentenceTransformer(model_name)
    embs = model.encode(texts, show_progress_bar=False)
    return np.array(embs)


def save_embeddings(out_dir: str, embs: np.ndarray):
    os.makedirs(out_dir, exist_ok=True)
    np.save(os.path.join(out_dir, 'bert_embeddings.npy'), embs)
