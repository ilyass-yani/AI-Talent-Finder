# Intégration du module `ai_pipeline/` (PFA — ESISA-TechForge4)

Ce document explique comment le nouveau pipeline IA a été intégré dans le projet existant.

---

## Ce qui a été ajouté

### 1. Nouveau module Python `backend/ai_pipeline/`

Module complet (52 fichiers Python) implémentant le pipeline PFA en 7 étapes :

```
CV brut → Extraction NLP → Structuration → Feature Engineering
        → Matching → Scoring → Décision → Explication
```

Structure :
```
backend/ai_pipeline/
├── config.py                       # Configuration centrale
├── preprocessing/                  # CV cleaning, skill normalization, data normalization
├── feature_engineering/            # TF-IDF, embeddings sémantiques, pair features
├── matching/                       # 5 stratégies (cosinus, bi-encoder, cross-encoder, hybride)
├── models/                         # LR / RF / XGBoost / CamemBERT
├── llm/                            # Fine-tuning LoRA / QLoRA / DoRA + inférence
├── scoring/                        # Scoring pondéré + règles métier + décision
├── explainability/                 # Règles + SHAP + LLM explanations
├── vector_db/                      # FAISS + ChromaDB
├── scraping/                       # LinkedIn / Indeed / Welcome to the Jungle
├── datasets/                       # Génération synthétique + chargement + augmentation
├── pipeline/                       # Orchestrateur de bout en bout
└── api/                            # Routers FastAPI (pipeline, llm, scraping)
```

### 2. Nouveaux endpoints REST

Enregistrés via `include_optional_router()` dans `backend/app/main.py` :

| Méthode | Route | Description |
|---|---|---|
| `POST` | `/pipeline/match` | Pipeline complet sur 1 CV + 1 offre |
| `POST` | `/pipeline/batch-match` | 1 CV contre N offres |
| `GET` | `/pipeline/health` | Healthcheck pipeline |
| `POST` | `/llm/score` | Inférence LLM directe (adaptateur LoRA) |
| `GET` | `/llm/status` | État du LLM |
| `GET` | `/scraping/jobs` | Scraping d'offres publiques |

Aucune collision avec les routes existantes (les anciennes sont sous `/api/*`).

### 3. Tests automatisés

`backend/ai_pipeline_tests/` — 21 tests (unitaires + intégration), tous passent.

```bash
cd backend
PYTHONPATH=. pytest ai_pipeline_tests/ -v
```

### 4. Dépendances additionnelles

Ajoutées à `backend/requirements.txt` :

- `trl>=0.10.0` — SFTTrainer pour LoRA/QLoRA
- `shap>=0.45.0` — Explicabilité
- `chromadb>=0.5.0` — Vector store alternative
- `xgboost>=2.0.0` — XGBoost model
- `accelerate>=0.33.0` — Requis par trl/transformers
- `datasets>=2.20.0` — HuggingFace datasets

Les autres (`fastapi`, `peft`, `bitsandbytes`, `selenium`, `beautifulsoup4`, `faiss-cpu`, `sentence-transformers`, `transformers`) étaient déjà présentes.

---

## Comment utiliser

### Démarrer l'API (anciens + nouveaux endpoints)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Documentation interactive : http://localhost:8000/docs

### Appeler depuis le frontend Next.js

```typescript
// frontend/lib/pipeline-api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function matchCVtoJob(payload: {
  cv_text: string;
  job_text: string;
  required_skills?: string[];
  nice_to_have_skills?: string[];
  min_years?: number;
  min_edu_level?: number;
  use_llm?: boolean;
}) {
  const res = await fetch(`${API_BASE}/pipeline/match`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Match failed: ${res.status}`);
  return res.json();
}
```

### Fine-tuning LLM (priorité PFA)

```bash
cd backend

# 1. Générer dataset synthétique (5000 paires équilibrées)
python ai_pipeline/../scripts/generate_synthetic_data.py \
    --n 5000 --output ../data/synthetic_pairs.jsonl

# 2. Fine-tuning QLoRA 4-bit
python ai_pipeline/../scripts/train_qlora.py \
    --data ../data/synthetic_pairs.jsonl \
    --model Qwen/Qwen2.5-1.5B-Instruct \
    --output models/qlora_matching
```

Les scripts d'entraînement complets sont dans `scripts/` (au niveau de `deliverable/` dans le ZIP original).

---

## Cohabitation avec l'ancien code

| Concept | Ancien (`app/`, `ai_module/`) | Nouveau (`ai_pipeline/`) |
|---|---|---|
| Routes API | `/api/matching`, `/api/scoring`, etc. | `/pipeline/*`, `/llm/*`, `/scraping/*` |
| Models SQLAlchemy | `app.models.*` | (n'utilise pas la DB) |
| Models ML | `ai_module/matching/*` | `ai_pipeline/models/*` |
| Préprocessing | `ai_module/nlp/*` | `ai_pipeline/preprocessing/*` |
| Fine-tuning LLM | ❌ | ✅ `ai_pipeline/llm/*` |
| Scoring + règles | `app/services/scoring.py` | `ai_pipeline/scoring/*` |
| Explicabilité | `ai_module/matching/explainability.py` | `ai_pipeline/explainability/*` |

Les deux peuvent coexister. Le nouveau module n'écrit pas en base ; il est stateless (pure inference). Pour persister les résultats, faire appeler `/pipeline/match` depuis un endpoint existant qui sait écrire dans la DB.

---

## Points d'attention

1. **Taille image Docker** — `peft`, `bitsandbytes`, `chromadb`, `xgboost` sont gros (~2-3 Go). Si Railway impose une limite stricte, déplacer ces deps dans `requirements-train.txt` et garder seulement `chromadb`, `shap`, `xgboost` dans `requirements.txt`.

2. **Modèle LLM** — pour activer `/llm/score`, il faut télécharger l'adaptateur LoRA fine-tuné et pointer la variable d'env `LLM_ADAPTER_PATH` vers son répertoire. Voir `.env.example` du ZIP original.

3. **Scraping** — les routes `/scraping/*` requièrent une connexion sortante. À usage académique uniquement (CGU LinkedIn/Indeed).

4. **Healthcheck** — `/pipeline/health` est disponible et peut être ajouté au healthcheck Docker en plus de `/health`.

---

## Équipe

**ESISA-TechForge4** — Encadrante : Mme. **FENNANE Salma**
