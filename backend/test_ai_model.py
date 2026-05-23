#!/usr/bin/env python3
"""
Example script showing how to integrate a custom Hugging Face model
for profile generation in the AI Talent Finder.

This script demonstrates:
1. Loading a custom model
2. Testing profile generation
3. Customizing the AI output parsing

Usage:
1. Choose your model from Hugging Face
2. Update the MODEL_NAME variable
3. Customize the _parse_ai_output method in profile_generator.py
4. Set USE_AI_PROFILE_GENERATOR=true in your .env file
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_module.nlp.profile_generator import ProfileGenerator

def test_ai_model():
    """Test the AI model with a sample job description."""

    # Sample job description
    job_description = """
    Senior Python Developer

    We are looking for a Senior Python Developer with 5+ years of experience.

    Required Skills:
    - Python (expert level)
    - FastAPI or Django
    - PostgreSQL or MySQL
    - Docker and Kubernetes
    - AWS or Azure cloud platforms
    - REST APIs and microservices

    Nice to have:
    - React.js
    - Machine Learning experience
    - DevOps practices

    Requirements:
    - Bachelor's degree in Computer Science or equivalent
    - 5+ years of software development experience
    - Experience with agile development
    - Strong problem-solving skills
    """

    print("Testing AI-powered profile generation...")
    print("=" * 50)

    # Enable AI mode
    ProfileGenerator.USE_AI_MODEL = True
    ProfileGenerator.HF_MODEL_NAME = "facebook/bart-large-cnn"  # Change this to your model

    try:
        profile = ProfileGenerator.generate_from_text(job_description)
        print("Generated Profile:")
        print(f"Method used: {profile.get('method_used', 'unknown')}")
        print(f"Overview: {profile.get('overview', 'N/A')}")
        print(f"Technical skills: {profile.get('technical_skills', [])}")
        print(f"Experience required: {profile.get('experience_years', 'N/A')} years")
        print(f"Education required: {profile.get('education_level', 'N/A')}")

    except Exception as e:
        print(f"Error: {e}")
        print("Falling back to rule-based generation...")

        ProfileGenerator.USE_AI_MODEL = False
        profile = ProfileGenerator.generate_from_text(job_description)
        print("Rule-based Profile:")
        print(f"Method used: {profile.get('method_used', 'unknown')}")
        print(f"Technical skills: {profile.get('technical_skills', [])}")
        print(f"Experience required: {profile.get('experience_years', 'N/A')} years")

if __name__ == "__main__":
    test_ai_model()