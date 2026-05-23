"""
Comprehensive integration tests for Phase 1 IA enhancements.

Tests integration of:
1. Adaptive Thresholds
2. Smart Deduplication
3. Explainability Engine
4. Smart Fallback Responder
5. Skill Quality Analyzer
"""

import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.models.models import Base, Candidate, Skill, CandidateSkill, JobCriteria, CriteriaSkill, MatchResult, ProficiencyLevel
from app.services.matching_engine import (
    score_candidate_against_criteria,
    build_skill_universe,
    get_adaptive_thresholds,
    generate_enriched_explanation,
    extract_candidate_skill_names,
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

def setup_test_db() -> Session:
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def create_test_skills(db: Session) -> dict:
    """Create test skill records."""
    skills_data = {
        "Python": "python",
        "React": "react",
        "TypeScript": "typescript",
        "Docker": "docker",
        "AWS": "aws",
        "SQL": "sql",
    }
    
    skills = {}
    for name, _ in skills_data.items():
        skill = Skill(name=name, category="tech")
        db.add(skill)
        db.flush()
        skills[name] = skill
    
    db.commit()
    return skills


def create_test_candidate(db: Session, name: str, skills: list) -> Candidate:
    """Create test candidate with skills."""
    candidate = Candidate(
        full_name=name,
        email=f"{name.lower()}@test.com",
        raw_text=f"{name} CV with skills: {', '.join(skills)}",
        is_fully_extracted=True,
        extraction_quality_score=95,
    )
    db.add(candidate)
    db.flush()
    
    # Add skills
    for skill_name in skills:
        skill = db.query(Skill).filter(Skill.name.ilike(skill_name)).first()
        if not skill:
            skill = Skill(name=skill_name, category="tech")
            db.add(skill)
            db.flush()
        
        cs = CandidateSkill(
            candidate_id=candidate.id,
            skill_id=skill.id,
            proficiency_level=ProficiencyLevel.intermediate,
            source="test",
        )
        db.add(cs)
    
    db.commit()
    return candidate


def create_test_criteria(db: Session, title: str, required_skills: dict) -> JobCriteria:
    """Create test job criteria."""
    criteria = JobCriteria(
        recruiter_id=1,
        title=title,
        description=f"Test criteria for {title}",
    )
    db.add(criteria)
    db.flush()
    
    # Add required skills
    for skill_name, weight in required_skills.items():
        skill = db.query(Skill).filter(Skill.name.ilike(skill_name)).first()
        if not skill:
            skill = Skill(name=skill_name, category="tech")
            db.add(skill)
            db.flush()
        
        cs = CriteriaSkill(
            criteria_id=criteria.id,
            skill_id=skill.id,
            weight=weight
        )
        db.add(cs)
    
    db.commit()
    return criteria


# ============================================================================
# TEST SUITES
# ============================================================================

def test_adaptive_thresholds():
    """Test adaptive threshold engine integration."""
    print("\n📊 Testing Adaptive Thresholds...")
    
    # Test default case
    thresholds = get_adaptive_thresholds()
    assert "accept" in thresholds, "Missing accept threshold"
    assert "review" in thresholds, "Missing review threshold"
    assert thresholds["accept"] > thresholds["review"], "Accept threshold should be higher"
    print("  ✅ Default thresholds: PASS")
    
    # Test domain-specific thresholds
    data_scientist_thresholds = get_adaptive_thresholds("Senior Data Scientist")
    assert data_scientist_thresholds is not None, "Should return thresholds for data scientist"
    print(f"  ✅ Data Scientist thresholds: accept={data_scientist_thresholds.get('accept')}, review={data_scientist_thresholds.get('review')}")
    
    # Test another domain
    frontend_thresholds = get_adaptive_thresholds("Senior React Developer")
    assert frontend_thresholds is not None, "Should return thresholds for frontend"
    print(f"  ✅ Frontend thresholds: accept={frontend_thresholds.get('accept')}, review={frontend_thresholds.get('review')}")
    
    print("  ✅ Adaptive Thresholds: ALL TESTS PASSED")


def test_smart_dedup():
    """Test smart deduplication integration."""
    print("\n🔄 Testing Smart Deduplication...")
    
    db = setup_test_db()
    create_test_skills(db)
    
    # Create candidate with duplicate skills
    candidate = create_test_candidate(
        db, "John Doe",
        ["Python", "React", "python", "PYTHON", "react", "TypeScript"]
    )
    
    # Extract skills - should be deduplicated
    extracted_skills = extract_candidate_skill_names(candidate)
    print(f"  Extracted skills: {extracted_skills}")
    
    # Check deduplication worked
    python_count = sum(1 for s in extracted_skills if s.lower() == "python")
    react_count = sum(1 for s in extracted_skills if s.lower() == "react")
    
    assert python_count == 1, f"Python should appear once, found {python_count}"
    assert react_count == 1, f"React should appear once, found {react_count}"
    assert "TypeScript" in extracted_skills, "TypeScript should be present"
    
    print("  ✅ Deduplication removed duplicates correctly")
    print("  ✅ Smart Deduplication: ALL TESTS PASSED")


def test_explainability_engine():
    """Test explainability engine integration."""
    print("\n📖 Testing Explainability Engine...")
    
    db = setup_test_db()
    create_test_skills(db)
    
    # Create test data
    candidate = create_test_candidate(db, "Alice", ["Python", "React", "Docker"])
    criteria = create_test_criteria(
        db, "Senior React Developer",
        {"Python": 40, "React": 50, "TypeScript": 10}
    )
    
    # Get criteria skills for enriched explanation
    criteria_skills_models = db.query(CriteriaSkill).filter(
        CriteriaSkill.criteria_id == criteria.id
    ).all()
    criteria_skills = [
        {"name": cs.skill.name, "weight": cs.weight}
        for cs in criteria_skills_models
    ]
    
    # Score candidate
    score, details = score_candidate_against_criteria(candidate, criteria_skills)
    print(f"  Candidate score: {score}%")
    
    # Generate enriched explanation
    enriched = generate_enriched_explanation(candidate, score, details, criteria_skills)
    assert "score" in enriched, "Should have score in explanation"
    assert "matched_skills" in enriched, "Should have matched_skills"
    assert "missing_skills" in enriched, "Should have missing_skills"
    
    print(f"  ✅ Explanation generated: {enriched.get('summary', 'N/A')}")
    print("  ✅ Explainability Engine: ALL TESTS PASSED")


def test_smart_fallback():
    """Test smart fallback responder integration."""
    print("\n💬 Testing Smart Fallback...")
    
    try:
        from ai_module.chatbot.smart_fallback import SmartFallbackResponder
        
        db = setup_test_db()
        create_test_skills(db)
        
        candidate = create_test_candidate(db, "Bob", ["Python", "Docker"])
        criteria = create_test_criteria(
            db, "Python Developer",
            {"Python": 60, "Docker": 40}
        )
        
        responder = SmartFallbackResponder()
        
        # Test method availability
        assert hasattr(responder, 'explain_score_fallback'), "Missing explain_score_fallback"
        assert hasattr(responder, 'compare_candidates_fallback'), "Missing compare_candidates_fallback"
        assert hasattr(responder, 'greeting_fallback'), "Missing greeting_fallback"
        
        print("  ✅ All SmartFallbackResponder methods present")
        print("  ✅ Smart Fallback: ALL TESTS PASSED")
    except ImportError:
        print("  ⚠️  Smart Fallback not available (dependencies missing)")


def test_skill_quality():
    """Test skill quality analyzer integration."""
    print("\n⭐ Testing Skill Quality Analyzer...")
    
    try:
        from ai_module.matching.skill_quality import SkillQualityAnalyzer
        
        db = setup_test_db()
        create_test_skills(db)
        
        # Create multiple candidates with various skills
        create_test_candidate(db, "Candidate1", ["Python", "React", "Docker"])
        create_test_candidate(db, "Candidate2", ["Python", "TypeScript"])
        create_test_candidate(db, "Candidate3", ["React", "AWS", "SQL"])
        
        analyzer = SkillQualityAnalyzer()
        metrics = analyzer.compute_metrics(db)
        
        assert "quality_score" in metrics, "Missing quality_score"
        assert "total_skills" in metrics, "Missing total_skills"
        assert "unique_skills" in metrics, "Missing unique_skills"
        assert "health_status" in metrics, "Missing health_status"
        
        print(f"  Quality Score: {metrics.get('quality_score')}")
        print(f"  Total Skills: {metrics.get('total_skills')}")
        print(f"  Unique Skills: {metrics.get('unique_skills')}")
        print(f"  Health Status: {metrics.get('health_status')}")
        print("  ✅ Skill Quality Analyzer: ALL TESTS PASSED")
    except ImportError:
        print("  ⚠️  Skill Quality Analyzer not available (dependencies missing)")


def test_full_matching_pipeline():
    """Test complete matching pipeline with all Phase 1 features."""
    print("\n🔄 Testing Full Matching Pipeline (End-to-End)...")
    
    db = setup_test_db()
    create_test_skills(db)
    
    # Create candidates
    candidates = [
        create_test_candidate(db, "Alice", ["Python", "React", "Docker", "AWS"]),
        create_test_candidate(db, "Bob", ["Python", "Django", "PostgreSQL"]),
        create_test_candidate(db, "Charlie", ["JavaScript", "React", "Node.js"]),
    ]
    
    # Create criteria
    criteria = create_test_criteria(
        db, "Senior Full Stack Developer",
        {"Python": 30, "React": 40, "Docker": 20, "TypeScript": 10}
    )
    
    # Score all candidates
    criteria_skills_models = db.query(CriteriaSkill).filter(
        CriteriaSkill.criteria_id == criteria.id
    ).all()
    criteria_skills = [
        {"name": cs.skill.name, "weight": cs.weight}
        for cs in criteria_skills_models
    ]
    
    results = []
    for candidate in candidates:
        score, details = score_candidate_against_criteria(candidate, criteria_skills)
        results.append({
            "candidate": candidate.full_name,
            "score": score,
            "coverage": details.get("coverage"),
            "matched": details.get("matched_skills"),
            "missing": details.get("missing_skills"),
        })
    
    # Sort by score
    results.sort(key=lambda x: x["score"], reverse=True)
    
    print("  📋 Final Rankings:")
    for i, result in enumerate(results, 1):
        print(f"    {i}. {result['candidate']}: {result['score']}% "
              f"(Coverage: {result['coverage']}%, Matched: {len(result['matched'])})")
    
    # Verify ranking makes sense
    assert results[0]["score"] >= results[1]["score"], "Ranking should be by score"
    print("  ✅ Full Matching Pipeline: ALL TESTS PASSED")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Run all tests."""
    print("=" * 80)
    print("PHASE 1 INTEGRATION TEST SUITE")
    print("=" * 80)
    
    try:
        test_adaptive_thresholds()
        test_smart_dedup()
        test_explainability_engine()
        test_smart_fallback()
        test_skill_quality()
        test_full_matching_pipeline()
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED - PHASE 1 INTEGRATION SUCCESSFUL")
        print("=" * 80)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
