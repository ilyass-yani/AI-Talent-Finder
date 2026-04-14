"""
NLP Service for HuggingFace Model Integration
Handles model loading, caching, and inference for CV extraction
"""

import logging
import os
from typing import Dict, List, Tuple, Optional
from sentence_transformers import SentenceTransformer, util
import torch

logger = logging.getLogger(__name__)


class NLPService:
    """
    Service for loading and using HuggingFace models for CV extraction
    
    Currently supports:
    - Sentence transformers for semantic matching and similarity
    - Can be extended for NER or other tasks
    """
    
    # Class-level cache for models (loaded once, shared across instances)
    _model_cache: Dict[str, 'SentenceTransformer'] = {}
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize NLP Service
        
        Args:
            model_name: HuggingFace model identifier
                Default: all-MiniLM-L6-v2 (lightweight, 22MB)
                Alternatives:
                - "all-mpnet-base-v2" (better accuracy, 420MB)
                - "all-roberta-large-v1" (best accuracy, 1GB)
        """
        self.model_name = model_name
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")
        
        # Load model on initialization
        self._load_model()
    
    def _load_model(self):
        """
        Load model from cache or download from HuggingFace
        Models are cached in ~/.cache/huggingface/
        """
        # Check if already in memory cache
        if self.model_name in self._model_cache:
            self.model = self._model_cache[self.model_name]
            logger.info(f"✓ Model loaded from memory cache: {self.model_name}")
            return
        
        try:
            logger.info(f"Loading model: {self.model_name}...")
            self.model = SentenceTransformer(
                self.model_name,
                device=self.device,
                cache_folder=os.path.expanduser("~/.cache/huggingface/")
            )
            
            # Store in class-level cache
            self._model_cache[self.model_name] = self.model
            logger.info(f"✓ Model loaded successfully: {self.model_name}")
            
        except Exception as e:
            logger.error(f"✗ Error loading model {self.model_name}: {str(e)}")
            raise
    
    def encode_texts(self, texts: List[str]) -> torch.Tensor:
        """
        Convert texts to embeddings (numerical representations)
        
        Args:
            texts: List of text strings to encode
            
        Returns:
            torch.Tensor of shape (len(texts), embedding_dim)
        """
        if not self.model:
            raise RuntimeError("Model not loaded")
        
        embeddings = self.model.encode(texts, convert_to_tensor=True)
        return embeddings
    
    def find_similar(
        self,
        query: str,
        candidates: List[str],
        top_k: int = 3,
        threshold: float = 0.3
    ) -> List[Tuple[str, float]]:
        """
        Find most similar texts using semantic similarity
        
        Args:
            query: The text to search for
            candidates: List of candidate texts
            top_k: Return top K matches
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of (text, similarity_score) tuples, sorted by similarity
        """
        if not candidates:
            return []
        
        # Encode query and candidates
        query_embedding = self.model.encode(query, convert_to_tensor=True)
        candidate_embeddings = self.model.encode(candidates, convert_to_tensor=True)
        
        # Calculate cosine similarity
        cos_scores = util.pytorch_cos_sim(query_embedding, candidate_embeddings)[0]
        
        # Get top matches above threshold
        results = []
        for idx, score in enumerate(cos_scores):
            score_val = score.item()
            if score_val >= threshold:
                results.append((candidates[idx], score_val))
        
        # Sort by score descending and return top K
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    def extract_job_title(self, text: str, company_context: Optional[str] = None) -> Optional[str]:
        """
        Extract job title from text using semantic similarity
        
        Example use case:
        - text: "Senior Software Engineer at Google, 3 years"
        - Returns: "Senior Software Engineer"
        
        Args:
            text: Text potentially containing job title
            company_context: Optional company name for better matching
            
        Returns:
            Extracted job title or None
        """
        if not text or len(text) < 3:
            return None
        
        # Common job title patterns to search for
        job_title_keywords = [
            "engineer", "developer", "manager", "architect", "analyst",
            "consultant", "specialist", "director", "lead", "coordinator",
            "officer", "associate", "senior", "junior", "principal"
        ]
        
        # Split text into tokens and find similarity with job titles
        text_lower = text.lower()
        
        # Simple heuristic: look for job title keywords
        for keyword in job_title_keywords:
            if keyword in text_lower:
                # Extract portion containing the keyword
                idx = text_lower.find(keyword)
                start = max(0, idx - 20)  # 20 chars before
                end = min(len(text), idx + len(keyword) + 20)  # 20 chars after
                
                candidate = text[start:end].strip()
                if len(candidate) > 3:
                    return candidate
        
        return None
    
    def extract_degree(self, text: str) -> Optional[str]:
        """
        Extract degree type from text using semantic matching
        
        Args:
            text: Text potentially containing degree
            
        Returns:
            Degree type (Bachelor, Master, PhD) or None
        """
        degrees = ["bachelor", "master", "phd", "doctorate", "associate", "diploma"]
        degree_mapping = {
            "bachelor": "Bachelor",
            "master": "Master",
            "phd": "PhD",
            "doctorate": "PhD",
            "associate": "Associate",
            "diploma": "Diploma"
        }
        
        text_lower = text.lower()
        for degree in degrees:
            if degree in text_lower:
                return degree_mapping[degree]
        
        return None
    
    def extract_institution(self, text: str, candidates: Optional[List[str]] = None) -> Optional[str]:
        """
        Extract institution/university name using semantic similarity
        
        Args:
            text: Text potentially containing institution
            candidates: Optional list of known institutions to match against
            
        Returns:
            Institution name or None
        """
        if not text:
            return None
        
        # If candidates provided, find most similar
        if candidates:
            results = self.find_similar(text, candidates, top_k=1, threshold=0.2)
            if results:
                return results[0][0]
        
        # Otherwise, look for common institution keywords
        institution_keywords = [
            "university", "institute", "college", "academy", "school", "polytechnic"
        ]
        
        text_lower = text.lower()
        for keyword in institution_keywords:
            if keyword in text_lower:
                return text.strip()
        
        return None
    
    def semantic_search_skills(
        self,
        text: str,
        skill_list: List[str],
        threshold: float = 0.4
    ) -> List[Tuple[str, float]]:
        """
        Find skills mentioned in text using semantic similarity
        
        This is more flexible than regex - catches variations like:
        - "Python" matches "python", "python programming", "py"
        - "JavaScript" matches "JS", "node.js"
        - "Machine Learning" matches "ML", "deep learning"
        
        Args:
            text: Text to search for skills
            skill_list: List of skills to match against
            threshold: Minimum similarity score (0-1), lower = more lenient
            
        Returns:
            List of (skill, confidence_score) tuples
        """
        if not text or not skill_list:
            return []
        
        # Split text into sentences/chunks for better matching
        chunks = [chunk.strip() for chunk in text.split('.') if chunk.strip()]
        
        found_skills = {}
        
        for skill in skill_list:
            for chunk in chunks:
                results = self.find_similar(
                    skill,
                    [chunk],
                    top_k=1,
                    threshold=threshold
                )
                
                if results:
                    score = results[0][1]
                    if skill not in found_skills or score > found_skills[skill]:
                        found_skills[skill] = score
        
        # Return as sorted list
        return sorted(
            found_skills.items(),
            key=lambda x: x[1],
            reverse=True
        )
    
    def classify_cv_section(self, text: str, return_scores: bool = False):
        """
        Classify which CV section a text belongs to
        
        Args:
            text: Text to classify
            return_scores: Return confidence scores for each section
            
        Returns:
            Section name or dict of scores
        """
        sections = {
            "contact": "email phone linkedin address",
            "experience": "worked employed job company years experience",
            "education": "degree university bachelor master phd graduated",
            "skills": "skills proficient expert knowledge experience",
            "summary": "profile objective summary about personal"
        }
        
        results = {}
        for section_name, section_keywords in sections.items():
            keyword_list = section_keywords.split()
            matches = self.find_similar(text, keyword_list, top_k=5, threshold=0.2)
            
            if matches:
                avg_score = sum(score for _, score in matches) / len(matches)
                results[section_name] = avg_score
        
        if return_scores:
            return results
        
        # Return highest scoring section
        if results:
            return max(results, key=results.get)
        return None
    
    def clear_cache(self):
        """Clear model from memory cache (free up RAM)"""
        if self.model_name in self._model_cache:
            del self._model_cache[self.model_name]
            logger.info(f"Cleared cache for {self.model_name}")
