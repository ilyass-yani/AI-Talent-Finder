# Representative Test Set for AI Talent Finder

# Contains real-world CVs and edge cases for quality validation

## Automation

Case definitions live in `backend/tests/fixtures/cv_cases.json` and can be run with:

```bash
PYTHONPATH=. python backend/scripts/run_cv_case_suite.py
```

## Testing Framework

### 1. CV Extraction Tests (NER + OCR)

#### Case 1: Well-formatted Modern CV (PDF-text)

```
Input: Professional CV (PDF-native text)
Expected Output:
  - Skills: Python, FastAPI, React, PostgreSQL, Docker ✓
  - Experience: 5 years backend engineer ✓
  - Education: Master in CS ✓
  - Languages: English, French ✓
Threshold: All components extracted correctly
```

#### Case 2: Scanned CV / Image-based PDF

```
Input: Scanned CV (requires OCR)
Expected Output (without OCR module):
  - Skills: Partially extracted (text-based only) ⚠️
  - Note: Requires tesseract binary installed
  - Fallback: Skip image sections if OCR unavailable
Threshold: At least 50% of text extracted
```

#### Case 3: Non-traditional Format (LinkedIn, ATS-from)

```
Input: Unstructured CV from LinkedIn export or ATS export
Expected Output:
  - Skills: Extracted from bullet points ✓
  - Experience: Parsed from timeline ✓
  - Education: Found and categorized ✓
  - Gaps: OK if some sections missing
Threshold: Core 3 sections (skills, exp, edu) present
```

#### Case 4: Multi-language CV (FR/EN/DE)

```
Input: CV with sections in English + French + German
Expected Output:
  - Languages detected: French, English, German ✓
  - Skills extracted across all languages ✓
  - Experience dates normalized ✓
Threshold: All languages recognized
```

#### Case 5: Highly Technical CV (with URLs, code snippets)

```
Input: Developer CV with GitHub links, code samples, performance metrics
Expected Output:
  - Skills: Extracted from code context ✓
  - Projects: Identified and linked ✓
  - Metrics: "Performance improved by 40%" → skill context ✓
Threshold: At least 5 relevant projects identified
```

---

### 2. Skill Extraction Tests (Dictionary + NER + Embeddings)

#### Case A: Common Tech Stack

```
CV Text: "Experienced Python developer with 3 years FastAPI expertise.
         Strong React and PostgreSQL skills. Kubernetes certified."

Expected Skills (exact match):
  - Python (EXACT, confidence: 100)
  - FastAPI (EXACT, confidence: 100)
  - React (EXACT, confidence: 100)
  - PostgreSQL (EXACT, confidence: 100)
  - Kubernetes (EXACT, confidence: 100)

Expected Skills (fuzzy match):
  - None expected (all common skills in dictionary)

Score: 5/5 skills found
```

#### Case B: Synonyms & Variations

```
CV Text: "Backend engineer with experience in:
         - Python programming
         - Front-end web dev with React.js
         - Database design (PostGres)
         - Container orchestration with K8s"

Expected Skills (fuzzy match, threshold 80):
  - Python ✓ (from "Python programming")
  - React ✓ (from "React.js", fuzzy match)
  - PostgreSQL ✓ (from "PostGres", fuzzy match)
  - Kubernetes ✓ (from "K8s", fuzzy match)

Score: 4/4 skills matched via fuzzy
```

#### Case C: Misspellings & Typos

```
CV Text: "Skills: Pyton, Djnago, Nokde.js, PostgresSql"

Expected Skills (fuzzy match, threshold 80):
  - Python (from "Pyton" with fuzzy: ~93)
  - Django (from "Djnago" with fuzzy: ~83)
  - Node.js (from "Nokde.js" with fuzzy: ~97)
  - PostgreSQL (from "PostgresSql" with fuzzy: ~90)

Score: 4/4 skills recovered from typos
```

#### Case D: Soft Skills Extraction

```
CV Text: "Strong communicator with excellent leadership abilities.
         Proven problem-solving and critical thinking skills.
         Team player with excellent interpersonal skills."

Expected Soft Skills:
  - Communication (EXACT)
  - Leadership (EXACT)
  - Problem Solving (EXACT)
  - Critical Thinking (EXACT)
  - Team Work (fuzzy: "Team player")
  - Interpersonal Skills (EXACT)

Score: 6/6 soft skills identified
```

#### Case E: Domain-specific Jargon

```
CV Text: "NLP specialist. Proficient in transformers, attention mechanisms,
         and sequence-to-sequence models. Experience with BERT, GPT-2.
         Computer vision background: CNNs, ResNet, YOLO."

Expected Skills:
  - NLP (from "NLP specialist")
  - Machine Learning (inferred context)
  - PyTorch / TensorFlow (implied)
  - Python (implied for ML)
  - Scikit-learn (possibly detected if mentioned)

Score: 3/5 skills detected directly; semantic matching should boost to 5/5
```

---

### 3. Semantic Matching & Embeddings Tests

#### Test 3.1: High Similarity (should match)

```
Candidate Skills: [Python, Django, REST API, PostgreSQL, Docker, AWS]
Job Requirements: [Python, FastAPI, PostgreSQL, Docker, AWS]

Expected Match Score: 80%+ (4/5 core matches + framework difference acceptable)
Threshold: ACCEPT (>80%)
```

#### Test 3.2: Low Similarity (should NOT match)

```
Candidate Skills: [Java, C++, Assembly, Linux, Embedded Systems]
Job Requirements: [Python, JavaScript, React, Node.js, Web Development]

Expected Match Score: <20% (no overlap)
Threshold: REJECT (<50%)
```

#### Test 3.3: Partial Overlap

```
Candidate Skills: [Python, JavaScript, React, Node.js, PostgreSQL]
Job Requirements: [Python, JavaScript, TypeScript, Vue.js, MongoDB]

Expected Match Score: 40-60% (2/5 exact + language family match)
Threshold: REVIEW (50-80%)
```

#### Test 3.4: Embedding-based Equivalence

```
Candidate: "Expert in deep neural networks and transformers"
Job: "TensorFlow / PyTorch engineer"

Without embeddings: "deep neural networks" ≠ "TensorFlow" (0% exact match)
With embeddings: High similarity due to semantic context (~75% similarity)

Threshold: ACCEPT with embeddings enabled; MARGINAL without
```

---

### 4. Chatbot Response Quality Tests (Recruiter Scenarios)

#### Scenario 1: Explain Match Score

```
User Query: "Why is Candidate #42 scoring 85%?"
Candidate: Python(95%), Django(90%), React(80%), PostgreSQL(85%)
Job: Python, Django, PostgreSQL, Redis

Expected Response (LLM Mode):
"Candidate #42 scores 85% because they have strong matching on your core tech stack.
They exceed expectations on Python (95%) and Django (90%), matching your senior role.
Minor gap: You need Redis experience, not detected in their CV.
Their React skills are a bonus for your full-stack needs."

Expected Response (Fallback Mode):
"Candidate #42 matches core skills: Python, Django, PostgreSQL.
Missing: Redis experience.
Skills: Python(95%), Django(90%), React(80%), PostgreSQL(85%)."

Quality Metric: Fallback ≤ LLM by ~40% in clarity/context
```

#### Scenario 2: Compare Candidates

```
User Query: "Compare Candidate A (78% score) and Candidate B (82% score)"
Candidate A: Python(90%), React(80%), AWS(70%)
Candidate B: Python(85%), React(85%), AWS(80%), Docker(80%)

Expected Response (LLM Mode):
"Candidate B is stronger overall due to docker expertise and consistency.
While A excels at Python, B offers better infrastructure skills and balanced stack.
Recommendation: Interview B if DevOps is critical; A if pure backend focus."

Expected Response (Fallback Mode):
"Candidate B: 82% (Python 85%, React 85%, AWS 80%, Docker 80%)
Candidate A: 78% (Python 90%, React 80%, AWS 70%)
B has more skills and Docker experience."

Quality Metric: Fallback correct but lacks strategic insight
```

#### Scenario 3: Suggest Ideal Candidate Profile

```
User Query: "What's the ideal profile for my Senior Backend role?"
Job Criteria: Python, FastAPI, PostgreSQL, AWS, Docker (5 required skills)

Expected Response (LLM Mode):
"For a Senior Backend role, focus on:
1. Python expertise (5+ years) — essential for FastAPI
2. FastAPI or similar REST framework experience
3. PostgreSQL optimization and complex query knowledge
4. AWS infrastructure (EC2, RDS, S3 at minimum)
5. Docker containerization for deployment
Soft skills: System design thinking, mentoring junior devs, communication."

Expected Response (Fallback Mode):
"Required skills: Python, FastAPI, PostgreSQL, AWS, Docker
Preferred: 5+ years experience, system design knowledge
Soft skills: Leadership, communication, problem-solving"

Quality Metric: LLM provides better context; fallback is functional
```

---

### 5. NLP Pipeline Edge Cases

#### Edge Case 1: Empty / Minimal CV

```
Input: "Resume: John Doe. Skills: Java."
Expected:
  - Name: John Doe (if NER works)
  - Skills: Java (1 skill detected)
  - Experience: None specified
Threshold: At least skill detection works
```

#### Edge Case 2: CV with Special Characters / Encoding Issues

```
Input: CV with accents "François", symbols "C++", emoji "🐍 Python"
Expected:
  - French language detected ✓
  - C++ recognized despite special char ✓
  - Python recognized despite emoji ✓
Threshold: Robust to encoding issues
```

#### Edge Case 3: CV with Irrelevant Content

```
Input: CV mentioning "proficient in cooking" and "expert in gardening"
Expected:
  - These skills NOT extracted (not in dictionary)
  - Other tech skills on CV extracted normally
Threshold: No false positives
```

#### Edge Case 4: Very Long CV (10+ pages)

```
Input: 15-page CV with extensive experience history
Expected:
  - All pages parsed ✓
  - Duplicate skills removed ✓
  - Performance: <5s processing time
Threshold: Handle large documents gracefully
```

---

## Test Execution Plan

### Phase 1: Unit Tests (Per Component)

```bash
# NER + Extraction
pytest backend/tests/test_ner_extractor.py -v

# Skill Extraction
pytest backend/tests/test_skill_extraction.py -v

# Semantic Matching
pytest backend/tests/test_semantic_matching.py -v

# Chatbot Fallback
pytest backend/tests/test_chatbot_fallback.py -v
```

### Phase 2: Integration Tests

```bash
# Full CV processing
pytest backend/tests/test_cv_processing.py -v

# Matching pipeline
pytest backend/tests/test_matching_pipeline.py -v

# End-to-end recruiter flow
pytest backend/tests/test_e2e_recruiter_flow.py -v
```

### Phase 3: Quality Metrics

```bash
# Metrics after test suite
- Skill extraction accuracy: >85%
- Semantic match precision: >90%
- Chatbot response quality (LLM): 4.5/5
- Chatbot response quality (Fallback): 3/5
- NER accuracy (with model): >90%
- NER fallback (regex): >70%
```

---

## Continuous Integration (CI/CD)

### GitHub Actions Workflow

```yaml
# .github/workflows/ai-quality-tests.yml
name: AI Pipeline Quality Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install -r backend/requirements-train.txt
      - name: Install Tesseract (OCR)
        run: sudo apt-get install -y tesseract-ocr
      - name: Run AI pipeline tests
        run: |
          pytest backend/tests/test_*.py -v --cov=backend/ai_module
          pytest backend/tests/test_semantic_matching.py -v
          pytest backend/tests/test_chatbot_fallback.py -v
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## Success Criteria

✅ All test cases execute without errors
✅ Skill extraction accuracy ≥ 85%
✅ Semantic matching precision ≥ 90%
✅ Chatbot quality (LLM) ≥ 4/5
✅ Fallback modes graceful (no crashes)
✅ Processing time <5s per CV
✅ CI/CD pipeline green on all PRs
