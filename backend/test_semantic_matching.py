#!/usr/bin/env python3
"""
Quick test script for semantic skill matching
Test the all-MiniLM-L6-v2 model integration
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

def test_basic_similarity():
    """Test basic similarity calculations"""
    from ai_module.matching.semantic_matcher import SemanticSkillMatcher
    
    print("=" * 60)
    print("🧪 TEST 1: Basic Similarity")
    print("=" * 60)
    
    test_pairs = [
        ("Python", "Python"),          # Should be ~1.0
        ("Python", "Django"),          # Should be moderate
        ("Python", "JavaScript"),      # Should be low
        ("PostgreSQL", "SQL"),         # Should be high
        ("Docker", "Kubernetes"),      # Should be moderate
        ("Python Developer", "Python Engineer"),  # Should be very high
    ]
    
    for text1, text2 in test_pairs:
        sim = SemanticSkillMatcher.semantic_similarity(text1, text2)
        bar = "█" * int(sim * 20) + "░" * (20 - int(sim * 20))
        print(f"  {text1:20} ↔ {text2:20} | {bar} {sim:.3f}")
    
    print()


def test_candidate_matching():
    """Test candidate to criteria matching"""
    from ai_module.matching.semantic_matcher import SemanticSkillMatcher
    
    print("=" * 60)
    print("🧪 TEST 2: Candidate Matching")
    print("=" * 60)
    
    # Scenario: Junior Python developer
    candidate_skills = [
        "Python",
        "Flask",
        "PostgreSQL",
        "Git",
        "HTML/CSS",
        "JavaScript (basics)"
    ]
    
    criteria_skills = [
        {"name": "Python", "weight": 100},
        {"name": "Django", "weight": 80},
        {"name": "PostgreSQL", "weight": 70},
        {"name": "Docker", "weight": 50},
        {"name": "REST API", "weight": 60}
    ]
    
    print(f"\n📋 Candidate Skills: {', '.join(candidate_skills)}")
    print(f"\n📌 Job Requirements:")
    for skill in criteria_skills:
        print(f"   - {skill['name']} (weight: {skill['weight']})")
    
    result = SemanticSkillMatcher.match_candidate_skills(
        candidate_skills=candidate_skills,
        criteria_skills=criteria_skills,
        threshold=0.6
    )
    
    print(f"\n✅ Results:")
    print(f"   Score: {result['score']:.1f}/100")
    print(f"   Matched: {result['total_matches']}/{result['total_criteria']} criteria")
    print(f"   Details: {result['details']}")
    
    print(f"\n📊 Detailed Matches:")
    for match in result['matched_skills']:
        sim_bar = "█" * int(match['similarity'] * 10) + "░" * (10 - int(match['similarity'] * 10))
        print(f"   ✓ {match['criteria_skill']:15} ← {match['matched_skill']:20} "
              f"[{sim_bar} {match['similarity']:.2%}] weight={match['weight']}")
    
    print()


def test_cache():
    """Test embedding cache"""
    from ai_module.matching.semantic_matcher import SemanticSkillMatcher
    import time
    
    print("=" * 60)
    print("🧪 TEST 3: Cache Performance")
    print("=" * 60)
    
    text = "Python Web Developer"
    
    # First call (load model + compute embedding)
    start = time.time()
    embed1 = SemanticSkillMatcher.get_embedding(text)
    time1 = time.time() - start
    
    # Second call (from cache)
    start = time.time()
    embed2 = SemanticSkillMatcher.get_embedding(text)
    time2 = time.time() - start
    
    print(f"\n⏱️  Performance:")
    print(f"   First call: {time1*1000:.1f}ms (includes model load)")
    print(f"   Cached call: {time2*1000:.2f}ms")
    print(f"   Speedup: {time1/time2:.0f}x faster")
    print(f"   Cache size: {SemanticSkillMatcher.get_cache_size()} embeddings")
    print(f"   Embedding dimension: 384D")
    
    print()


def test_semantic_skill_match():
    """Test the simple semantic_skill_match function"""
    from ai_module.matching.semantic_matcher import semantic_skill_match
    
    print("=" * 60)
    print("🧪 TEST 4: semantic_skill_match() Function")
    print("=" * 60)
    
    test_cases = [
        ("Python", "Python", 0.95),
        ("Python", "Django", 0.5),
        ("Frontend", "React", 0.7),
        ("Database", "PostgreSQL", 0.8),
    ]
    
    for skill1, skill2, expected_above in test_cases:
        is_match, sim = semantic_skill_match(skill1, skill2, threshold=0.6)
        status = "✓" if (sim >= 0.6) == is_match else "✗"
        print(f"  {status} {skill1:15} ↔ {skill2:15} | Match: {is_match:5} | Sim: {sim:.3f}")
    
    print()


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  🤖 Semantic Skill Matching - Test Suite".center(58) + "║")
    print("║" + "  all-MiniLM-L6-v2 Integration".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    
    try:
        test_basic_similarity()
        test_candidate_matching()
        test_cache()
        test_semantic_skill_match()
        
        print("=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)
        
    except ImportError as e:
        print(f"❌ Error: {e}")
        print("\n💡 Please install sentence-transformers:")
        print("   pip install sentence-transformers==3.0.*")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
