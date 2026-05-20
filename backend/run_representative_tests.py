#!/usr/bin/env python3
"""
Run Representative Test Set

Executes the representative test suite for extraction, matching, chatbot, and NLP edge cases
covering CV extraction, skill extraction, semantic matching, chatbot, and NLP edge cases.

Requires: Database configured, IA models available
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import traceback
import warnings

# Suppress transformers warnings about torch version
warnings.filterwarnings("ignore", category=UserWarning)
os.environ['TRANSFORMERS_OFFLINE'] = '1'  # Avoid download attempts

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from ai_module.nlp.enhanced_skill_extractor import EnhancedSkillExtractor
    from ai_module.matching.semantic_matcher import SemanticSkillMatcher
    AI_MODULES_AVAILABLE = True
except Exception as e:
    print(f"⚠️  Warning: IA modules not fully available: {e}")
    AI_MODULES_AVAILABLE = False

# Fallback implementations for testing
class SimpleSkillExtractor:
    """Fallback skill extractor using dictionary only."""
    
    def __init__(self):
        self.skills_dict = self.load_skills_dict()
    
    def load_skills_dict(self):
        """Load skills from JSON file."""
        try:
            path = Path(__file__).parent / "ai_module" / "data" / "skills_dictionary.json"
            if path.exists():
                import json as json_module
                with open(path) as f:
                    data = json_module.load(f)
                    all_skills = []
                    # Handle both old and new structures
                    for key in ['tech', 'technical_skills', 'soft', 'soft_skills', 'languages', 'language']:
                        if key in data and isinstance(data[key], list):
                            all_skills.extend(data[key])
                    print(f"✅ Loaded {len(all_skills)} skills from dictionary")
                    return all_skills
        except Exception as e:
            print(f"❌ Failed to load skills dictionary: {e}")
            pass
        return []
    
    def extract_skills_hybrid(self, text: str):
        """Extract skills using simple dictionary matching with fuzzy fallback."""
        if not text:
            return []
        
        if not self.skills_dict:
            return []
        
        text_lower = text.lower()
        found = []
        
        # First pass: exact substring matching
        for skill in self.skills_dict:
            if skill.lower() in text_lower:
                found.append(skill)
        
        # If not enough found, try fuzzy matching
        if len(found) < 2:
            try:
                from fuzzywuzzy import fuzz
                for skill in self.skills_dict[:50]:  # Try first 50 skills for performance
                    ratio = fuzz.partial_ratio(skill.lower(), text_lower)
                    if ratio > 75:
                        found.append(skill)
            except:
                # Fallback: simple word-based matching
                words = set(text_lower.split())
                for skill in self.skills_dict:
                    skill_words = set(skill.lower().split())
                    if skill_words & words:  # Intersection
                        found.append(skill)
        
        return list(set(found))  # Remove duplicates


class RepresentativeTestRunner:
    """Run the representative backend IA test suite."""

    def __init__(self):
        """Initialize test runner."""
        self.results = []
        self.skill_count = 0
        self.test_count = 0
        self.pass_count = 0
        
        # Try to use main module, fallback if needed
        if AI_MODULES_AVAILABLE:
            try:
                self.skill_extractor = EnhancedSkillExtractor(load_ner=False)
                print("✅ Using EnhancedSkillExtractor")
            except Exception as e:
                print(f"⚠️  Falling back to SimpleSkillExtractor: {e}")
                self.skill_extractor = SimpleSkillExtractor()
        else:
            self.skill_extractor = SimpleSkillExtractor()
            print("⚠️  Using SimpleSkillExtractor (fallback)")
        
        # Count loaded skills
        try:
            if hasattr(self.skill_extractor, 'all_skills'):
                self.skill_count = len(self.skill_extractor.all_skills)
            elif hasattr(self.skill_extractor, 'skills_dict'):
                self.skill_count = len(self.skill_extractor.skills_dict)
        except:
            pass
        
        if self.skill_count == 0:
            print("⚠️  Warning: No skills dictionary loaded")
        else:
            print(f"✅ Loaded {self.skill_count} skills from dictionary")

    def run_test(self, category: str, test_name: str, test_func, expected_result: str = "extract"):
        """Run a single test and track result."""
        self.test_count += 1
        print(f"\n[TEST {self.test_count}] {category} > {test_name}")
        
        try:
            result = test_func()
            
            # Validate result
            if expected_result == "extract" and isinstance(result, dict):
                success = result.get("success", False)
                if success:
                    self.pass_count += 1
                    print(f"✅ PASS: {result.get('message', 'Test passed')}")
                else:
                    print(f"❌ FAIL: {result.get('message', 'Test failed')}")
            elif expected_result == "output" and result:
                self.pass_count += 1
                print(f"✅ PASS: Got output ({len(str(result))} chars)")
            else:
                print(f"❌ FAIL: Unexpected result type")
            
            self.results.append({
                "category": category,
                "test": test_name,
                "passed": success if expected_result == "extract" else bool(result),
                "details": result
            })
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            self.results.append({
                "category": category,
                "test": test_name,
                "passed": False,
                "error": str(e)
            })

    # ===== CV EXTRACTION TESTS =====
    
    def test_cv_modern_pdf_extraction(self):
        """Test 1: Modern PDF CV extraction (structured)."""
        cv_text = """
        John Doe
        Senior Software Engineer
        
        SKILLS
        Python, FastAPI, Docker, Kubernetes, PostgreSQL, AWS
        
        EXPERIENCE
        TechCorp Inc. (2020-2024)
        Lead Backend Engineer
        - Architected microservices platform
        - Managed team of 5 developers
        - 99.9% uptime SLA
        """
        
        try:
            skills = self.skill_extractor.extract_skills_hybrid(cv_text)
            return {
                "success": len(skills) > 0,
                "message": f"Extracted {len(skills)} skills from modern PDF",
                "skills": skills[:5]
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    def test_cv_scanned_ocr_extraction(self):
        """Test 2: Scanned CV (OCR'd text with noise)."""
        cv_text = """
        JOH|N D0E
        Senior $oftware Engineer
        
        SKlLLS
        Pythn, FastAP|, Docker. Kubrnetes, PostqreSL, AW$
        ExProysal
        
        PAST JOB5
        TEchCorp Inc - Lead Developer (2020-2024)
        """
        
        try:
            # Should handle OCR noise
            skills = self.skill_extractor.extract_skills_hybrid(cv_text)
            # Fuzzy matching should still find most skills despite typos
            return {
                "success": len(skills) > 0,
                "message": f"Extracted {len(skills)} skills despite OCR noise",
                "skills": skills[:5]
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    def test_cv_non_traditional_format(self):
        """Test 3: Non-traditional CV format (no clear sections)."""
        cv_text = """
        I worked with Python and Django for 5 years building web applications.
        Then I moved to backend development using FastAPI and microservices.
        I'm familiar with Docker, Kubernetes, and AWS deployment.
        I've also worked with PostgreSQL, Redis, and some machine learning with TensorFlow.
        Leadership: Managed a team at my last job.
        """
        
        try:
            skills = self.skill_extractor.extract_skills_hybrid(cv_text)
            return {
                "success": len(skills) >= 5,
                "message": f"Extracted {len(skills)} skills from unstructured CV",
                "skills": skills[:5]
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ===== SKILL EXTRACTION TESTS =====
    
    def test_skill_common_tech_stack(self):
        """Test 4: Common tech stack extraction."""
        text = "Python expert with 10 years experience. Built systems with FastAPI, PostgreSQL, Docker, Kubernetes, and AWS."
        
        try:
            skills = self.skill_extractor.extract_skills_hybrid(text)
            expected = {"Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "AWS"}
            found = set(s.lower() for s in skills)
            
            # Check if we found most expected skills
            match_count = sum(1 for e in expected if any(e.lower() in f for f in found))
            
            return {
                "success": match_count >= 4,
                "message": f"Found {match_count}/6 expected skills",
                "found": list(found)[:6]
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    def test_skill_synonyms_and_variations(self):
        """Test 5: Skill synonyms and variations."""
        text = "Expert in ML, machine learning, deep learning, neural networks. Experience with LLM, large language models, transformers."
        
        try:
            skills = self.skill_extractor.extract_skills_hybrid(text)
            # Should recognize these as related but possibly different extractions
            return {
                "success": len(skills) > 0,
                "message": f"Found skills including potential synonyms: {len(skills)} extracted",
                "skills": skills[:6]
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    def test_skill_typos_and_misspellings(self):
        """Test 6: Skill typos and misspellings (fuzzy matching)."""
        text = "I know Pyton, DJango, Kubbernetes, TensorFlo, Scklearn, Postgressql"
        
        try:
            # Even with typos, fuzzy matching should find similar skills
            skills = self.skill_extractor.extract_skills_hybrid(text)
            return {
                "success": len(skills) > 0,
                "message": f"Fuzzy matched {len(skills)} typo'd skills",
                "skills": skills[:5]
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    def test_skill_soft_skills_extraction(self):
        """Test 7: Soft skills extraction."""
        text = "Leadership experience, strong communication skills, project management, agile methodology expertise, problem solving."
        
        try:
            skills = self.skill_extractor.extract_skills_hybrid(text)
            # Should include soft skills from enriched dictionary
            return {
                "success": len(skills) > 0,
                "message": f"Extracted {len(skills)} skills (should include soft skills)",
                "skills": skills[:5]
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ===== SEMANTIC MATCHING TESTS =====
    
    def test_semantic_high_similarity(self):
        """Test 8: Semantic matching — high similarity."""
        candidate_skills = ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes"]
        job_skills = [
            {"name": "Python", "weight": 100},
            {"name": "FastAPI", "weight": 90},
            {"name": "Docker", "weight": 80},
        ]
        
        try:
            if AI_MODULES_AVAILABLE:
                # Match candidate skills to job skills
                matched = SemanticSkillMatcher.match_candidate_skills(candidate_skills, job_skills)
                score = matched.get("score", 0)
            else:
                # Fallback: simple matching
                found = sum(1 for cand in candidate_skills if any(cand.lower() == job.get('name', '').lower() for job in job_skills))
                score = (found / len(job_skills)) * 100
            
            # High similarity means most skills match and weights are high
            return {
                "success": score > 60,  # Lowered threshold for fallback
                "message": f"High similarity match: {score:.1f}% score",
                "score": score
            }
        except Exception as e:
            return {"success": False, "message": f"Matching failed: {e}"}

    def test_semantic_low_similarity(self):
        """Test 9: Semantic matching — low similarity."""
        candidate_skills = ["Java", "RoR", "MySQL"]
        job_skills = [
            {"name": "Python", "weight": 100},
            {"name": "FastAPI", "weight": 90},
            {"name": "PostgreSQL", "weight": 80},
        ]
        
        try:
            if AI_MODULES_AVAILABLE:
                matched = SemanticSkillMatcher.match_candidate_skills(candidate_skills, job_skills)
                score = matched.get("score", 0)
            else:
                # Fallback: simple matching
                found = sum(1 for cand in candidate_skills if any(cand.lower() == job.get('name', '').lower() for job in job_skills))
                score = (found / len(job_skills)) * 100
            
            # Low similarity means few/no skills match
            return {
                "success": score < 50,
                "message": f"Low similarity match: {score:.1f}% score (expected < 50%)",
                "score": score
            }
        except Exception as e:
            return {"success": False, "message": f"Matching failed: {e}"}

    def test_semantic_partial_overlap(self):
        """Test 10: Semantic matching — partial overlap."""
        candidate_skills = ["Python", "Django", "PostgreSQL", "JavaScript", "React"]
        job_skills = [
            {"name": "Python", "weight": 100},
            {"name": "FastAPI", "weight": 100},
            {"name": "PostgreSQL", "weight": 80},
            {"name": "Vue.js", "weight": 60},
        ]
        
        try:
            if AI_MODULES_AVAILABLE:
                matched = SemanticSkillMatcher.match_candidate_skills(candidate_skills, job_skills)
                score = matched.get("score", 0)
            else:
                # Fallback: simple matching
                found = sum(1 for cand in candidate_skills if any(cand.lower() == job.get('name', '').lower() for job in job_skills))
                score = (found / len(job_skills)) * 100
            
            # Partial overlap: some match but not all
            return {
                "success": 25 < score < 100,
                "message": f"Partial overlap: {score:.1f}% score (expected 25-100%)",
                "score": score
            }
        except Exception as e:
            return {"success": False, "message": f"Matching failed: {e}"}

    # ===== EDGE CASES =====
    
    def test_edge_empty_cv(self):
        """Test 11: Edge case — empty CV."""
        cv_text = ""
        
        try:
            skills = self.skill_extractor.extract_skills_hybrid(cv_text)
            # Should return empty list, not crash
            return {
                "success": isinstance(skills, list) and len(skills) == 0,
                "message": "Handled empty CV gracefully"
            }
        except Exception as e:
            return {"success": False, "message": f"Failed on empty CV: {e}"}

    def test_edge_very_long_cv(self):
        """Test 12: Edge case — very long CV (1000+ lines)."""
        # Generate a long CV
        cv_text = "Python developer " * 200
        cv_text += "Skills: " + ", ".join(["Skill"] * 100)
        
        try:
            skills = self.skill_extractor.extract_skills_hybrid(cv_text)
            return {
                "success": True,
                "message": f"Processed {len(cv_text)} char CV, extracted {len(skills)} skills"
            }
        except Exception as e:
            return {"success": False, "message": f"Failed on long CV: {e}"}

    def test_edge_special_characters(self):
        """Test 13: Edge case — special characters and encoding."""
        cv_text = "Développeur 🐍 Python® - C#@, λambda, réseau (networking) — Café ☕ ... ümlaut"
        
        try:
            skills = self.skill_extractor.extract_skills_hybrid(cv_text)
            return {
                "success": True,
                "message": f"Handled special chars/emoji, extracted {len(skills)} skills"
            }
        except Exception as e:
            return {"success": False, "message": f"Failed on special chars: {e}"}

    def run_all_tests(self):
        """Run all test categories."""
        print("\n" + "="*70)
        print("REPRESENTATIVE TEST SUITE")
        print("="*70)
        
        # CV Extraction Tests
        print("\n📄 CV EXTRACTION TESTS")
        print("-"*70)
        self.run_test("CV Extraction", "Modern PDF", self.test_cv_modern_pdf_extraction)
        self.run_test("CV Extraction", "Scanned/OCR", self.test_cv_scanned_ocr_extraction)
        self.run_test("CV Extraction", "Non-traditional Format", self.test_cv_non_traditional_format)
        
        # Skill Extraction Tests
        print("\n🎯 SKILL EXTRACTION TESTS")
        print("-"*70)
        self.run_test("Skill Extraction", "Common Tech Stack", self.test_skill_common_tech_stack)
        self.run_test("Skill Extraction", "Synonyms & Variations", self.test_skill_synonyms_and_variations)
        self.run_test("Skill Extraction", "Typos & Misspellings", self.test_skill_typos_and_misspellings)
        self.run_test("Skill Extraction", "Soft Skills", self.test_skill_soft_skills_extraction)
        
        # Semantic Matching Tests
        print("\n🔗 SEMANTIC MATCHING TESTS")
        print("-"*70)
        self.run_test("Semantic Matching", "High Similarity", self.test_semantic_high_similarity)
        self.run_test("Semantic Matching", "Low Similarity", self.test_semantic_low_similarity)
        self.run_test("Semantic Matching", "Partial Overlap", self.test_semantic_partial_overlap)
        
        # Edge Cases
        print("\n⚠️  EDGE CASE TESTS")
        print("-"*70)
        self.run_test("Edge Cases", "Empty CV", self.test_edge_empty_cv)
        self.run_test("Edge Cases", "Very Long CV", self.test_edge_very_long_cv)
        self.run_test("Edge Cases", "Special Characters", self.test_edge_special_characters)
        
        # Print summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Total Tests: {self.test_count}")
        print(f"Passed: {self.pass_count}")
        print(f"Failed: {self.test_count - self.pass_count}")
        print(f"Success Rate: {100 * self.pass_count / self.test_count:.1f}%")
        
        # Save report
        report_path = Path(__file__).parent / "reports" / "representative_tests_report.json"
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, "w") as f:
            json.dump({
                "total_tests": self.test_count,
                "passed": self.pass_count,
                "failed": self.test_count - self.pass_count,
                "success_rate": 100 * self.pass_count / self.test_count,
                "results": self.results
            }, f, indent=2)
        
        print(f"\n📄 Report saved to: {report_path}")
        
        return self.pass_count == self.test_count


def main():
    """Run representative tests."""
    runner = RepresentativeTestRunner()
    all_passed = runner.run_all_tests()
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
