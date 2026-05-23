"""Bi-Encoder avec indexation FAISS pour matching scalable.

Architecture :
    1. À l'indexation : on encode tous les CV et on les met dans un index FAISS
    2. À la requête   : on encode le job, et on cherche les k plus proches en O(log N)

C'est l'approche "production" pour matcher contre des millions de CV.

Comparé à SemanticMatcher, BiEncoderMatcher est conçu pour :
    - garder un index persistant en mémoire / disque
    - répondre à plusieurs requêtes (jobs) sans re-encoder les CV
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from ai_pipeline.feature_engineering.semantic_features import SemanticFeatureExtractor
from ai_pipeline.matching.base import BaseMatcher, MatchCandidate, MatchResult
from ai_pipeline.preprocessing.skill_normalizer import SkillNormalizer

try:
    import faiss  # type: ignore
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False


class BiEncoderMatcher(BaseMatcher):
    """Bi-Encoder + FAISS pour recherche rapide.

    Usage :
        >>> matcher = BiEncoderMatcher()
        >>> matcher.index(candidates_list)
        >>> results = matcher.search(job_text, top_k=20)
    """

    name = "bi_encoder"

    def __init__(
        self,
        encoder: Optional[SemanticFeatureExtractor] = None,
        use_faiss: bool = True,
    ) -> None:
        self.encoder = encoder or SemanticFeatureExtractor()
        self.use_faiss = use_faiss and FAISS_AVAILABLE
        self.skill_normalizer = SkillNormalizer()

        self._candidates: List[MatchCandidate] = []
        self._embeddings: Optional[np.ndarray] = None
        self._faiss_index = None

    # ------------------------------------------------------------------ #
    # Indexation
    # ------------------------------------------------------------------ #

    def index(self, candidates: Sequence[MatchCandidate], show_progress: bool = False) -> None:
        """Indexe une liste de candidats. Remplace l'index existant."""
        if not candidates:
            return

        self._candidates = list(candidates)
        texts = [c.text for c in candidates]
        self._embeddings = self.encoder.encode(texts, show_progress=show_progress)

        if self.use_faiss:
            self._build_faiss_index()

    def add(self, candidates: Sequence[MatchCandidate]) -> None:
        """Ajoute des candidats à l'index existant (incrémental)."""
        if not candidates:
            return
        new_texts = [c.text for c in candidates]
        new_embs = self.encoder.encode(new_texts)
        self._candidates.extend(candidates)

        if self._embeddings is None:
            self._embeddings = new_embs
        else:
            self._embeddings = np.vstack([self._embeddings, new_embs])

        if self.use_faiss:
            if self._faiss_index is None:
                self._build_faiss_index()
            else:
                self._faiss_index.add(new_embs.astype(np.float32))

    def _build_faiss_index(self) -> None:
        if not FAISS_AVAILABLE or self._embeddings is None:
            return
        dim = self._embeddings.shape[1]
        # IndexFlatIP : produit scalaire = cosine si embeddings normalisés
        # (on suppose encoder.normalize=True, ce qui est notre default)
        self._faiss_index = faiss.IndexFlatIP(dim)
        self._faiss_index.add(self._embeddings.astype(np.float32))

    # ------------------------------------------------------------------ #
    # Search
    # ------------------------------------------------------------------ #

    def search(
        self,
        job_text: str,
        job_skills: Optional[List[str]] = None,
        top_k: int = 20,
    ) -> List[MatchResult]:
        if not self._candidates or self._embeddings is None:
            return []

        job_emb = self.encoder.encode_single(job_text).astype(np.float32)

        if self.use_faiss and self._faiss_index is not None:
            k = min(top_k, len(self._candidates))
            scores, indices = self._faiss_index.search(
                job_emb.reshape(1, -1), k
            )
            scores = scores[0]
            indices = indices[0]
        else:
            # Fallback numpy
            sims = self._embeddings @ job_emb
            indices = np.argsort(sims)[::-1][:top_k]
            scores = sims[indices]

        # Construction des résultats
        job_norm = set(self.skill_normalizer.normalize_list(job_skills or []))
        results: List[MatchResult] = []
        for idx, raw_score in zip(indices, scores):
            if idx < 0:
                continue
            candidate = self._candidates[int(idx)]
            cv_norm = set(self.skill_normalizer.normalize_list(candidate.skills))
            matched = sorted(cv_norm & job_norm)
            missing = sorted(job_norm - cv_norm)
            extra = sorted(cv_norm - job_norm)
            sem_score = max(0.0, min(1.0, float(raw_score)))
            results.append(MatchResult(
                candidate_id=candidate.id,
                score=round(sem_score, 4),
                matched_skills=matched,
                missing_skills=missing,
                extra_skills=extra,
                details={
                    "method": "bi_encoder" + ("+faiss" if self.use_faiss else "+numpy"),
                    "rank": int(np.where(indices == idx)[0][0]),
                },
            ))
        return results

    # ------------------------------------------------------------------ #
    # Interface BaseMatcher (pour compat)
    # ------------------------------------------------------------------ #

    def match_one(
        self,
        candidate: MatchCandidate,
        job_text: str,
        job_skills: Optional[List[str]] = None,
    ) -> MatchResult:
        # Compatibilité : on encode juste la paire sans index
        cv_emb = self.encoder.encode_single(candidate.text)
        job_emb = self.encoder.encode_single(job_text)
        sem_score = max(0.0, min(1.0, SemanticFeatureExtractor.cosine_similarity(cv_emb, job_emb)))

        job_norm = set(self.skill_normalizer.normalize_list(job_skills or []))
        cv_norm = set(self.skill_normalizer.normalize_list(candidate.skills))
        return MatchResult(
            candidate_id=candidate.id,
            score=round(sem_score, 4),
            matched_skills=sorted(cv_norm & job_norm),
            missing_skills=sorted(job_norm - cv_norm),
            extra_skills=sorted(cv_norm - job_norm),
            details={"method": "bi_encoder_pair"},
        )

    # ------------------------------------------------------------------ #
    # Persistance
    # ------------------------------------------------------------------ #

    def save(self, directory: str | Path) -> None:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        if self._embeddings is not None:
            np.save(directory / "embeddings.npy", self._embeddings)
        if self._candidates:
            import json
            payload = [
                {
                    "id": c.id,
                    "text": c.text,
                    "skills": c.skills,
                    "metadata": c.metadata,
                }
                for c in self._candidates
            ]
            (directory / "candidates.json").write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
        if self._faiss_index is not None and FAISS_AVAILABLE:
            faiss.write_index(self._faiss_index, str(directory / "index.faiss"))

    def load(self, directory: str | Path) -> None:
        import json
        directory = Path(directory)
        emb_path = directory / "embeddings.npy"
        cand_path = directory / "candidates.json"
        idx_path = directory / "index.faiss"

        if emb_path.exists():
            self._embeddings = np.load(emb_path)
        if cand_path.exists():
            payload = json.loads(cand_path.read_text(encoding="utf-8"))
            self._candidates = [
                MatchCandidate(
                    id=p["id"],
                    text=p["text"],
                    skills=p.get("skills", []),
                    metadata=p.get("metadata", {}),
                )
                for p in payload
            ]
        if idx_path.exists() and FAISS_AVAILABLE:
            self._faiss_index = faiss.read_index(str(idx_path))
        elif self._embeddings is not None and self.use_faiss:
            self._build_faiss_index()

    @property
    def n_indexed(self) -> int:
        return len(self._candidates)
