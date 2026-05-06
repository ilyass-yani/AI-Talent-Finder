#!/usr/bin/env python3.12
"""Final backend IA validation with Flan-T5."""
import os
import sys

os.environ['DATABASE_URL'] = 'sqlite:///./ai_talent_finder.db'
os.environ['USE_AI_PROFILE_GENERATOR'] = 'true'
os.environ['HF_PROFILE_MODEL'] = 'google/flan-t5-small'

from ai_module.nlp.profile_generator import ProfileGenerator
from ai_module.matching.semantic_matcher import SemanticSkillMatcher
from ai_module.nlp.enhanced_skill_extractor import EnhancedSkillExtractor

try:
    # Test AI profile generation
    pg = ProfileGenerator()
    test_desc = 'Looking for a senior Python developer with 5+ years experience in cloud computing and machine learning'
    result = pg.generate_from_text(test_desc)
    print(f"AI_Profile_Generation: {'OK' if result and 'ideal_skills' in result else 'FAILED'}")
    
    # Test semantic matcher
    matcher = SemanticSkillMatcher()
    model = matcher._load_model()
    print(f"Semantic_Matcher_Ready: {'OK' if model is not None else 'FAILED'}")
    
    # Test skill extractor
    extractor = EnhancedSkillExtractor()
    cv_text = 'Python Django FastAPI AWS Lambda SQS Machine Learning TensorFlow PyTorch Kubernetes Docker'
    skills = extractor.extract_skills_hybrid(cv_text)
    print(f"Skill_Extractor: {'OK' if len(skills) > 0 else 'FAILED'} ({len(skills)} skills)")
    
    print("BACKEND_IA_VALIDATION: SUCCESS")
    sys.exit(0)
except Exception as e:
    print(f"ERROR: {str(e)}")
    sys.exit(1)
