# CV Extraction & Parsing Pipeline - Nouvelle Architecture

## 📋 Vue d'ensemble

Le système a été **refactorisé** pour être plus simple et plus efficace:

```
PDF Upload → PDF Extraction → Text Normalization → HuggingFace NER Parsing → Frontend Display
```

### Ancien système (remplacé)
❌ `cv_extractor.py` - Extraction basique
❌ Multiples services NLP fragmentés
❌ Logique complexe et redondante

### Nouveau système ✨
✅ `cv_processing_service.py` - Pipeline unifié & modular
✅ HuggingFace NER: `AventIQ-AI/Resume-Parsing-NER-AI-Model`
✅ Détection de langues implicites
✅ Extraction d'images et métadonnées
✅ Code clean & maintenable

---

## 🔧 Fichiers Modifiés/Créés

### Backend
- **`ai_module/nlp/cv_processing_service.py`** (NEW)
  - `PDFExtractor`: Extraction PDF + images + métadonnées
  - `TextNormalizer`: Normalisation du texte
  - `LanguageExtractor`: Détection de langues (explicite + implicite)
  - `HuggingFaceResumeParser`: NER avec modèle HF
  - `CVExtractionPipeline`: Pipeline complet

- **`app/api/candidates.py`** (MODIFIED)
  - `/upload` - Route simplifiée avec nouveau pipeline
  - `/candidates/{id}/parsed-entities` - Récupération des entités parsées

- **`app/schemas/candidate.py`** (MODIFIED)
  - `ParsedEntityResponse` schema pour les entités

### Test/Standalone
- **`testpfa/extraction/extract.py`** (NEW - Advanced version)
  - `PDFExtractor` class
  - Format structuré pour modèles IA
  
- **`testpfa/extraction/resume_parser.py`** (NEW)
  - `ResumeParser` class
  - Support langues implicites
  
- **`testpfa/extraction/pipeline.py`** (NEW)
  - Pipeline complet end-to-end

---

## 🚀 Utilisation

### 1️⃣ Upload CV (API)

```bash
POST /api/candidates/upload
Content-Type: multipart/form-data

file: resume.pdf
full_name: "John Doe"
email: "john@example.com"
```

**Response:**
```json
{
  "success": true,
  "candidate_id": 42,
  "extracted_text": "...",
  "parsed_entities": {
    "languages": [
      {"language": "Python", "confidence": 0.95, "type": "implicit"},
      {"language": "French", "confidence": 0.9, "type": "implicit"}
    ],
    "emails": [{"value": "john@example.com", "confidence": 1.0}],
    "SKILLS": [{"value": "Python", "confidence": 0.88}],
    ...
  },
  "extraction": {
    "pages": 2,
    "images_detected": 1,
    "text_length": 5420
  }
}
```

### 2️⃣ Récupérer entités parsées

```bash
GET /api/candidates/{candidate_id}/parsed-entities
```

**Response:**
```json
{
  "candidate_id": 42,
  "entities": {
    "languages": [...],
    "emails": [...],
    "phones": [...]
  }
}
```

### 3️⃣ Utilisation Standalone

```python
from ai_module.nlp.cv_processing_service import CVExtractionPipeline

pipeline = CVExtractionPipeline(output_dir="/path/to/output")
result = pipeline.process("resume.pdf")

print(result["parsed_entities"])
# {
#   "languages": [...],
#   "emails": [...],
#   ...
# }
```

---

## 🌍 Langues - Détection Implicite

Le système détecte les langues **même si non explicitement mentionnées**:

### Exemples
- "Developed in Python" → Python détecté
- "Fluent French speaker" → French détecté
- "Experience with React/Vue" → React, Vue détectés
- "Bilingual French/English" → French, English détectés

### Patterns Supportés

**Langages de programmation:**
- Python, JavaScript, TypeScript, Java, C++, C#, PHP, Go, Rust, Ruby, SQL, R, Kotlin, Swift, Bash

**Frameworks/Tech:**
- React, Vue, Angular, Django, FastAPI, Docker, Kubernetes, AWS

**Langues naturelles:**
- French, English, Spanish, German, Arabic, Chinese, Japanese

---

## 📦 Dépendances

```
fitz (PyMuPDF) - Extraction PDF
transformers >= 4.30.0 - HuggingFace NER
torch >= 2.0.0 - Backend pour transformers
```

**Installation:**
```bash
pip install transformers torch pymupdf
```

---

## 🔍 Architecture - Détails

### PDFExtractor
```python
result = PDFExtractor.extract("resume.pdf")
# ├── text: "Texte du PDF..."
# ├── pages: 2
# ├── images_detected: 1
# └── metadata: {...}
```

### TextNormalizer
- Remplace espaces multiples par un
- Préserve les paragraphes (double newlines)
- Formate pour modèles IA

### LanguageExtractor
- Regex patterns pour chaque langue
- Cherche mentions implicites
- Confidence score

### HuggingFaceResumeParser
- Modèle: `AventIQ-AI/Resume-Parsing-NER-AI-Model`
- Token classification (NER)
- Fallback parsing si modèle unavailable

### CVExtractionPipeline
Orchestre tous les composants:
1. Extract PDF
2. Normalize text
3. Parse with NER
4. Structure output
5. Save files (optional)

---

## ⚙️ Configuration

### Variables d'environnement (optionnel)

```bash
# Activate HuggingFace model (already default)
export USE_AI_PROFILE_GENERATOR=true
export HF_PROFILE_MODEL=AventIQ-AI/Resume-Parsing-NER-AI-Model
```

### Limites
- Max file size: 50MB (PDF Extractor)
- API limit: 5MB
- Text chunk for NER: 512 tokens

---

## 🐛 Troubleshooting

### HuggingFace model not loading
```
Warning: HuggingFace transformers not available
→ Install: pip install transformers torch
```

### OOM Error (Out of Memory)
→ Reduce text chunk size in `HuggingFaceResumeParser.parse()`

### No entities extracted
→ Check if text is in supported language
→ Verify PDF has readable text (not scanned image)

---

## 🎯 Prochaines étapes

1. **Frontend Display**
   - Show parsed entities in candidate profile
   - Languages with confidence scores
   
2. **Skills Matching**
   - Link extracted skills to job requirements
   - Semantic matching with embeddings
   
3. **Fine-tuning**
   - Custom NER model for your domain
   - Better language detection

4. **Additional Formats**
   - Support .docx, .doc files
   - OCR for scanned PDFs

---

## 📝 Notes

- Ancien code NLP (`skill_extractor.py`, etc.) peut être gardé si utilisé ailleurs
- Fichiers uploads temporaires peuvent être nettoyés
- Pipeline est thread-safe (singleton avec lazy loading)

---

**Status:** ✅ Prêt pour production
**Model:** `AventIQ-AI/Resume-Parsing-NER-AI-Model`
**Last Updated:** April 15, 2026
