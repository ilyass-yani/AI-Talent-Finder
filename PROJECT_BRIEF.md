# PROJECT_BRIEF.md — AI Talent Finder

> Destiné à un assistant IA sans accès au code. Basé exclusivement sur lecture du code réel (juin 2026).

---

## 1. Vue d'ensemble

**AI Talent Finder** est une plateforme de recrutement augmentée par IA. Elle permet à des recruteurs de déposer des fiches de poste, de parser des CV candidats et d'obtenir un classement automatique des profils par pertinence via un moteur de matching sémantique. Les candidats peuvent déposer leur CV et choisir de rendre leur profil visible aux recruteurs. Un chatbot recruitement alimenté par Claude (Anthropic) ou un LLM local répond aux questions contextuelles sur les scores et les candidats. Un panneau admin permet de gérer les utilisateurs, de modérer les offres et de configurer les paramètres du pipeline IA.

**Rôles utilisateurs** (définis dans `app/models/models.py` enum `UserRole`) :
- `admin` — gestion des utilisateurs, modération, configuration pipeline
- `recruiter` — dépose des offres, lance le matching, consulte les candidats visibles
- `candidate` — dépose un CV, contrôle sa visibilité

---

## 2. Stack technique

### Frontend
- **Framework** : Next.js 16 (React 19), TypeScript
- **Appels API** : Axios (`src/services/api.ts`), client centralisé avec intercepteurs JWT et trailing-slash
- **State management** : état local React (`useState`), pas de store global (pas de Redux/Zustand/Jotai)
- **Formulaires** : React Hook Form + Zod (validation)
- **UI** : Tailwind CSS v4, Lucide React (icônes), Recharts (graphiques)
- **Tests** : Jest + Testing Library (unit), Playwright (e2e)

### Backend
- **Framework** : FastAPI (Python), avec `redirect_slashes=True`
- **ORM** : SQLAlchemy (`declarative_base`)
- **Migrations** : Alembic (dossier `backend/alembic/versions/`)
- **Auth** : JWT (librairie `python-jose`), hachage argon2/bcrypt (`passlib`)
- **PDF / OCR** : PyMuPDF (`fitz`), pdfplumber, Tesseract via `pytesseract`
- **ML** : scikit-learn, joblib, sentence-transformers (SentenceTransformer), numpy, xgboost (optionnel)
- **NLP** : modèles HuggingFace (NER CV), extraction de compétences par dictionnaire + fuzzy matching

### Base de données
- **Prod** : PostgreSQL via Supabase (URL dans `DATABASE_URL`)
- **Dev** : SQLite fallback automatique si `DATABASE_URL` absent (`ai_talent_finder.db` à la racine backend)

### Déploiement
- **Frontend** : Vercel (Next.js) — URL prod : `https://ai-talent-finder-flame.vercel.app`
- **Backend** : Docker sur Hugging Face Spaces — URL prod : `https://RHmaster-ai-talent-finder-backend.hf.space`, port exposé `7860`
- **Base** : Supabase (PostgreSQL managé)
- Configuration Railway présente (`railway.json`, `Dockerfile.railway`) mais **n'est plus l'URL cible** — était l'ancienne URL prod.

---

## 3. Architecture & arborescence

### Backend (`backend/`)

```
backend/
├── app/
│   ├── api/           # Routes FastAPI (un fichier par domaine)
│   ├── core/          # Config DB, sécurité JWT, dépendances FastAPI
│   ├── models/        # Modèles SQLAlchemy (models.py)
│   ├── schemas/       # Schémas Pydantic (validation I/O)
│   ├── services/      # Logique métier : extraction CV, matching, scoring
│   └── main.py        # Entrée FastAPI, CORS, startup, inclusion routers
├── ai_module/
│   ├── nlp/           # Parsers CV, extracteurs de compétences, NER, générateur de profil
│   ├── matching/      # CosineScorer, SemanticMatcher, AdaptiveThresholds, SkillQuality
│   ├── feedback/      # RecruiterFeedbackEngine, RecommendationsEngine, BiasDetector
│   └── chatbot/       # ConversationMemory, SmartFallbackResponder
├── alembic/           # Migrations Alembic
│   └── versions/      # Fichiers de migration (chaîne linéaire)
├── models/            # Artefacts ML sérialisés (.joblib) — non versionnés
├── uploads/           # Dossier uploads (plus utilisé : le PDF est maintenant supprimé après parse)
├── Dockerfile         # Image HF Spaces (Python 3.11-slim, port 7860)
└── requirements.txt   # Dépendances Python prod
```

### Frontend (`frontend/`)

```
frontend/
├── src/
│   ├── app/           # Pages Next.js App Router (dossier = route URL)
│   │   ├── auth/      # login, register
│   │   ├── admin/     # dashboard, users, jobs, monitoring, pipeline
│   │   ├── recruiter/ # dashboard, chatbot, shortlist, feedback, export
│   │   ├── candidate/ # dashboard, profile, profile/edit, upload
│   │   ├── candidates/# liste [recruteur] + détail [id]
│   │   ├── matching/  # interface matching
│   │   ├── scoring/   # interface scoring
│   │   ├── jobs/      # gestion fiches de poste
│   │   ├── skills/    # gestion compétences
│   │   ├── demo/      # page démo publique (sans auth)
│   │   └── page.tsx   # Landing page publique
│   ├── services/      # Clients API par domaine (api.ts, auth.ts, candidates.ts…)
│   ├── components/    # Composants réutilisables (Navbar, CandidateCard, ScoreGauge…)
│   ├── hooks/         # useApi.ts (wrapper Axios), useTheme.tsx
│   └── utils/         # errorHandler.ts
├── public/
│   └── runtime-config.js  # Injecte __NEXT_PUBLIC_API_URL au runtime (écrit par docker-entrypoint.sh)
├── next.config.ts     # Config Next.js (rewrites, headers, images)
└── Dockerfile.railway # Image Docker front (Node 20, port 8080)
```

### Comment le front parle au back

1. **URL base** : définie dans `src/services/api.ts` via `resolveApiUrl()` :
   - Lit `window.__NEXT_PUBLIC_API_URL` (runtime, côté browser) ou `process.env.NEXT_PUBLIC_API_URL` (build)
   - Si valeur trouvée et commence par `http` → `${url}/api` (suppression du slash final, ajout `/api`)
   - Sinon → fallback `http://127.0.0.1:8000/api`
2. **Token JWT** : stocké dans `localStorage` sous la clé `access_token`. L'intercepteur de requête Axios l'injecte automatiquement en `Authorization: Bearer <token>`.
3. **Trailing slash** : l'intercepteur ajoute un `/` final à tous les chemins sauf les routes auth (`/auth/login`, `/auth/register`, `/auth/me`, `/auth/logout`).
4. **⚠️ Résidu dans `next.config.ts`** : les rewrites server-side pointent encore vers Railway (`/api/:path*` → Railway). Ces rewrites ne sont jamais déclenchés en pratique car Axios utilise une URL absolue — mais c'est une dette technique à nettoyer.

---

## 4. Base de données

Toutes les tables sont définies dans `backend/app/models/models.py`.

| Table | Colonnes principales | Relations |
|---|---|---|
| `users` | `id`, `email` (unique), `hashed_password`, `full_name`, `role` (admin/recruiter/candidate), `is_active`, `created_at` | → candidate (1:1), job_criteria (1:N), favorites (1:N) |
| `candidates` | `id`, `user_id` (FK users, unique), `full_name`, `email` (unique), `phone`, `linkedin_url`, `github_url`, `cv_path` (null si PDF non conservé), `raw_text`, `owner_role` ("candidate"\|"recruiter"), `is_visible` (bool, défaut false), `created_at`, `updated_at` | → user (N:1), candidate_skills (1:N), experiences (1:N), educations (1:N), match_results (1:N), favorites (1:N) |
| `candidates` (champs NER) | `extracted_name`, `extracted_emails` (JSON), `extracted_phones` (JSON), `extracted_job_titles` (JSON), `extracted_companies` (JSON), `extracted_education` (JSON), `extraction_quality_score` (float 0–100), `ner_extraction_data` (JSON complet), `is_fully_extracted` (bool) | — |
| `skills` | `id`, `name` (unique), `category` (tech/soft/language), `synonyms` (CSV) | → candidate_skills (1:N), criteria_skills (1:N) |
| `candidate_skills` | `id`, `candidate_id` (FK), `skill_id` (FK), `proficiency_level` (beginner/intermediate/advanced/expert), `source` | → candidate (N:1), skill (N:1) |
| `experiences` | `id`, `candidate_id` (FK), `title`, `company`, `duration_months`, `description` | → candidate (N:1) |
| `educations` | `id`, `candidate_id` (FK), `degree`, `institution`, `field`, `year` | → candidate (N:1) |
| `job_criteria` | `id`, `recruiter_id` (FK users), `title`, `description`, `moderation_status` (pending/approved/rejected), `created_at` | → recruiter (N:1), criteria_skills (1:N), match_results (1:N) |
| `criteria_skills` | `id`, `criteria_id` (FK), `skill_id` (FK), `weight` (0–100) | → criteria (N:1), skill (N:1) |
| `match_results` | `id`, `criteria_id` (FK), `candidate_id` (FK), `score` (float 0–1), `explanation` (JSON sérialisé), `created_at` | → criteria (N:1), candidate (N:1) |
| `favorites` | `id`, `recruiter_id` (FK users), `candidate_id` (FK candidates), `created_at` | → recruiter (N:1), candidate (N:1) |
| `system_settings` | `id`, `key` (unique), `value` (JSON), `updated_at`, `updated_by` (FK users nullable) | stockage key/value pour config pipeline |
| `activity_logs` | `id`, `timestamp`, `level` (INFO/WARNING/ERROR), `action` (ex: "auth.login"), `user_id` (FK nullable), `detail` | → user (N:1) |
| `recruiter_feedback` | `id`, `criteria_id` (FK), `candidate_id` (FK), `recruiter_id` (FK), `model_predicted_score`, `model_predicted_decision`, `recruiter_decision`, `recruiter_score_override`, `feedback_reason`, `is_override`, `hire_outcome`, `hire_date`, `created_at`, `updated_at` | → criteria, candidate, recruiter |

**Chaîne de migrations Alembic** :
`4402afc8b225` → `000001_create_all_tables` → `add_ner_extraction` → `20260513_create_recruiter_feedback` → `20260615_add_admin_fields` → `20260617_add_profile_visibility`

---

## 5. API backend

Tous les préfixes commencent par `/api`. L'app démarre sur le port `7860` (HF Spaces).

### Auth — `/api/auth`
| Méthode | Chemin | Description |
|---|---|---|
| POST | `/register` | Inscription → retourne JWT + user |
| POST | `/login` | Connexion → retourne JWT + user |
| GET | `/me` | Profil de l'utilisateur courant (auth requis) |

### Candidates — `/api/candidates` (auth requis sur tout le router)
| Méthode | Chemin | Description |
|---|---|---|
| GET | `/` | Liste candidates filtrée par visibilité selon le rôle (recruteur: ses dépôts + candidats visibles; candidat: son propre profil; admin: tout) |
| POST | `/` | Création/upsert candidat par email |
| GET | `/me/profile` | Profil du candidat connecté |
| POST | `/me/profile` | Création/mise à jour manuelle du profil candidat |
| PATCH | `/me/visibility` | Bascule `is_visible` true/false (candidat seulement) |
| POST | `/upload` | Upload CV (PDF/TXT max 5 MB) → /tmp → NER → profil en base → suppression fichier |
| POST | `/upload-cv-with-ner` | Upload alternatif avec ResumeNERExtractor |
| GET | `/{id}` | Détail candidat (contrôle permission via `_can_access_profile()`, retourne 404 si accès refusé) |
| PUT | `/{id}` | Mise à jour (propriétaire ou admin) |
| DELETE | `/{id}` | Suppression (propriétaire ou admin — droit à l'effacement RGPD) |
| GET | `/{id}/cv` | Téléchargement PDF si cv_path non null (peu probable avec la nouvelle logique) |

**Règle de permission centralisée** (`_can_access_profile()`) :
- Propriétaire (`user_id == current_user.id`) → autorisé
- Recruteur connecté + `owner_role == "candidate"` + `is_visible == true` → autorisé
- Sinon → 404 (pas de 403 pour ne pas révéler l'existence)

### Matching — `/api/matching` (auth requis)
| Méthode | Chemin | Description |
|---|---|---|
| POST | `/criteria` | Créer une fiche de poste avec compétences requises |
| POST | `/search/{criteria_id}` | Recherche candidats (CosineScorer) |
| POST | `/{criteria_id}/results` | Lance le matching complet, persiste en base, retourne classement |
| GET | `/{criteria_id}/results` | Récupère les résultats de matching stockés |
| POST | `/{criteria_id}/predict` | Scoring ML (baseline joblib ou siamese SentenceTransformer) |
| POST | `/generate-profile` | Génère un profil idéal à partir d'une description de poste |
| POST | `/generate-and-match` | Génère profil idéal + matche contre tous les candidats |
| POST | `/match-explanation` | Explication humaine d'un score candidat/poste |
| POST | `/shortlist-summary` | Résumé stratégique de la shortlist |
| POST | `/enriched-explanation` | Explication enrichie avec forces/lacunes |
| GET | `/results` | Tous les match_results (filtrables par criteria_id, candidate_id) |
| GET | `/criteria/{criteria_id}` | Détail d'une fiche de poste |
| GET | `/candidate/{id}/analysis` | Analyse détaillée NER + matching d'un candidat |
| POST | `/calculate/{candidate_id}/{criteria_id}` | Calcul pairwise + persistance |
| GET | `/admin/skills-quality` | Métriques qualité du pool de compétences (admin) |

### Criteria (canonique) — `/api/criteria` (auth Bearer)
| Méthode | Chemin | Description |
|---|---|---|
| POST | `/` | Créer une fiche de poste |
| GET | `/` | Lister ses fiches de poste |
| GET | `/{id}` | Détail fiche de poste |
| PUT | `/{id}` | Mise à jour |
| DELETE | `/{id}` | Suppression |
| POST | `/{id}/results` | Lance le matching (dupliqué avec `/api/matching/{id}/results`) |
| GET | `/{id}/results` | Résultats matching |

### Jobs — `/api/jobs`
| Méthode | Chemin | Description |
|---|---|---|
| GET | `/` | Liste les job_criteria (tous utilisateurs authentifiés) |
| GET | `/{id}` | Détail |
| POST | `/` | Créer une offre |
| PUT | `/{id}` | Mettre à jour |
| DELETE | `/{id}` | Supprimer |
| POST | `/{id}/skills` | Ajouter une compétence requise |
| DELETE | `/{id}/skills/{skill_id}` | Retirer une compétence requise |

### Skills — `/api/skills`
| Méthode | Chemin | Description |
|---|---|---|
| GET | `/` | Liste des compétences |
| GET | `/{id}` | Détail |
| POST | `/` | Créer une compétence |
| DELETE | `/{id}` | Supprimer |

### Experiences — `/api/experiences`
CRUD complet : GET `/`, GET `/{id}`, POST `/`, PUT `/{id}`, DELETE `/{id}`

### Educations — `/api/educations`
CRUD complet : GET `/`, GET `/{id}`, POST `/`, PUT `/{id}`, DELETE `/{id}`

### Favorites — `/api/favorites`
| Méthode | Chemin | Description |
|---|---|---|
| POST | `/{candidate_id}` | Ajouter aux favoris |
| DELETE | `/{candidate_id}` | Retirer des favoris |
| GET | `/` | Liste des favoris du recruteur connecté |

### Chat — `/api/chat`
| Méthode | Chemin | Description |
|---|---|---|
| POST | `` (chemin vide) | Message chatbot → détection intention → Claude API ou LLM local ou fallback template |
| POST | `/ideal-profile` | Génère un profil idéal de candidat via LLM ou fallback |

### Export — `/api/export`
| Méthode | Chemin | Description |
|---|---|---|
| POST | `/{format}` | Export shortlist (format: `csv`, `xlsx`, `pdf`) |

### Feedback (Phase 3) — `/api/feedback`
| Méthode | Chemin | Description |
|---|---|---|
| POST | `/record-decision` | Enregistre la décision recruter vs prédiction modèle |
| GET | `/statistics` | Statistiques agrégées sur les feedbacks |
| GET | `/misclassified` | Cas mal classifiés par le modèle |
| GET | `/recommendations/skills` | Recommandations de compétences |
| GET | `/recommendations/complementary` | Compétences complémentaires |
| GET | `/recommendations/certifications` | Recommandations de certifications |
| POST | `/recommendations/gap-analysis` | Analyse d'écarts de compétences |
| POST | `/bias-analyze` | Analyse de biais dans les décisions de matching |
| GET | `/bias-alerts-summary` | Résumé des alertes de biais |
| POST | `/retrain-model` | Déclenche un ré-entraînement du modèle |

### Admin — `/api/admin` (admin uniquement)
| Méthode | Chemin | Description |
|---|---|---|
| GET | `/users` | Liste paginée des utilisateurs (filtrable rôle/statut) |
| PATCH | `/users/{id}/status` | Activer/désactiver un compte |
| DELETE | `/users/{id}` | Supprimer un utilisateur |
| GET | `/jobs` | Liste paginée des offres (filtrable moderation_status) |
| PATCH | `/jobs/{id}/moderation` | Approuver/rejeter une offre |
| DELETE | `/jobs/{id}` | Supprimer une offre |
| GET | `/stats` | Statistiques globales (nb users, candidats, offres, matches) |

### Pipeline — `/api/pipeline`
Endpoints bas niveau : upload CV brut, extraction features pairwise, scoring direct, fit vectorizer.

### Scoring — `/api/matching` (préfixe partagé)
Endpoints de scoring et de dataset synthétique :
- `POST /score` — score un candidat contre un poste
- `POST /test-dataset` — génère un dataset synthétique
- `GET /health` — santé du service de scoring

### Health (pas de préfixe `/api`)
- `GET /health` → `{"status": "ok", "version": "1.0.0"}`
- `GET /health/deps` → capacités ML disponibles

---

## 6. Fonctionnalités front

| Route | Rôle cible | Ce que ça fait |
|---|---|---|
| `/` | tous | Landing page publique : présentation, FAQ, formulaire de contact |
| `/auth/login` | tous | Formulaire connexion → JWT stocké en localStorage |
| `/auth/register` | tous | Formulaire inscription (choix du rôle : candidat ou recruteur) |
| `/recruiter/dashboard` | recruteur | Vue synthétique : offres actives, derniers matchings, stats |
| `/recruiter/chatbot` | recruteur | Interface chatbot IA (accessible sans auth selon code) |
| `/recruiter/shortlist` | recruteur | Liste des candidats shortlistés avec scores |
| `/recruiter/feedback` | recruteur | Saisie des décisions recruter pour le feedback loop |
| `/recruiter/export` | recruteur | Export CSV/XLSX/PDF de la shortlist |
| `/candidate/dashboard` | candidat | Vue d'ensemble du profil et de sa visibilité |
| `/candidate/profile` | candidat | Affichage du profil extrait du CV |
| `/candidate/profile/edit` | candidat | Édition manuelle du profil |
| `/candidate/upload` | candidat | Upload de CV → parsing NER → création profil |
| `/candidates` | recruteur | Liste des candidats visibles (filtrés côté serveur) |
| `/candidates/[id]` | recruteur | Détail d'un candidat avec scores de matching |
| `/admin/dashboard` | admin | Stats globales de la plateforme |
| `/admin/users` | admin | Gestion utilisateurs (activation/désactivation/suppression) |
| `/admin/jobs` | admin | Modération des offres (approuver/rejeter) |
| `/admin/monitoring` | admin | Logs d'activité et monitoring |
| `/admin/pipeline` | admin | Configuration paramètres pipeline IA |
| `/matching` | recruteur | Interface de création de fiche de poste + lancement matching |
| `/scoring` | recruteur | Interface de scoring direct candidat/poste |
| `/jobs` | recruteur | CRUD fiches de poste |
| `/skills` | recruteur/admin | CRUD référentiel de compétences |
| `/demo` | tous | Page démo accessible sans authentification (route explicitement exclue du redirect 401) |

---

## 7. Logique IA / ML

### Extraction de CV (`app/services/cv_extractor.py`, `ai_module/nlp/`)

**Pipeline PDF → profil structuré** :
1. PDF écrit dans un fichier temporaire (`/tmp` via `tempfile`)
2. Extraction texte : PyMuPDF (`fitz`) en priorité, pdfplumber en fallback, Tesseract OCR si score d'extraction < seuil (`CV_OCR_TRIGGER_SCORE`)
3. Nettoyage texte : `CVCleaner` (`ai_module/nlp/cv_cleaner.py`)
4. NER : `HFResumeNERParser` (modèle HuggingFace configuré via `HF_CV_NER_MODEL`) ou `ResumeNERExtractor` (fallback) → extrait nom, email, téléphone, postes, entreprises, formation
5. Extraction compétences : `EnhancedSkillExtractor` (dictionnaire + fuzzy matching) ou `SkillExtractor`
6. `CVExtractionResult.quality_score` (0–100) : score de complétude de l'extraction
7. PDF supprimé dans le bloc `finally` → seuls le texte brut et les données structurées sont persistés

### Matching candidat/poste (`app/services/matching_engine.py`, `ai_module/matching/`)

**Trois modes** :
1. **CosineScorer** (`ai_module/matching/scorer.py`) : matching pondéré par compétences, cosine similarity dans l'espace des compétences connues
2. **Modèle baseline** (`models/final_match_model.joblib` ou `models/baseline_model.joblib`) : pipeline TF-IDF + SVD + classificateur (RandomForest, XGBoost ou Logistique), retourne une probabilité × 100
3. **Modèle Siamese** (`models/siamese_model_phase2_full/`) : SentenceTransformer, dot product entre embeddings candidat et offre normalisés

**Seuils de décision** (`_decision_from_score()`) :
- score ≥ `MATCH_ACCEPT_THRESHOLD` (défaut 94.78) → `"accepted"`
- score ≥ `MATCH_REVIEW_THRESHOLD` (défaut 89.78) → `"review"`
- sinon → `"rejected"`

### Explainability (`app/services/explainability_engine.py`)
Génère des textes de justification humains pour les scores : compétences matchées/manquantes, alignement expérience, interprétation globale (🟢/🟡/🔴), recommandations.

### Génération de profil idéal (`ai_module/nlp/profile_generator.py`)
`ProfileGenerator.generate_from_text()` : génère la liste de compétences idéales pour un intitulé de poste. Fallback par règles et mots-clés si le modèle n'est pas disponible.

### Chatbot recruteur (`app/api/chat.py`, `ai_module/chatbot/`)
- **Détection d'intention** : règles sur mots-clés (greeting, explanation, comparison, exploration, adjustment, general)
- **LLM** : appel Claude API (`ANTHROPIC_API_KEY`) ou LLM local OpenAI-compatible (`LOCAL_LLM_BASE_URL`). Si aucun disponible → réponse template déterministe (`SmartFallbackResponder`)
- **Mémoire** : `ConversationMemory` (session_id) stocke l'historique en mémoire (pas persisté en base)
- Modèle Claude utilisé : configurable via `ANTHROPIC_MODEL` (défaut : `claude-3-5-sonnet-20241022`)

### Phase 3 — Feedback & amélioration continue (`ai_module/feedback/`)
- `RecruiterFeedbackEngine` : capture des décisions recruteur vs prédictions modèle, détecte les surcharges/sous-évaluations
- `SkillRecommendationsEngine` : recommande des compétences à développer selon les patterns de recrutement
- `BiasDetector` : détecte des biais potentiels dans les décisions de matching (ex: sur-pondération d'une compétence)

---

## 8. Variables d'environnement

### Backend (FastAPI)
| Variable | Rôle |
|---|---|
| `DATABASE_URL` | URL PostgreSQL complète (ex: `postgresql://user:pass@host/db`). Si absent → SQLite local. |
| `SECRET_KEY` | Clé de signature JWT (HS256). Défaut insécurisé présent dans le code → **à changer en prod**. |
| `ANTHROPIC_API_KEY` | Clé API Anthropic pour le chatbot Claude. Si absent → fallback template. |
| `ANTHROPIC_MODEL` | Modèle Claude à utiliser (défaut: `claude-3-5-sonnet-20241022`) |
| `LOCAL_LLM_BASE_URL` | URL base d'un LLM local compatible OpenAI (ex: Ollama) |
| `LOCAL_LLM_MODEL` | Nom du modèle LLM local (défaut: `local-llm`) |
| `LOCAL_LLM_MAX_TOKENS` | Tokens max réponse LLM local (défaut: 700) |
| `LOCAL_LLM_TIMEOUT` | Timeout en secondes pour le LLM local (défaut: 30) |
| `HF_CV_NER_MODEL` | Identifiant modèle HuggingFace pour le NER CV |
| `HF_PROFILE_MODEL` | Identifiant modèle HF pour la génération de profil idéal |
| `HF_SKILL_NER_MODEL` | Identifiant modèle HF pour l'extraction de compétences |
| `SEMANTIC_EMBEDDING_MODEL` | Modèle d'embedding sémantique (SentenceTransformer) |
| `SEMANTIC_MATCH_THRESHOLD` | Seuil de similarité sémantique pour le matching |
| `SKILL_NORMALIZATION_THRESHOLD` | Seuil de fuzzy matching pour la normalisation des compétences |
| `MATCH_ACCEPT_THRESHOLD` | Score (0–100) au-dessus duquel la décision est "accepted" (défaut: 94.78) |
| `MATCH_REVIEW_THRESHOLD` | Score (0–100) au-dessus duquel la décision est "review" (défaut: 89.78) |
| `ENABLE_HTTPS_REDIRECT` | `"true"` pour activer le middleware de redirection HTTPS (proxy reverse) |
| `AI_FEATURES_REQUIRED` | Liste des features IA obligatoires au démarrage (sinon l'app refuse de démarrer) |
| `USE_AI_PROFILE_GENERATOR` | `"true"` pour activer le générateur IA de profil |
| `TOP_K` | Nombre de candidats retournés par l'endpoint `/predict` |
| `TESSERACT_CMD` | Chemin du binaire Tesseract (si non dans PATH) |
| `CV_FORCE_OCR` | `"true"` pour forcer l'OCR même si pdfplumber extrait du texte |
| `CV_OCR_LANG` | Langue OCR Tesseract (ex: `fra+eng`) |
| `CV_OCR_DPI` | Résolution de rendu PDF pour OCR |
| `CV_OCR_TRIGGER_SCORE` | Score texte en-dessous duquel l'OCR est déclenché |
| `CV_OCR_MAX_PAGES` | Nombre max de pages à traiter par OCR |
| `CV_EXTRACTION_DEBUG` | `"true"` pour logs détaillés d'extraction |
| `RAILWAY_ENVIRONMENT_NAME` | Injecté automatiquement par Railway — utilisé pour détecter l'env prod |

### Frontend (Next.js)
| Variable | Rôle |
|---|---|
| `NEXT_PUBLIC_API_URL` | URL de base du backend **sans** `/api` ni slash final (ex: `https://RHmaster-ai-talent-finder-backend.hf.space`). **Obligatoire en prod sur Vercel.** |
| `NEXT_PUBLIC_API_TIMEOUT_MS` | Timeout requêtes Axios en ms (défaut: 30000) |
| `NEXT_PUBLIC_CV_UPLOAD_TIMEOUT_MS` | Timeout spécifique upload CV en ms (défaut: 180000) |

---

## 9. Configuration & déploiement

### Lancer en local

**Backend** :
```bash
cd backend
pip install -r requirements.txt
# Optionnel : copier .env à la racine du repo avec DATABASE_URL, SECRET_KEY, etc.
alembic upgrade head          # Appliquer les migrations
uvicorn app.main:app --reload --port 8000
# → http://127.0.0.1:8000
# → Swagger UI : http://127.0.0.1:8000/docs
```

**Frontend** :
```bash
cd frontend
npm install
# Créer frontend/.env.local avec :
# NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
npm run dev
# → http://localhost:3000
```

### Déploiement production

**Backend (HF Spaces)** :
- Image Docker : `backend/Dockerfile` (Python 3.11-slim, apt: tesseract-ocr, poppler-utils, libpq-dev)
- Port : `7860` (standard HF Spaces)
- Entrypoint : `docker-entrypoint.sh` (dans le repo backend)
- Au démarrage FastAPI (`on_startup`) : `Base.metadata.create_all()` — crée les tables manquantes. **Note** : `alembic upgrade head` n'est PAS automatiquement appelé au démarrage depuis le code — la création des tables se fait via SQLAlchemy directement.

**Frontend (Vercel)** :
- Vercel détecte automatiquement Next.js
- Variable d'env à configurer dans Vercel Dashboard : `NEXT_PUBLIC_API_URL=https://RHmaster-ai-talent-finder-backend.hf.space`
- Un redéploiement est requis après tout changement de variable d'env

**Base (Supabase)** :
- PostgreSQL managé
- `DATABASE_URL` au format `postgresql://user:password@host:5432/db`

### Particularités connues

1. **CORS** : autorisées uniquement `https://ai-talent-finder-flame.vercel.app` et `http://localhost:3000` (défini en dur dans `app/main.py`). Toute nouvelle origine Vercel doit être ajoutée manuellement.
2. **HTTPS derrière proxy** : middleware `HTTPSRedirectMiddleware` conditionnel (variable `ENABLE_HTTPS_REDIRECT=true`) pour corriger le scheme des redirections derrière Railway/HF.
3. **Migrations** : la chaîne Alembic est linéaire. L'ordre d'application est critique. Ne pas sauter de révision.
4. **Artefacts ML** : le dossier `models/` n'est pas versionné. Les fichiers `.joblib` et `siamese_model_*` doivent être présents dans l'image Docker pour activer le scoring ML. Sans eux, l'endpoint `/predict` retourne 404.
5. **`redirect_slashes=True`** : FastAPI redirige automatiquement `/api/candidates` → `/api/candidates/`. L'intercepteur Axios ajoute le slash côté front pour éviter ces redirections.

---

## 10. État actuel & points d'attention

### Ce qui fonctionne
- Auth complète (inscription, connexion, JWT 30 jours)
- Upload CV + extraction NER + persistance profil structuré
- Matching candidat/poste (CosineScorer, baseline joblib si artefact présent)
- Chatbot avec fallback template (sans clé API Anthropic)
- Export shortlist CSV/XLSX/PDF
- Panel admin (users, modération, stats, logs)
- Visibilité des profils candidats (owner_role/is_visible, migration 20260617)
- Déploiement HF Spaces opérationnel (CORS correct)

### Ce qui est désactivé / conditionnel
- **Chatbot IA** : non fonctionnel sans `ANTHROPIC_API_KEY` ou `LOCAL_LLM_BASE_URL`. Le fallback template-based prend le relais (réponses correctes mais non génératives).
- **Scoring ML avancé** (`/predict`) : nécessite les artefacts `models/final_match_model.joblib` et/ou `models/siamese_model_phase2_full/`. Si absents → 404.
- **OCR Tesseract** : fonctionne uniquement si `tesseract-ocr` est installé (présent dans le Dockerfile, absent en dev si non installé localement).
- **Phase 3 feedback** : modules importés avec fallback silencieux — si `ai_module.feedback.*` non disponible, les endpoints retournent des erreurs 500.
- **Tous les routers** : chargés conditionnellement via `include_optional_router()`. Un import qui échoue (dépendance ML manquante) est loggué en WARNING et le router est ignoré — l'app démarre quand même.

### Bugs connus / dettes techniques
- **`next.config.ts` rewrites** : toujours pointés vers `railway.app` en production (dead code car Axios utilise des URLs absolues, mais source de confusion).
- **`recruiter_id` hardcodé à `1`** dans `POST /api/matching/criteria` : les fiches de poste créées via cette route sont toutes attribuées à l'utilisateur ID=1, indépendamment de l'utilisateur connecté. Les routes `/api/criteria` et `/api/jobs` sont correctes.
- **Duplication de routes** : `/api/matching/criteria` et `/api/criteria` font des choses similaires. `/api/matching/{id}/results` et `/api/criteria/{id}/results` sont dupliqués. Certains endpoints ont les deux variantes avec et sans trailing slash codées explicitement.
- **Token JWT** : durée de vie fixe 30 jours, sans mécanisme de refresh ni de révocation.
- **`SECRET_KEY`** : valeur par défaut non sécurisée présente dans `security.py` — doit être surchargée impérativement en production.
- **`pdf_url` / stockage PDF** : non implémenté. Si un recruteur demande plus tard à télécharger le PDF original, ce n'est pas possible (décision réversible documentée dans la checklist).
