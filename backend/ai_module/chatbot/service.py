"""
Chatbot Module - AI-powered conversation and profile generation
Étape 8 - Chatbot & Génération de profil idéal
"""

from typing import List, Dict, Optional
from anthropic import Anthropic


class ChatbotService:
    """
    Chatbot service using Anthropic Claude
    Handles 4 types of questions:
    1. Explanation - "Why does this candidate have score X?"
    2. Comparison - "Compare these candidates"
    3. Exploration - "Find candidates with skill X"
    4. Adjustment - "Change weight of skill X"
    """
    
    SYSTEM_PROMPT = """You are an expert recruitment consultant chatbot for AI Talent Finder.
Your role is to help recruiters make informed hiring decisions by:
1. Explaining candidate scores and matching results
2. Comparing candidates profiles
3. Helping explore candidate databases
4. Suggesting criteria adjustments

Always be professional, concise, and data-driven.
Provide specific numbers and examples when available.
Format your responses clearly with bullet points or tables when needed."""
    
    def __init__(self, api_key: str):
        """
        Initialize chatbot with Anthropic API key
        
        Args:
            api_key: Anthropic Claude API key
        """
        self.client = Anthropic()
        self.api_key = api_key
        self.conversation_history = []
    
    def add_context(self, context: Dict) -> str:
        """
        Add context about current recruiter state
        Context includes: current criteria, top candidates, filters
        
        Args:
            context: {
                "criteria": {"title": "...", "skills": {...}},
                "top_candidates": [{"name": "...", "score": ...}, ...],
                "filters": {...}
            }
        Returns:
            Formatted context string
        """
        context_str = "CURRENT CONTEXT:\n"
        
        if "criteria" in context:
            context_str += f"\nJob Criteria: {context['criteria'].get('title', 'Unnamed')}\n"
            if "skills" in context["criteria"]:
                context_str += "Required Skills:\n"
                for skill, weight in context["criteria"]["skills"].items():
                    context_str += f"  - {skill}: {weight}%\n"
        
        if "top_candidates" in context:
            context_str += "\nTop Candidates:\n"
            for cand in context["top_candidates"][:5]:
                context_str += f"  - {cand.get('name', 'Unknown')} (Score: {cand.get('score', 0):.1f}%)\n"
        
        return context_str
    
    def explain_score(self, candidate_name: str, score: float, breakdown: Dict) -> str:
        """
        Explain why a candidate has a specific score
        
        Args:
            candidate_name: Candidate name
            score: Match score (0-100)
            breakdown: Skill breakdown {skill: points}
        
        Returns:
            AI-generated explanation
        """
        message = f"""Please explain why {candidate_name} has a match score of {score:.1f}%.

Score Breakdown:
"""
        for skill, points in breakdown.items():
            message += f"- {skill}: {points}\n"
        
        return self._send_message(message)
    
    def compare_candidates(self, candidates: List[Dict]) -> str:
        """
        Compare multiple candidates
        
        Args:
            candidates: List of {name, score, skills}
        
        Returns:
            AI-generated comparison
        """
        message = "Please compare these candidates for the position:\n\n"
        for cand in candidates:
            message += f"- {cand.get('name', 'Candidate')}: Score {cand.get('score', 0):.1f}%\n"
            if "skills" in cand:
                message += f"  Skills: {', '.join(cand['skills'][:5])}\n"
        
        message += "\nHighlight strengths, weaknesses, and your recommendation."
        
        return self._send_message(message)
    
    def generate_ideal_profile(self, job_description: str) -> Dict:
        """
        Generate ideal candidate profile from job description
        
        Étape 8 - Génération de profil idéal
        
        Args:
            job_description: Text description of job needs
        
        Returns:
            {
                "skills": {skill: weight (0-100)},
                "experience": "years",
                "education": "level",
                "explanation": "why these choices"
            }
        """
        prompt = f"""Based on this job description, generate an ideal candidate profile:

{job_description}

Please extract:
1. Key technical skills (with importance weight 0-100)
2. Soft skills required
3. Years of experience
4. Education requirements
5. Languages

Return as structured data."""
        
        response = self._send_message(prompt)
        
        # Parse response into structure (simplified - enhance with actual parsing)
        return {
            "skills": {},  # Would parse from response
            "experience": "3+",
            "education": "Bachelor's",
            "explanation": response
        }
    
    def _send_message(self, user_message: str) -> str:
        """
        Send message to Claude and get response
        
        Args:
            user_message: User input
        
        Returns:
            AI response
        """
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Call Claude API
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            system=self.SYSTEM_PROMPT,
            messages=self.conversation_history
        )
        
        # Extract response
        assistant_message = response.content[0].text
        
        # Add to history
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })
        
        return assistant_message
    
    def chat(self, user_input: str, context: Optional[Dict] = None) -> str:
        """
        Main chat endpoint
        Handles all 4 types of questions automatically
        
        Args:
            user_input: User question/input
            context: Optional context about current state
        
        Returns:
            Chatbot response
        """
        # Prepare message with context
        if context:
            full_message = self.add_context(context) + "\n\n" + user_input
        else:
            full_message = user_input
        
        return self._send_message(full_message)
    
    def reset_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []
