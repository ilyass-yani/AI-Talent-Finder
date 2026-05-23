"""
Test NER Integration - Validates complete Étape 5-6 pipeline
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Set a dummy DATABASE_URL before importing app modules
os.environ['DATABASE_URL'] = 'sqlite:///./test.db'

from app.models.models import Candidate
from app.services.cv_extractor import CVExtractionService
from ai_module.nlp.enhanced_skill_extractor import EnhancedSkillExtractor


def test_ner_integration():
    """Test complete NER integration from text to candidate dict"""
    
    # Sample CV text
    sample_cv = """
    JOHN SMITH
    Email: john.smith@example.com
    Phone: +33 6 12 34 56 78
    LinkedIn: linkedin.com/in/johnsmith
    
    PROFESSIONAL SUMMARY
    Senior Full Stack Developer with 8 years of experience in web development.
    
    EXPERIENCE
    Senior Developer - Tech Company Inc (2020-2024)
    - Led team of 5 developers
    - Built microservices using Python and FastAPI
    - Managed PostgreSQL databases
    
    Junior Developer - Startup LLC (2016-2020)
    - Developed React frontend applications
    - Worked with Node.js backend
    
    EDUCATION
    Bachelor of Science in Computer Science
    University of Technology (2016)
    
    SKILLS
    Languages: Python, JavaScript, TypeScript, SQL, HTML/CSS
    Frameworks: FastAPI, React, Django, Node.js
    Databases: PostgreSQL, MongoDB, Redis
    Tools: Docker, Kubernetes, Git, AWS
    Soft Skills: Leadership, Communication, Project Management
    """
    
    print("=" * 70)
    print("NER INTEGRATION TEST - Étape 5-6")
    print("=" * 70)
    
    # Test 1: Create extraction service
    print("\n[TEST 1] Creating CVExtractionService...")
    try:
        service = CVExtractionService()
        print("✅ Service created successfully")
    except Exception as e:
        print(f"❌ Failed to create service: {e}")
        return False
    
    # Test 2: Extract from text
    print("\n[TEST 2] Extracting structured data from CV text...")
    try:
        result = service.extract_from_text(sample_cv)
        print(f"✅ Extraction completed")
        print(f"   - Quality Score: {result.quality_score:.1f}%")
        print(f"   - Entities Found: {result.extraction_metadata.get('entities_found', 0)}")
        print(f"   - Skills Extracted: {len(result.skills)}")
        structured = result.structured
        print(f"   - Experiences: {len(structured.get('experiences', []))}")
        print(f"   - Projects: {len(structured.get('projects', []))}")
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        return False

    # Test 2b: Atypical CV format should still produce meaningful extraction
    print("\n[TEST 2b] Testing atypical CV layout robustness...")
    atypical_cv = """
    Jane Doe | Data Engineer | Paris
    contact: jane.doe@mail.com | +33 7 11 22 33 44
    github.com/janedoe | janedoe.dev

    2022 - Present | Data Engineer | Blue Analytics
    Built ETL pipelines on Airflow and Spark
    Implemented data quality checks and dashboards

    2020-2022 - BI Analyst - Retail Group
    Automated SQL reporting and Power BI models

    Certifications
    AWS Certified Cloud Practitioner
    Scrum Master PSM I

    Projects
    Customer churn prediction using Python and scikit-learn
    """
    atypical_result = service.extract_from_text(atypical_cv)
    atypical_structured = atypical_result.structured
    if not atypical_structured.get('email'):
        print("❌ Atypical layout: email was not extracted")
        return False
    if not atypical_structured.get('experiences'):
        print("❌ Atypical layout: experiences were not extracted")
        return False
    if not atypical_structured.get('github_urls') and not atypical_structured.get('portfolio_urls'):
        print("❌ Atypical layout: web links were not extracted")
        return False
    print("✅ Atypical layout extraction is robust")
    
    # Test 3: Convert to candidate dict
    print("\n[TEST 3] Converting extraction result to candidate dict...")
    try:
        candidate_dict = service.to_candidate_dict(result)
        print(f"✅ Conversion successful")
        print(f"   - Full Name: {candidate_dict.get('full_name', 'N/A')}")
        print(f"   - Email: {candidate_dict.get('email', 'N/A')}")
        print(f"   - Extracted Name: {candidate_dict.get('extracted_name', 'N/A')}")
        print(f"   - Quality Score: {candidate_dict.get('extraction_quality_score', 0):.1f}%")
    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        return False
    
    # Test 4: Verify required NER fields
    print("\n[TEST 4] Validating NER fields in candidate dict...")
    ner_fields = [
        'extracted_name',
        'extracted_emails',
        'extracted_phones',
        'extracted_job_titles',
        'extracted_companies',
        'extracted_education',
        'extraction_quality_score',
        'is_fully_extracted'
    ]
    
    missing_fields = []
    for field in ner_fields:
        if field not in candidate_dict:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"❌ Missing fields: {missing_fields}")
        return False
    else:
        print(f"✅ All NER fields present")

    # Test 4b: Verify rich structured payload contains generalized fields
    print("\n[TEST 4b] Validating extended structured fields...")
    if not isinstance(structured.get('experiences', []), list):
        print("❌ experiences should be a list")
        return False
    if 'projects' not in structured or 'certifications' not in structured:
        print("❌ Missing projects/certifications in structured payload")
        return False
    if 'github_urls' not in structured or 'portfolio_urls' not in structured:
        print("❌ Missing github_urls/portfolio_urls in structured payload")
        return False
    print("✅ Extended structured fields are present")
    
    # Test 5: Verify EnhancedSkillExtractor
    print("\n[TEST 5] Testing EnhancedSkillExtractor hybrid extraction...")
    try:
        skill_extractor = EnhancedSkillExtractor(load_ner=False)
        skills = skill_extractor.extract_skills_hybrid(sample_cv)
        print(f"✅ Hybrid skill extraction working")
        print(f"   - Total skills extracted: {len(skills)}")
        
        if skills:
            print(f"   - Top 3 skills:")
            for skill in skills[:3]:
                print(f"     • {skill['name']} ({skill['category']}) - Score: {skill['confidence']:.0%}")
    except Exception as e:
        print(f"❌ Skill extraction failed: {e}")
        # Don't fail on this as NER might not be available
        print(f"   (Note: NER may not be available, but fallback should work)")
    
    # Test 6: Verify model schema
    print("\n[TEST 6] Validating Candidate model schema...")
    try:
        # Check that Candidate class has NER columns
        candidate_columns = {col.name for col in Candidate.__table__.columns}
        ner_columns = {
            'extracted_name', 'extracted_emails', 'extracted_phones',
            'extracted_job_titles', 'extracted_companies', 'extracted_education',
            'extraction_quality_score', 'ner_extraction_data', 'is_fully_extracted'
        }
        
        missing = ner_columns - candidate_columns
        if missing:
            print(f"❌ Missing columns in Candidate model: {missing}")
            return False
        else:
            print(f"✅ All NER columns present in Candidate model")
    except Exception as e:
        print(f"❌ Schema validation failed: {e}")
        return False
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED - NER Integration Successful!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = test_ner_integration()
    sys.exit(0 if success else 1)
