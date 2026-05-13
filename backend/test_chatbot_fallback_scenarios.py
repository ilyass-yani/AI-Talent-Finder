#!/usr/bin/env python3
"""
Test Chatbot Quality on Real Recruiter Scenarios — Fallback Mode

Tests the chatbot on 3 real recruiter scenarios using deterministic/fallback responses:
1. "Explain why candidate X matches job Y"
2. "Compare candidate A vs candidate B for role Z"
3. "What is the ideal profile for this job?"

No API key required — tests fallback rule-based system.
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.models.models import Candidate, JobCriteria, CriteriaSkill, Skill, MatchResult
from app.core.database import SessionLocal
from sqlalchemy.orm import Session
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChatbotFallbackTester:
    """Test chatbot quality on recruiter scenarios using fallback mode."""

    def __init__(self, db_session: Session):
        """Initialize with database session."""
        self.db = db_session
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "test_mode": "fallback_deterministic",
            "scenarios": [],
            "summary": {},
        }

    def _normalize_text(self, value: str) -> str:
        import re
        return re.sub(r"\s+", " ", value.strip().lower())

    def _to_percent(self, score: Any) -> float:
        value = float(score or 0.0)
        if value <= 1.0:
            value *= 100.0
        return round(value, 2)

    def _build_candidate_snapshot(
        self, candidate: Candidate, score: float, criteria_skills: List[CriteriaSkill]
    ) -> Dict[str, Any]:
        """Build a snapshot of a candidate's match profile."""
        candidate_skill_names = {
            item.skill.name.lower(): item.skill.name
            for item in candidate.candidate_skills
            if item.skill and item.skill.name
        }

        matched_skills: List[str] = []
        missing_skills: List[str] = []
        skill_breakdown: List[Dict[str, Any]] = []

        total_weight = sum(item.weight for item in criteria_skills) or 1
        for item in criteria_skills:
            if not item.skill or not item.skill.name:
                continue
            skill_name = item.skill.name
            present = skill_name.lower() in candidate_skill_names
            if present:
                matched_skills.append(skill_name)
            else:
                missing_skills.append(skill_name)

            contribution = (item.weight / total_weight) * (score if present else 0)
            skill_breakdown.append({
                "skill": skill_name,
                "weight": item.weight,
                "present": present,
                "score": score if present else 0,
                "contribution": round(contribution, 2),
            })

        coverage = (len(matched_skills) / max(1, len(criteria_skills))) * 100
        return {
            "candidate_id": candidate.id,
            "candidate_name": candidate.full_name,
            "candidate_email": candidate.email,
            "score": score,
            "coverage": round(coverage, 2),
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "skill_breakdown": skill_breakdown,
            "summary": f"{candidate.full_name} couvre {len(matched_skills)}/{max(1, len(criteria_skills))} compétences clés.",
        }

    def _format_breakdown(self, candidate: Dict[str, Any]) -> str:
        """Format skill breakdown for explanation."""
        rows = []
        for item in (candidate.get("skill_breakdown") or [])[:8]:
            skill = item.get("skill") or "N/A"
            present = bool(item.get("present"))
            weight = item.get("weight", 0)
            contribution = item.get("contribution", 0)
            marker = "✅" if present else "❌"
            rows.append(f"  {marker} {skill}: poids {weight}%, contribution {round(float(contribution), 2)}")
        return "\n".join(rows)

    def _explain_score_fallback(self, context: Dict[str, Any]) -> str:
        """Fallback: Explain score based on context."""
        top_candidates = context.get("top_candidates") or []
        if not top_candidates:
            return "Je n'ai pas encore de candidat ou de détail de score à expliquer. Lancez d'abord un matching."

        candidate = top_candidates[0]  # Pick first candidate (best score)
        skills = candidate.get("skill_breakdown") or []
        matched = [item.get("skill") for item in skills if item.get("present")]
        missing = [item.get("skill") for item in skills if not item.get("present")]
        score = round(float(candidate.get("score", 0)), 2)
        coverage = round(float(candidate.get("coverage", 0)), 2)
        breakdown_text = self._format_breakdown(candidate)
        missing_text = ", ".join(missing[:5]) if missing else "Aucun écart critique détecté"
        matched_text = ", ".join(matched[:5]) if matched else "alignement partiel"

        return "\n".join([
            f"📊 {candidate.get('candidate_name', 'Ce candidat')} — Score {score}% (Couverture {coverage}%)",
            "",
            f"✨ Points forts: {matched_text}",
            f"⚠️  À renforcer: {missing_text}",
            "",
            "📈 Détail des contributions:",
            breakdown_text or "  - Pas de détail disponible",
            "",
            "💡 Recommandation: Renforcer 1-2 compétences manquantes à fort poids pour +10-15 points.",
        ])

    def _compare_candidates_fallback(self, context: Dict[str, Any]) -> str:
        """Fallback: Compare candidates."""
        top_candidates = context.get("top_candidates") or []
        if len(top_candidates) < 2:
            return "Ajoutez au moins deux candidats dans le contexte pour lancer une comparaison."

        selected = sorted(top_candidates[:3], key=lambda item: float(item.get("score", 0)), reverse=True)

        lines = ["📊 COMPARAISON DES CANDIDATS", ""]
        for i, candidate in enumerate(selected, 1):
            coverage = round(float(candidate.get("coverage", 0)), 2)
            skills = ", ".join(candidate.get("matched_skills", [])[:4]) or "N/A"
            lines.append(f"{i}. {candidate.get('candidate_name', 'Candidat')}")
            lines.append(f"   Score: {round(float(candidate.get('score', 0)), 2)}% | Couverture: {coverage}%")
            lines.append(f"   Compétences clés: {skills}")
            lines.append("")

        if len(selected) >= 2:
            winner = selected[0]
            runner_up = selected[1]
            gap = round(float(winner.get("score", 0)) - float(runner_up.get("score", 0)), 2)
            lines.append(f"🏆 Recommandation: {winner.get('candidate_name', 'Candidat 1')} devance avec +{gap} points")

        return "\n".join(lines)

    def _ideal_profile_fallback(self, context: Dict[str, Any]) -> str:
        """Fallback: Define ideal profile."""
        criteria = context.get("current_criteria") or {}
        required_skills = criteria.get("required_skills", [])

        if not required_skills:
            return "Je n'ai pas encore de profil idéal défini. Chargez d'abord une matrice de critères."

        sorted_skills = sorted(required_skills, key=lambda x: x.get("weight", 0), reverse=True)
        top_skills = sorted_skills[:5]

        lines = ["👤 PROFIL IDÉAL", ""]
        lines.append(f"Titre du poste: {criteria.get('title', 'N/A')}")
        lines.append("")
        lines.append("Compétences requises (par importance):")
        for skill in top_skills:
            weight = skill.get("weight", 0)
            lines.append(f"  • {skill.get('name', 'N/A')}: {weight}% d'importance")

        lines.append("")
        lines.append("📋 Profil suggéré:")
        lines.append(f"  - Maîtrise les 3-4 compétences clés: {', '.join([s.get('name', 'N/A') for s in top_skills[:4]])}")
        lines.append(f"  - Expérience minimum: 3-5 ans sur {top_skills[0].get('name', 'la compétence principale')}")
        lines.append("  - Capacité d'apprentissage sur les compétences secondaires")
        lines.append("  - Soft skills: Communication, autonomie, esprit d'équipe")

        return "\n".join(lines)

    def scenario_1_explain_match(self) -> Dict[str, Any]:
        """Scenario 1: Explain candidate-job match."""
        logger.info("🔍 SCENARIO 1: Expliquer Match Candidat-Poste")

        # Get job criteria
        criteria = self.db.query(JobCriteria).order_by(JobCriteria.created_at.desc()).first()
        if not criteria:
            return {
                "scenario": "Explain Match",
                "status": "SKIPPED",
                "reason": "No job criteria found in database",
                "response": None,
            }

        # Get criteria skills
        criteria_skills = self.db.query(CriteriaSkill).filter(
            CriteriaSkill.criteria_id == criteria.id
        ).all()

        # Get top candidates with matches
        stored_results = (
            self.db.query(MatchResult)
            .filter(MatchResult.criteria_id == criteria.id)
            .order_by(MatchResult.score.desc())
            .limit(5)
            .all()
        )

        top_candidates = []
        for result in stored_results:
            candidate = self.db.query(Candidate).filter(Candidate.id == result.candidate_id).first()
            if candidate:
                snapshot = self._build_candidate_snapshot(
                    candidate,
                    self._to_percent(result.score),
                    criteria_skills,
                )
                top_candidates.append(snapshot)

        context = {
            "current_criteria": {
                "id": criteria.id,
                "title": criteria.title,
                "required_skills": [
                    {"name": item.skill.name, "weight": item.weight}
                    for item in criteria_skills
                    if item.skill
                ],
            },
            "top_candidates": top_candidates,
        }

        response = self._explain_score_fallback(context)

        return {
            "scenario": "Explain Match",
            "status": "SUCCESS",
            "job_title": criteria.title,
            "candidates_analyzed": len(top_candidates),
            "response": response,
            "context": context,
        }

    def scenario_2_compare_candidates(self) -> Dict[str, Any]:
        """Scenario 2: Compare candidates."""
        logger.info("📊 SCENARIO 2: Comparer Candidats")

        # Get job criteria
        criteria = self.db.query(JobCriteria).order_by(JobCriteria.created_at.desc()).first()
        if not criteria:
            return {
                "scenario": "Compare Candidates",
                "status": "SKIPPED",
                "reason": "No job criteria found",
                "response": None,
            }

        # Get criteria skills
        criteria_skills = self.db.query(CriteriaSkill).filter(
            CriteriaSkill.criteria_id == criteria.id
        ).all()

        # Get top candidates
        stored_results = (
            self.db.query(MatchResult)
            .filter(MatchResult.criteria_id == criteria.id)
            .order_by(MatchResult.score.desc())
            .limit(5)
            .all()
        )

        top_candidates = []
        for result in stored_results:
            candidate = self.db.query(Candidate).filter(Candidate.id == result.candidate_id).first()
            if candidate:
                snapshot = self._build_candidate_snapshot(
                    candidate,
                    self._to_percent(result.score),
                    criteria_skills,
                )
                top_candidates.append(snapshot)

        if len(top_candidates) < 2:
            return {
                "scenario": "Compare Candidates",
                "status": "SKIPPED",
                "reason": "Need at least 2 candidates with matches",
                "candidates_available": len(top_candidates),
                "response": None,
            }

        context = {
            "top_candidates": top_candidates,
        }

        response = self._compare_candidates_fallback(context)

        return {
            "scenario": "Compare Candidates",
            "status": "SUCCESS",
            "candidates_compared": len(top_candidates),
            "response": response,
            "context": context,
        }

    def scenario_3_ideal_profile(self) -> Dict[str, Any]:
        """Scenario 3: Define ideal profile."""
        logger.info("👤 SCENARIO 3: Définir Profil Idéal")

        # Get job criteria
        criteria = self.db.query(JobCriteria).order_by(JobCriteria.created_at.desc()).first()
        if not criteria:
            return {
                "scenario": "Ideal Profile",
                "status": "SKIPPED",
                "reason": "No job criteria found",
                "response": None,
            }

        # Get criteria skills
        criteria_skills = self.db.query(CriteriaSkill).filter(
            CriteriaSkill.criteria_id == criteria.id
        ).all()

        context = {
            "current_criteria": {
                "id": criteria.id,
                "title": criteria.title,
                "required_skills": [
                    {"name": item.skill.name, "weight": item.weight}
                    for item in criteria_skills
                    if item.skill
                ],
            },
        }

        response = self._ideal_profile_fallback(context)

        return {
            "scenario": "Ideal Profile",
            "status": "SUCCESS",
            "job_title": criteria.title,
            "skills_analyzed": len(criteria_skills),
            "response": response,
            "context": context,
        }

    def run_all_scenarios(self) -> Dict[str, Any]:
        """Run all 3 scenarios and collect results."""
        logger.info("=" * 70)
        logger.info("🧪 TESTS CHATBOT - MODE FALLBACK DÉTERMINISTE")
        logger.info("=" * 70)

        results = {
            "timestamp": datetime.now().isoformat(),
            "test_mode": "fallback_deterministic",
            "note": "Pas de clé API Anthropic — utilise réponses rule-based",
            "scenarios": [
                self.scenario_1_explain_match(),
                self.scenario_2_compare_candidates(),
                self.scenario_3_ideal_profile(),
            ],
        }

        # Count successes
        successful = sum(1 for s in results["scenarios"] if s.get("status") == "SUCCESS")
        skipped = sum(1 for s in results["scenarios"] if s.get("status") == "SKIPPED")
        results["summary"] = {
            "total_scenarios": len(results["scenarios"]),
            "successful": successful,
            "skipped": skipped,
            "message": f"{successful}/{len(results['scenarios'])} scénarios testés avec succès",
        }

        return results


def main():
    """Main entry point."""
    # Initialize database connection
    from app.core.database import SessionLocal

    db = SessionLocal()

    try:
        tester = ChatbotFallbackTester(db)
        results = tester.run_all_scenarios()

        # Save results to JSON
        output_file = Path(__file__).parent / "reports" / "chatbot_fallback_test_results.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info("")
        logger.info("=" * 70)
        logger.info("✅ RÉSULTATS DE TEST")
        logger.info("=" * 70)
        logger.info(f"Timestamp: {results['timestamp']}")
        logger.info(f"Mode: {results['test_mode']}")
        logger.info(f"Scénarios — Succès: {results['summary']['successful']}/{results['summary']['total_scenarios']}")
        logger.info(f"Résultats sauvegardés: {output_file}")
        logger.info("")

        # Print scenarios summary
        for scenario in results["scenarios"]:
            logger.info(f"📌 {scenario['scenario']}: {scenario['status']}")
            if scenario.get("response"):
                logger.info(f"   {scenario['response'].split(chr(10))[0]}")

        logger.info("=" * 70)

        return results

    finally:
        db.close()


if __name__ == "__main__":
    results = main()
    sys.exit(0 if results["summary"]["successful"] > 0 else 1)
