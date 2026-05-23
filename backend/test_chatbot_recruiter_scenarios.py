#!/usr/bin/env python3
"""
Test Chatbot Quality on Real Recruiter Scenarios

This script tests the chatbot on 3 real recruiter scenarios:
1. "Explain why candidate X matches job Y"
2. "Compare candidate A vs candidate B for role Z"
3. "What is the ideal profile for this job?"

Requires: ANTHROPIC_API_KEY environment variable set
"""

import json
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from anthropic import Anthropic
from app.models import Job, Candidate
from app.services.matching_service import MatchingService
from app.schemas import CandidateProfile
from ai_module.nlp.enhanced_skill_extractor import EnhancedSkillExtractor
from ai_module.matching.semantic_matcher import SemanticSkillMatcher


class ChatbotQualityTester:
    """Test chatbot quality on recruiter scenarios."""

    def __init__(self, api_key: str = None):
        """Initialize with Anthropic API key."""
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        
        self.client = Anthropic()
        self.conversation_history = []
        self.skill_extractor = EnhancedSkillExtractor(load_ner=False)

    def reset_conversation(self):
        """Reset conversation history for new scenario."""
        self.conversation_history = []

    def _chat(self, user_message: str) -> str:
        """Send message to Claude and get response."""
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            system="""You are an expert HR recruiter assistant. You help recruiters understand candidate-job matches, 
compare candidates, and define ideal profiles. Be concise but insightful. Focus on:
- Technical skill alignment
- Experience relevance
- Growth potential
- Risk factors""",
            messages=self.conversation_history
        )
        
        assistant_message = response.content[0].text
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })
        
        return assistant_message

    def scenario_1_explain_match(self):
        """Scenario 1: Explain why candidate matches job."""
        print("\n" + "="*70)
        print("SCENARIO 1: Explain Candidate-Job Match")
        print("="*70)
        
        self.reset_conversation()
        
        # Sample candidate
        candidate_cv = """
        Senior Python Developer
        Skills: Python 10 years, FastAPI 4 years, Docker, Kubernetes, PostgreSQL, Redis
        Experience: 
        - Led team of 5 developers at TechCorp (3 years)
        - Built microservices architecture serving 1M+ users
        - Open source contributor (Flask, requests)
        """
        
        # Sample job
        job_description = """
        Senior Backend Engineer - Python/FastAPI
        Location: Remote
        Responsibilities:
        - Design and implement scalable APIs
        - Lead technical decisions for backend team
        - Mentor junior developers
        Requirements:
        - 5+ years Python experience
        - FastAPI or similar framework
        - Docker & container orchestration knowledge
        - Team leadership experience
        """
        
        # Extract skills from CV
        extracted_skills = self.skill_extractor.extract_skills_hybrid(candidate_cv)
        
        # Create prompt
        prompt = f"""
I have a candidate with this profile:
{candidate_cv}

Extracted skills: {', '.join(extracted_skills[:10])}

For this job:
{job_description}

Explain why this candidate is a good or bad fit, in 3-4 sentences. Focus on skill alignment and experience.
"""
        
        print("\n📋 Candidate CV:")
        print(candidate_cv)
        print("\n📋 Job Description:")
        print(job_description)
        print(f"\n🔍 Extracted skills: {', '.join(extracted_skills[:8])}")
        
        response = self._chat(prompt)
        print(f"\n💬 Chatbot Analysis:\n{response}")
        
        # Follow-up question
        follow_up = "What are the top 3 risks with this candidate?"
        print(f"\n❓ Follow-up: {follow_up}")
        response2 = self._chat(follow_up)
        print(f"💬 Response:\n{response2}")
        
        return {
            "scenario": "explain_match",
            "initial_response": response,
            "followup_response": response2,
            "status": "✅ SUCCESS"
        }

    def scenario_2_compare_candidates(self):
        """Scenario 2: Compare two candidates for same role."""
        print("\n" + "="*70)
        print("SCENARIO 2: Compare Candidates for Same Role")
        print("="*70)
        
        self.reset_conversation()
        
        candidate_a = """
        Software Engineer
        Skills: Python 8 years, Django 5 years, JavaScript, React, AWS, PostgreSQL
        Experience: 
        - Full-stack developer at StartupX (4 years)
        - Shipped 3 major products
        - No team leadership experience
        - Bachelor's in CS
        """
        
        candidate_b = """
        Tech Lead
        Skills: Python 6 years, FastAPI 3 years, Docker, Kubernetes, AWS, Team leadership
        Experience:
        - Led backend team of 3 at EstablishedCorp (2 years)
        - Backend architect, migrated monolith to microservices
        - 2 years team leadership
        - Master's in Computer Science
        """
        
        role_desc = """
        Senior Backend Engineer - Team Leadership Track
        - 5+ years backend development
        - Team leadership experience preferred
        - FastAPI or similar modern framework
        - Cloud deployment (AWS)
        """
        
        prompt = f"""
Compare these 2 candidates for this role:

**Candidate A:**
{candidate_a}

**Candidate B:**
{candidate_b}

**Role:**
{role_desc}

Which candidate is better suited? Create a quick comparison table with pros/cons.
"""
        
        print("\n👤 Candidate A:")
        print(candidate_a)
        print("\n👤 Candidate B:")
        print(candidate_b)
        print("\n📋 Role Description:")
        print(role_desc)
        
        response = self._chat(prompt)
        print(f"\n💬 Comparison:\n{response}")
        
        # Follow-up
        follow_up = "If I can only hire one, who should it be and why?"
        print(f"\n❓ Follow-up: {follow_up}")
        response2 = self._chat(follow_up)
        print(f"💬 Response:\n{response2}")
        
        return {
            "scenario": "compare_candidates",
            "initial_response": response,
            "followup_response": response2,
            "status": "✅ SUCCESS"
        }

    def scenario_3_ideal_profile(self):
        """Scenario 3: Define ideal profile for role."""
        print("\n" + "="*70)
        print("SCENARIO 3: Define Ideal Profile for Role")
        print("="*70)
        
        self.reset_conversation()
        
        job_description = """
        Data Engineer
        Location: San Francisco
        We're building a real-time data pipeline for a high-frequency trading platform.
        
        Responsibilities:
        - Design and maintain ETL pipelines
        - Build data infrastructure on cloud
        - Optimize query performance
        - Mentor data analysts
        
        Tech stack: Python, Spark, Kafka, PostgreSQL, GCP, Airflow
        
        Company: 5-year-old fintech startup, $200M funding
        """
        
        prompt = f"""
Describe the ideal candidate profile for this role. Consider:
- Technical skills (specific tools, languages)
- Experience depth needed
- Soft skills
- Team fit
- Growth potential

Role details:
{job_description}

Be specific: what's the exact experience level, what tools matter most?
"""
        
        print("\n📋 Job Description:")
        print(job_description)
        
        response = self._chat(prompt)
        print(f"\n💬 Ideal Profile:\n{response}")
        
        # Follow-up
        follow_up = "How would you weight these requirements? Which are must-have vs nice-to-have?"
        print(f"\n❓ Follow-up: {follow_up}")
        response2 = self._chat(follow_up)
        print(f"💬 Response:\n{response2}")
        
        return {
            "scenario": "ideal_profile",
            "initial_response": response,
            "followup_response": response2,
            "status": "✅ SUCCESS"
        }


def main():
    """Run all chatbot scenarios."""
    print("\n🤖 AI Talent Finder — Chatbot Quality Testing")
    print("Testing 3 real recruiter scenarios")
    
    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n❌ ERROR: ANTHROPIC_API_KEY not set")
        print("Export it: export ANTHROPIC_API_KEY='sk-...'")
        return 1
    
    print(f"✅ Anthropic API configured")
    
    try:
        tester = ChatbotQualityTester(api_key)
    except Exception as e:
        print(f"❌ Failed to initialize chatbot: {e}")
        return 1
    
    results = []
    
    # Run scenarios
    try:
        result1 = tester.scenario_1_explain_match()
        results.append(result1)
    except Exception as e:
        print(f"\n❌ Scenario 1 failed: {e}")
        results.append({"scenario": "explain_match", "status": f"❌ FAILED: {e}"})
    
    try:
        result2 = tester.scenario_2_compare_candidates()
        results.append(result2)
    except Exception as e:
        print(f"\n❌ Scenario 2 failed: {e}")
        results.append({"scenario": "compare_candidates", "status": f"❌ FAILED: {e}"})
    
    try:
        result3 = tester.scenario_3_ideal_profile()
        results.append(result3)
    except Exception as e:
        print(f"\n❌ Scenario 3 failed: {e}")
        results.append({"scenario": "ideal_profile", "status": f"❌ FAILED: {e}"})
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    success_count = sum(1 for r in results if r.get("status") == "✅ SUCCESS")
    total_count = len(results)
    
    for r in results:
        scenario = r.get("scenario", "unknown").replace("_", " ").title()
        status = r.get("status", "?")
        print(f"{status} — {scenario}")
    
    print(f"\n📊 Result: {success_count}/{total_count} scenarios passed")
    
    # Save results
    report_path = Path(__file__).parent / "reports" / "chatbot_quality_test.json"
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"📄 Report saved to: {report_path}")
    
    return 0 if success_count == total_count else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
