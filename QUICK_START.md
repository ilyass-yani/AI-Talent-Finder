# 🚀 Quick Start - Semantic Matching (all-MiniLM-L6-v2)

Démarrage rapide en 5 minutes !

---

## ⚡ Installation (2 minutes)

### Étape 1 : Installer les packages

```bash
cd backend
pip install -r requirements.txt
```

**C'est tout !** Le modèle se téléchargera automatiquement à la première utilisation.

---

## 🧪 Test Rapide (1 minute)

### Option A : Test du module directement

```bash
cd backend

# Tester la similarité sémantique
python -c "
from ai_module.matching.semantic_matcher import SemanticSkillMatcher
sim = SemanticSkillMatcher.semantic_similarity('Python Developer', 'Python Engineer')
print(f'Similarité: {sim:.1%}')  # Affichera ~92%
"
```

### Option B : Suite de tests complète

```bash
cd backend
python test_semantic_matching.py
```

**Cela va exécuter 4 tests :**

1. ✓ Similarité entre paires de compétences
2. ✓ Matching candidat vs critères
3. ✓ Performance du cache
4. ✓ Fonction simplifiée `semantic_skill_match()`

---

## 🎮 Tester l'API (2 minutes)

### 1️⃣ Démarrer le serveur

```bash
cd backend
python -m uvicorn app.main:app --reload
```

L'API sera disponible à `http://localhost:8000`

### 2️⃣ Tester dans un autre terminal

```bash
cd backend
python test_api_semantic_matching.py
```

Cela va:

- Créer des critères de job
- Chercher des candidats matching
- Générer un profil idéal
- Matcher les candidats

---

## 📖 Exemples d'Utilisation

### Exemple 1 : Similarité Simple

```python
from ai_module.matching.semantic_matcher import SemanticSkillMatcher

# Comparar deux compétences
score = SemanticSkillMatcher.semantic_similarity("Python", "Django")
print(score)  # 0.45 (frameworks différents)

score = SemanticSkillMatcher.semantic_similarity("SQL", "PostgreSQL")
print(score)  # 0.85 (très similaire)
```

### Exemple 2 : Matcher un Candidat

```python
from ai_module.matching.semantic_matcher import SemanticSkillMatcher

# Skills du candidat
candidate_skills = ["Python", "Flask", "PostgreSQL", "Docker"]

# Demandes du recruteur
criteria = [
    {"name": "Python", "weight": 100},
    {"name": "Django", "weight": 80},
    {"name": "Database", "weight": 60}
]

# Faire le match
result = SemanticSkillMatcher.match_candidate_skills(
    candidate_skills=candidate_skills,
    criteria_skills=criteria,
    threshold=0.6  # 60% de similarité pour matcher
)

print(f"Score: {result['score']:.1f}/100")
# Output: Score: 76.7/100
# Explication:
#   - Python → Python = 100% ✓
#   - Django → Flask = 75% ✓
#   - Database → PostgreSQL = 88% ✓
```

### Exemple 3 : API REST

```bash
# Mode 1 : Créer des critères et chercher
curl -X POST http://localhost:8000/api/matching/criteria \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Python Developer",
    "description": "Need Python and Django expert",
    "required_skills": [
      {"name": "Python", "weight": 100},
      {"name": "Django", "weight": 80}
    ]
  }'

# Mode 2 : Générer et matcher (complet)
curl -X POST http://localhost:8000/api/matching/generate-and-match \
  -H "Content-Type: application/json" \
  -d '{
    "job_title": "Senior Developer",
    "description": "Besoin expert Python, Django, PostgreSQL, Docker"
  }'
```

---

## 🔑 Concepts Clés

### Semantic Matching (Matching Sémantique)

**Ancien système (exact matching):**

```
Candidat: "Python", "Flask", "PostgreSQL"
Critères: "Python", "Django", "Database"
Résultat: 1 match sur 3 = 33%
```

**Nouveau système (semantic matching):**

```
Candidat: "Python", "Flask", "PostgreSQL"
Critères: "Python", "Django", "Database"
Résultat: 3 matches sémantiques = 87%
Explication:
  ✓ Python = Python (100%)
  ✓ Flask ≈ Django (web framework, 75%)
  ✓ PostgreSQL ≈ Database (88%)
```

### Embeddings 384D

Le modèle `all-MiniLM-L6-v2` convertit chaque texte en un vecteur de **384 dimensions** dans un espace sémantique continu.

```
"Python Developer"     → [0.12, -0.45, 0.89, ..., 0.23]  (384D)
"Python Engineer"      → [0.11, -0.46, 0.90, ..., 0.24]  (384D)
Similarité (cosinus)   → 0.92
```

---

## ⚙️ Configuration

### Ajuster la Sensibilité du Matching

Dans votre code:

```python
# Plus permissif (54% similarité = match)
result = SemanticSkillMatcher.match_candidate_skills(
    ...,
    threshold=0.54  # Les matches moins bons passent
)

# Par défaut (60% similarité = match)
result = SemanticSkillMatcher.match_candidate_skills(
    ...,
    threshold=0.6   # Équilibré
)

# Plus strict (80% similarité = match)
result = SemanticSkillMatcher.match_candidate_skills(
    ...,
    threshold=0.8   # Seulement les très bons matches
)
```

### Vider le Cache

```python
from ai_module.matching.semantic_matcher import SemanticSkillMatcher

# Voir la taille du cache
print(SemanticSkillMatcher.get_cache_size())  # ex: 125 embeddings

# Vider pour libérer de la mémoire
SemanticSkillMatcher.clear_cache()
```

---

## 📊 Performance

| Opération                            | Temps                    |
| ------------------------------------ | ------------------------ |
| Charger le modèle                    | ~2-3 secondes (une fois) |
| Embedding une compétence             | 5-10 ms (première fois)  |
| Embedding une compétence (cached)    | <1 ms                    |
| Matcher 10 compétences vs 5 critères | ~50-100 ms               |

---

## 🐛 Troubleshooting

### Mode Extraction CV Qualite Max (OCR agressif)

Pour maximiser la qualite d'extraction sur des CV scans/PDF complexes:

```bash
# macOS
brew install tesseract tesseract-lang

cd backend
cp .env.quality-max.example .env
pip install -r requirements.txt
```

Variables OCR principales:

- `CV_OCR_MODE=aggressive` : force l'OCR sur les PDF
- `CV_OCR_MODE=ultra` : OCR page par page sur les zones faibles (qualite max)
- `CV_OCR_MAX_PAGES=12` : lit plus de pages
- `CV_OCR_DPI=300` : meilleure lecture OCR
- `CV_OCR_LANG=fra+eng` : meilleur mix FR/EN
- `CV_OCR_PAGE_TRIGGER_SCORE=140` : seuil de declenchement OCR par page en mode ultra

Tradeoff attendu: meilleure extraction, mais upload plus long.

### Erreur: "sentence-transformers not installed"

```bash
pip install sentence-transformers==3.0.*
pip install torch==2.2.*
```

### Erreur: "Model download failed"

```bash
# Forcer le téléchargement
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
```

### Erreur: "Failed building wheel for faiss-cpu" / "swig not found"

Le projet fonctionne sans FAISS (fallback automatique actif). Si l'installation de `faiss-cpu` echoue, continue avec:

```bash
cd backend
python3.12 -m pip install -r requirements.txt
```

Si tu veux FAISS quand meme:

```bash
brew install swig
cd backend
python3.12 -m pip install -r requirements-faiss-optional.txt
```

### CPU vs GPU

Par défaut, le modèle s'exécute sur CPU. Pour GPU (CUDA):

```python
from ai_module.matching.semantic_matcher import SemanticSkillMatcher

# Le modèle auto-détecte GPU s'il est disponible
# Sinon changer dans semantic_matcher.py :
# model = SentenceTransformer(model_name, device='cuda')
```

---

## 📚 Fichiers Importants

| Fichier                                  | Description                   |
| ---------------------------------------- | ----------------------------- |
| `SEMANTIC_MATCHING_SUMMARY.md`           | Vue d'ensemble complète       |
| `SEMANTIC_MATCHING_GUIDE.md`             | Guide détaillé + architecture |
| `ai_module/matching/semantic_matcher.py` | Code principal                |
| `test_semantic_matching.py`              | Tests du module               |
| `test_api_semantic_matching.py`          | Tests de l'API                |

---

## ✅ Checklist d'Installation

- [ ] `pip install -r requirements.txt` exécuté
- [ ] `python test_semantic_matching.py` réussi
- [ ] Serveur FastAPI démarré
- [ ] `test_api_semantic_matching.py` réussi
- [ ] Score différent avant/après semantic matching

---

## 🎯 Prochaines Étapes

1. **Intégration**: Tester avec vos candidats réels et critères actuels
2. **Optimisation**: Ajuster le threshold (0.5-0.8) selon vos préférences
3. **Performance**: Envisager le caching Redis si beaucoup de requêtes
4. **Fine-tuning**: Fine-tuner le modèle sur votre vocabulary métier (avancé)

---

## 💡 Tips & Tricks

### Déboguer un match

```python
# Voir les détails d'un matching
result = SemanticSkillMatcher.match_candidate_skills(...)

for match in result['matched_skills']:
    print(f"{match['criteria_skill']} → {match['matched_skill']}: {match['similarity']:.1%}")
    # "Django" → "Flask": 75%
    # "Database" → "PostgreSQL": 88%
```

### Tester rapidement deux skills

```python
from ai_module.matching.semantic_matcher import semantic_skill_match

is_match, sim = semantic_skill_match("Python", "Django", threshold=0.6)
print(f"Match: {is_match}, Score: {sim:.1%}")
```

### Batch processing (plus rapide)

```python
# Plus rapide que d'appeler get_embedding() plusieurs fois
embeddings = SemanticSkillMatcher.get_embeddings_batch([
    "Python", "Django", "PostgreSQL", "Docker"
])
```

---

**Vous êtes prêt ! Commencez par `python test_semantic_matching.py` 🚀**
