"""
BERT Embeddings for Semantic CV-Job Matching
ÉTAPE 2: Advanced feature engineering avec BERT pour +5-10% amélioration
"""

import os
import logging
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModel

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

logger = logging.getLogger(__name__)


class BertEmbedder:
    """Generate BERT embeddings for CV and job text."""
    
    def __init__(
        self,
        model_name: str = "distilbert-base-multilingual-cased",
        device: Optional[str] = None,
        cache_dir: Optional[str] = None,
    ):
        """Initialize BERT embedder.
        
        Args:
            model_name: HuggingFace model identifier
            device: 'cuda' or 'cpu' (auto-detect if None)
            cache_dir: Cache directory for downloaded models
        """
        self.model_name = model_name
        self.cache_dir = cache_dir or "models/bert_cache"
        
        # Device selection
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        logger.info(f"🚀 Initializing BERT embedder: {model_name} on {self.device}")
        
        # Load tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir=self.cache_dir,
            trust_remote_code=True,
        )
        
        self.model = AutoModel.from_pretrained(
            model_name,
            cache_dir=self.cache_dir,
            trust_remote_code=True,
        ).to(self.device)
        
        # Set model to evaluation mode
        self.model.eval()
        
        # Embedding dimension
        self.embedding_dim = self.model.config.hidden_size
        logger.info(f"✅ BERT loaded. Embedding dimension: {self.embedding_dim}")
    
    def embed_text(
        self,
        text: str,
        max_length: int = 512,
        pooling: str = "mean",
    ) -> np.ndarray:
        """Generate embedding for a single text.
        
        Args:
            text: Input text
            max_length: Maximum token length
            pooling: 'mean', 'cls', or 'max' pooling strategy
        
        Returns:
            Embedding as numpy array (shape: embedding_dim,)
        """
        # Tokenize
        inputs = self.tokenizer(
            text,
            max_length=max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        
        # Move to device
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Generate embeddings
        with torch.no_grad():
            outputs = self.model(**inputs, output_hidden_states=True)
            hidden_states = outputs.last_hidden_state  # (batch, seq, hidden)
        
        # Pool embeddings
        if pooling == "mean":
            # Mean pooling with attention mask
            attention_mask = inputs["attention_mask"].unsqueeze(-1)
            masked_output = outputs.last_hidden_state * attention_mask
            embedding = masked_output.sum(dim=1) / attention_mask.sum(dim=1)
        
        elif pooling == "cls":
            # CLS token (first token)
            embedding = outputs.last_hidden_state[:, 0, :]
        
        elif pooling == "max":
            # Max pooling
            embedding = outputs.last_hidden_state.max(dim=1)[0]
        
        else:
            raise ValueError(f"Unknown pooling: {pooling}")
        
        # Convert to numpy
        embedding = embedding.detach().cpu().numpy()[0]
        
        # Normalize
        embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
        
        return embedding
    
    def embed_batch(
        self,
        texts: List[str],
        max_length: int = 512,
        pooling: str = "mean",
        batch_size: int = 32,
    ) -> np.ndarray:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            max_length: Maximum token length
            pooling: Pooling strategy
            batch_size: Processing batch size
        
        Returns:
            Embeddings as numpy array (shape: len(texts), embedding_dim)
        """
        embeddings = []
        
        logger.info(f"📊 Generating embeddings for {len(texts)} texts...")
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            # Tokenize batch
            inputs = self.tokenizer(
                batch_texts,
                max_length=max_length,
                padding="max_length",
                truncation=True,
                return_tensors="pt",
            )
            
            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate embeddings
            with torch.no_grad():
                outputs = self.model(**inputs)
            
            # Pool
            if pooling == "mean":
                attention_mask = inputs["attention_mask"].unsqueeze(-1)
                masked_output = outputs.last_hidden_state * attention_mask
                batch_embeddings = masked_output.sum(dim=1) / attention_mask.sum(dim=1)
            
            elif pooling == "cls":
                batch_embeddings = outputs.last_hidden_state[:, 0, :]
            
            else:
                batch_embeddings = outputs.last_hidden_state.max(dim=1)[0]
            
            # Normalize
            batch_embeddings = batch_embeddings.detach().cpu().numpy()
            batch_embeddings = batch_embeddings / (np.linalg.norm(batch_embeddings, axis=1, keepdims=True) + 1e-8)
            
            embeddings.append(batch_embeddings)
            
            logger.debug(f"✓ Processed batch {i // batch_size + 1}")
        
        # Concatenate
        all_embeddings = np.vstack(embeddings)
        logger.info(f"✅ Generated {len(all_embeddings)} embeddings")
        
        return all_embeddings
    
    def cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings."""
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def similarity_matrix(self, embeddings1: np.ndarray, embeddings2: np.ndarray) -> np.ndarray:
        """Compute similarity matrix between two sets of embeddings."""
        # Normalize embeddings
        emb1_norm = embeddings1 / (np.linalg.norm(embeddings1, axis=1, keepdims=True) + 1e-8)
        emb2_norm = embeddings2 / (np.linalg.norm(embeddings2, axis=1, keepdims=True) + 1e-8)
        
        # Compute similarity
        similarity = np.dot(emb1_norm, emb2_norm.T)
        return similarity


class BertMatcher:
    """Match CVs to jobs using BERT embeddings."""
    
    def __init__(
        self,
        model_name: str = "distilbert-base-multilingual-cased",
        use_faiss: bool = True,
        cache_dir: Optional[str] = None,
    ):
        """Initialize matcher."""
        self.embedder = BertEmbedder(model_name, cache_dir=cache_dir)
        self.use_faiss = use_faiss and FAISS_AVAILABLE
        self.index = None
        self.embeddings_cache = {}
        
        logger.info(f"✅ BertMatcher initialized (FAISS: {self.use_faiss})")
    
    def build_index(self, texts: List[str], index_type: str = "flat") -> Tuple[Any, np.ndarray]:
        """Build FAISS index for similarity search.
        
        Args:
            texts: List of texts to index
            index_type: 'flat' or 'ivf' (inverted file for large datasets)
        
        Returns:
            (faiss_index, embeddings)
        """
        if not self.use_faiss:
            logger.warning("⚠️ FAISS not available. Using numpy similarity.")
            return None, self.embedder.embed_batch(texts)
        
        logger.info(f"🔍 Building FAISS index for {len(texts)} texts...")
        
        # Generate embeddings
        embeddings = self.embedder.embed_batch(texts)
        
        # Create FAISS index
        if index_type == "flat":
            index = faiss.IndexFlatL2(self.embedder.embedding_dim)
        elif index_type == "ivf":
            # IVF for large datasets
            nlist = min(100, len(texts) // 10)
            quantizer = faiss.IndexFlatL2(self.embedder.embedding_dim)
            index = faiss.IndexIVFFlat(quantizer, self.embedder.embedding_dim, nlist)
            if len(embeddings) >= nlist:
                index.train(embeddings.astype("float32"))
        else:
            raise ValueError(f"Unknown index type: {index_type}")
        
        # Add embeddings
        index.add(embeddings.astype("float32"))
        
        self.index = index
        self.embeddings_cache = {i: emb for i, emb in enumerate(embeddings)}
        
        logger.info(f"✅ Index built with {len(embeddings)} vectors")
        return index, embeddings
    
    def search_similar(
        self,
        query_text: str,
        reference_texts: List[str] = None,
        top_k: int = 10,
    ) -> List[Tuple[int, float, str]]:
        """Find most similar texts.
        
        Args:
            query_text: Query text
            reference_texts: Reference texts (if index not built)
            top_k: Number of results
        
        Returns:
            List of (index, similarity_score, text) tuples
        """
        # Generate query embedding
        query_embedding = self.embedder.embed_text(query_text)
        
        if self.index is None:
            # No index: compute similarities directly
            if reference_texts is None:
                raise ValueError("Either build index or provide reference_texts")
            
            ref_embeddings = self.embedder.embed_batch(reference_texts)
            similarities = self.embedder.similarity_matrix(
                query_embedding.reshape(1, -1),
                ref_embeddings
            )[0]
            
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            results = [
                (idx, float(similarities[idx]), reference_texts[idx])
                for idx in top_indices
            ]
        
        else:
            # Use FAISS
            distances, indices = self.index.search(
                query_embedding.reshape(1, -1).astype("float32"),
                top_k
            )
            
            # Convert distances to similarities
            results = [
                (idx, 1 / (1 + dist), "")  # Using cached embeddings
                for idx, dist in zip(indices[0], distances[0])
            ]
        
        return results
    
    def match_cv_to_job(
        self,
        cv_text: str,
        job_description: str,
        weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Match a CV to a job with detailed analysis.
        
        Args:
            cv_text: Candidate CV
            job_description: Job posting
            weights: Weighting for different components
        
        Returns:
            Match result with scores and insights
        """
        if weights is None:
            weights = {
                "description": 0.40,
                "requirements": 0.35,
                "company": 0.15,
                "title": 0.10,
            }
        
        # Extract components from job description
        job_sections = self._extract_job_sections(job_description)
        
        # Generate embeddings
        cv_emb = self.embedder.embed_text(cv_text)
        
        scores = {}
        
        # Description matching
        if job_sections.get("description"):
            desc_emb = self.embedder.embed_text(job_sections["description"])
            scores["description"] = self.embedder.cosine_similarity(cv_emb, desc_emb)
        
        # Requirements matching
        if job_sections.get("requirements"):
            req_emb = self.embedder.embed_text(job_sections["requirements"])
            scores["requirements"] = self.embedder.cosine_similarity(cv_emb, req_emb)
        
        # Company matching
        if job_sections.get("company"):
            comp_emb = self.embedder.embed_text(job_sections["company"])
            scores["company"] = self.embedder.cosine_similarity(cv_emb, comp_emb)
        
        # Title matching
        if job_sections.get("title"):
            title_emb = self.embedder.embed_text(job_sections["title"])
            scores["title"] = self.embedder.cosine_similarity(cv_emb, title_emb)
        
        # Weighted score
        final_score = sum(
            scores.get(key, 0) * weight
            for key, weight in weights.items()
        )
        
        return {
            "overall_score": float(final_score),
            "component_scores": {k: float(v) for k, v in scores.items()},
            "match_level": self._classify_match(final_score),
            "insights": self._generate_insights(cv_text, job_description, scores),
        }
    
    def _extract_job_sections(self, job_text: str) -> Dict[str, str]:
        """Extract main sections from job description."""
        sections = {
            "description": job_text[:500],  # First 500 chars as overview
            "requirements": job_text,  # Full text for requirements
            "company": "",
            "title": "",
        }
        return sections
    
    def _classify_match(self, score: float) -> str:
        """Classify match level based on score."""
        if score >= 0.75:
            return "excellent"
        elif score >= 0.60:
            return "good"
        elif score >= 0.45:
            return "fair"
        else:
            return "poor"
    
    def _generate_insights(
        self,
        cv_text: str,
        job_text: str,
        scores: Dict[str, float],
    ) -> List[str]:
        """Generate human-readable insights about the match."""
        insights = []
        
        avg_score = np.mean(list(scores.values())) if scores else 0
        
        if avg_score >= 0.75:
            insights.append("Strong semantic match across all sections")
        elif avg_score >= 0.60:
            insights.append("Good match with some gaps in specific areas")
        else:
            insights.append("Limited semantic alignment - may require additional review")
        
        # Component-specific insights
        if scores.get("description", 0) > 0.70:
            insights.append("Job description aligns well with candidate background")
        
        if scores.get("requirements", 0) > 0.70:
            insights.append("Candidate appears to meet key requirements")
        
        if scores.get("title", 0) < 0.50:
            insights.append("Role title differs from candidate's experience")
        
        return insights
    
    def batch_match(
        self,
        cv_texts: List[str],
        job_description: str,
    ) -> List[Tuple[int, float, str]]:
        """Match multiple CVs to a single job.
        
        Returns:
            List of (cv_index, score, match_level) tuples
        """
        logger.info(f"📊 Matching {len(cv_texts)} CVs to job...")
        
        # Generate embeddings
        cv_embeddings = self.embedder.embed_batch(cv_texts)
        job_embedding = self.embedder.embed_text(job_description)
        
        # Compute similarities
        similarities = self.embedder.similarity_matrix(
            cv_embeddings,
            job_embedding.reshape(1, -1)
        ).squeeze()
        
        # Rank
        results = [
            (i, float(similarities[i]), self._classify_match(similarities[i]))
            for i in np.argsort(similarities)[::-1]
        ]
        
        logger.info(f"✅ Matching completed")
        return results


def enhance_cv_job_pair(
    cv_text: str,
    job_text: str,
    bert_model: str = "distilbert-base-multilingual-cased",
) -> Dict[str, Any]:
    """Enhanced feature extraction using BERT.
    
    Returns features suitable for ML models (+5-10% improvement over TF-IDF).
    """
    matcher = BertMatcher(bert_model)
    
    # Generate embeddings
    cv_embedding = matcher.embedder.embed_text(cv_text)
    job_embedding = matcher.embedder.embed_text(job_text)
    
    # Compute similarity features
    similarity = matcher.embedder.cosine_similarity(cv_embedding, job_embedding)
    
    return {
        "bert_similarity": float(similarity),
        "cv_embedding": cv_embedding,
        "job_embedding": job_embedding,
        "embedding_dim": matcher.embedder.embedding_dim,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Example usage
    cv_text = """
    Python Developer with 5 years experience
    Skills: Python, FastAPI, PostgreSQL, Docker, Kubernetes
    Experience: Backend development at TechCorp
    """
    
    job_text = """
    Senior Backend Developer
    Required: Python, FastAPI, PostgreSQL, Docker
    Location: Remote
    """
    
    matcher = BertMatcher()
    result = matcher.match_cv_to_job(cv_text, job_text)
    
    print(f"Match Score: {result['overall_score']:.3f}")
    print(f"Match Level: {result['match_level']}")
    print(f"Insights: {result['insights']}")
