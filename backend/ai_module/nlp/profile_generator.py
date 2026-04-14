"""
AI-powered profile generator for job descriptions using Hugging Face models.
This module creates candidate profiles from free-form text using either rule-based
or AI-powered approaches.
"""

import re
import os
from typing import List, Dict, Optional, Any
from ai_module.nlp.cv_cleaner import CVCleaner

# Hugging Face imports (will be loaded when needed)
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
    import torch
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    print("Warning: Hugging Face transformers not available. Using rule-based generation only.")


class ProfileGenerator:
    """
    Profile generator that can use either rule-based or AI-powered approaches.
    
    HUGGING FACE MODEL CONFIGURATION:
    ================================
    
    To enable AI-powered profile generation from Hugging Face models:
    
    1. Install transformers if not already installed:
       pip install transformers torch
    
    2. Set environment variables:
       export USE_AI_PROFILE_GENERATOR=true
       export HF_PROFILE_MODEL="model-name-here"
    
    3. Available model types and examples:
    
       A) Token Classification (NER) - Recommended for CV parsing:
          - dslim/bert-base-multilingual-cased-ner-hrl
          - dbmdz/bert-base-french-europeana-cased
          Usage: Extracts entities (companies, skills, positions)
       
       B) Text Generation / Summarization:
          - facebook/bart-large-cnn (summarization)
          - t5-small (text-to-text)
          - microsoft/DialoGPT-medium (conversational)
          Usage: Generates structured profiles from descriptions
       
       C) Document Classification:
          - distilbert-base-uncased-finetuned-sst-2-english
          Usage: Categorizes CV sections and skills
    
    4. Custom model setup:
       - Download from huggingface.co
       - Set HF_PROFILE_MODEL to your model ID
       - Adjust _generate_with_ai() based on model output format
    
    5. Model loading is lazy (first use triggers download)
       - Models are cached in ~/.cache/huggingface
       - First load takes time (depends on model size)
    """

    # Configuration for Hugging Face models
    # ==== CUSTOMIZE THESE FOR YOUR AI MODEL ====
    USE_AI_MODEL = os.getenv("USE_AI_PROFILE_GENERATOR", "false").lower() == "true"
    HF_PROFILE_MODEL = os.getenv("HF_PROFILE_MODEL", "facebook/bart-large-cnn")  # Default: Summarization model
    
    # Optional: NER model for entity extraction (highly recommended for CVs)
    HF_NER_MODEL = os.getenv("HF_NER_MODEL", "dslim/bert-base-multilingual-cased-ner-hrl")  # Named Entity Recognition

    # Cache for loaded models
    _model_cache = {}

    TECH_SKILLS = [
        "python", "fastapi", "django", "sql", "postgresql", "mysql",
        "docker", "kubernetes", "aws", "azure", "gcp", "javascript",
        "react", "nodejs", "flask", "git", "devops", "api",
        "microservices", "data", "etl", "pandas", "numpy",
        "machine learning", "nlp", "cloud", "linux"
    ]

    SOFT_SKILLS = [
        "communication", "teamwork", "collaboration", "leadership",
        "problem solving", "adaptability", "creativity", "organization",
        "autonomy", "critical thinking", "time management", "planning"
    ]

    LANGUAGES = [
        "english", "french", "spanish", "german", "italian", "portuguese",
        "arabic", "mandarin", "japanese"
    ]

    EDUCATION_LEVELS = {
        "phd": "PhD or equivalent",
        "doctorate": "PhD or equivalent",
        "master": "Master's degree",
        "msc": "Master's degree",
        "bachelor": "Bachelor's degree",
        "licence": "Bachelor's degree",
        "diploma": "Diploma or Bachelor's degree",
        "engineering": "Engineering degree",
        "high school": "High school diploma"
    }

    EXPERIENCE_PATTERNS = [
        r"(?P<years>[0-9]{1,2})\s*\+?\s*(?:years|yrs|ans)",
        r"(?P<years>[0-9]{1,2})\s*\+?\s*(?:years|yrs|ans)\s*of experience",
        r"minimum of (?P<years>[0-9]{1,2})\s*\+?\s*(?:years|yrs|ans)",
    ]

    @classmethod
    def _load_ai_model(cls, model_name: str = None) -> Optional[Any]:
        """
        Load and cache a Hugging Face model for profile generation.
        
        CUSTOMIZE: Update this method when using a specific model type:
        - For NER models: use pipeline("token-classification", model=model_name)
        - For text generation: use pipeline("text-generation", model=model_name)
        - For QA: use pipeline("question-answering", model=model_name)
        """
        if not HF_AVAILABLE:
            print("Hugging Face not available. Install with: pip install transformers torch")
            return None

        model_key = model_name or cls.HF_MODEL_NAME
        if model_key in cls._model_cache:
            return cls._model_cache[model_key]

        try:
            print(f"Loading AI model: {model_key}")
            # For now, using a summarization pipeline as placeholder
            # You can replace this with your specific model
            model = pipeline("summarization", model=model_key)
            cls._model_cache[model_key] = model
            return model
        except Exception as e:
            print(f"Failed to load AI model {model_key}: {e}")
            return None

    @classmethod
    def _generate_with_ai(cls, text: str, model_name: str = None) -> Dict[str, Any]:
        """
        Generate profile using AI model.

        CUSTOMIZATION GUIDE:
        1. Choose your model from Hugging Face based on your needs:
           - Text generation: microsoft/DialoGPT-medium, facebook/blenderbot
           - Instruction following: models fine-tuned for instructions
           - Summarization: facebook/bart-large-cnn, t5-small
           - Question answering: deepset/roberta-base-squad2

        2. Update the prompt below to match your model's expected input format

        3. Modify the model inference code based on your model's API

        4. Customize _parse_ai_output() to parse your model's specific output format

        5. Set USE_AI_PROFILE_GENERATOR=true and HF_PROFILE_MODEL in your .env file
        """
        model = cls._load_ai_model(model_name)
        if not model:
            print("Falling back to rule-based generation")
            return cls._generate_with_rules(text)

        try:
            # Clean and prepare text
            cleaned_text = CVCleaner.clean_text(text)

            # === CUSTOMIZE THIS PROMPT BASED ON YOUR MODEL ===
            prompt = f"""
            Analyze this job description and create an ideal candidate profile:

            Job Description:
            {cleaned_text}

            Extract and provide:
            - Required technical skills (list)
            - Required soft skills (list)
            - Required years of experience (number)
            - Required education level (string)
            - Key responsibilities (list)

            Format your response as a structured summary.
            """

            # === CUSTOMIZE THIS BASED ON YOUR MODEL TYPE ===
            # For summarization models (like BART):
            if hasattr(model, 'summarize') or 'summarization' in str(type(model)).lower():
                result = model(prompt, max_length=500, min_length=100, do_sample=False)
                ai_output = result[0]['summary_text'] if result else ""

            # For conversational models (like DialoGPT, BlenderBot):
            elif hasattr(model, '__call__') and 'conversation' in str(type(model)).lower():
                # Adjust parameters based on your specific model
                result = model(prompt, max_length=200, num_return_sequences=1)
                ai_output = result[0]['generated_text'] if result else ""

            # For other model types - customize here
            else:
                print(f"Unsupported model type: {type(model)}")
                ai_output = "Model type not supported - customize the inference code"

            # Parse AI output and structure it (you'll need to customize this)
            return cls._parse_ai_output(ai_output, cleaned_text)

        except Exception as e:
            print(f"AI generation failed: {e}")
            return cls._generate_with_rules(text)

    @classmethod
    def _parse_ai_output(cls, ai_output: str, original_text: str) -> Dict[str, Any]:
        """
        Parse AI model output into structured profile.
        Customize this based on your model's output format.
        """
        # Placeholder parsing - customize based on your model's output
        # For now, fall back to rules but you can enhance this
        return cls._generate_with_rules(original_text)

    @classmethod
    def _generate_with_rules(cls, text: str) -> Dict[str, Any]:
        """
        Original rule-based generation method.
        """
        cleaned_text = CVCleaner.clean_text(text)
        overview = text.strip().split("\n", 1)[0]

        technical = cls._find_keywords(text, cls.TECH_SKILLS)
        soft = cls._find_keywords(text, cls.SOFT_SKILLS)
        languages = cls._find_keywords(text, cls.LANGUAGES)

        experience_years = cls._extract_years(text)
        education = cls._extract_education(text)

        # Create skill levels
        skills = {}
        for skill in technical + soft:
            skills[skill] = cls._profile_level(text, skill)

    @classmethod
    def generate_from_text(cls, text: str, model_name: str = None) -> Dict[str, Any]:
        """
        Main method to generate profile from job description text.
        Uses AI model if available and enabled, otherwise falls back to rules.

        Args:
            text: Job description text
            model_name: Optional specific Hugging Face model to use

        Returns:
            Dictionary containing the ideal candidate profile
        """
        if cls.USE_AI_MODEL and HF_AVAILABLE:
            return cls._generate_with_ai(text, model_name)
        else:
            return cls._generate_with_rules(text)

    # Legacy methods for backward compatibility
    @classmethod
    def _find_keywords(cls, text: str, words: List[str]) -> List[str]:
        """Find keywords in text using regex matching."""
        found = []
        lower_text = text.lower()
        for word in words:
            pattern = rf"\b{re.escape(word)}\b"
            if re.search(pattern, lower_text):
                found.append(word)
        return found

    @classmethod
    def _extract_years(cls, text: str) -> int:
        """Extract experience years from text."""
        lower = text.lower()
        for pattern in cls.EXPERIENCE_PATTERNS:
            match = re.search(pattern, lower)
            if match and match.group("years"):
                try:
                    return int(match.group("years"))
                except ValueError:
                    continue

        if "senior" in lower or "lead" in lower:
            return 5
        if "mid-level" in lower or "mid level" in lower:
            return 3
        if "junior" in lower:
            return 1
        return 2

    @classmethod
    def _extract_education(cls, text: str) -> str:
        """Extract education level from text."""
        lower = text.lower()
        for key, label in cls.EDUCATION_LEVELS.items():
            if key in lower:
                return label
        return "Bachelor's degree or equivalent"

    @classmethod
    def _profile_level(cls, text: str, skill: str) -> str:
        """Determine skill level based on context."""
        lower = text.lower()
        if any(prefix in lower for prefix in ["senior", "expert", "advanced", "lead"]):
            return "advanced"
        if any(prefix in lower for prefix in ["junior", "entry", "beginner"]):
            return "beginner"
        return "intermediate"
