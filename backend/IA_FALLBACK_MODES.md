# 🚀 Modes de Fallback IA — Robustesse et Dégradation Gracieuse

## Vue d'ensemble

Le système IA du projet bascule automatiquement en mode **fallback** lorsque des dépendances optionnelles ou des clés API ne sont pas disponibles. Cette architecture garantit que l'application reste fonctionnelle, même en environnement dégradé.

---

## 1️⃣ Embeddings & Matching Sémantique

### Mode Normal (avec `sentence-transformers`)

- **Composant** : `ai_module/matching/semantic_matcher.py` — `SemanticSkillMatcher`
- **Dépendance** : `sentence-transformers>=3.0.0`, `torch>=1.11.0`
- **Comportement** : Génère embeddings vectoriels 384D pour les compétences, calcule similarités cosinus.
- **Performance** : ~5-10ms (première exécution + cache), <1ms (cached)

### Mode Fallback (sans `torch` ou `sentence-transformers`)

- **Lieu d'activation** : `ai_module/matching/semantic_matcher.py:get_embedding()`
- **Implémentation** : retourne `None` ou score par défaut (0.0)
- **Comportement** : Matching basé sur **fuzzy matching** (Levenshtein) uniquement
- **Qualité** : ⚠️ **Dégradée** — perte de précision sémantique, correspondances "contains" ou similitude de chaînes
- **Impact** : Les matchings deviennent plus stricts et peuvent rejeter des candidats valides

**Activation** :

```python
# Vérifie présence du module
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_AVAILABLE = False
    logger.warning("sentence-transformers not available; fallback to fuzzy matching")
```

---

## 2️⃣ Extraction NER (Named Entity Recognition)

### Mode Normal (avec `spacy` + modèle NER)

- **Composant** : `ai_module/nlp/enhanced_skill_extractor.py` — `EnhancedSkillExtractor`
- **Dépendance** : `spacy`, spacy model (`en_core_web_md` ou `en_core_web_lg`)
- **Comportement** : Extrait entités nommées (personnes, dates, localisations, organisations) et compétences
- **Performance** : ~50-100ms par CV

### Mode Fallback (sans `spacy` ou modèle NER)

- **Activation flag** : `load_ner=False` (utilisé en prod par défaut)
- **Implémentation** : Regex + pattern matching, fuzzy skill matching
- **Comportement** :
  - Extraction basée sur **regex et dictionnaire** de compétences
  - Pas d'extraction de dates/durées/localisations
  - Récupère skills uniquement si trouvés dans le dictionnaire de compétences
- **Qualité** : ⚠️ **Basique mais stable** — couverture limitée aux skills connus
- **Impact** : CV avec skills inconnus en ortho alternative (ex: "ML" vs "Machine Learning") peuvent ne pas être reconnus

**Activation** :

```python
# load_ner=False → fallback à hybride (regex + fuzzy)
ex = EnhancedSkillExtractor(load_ner=False)
skills = ex.extract_skills_hybrid(cv_text)
```

---

## 3️⃣ OCR (Tesseract)

### Mode Normal (avec `pytesseract` + `tesseract` natif)

- **Composant** : `app/services/cv_extractor.py` — `CVExtractor.extract_from_pdf()`
- **Dépendance** : `pytesseract>=0.3.10`, native binary `tesseract` (via `brew install tesseract`)
- **Comportement** : Convertit images/scans en texte OCR
- **Performance** : ~2-5s par page scannée

### Mode Fallback (sans `tesseract` natif)

- **Activation** : Si `pytesseract` ne trouve pas `tesseract` exécutable
- **Implémentation** : Extrait texte via **PyMuPDF/pdfplumber** (PDF natif) uniquement
- **Comportement** :
  - Ignore les pages scannées ou images
  - Extrait seulement le texte embédié (PDFs texte)
  - Qualité mauvaise pour CV scannés
- **Qualité** : ⚠️ **Très limitée pour CVs scannés/images**
- **Impact** : CV au format image (scan) ne seront **pas traités**

**Activation** :

```python
# Dans CVExtractor.extract_from_pdf()
try:
    text = pytesseract.image_to_string(image)
except pytesseract.TesseractNotFoundError:
    logger.warning("Tesseract not installed; skipping OCR for image-based PDFs")
    text = []  # fallback: skip OCR
```

**Installation OCR (macOS)** :

```bash
brew install tesseract tesseract-lang
```

---

## 4️⃣ LLM Chatbot (Anthropic Claude)

### Mode Normal (avec `ANTHROPIC_API_KEY`)

- **Composant** : `app/api/chat.py` — `ChatService.generate_response()`
- **Dépendance** : `anthropic>=0.45.0`, env var `ANTHROPIC_API_KEY`
- **Comportement** : Appelle Claude API pour générer réponses contextuelles (expliquer match, comparer candidats, etc.)
- **Performance** : ~2-5s par requête (API latency)
- **Qualité** : ⭐⭐⭐⭐⭐ Très naturelles et contextuelles

### Mode Fallback (clé API absente ou API erreur)

- **Activation** : Si `ANTHROPIC_API_KEY` vide ou appel API échoue
- **Implémentation** : Réponses **rule-based / template-based** en dur
- **Comportement** :
  - Patterns pré-définis pour questions courantes (expliquer score, lister candidats)
  - Pas d'apprentissage du contexte
  - Réponses génériques / limitées
- **Qualité** : ⚠️ **Basique et répétitif**
- **Impact** : UX recruteur dégradée, réponses peu flexibles

**Activation** :

```python
# ChatService.generate_response()
if not ANTHROPIC_API_KEY:
    logger.warning("ANTHROPIC_API_KEY not set; using rule-based fallback")
    return generate_fallback_response(question_type, context)
```

**Configuration env** :

```env
ANTHROPIC_API_KEY=sk-ant-...  # Optionnel
```

---

## 5️⃣ Profile Generator (LLM pour synthèse profil)

### Mode Normal (avec `ANTHROPIC_API_KEY` + `USE_AI_PROFILE_GENERATOR=true`)

- **Composant** : `ai_module/nlp/profile_generator.py` — `ProfileGenerator.generate_from_text()`
- **Comportement** : Synthétise CV en profil structuré (expérience, skills, diplômes) via Claude
- **Performance** : ~3-5s par CV
- **Qualité** : ⭐⭐⭐⭐ Précis et contextualisé

### Mode Fallback (flag `USE_AI_PROFILE_GENERATOR=false` ou API erreur)

- **Activation** : Par défaut en production (`USE_AI_PROFILE_GENERATOR=false`)
- **Implémentation** : Extraction **rule-based** + regex + NER fallback
- **Comportement** :
  - Parsing structuré basé sur patterns (années, mots-clés, sections)
  - Qualité dépend du format du CV
  - Peut manquer les infos implicites
- **Qualité** : ⚠️ **Plus rigide et sensible au format**
- **Impact** : Certains CVs mal formatés peuvent ne pas être correctement analysés

**Activation** :

```python
# Backend env var
USE_AI_PROFILE_GENERATOR=true   # Mode IA (prod: false)
```

---

## 6️⃣ Matching Model (XGBoost / Fallback Linear)

### Mode Normal (avec `models/final_match_model.joblib`)

- **Composant** : `app/services/matching_service.py` — `MatchingService.calculate_score()`
- **Modèle** : XGBoost entraîné sur dataset `data/final_training_pairs.csv`
- **Comportement** : Scoring non-linéaire, poids ajustés
- **Performance** : ~5-10ms par score
- **Qualité** : ⭐⭐⭐⭐ D'après validations précédentes

### Mode Fallback (modèle absent ou load erreur)

- **Activation** : Si `models/final_match_model.joblib` n'existe pas ou load échoue
- **Implémentation** : Linear scoring basé sur compétences + seuils
- **Comportement** :
  - Calcul : `score = sum(skill_weights * candidate_skills) / sum(job_weights)`
  - Pondérations fixes (non apprises)
  - Moins nuancé
- **Qualité** : ⚠️ **Basique mais transparent**
- **Impact** : Résultats moins affinés, peut favoriser/défavoriser certains profils

**Activation** :

```python
try:
    model = joblib.load('models/final_match_model.joblib')
except FileNotFoundError:
    logger.warning("final_match_model not found; using linear fallback")
    model = LinearMatchingFallback()
```

---

## 📋 Récapitulatif par Composant

| Composant       | Normal                   | Fallback                 | Impact Dégradation                           |
| --------------- | ------------------------ | ------------------------ | -------------------------------------------- |
| **Embeddings**  | Vectoriel 384D + cosinus | Fuzzy matching           | Perte de précision sémantique (-30% approx.) |
| **NER**         | spaCy + LLM context      | Regex + dictionnaire     | Couverture limitée aux skills connus         |
| **OCR**         | Tesseract Native         | PyMuPDF texte uniquement | CVs scannés ignorés ❌                       |
| **Chatbot**     | Claude API               | Rule-based templates     | Réponses rigides, peu flexibles              |
| **Profile Gen** | LLM (Claude)             | Regex + NER fallback     | Perte contexte implicite                     |
| **Matching**    | XGBoost                  | Linear rules             | Scoring moins nuancé                         |

---

## 🔧 Activation des Modes Fallback

### Via Variables d'Environnement

```bash
# Désactiver ANTHROPIC (chatbot + profile gen en fallback)
unset ANTHROPIC_API_KEY

# Désactiver profile generator IA (force rule-based)
USE_AI_PROFILE_GENERATOR=false

# OCR désactivé (pas de tesseract)
# (pas de flag — détection automatique)
```

### Via Code

```python
# Forcer fallback embeddings
os.environ['USE_SEMANTIC_MATCHING'] = 'false'

# Charger sans NER
extractor = EnhancedSkillExtractor(load_ner=False)
```

---

## 📊 Recommandations Encadrante

1. ✅ **Dépendances optionnelles installées** en prod (`requirements.txt` contient `transformers`, `sentence-transformers`, `torch`, `anthropic`, `pytesseract`, `spacy`)
2. ⚠️ **Documenter fallbacks** (✅ Fait — ce fichier)
3. 📈 **Enrichir dictionnaire compétences** → voir `backend/ai_module/nlp/skills_dictionary.py`
4. 🧪 **Tester fallbacks** → cas de tests dans `backend/tests/test_ner_fallback.py`
5. 🔄 **Régénérer artefacts IA** → voir `backend/scripts/build_final_matching_artifacts.py`

---

## 💡 Prochains Pas

- **Local dev** : installer dépendances optionnelles (`pip install -r requirements.txt`)
- **Production** : monitorer logs pour déterminer si fallbacks sont activés (`logger.warning("... fallback...")`)
- **Tests** : valider comportement fallback avec cas limites (CVs mal formatés, skills inconnus, etc.)
