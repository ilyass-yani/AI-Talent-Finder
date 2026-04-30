# 🧠 AI Talent Finder

**Plateforme intelligente de recrutement assistée par IA**

ESISA-TechForge4 — SY El Hadji Bassirou • DORE Gopou Junior • YANI Ilyass • YOUBI Omar

---

## 🚀 Démarrage rapide

### Option 1 — Docker (recommandé)

```bash
cp .env.example .env    # Configurer les variables
docker-compose up       # Lance PostgreSQL + Backend + Frontend
```

→ Frontend : `http://localhost:3000`
→ Backend : `http://localhost:8000/docs`

### Option 2 — Manuel

```bash
# Terminal 1 — Backend
cd backend
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
```

### Option 3 — Railway (production)

Créer 3 services Railway:

- PostgreSQL (plugin Railway)
- Backend (Root Directory: `backend`, Dockerfile)
- Frontend (Root Directory: `frontend`, Dockerfile)

Variables minimales à définir:

```env
# Backend
DATABASE_URL=<Postgres Railway URL>
SECRET_KEY=<minimum-32-characters>
ALLOWED_ORIGINS=<Frontend Railway URL>
ANTHROPIC_API_KEY=<optional>

# Frontend
NEXT_PUBLIC_API_URL=<Backend Railway URL>
NODE_ENV=production
```

Les fichiers `backend/railway.json` et `frontend/railway.json` sont inclus pour forcer le mode Dockerfile et définir les healthchecks.

### Comptes de test

| Rôle | Email | Mot de passe |
|---|---|---|
| Candidat | alice@test.com | password123 |
| Recruteur | bob@test.com | password123 |

---

## 📁 Structure du projet

```
AI-Talent-Finder/
├── backend/
│   ├── app/
│   │   ├── api/              # 13 fichiers de routes
│   │   │   ├── auth.py       # POST /register, /login, GET /me
│   │   │   ├── candidates.py # CRUD candidats + upload CV
│   │   │   ├── skills.py     # CRUD compétences
│   │   │   ├── jobs.py       # CRUD critères de poste
│   │   │   ├── criteria.py   # Critères avancés + matching
│   │   │   ├── matching.py   # Moteur de matching + profil idéal
│   │   │   ├── favorites.py  # Shortlist favoris
│   │   │   ├── chat.py       # Chatbot IA (Anthropic + fallback)
│   │   │   ├── export.py     # Export PDF/CSV/Excel
│   │   │   ├── experiences.py
│   │   │   ├── educations.py
│   │   │   └── match_results.py
│   │   ├── models/models.py  # 10 modèles SQLAlchemy
│   │   ├── schemas/          # Schémas Pydantic
│   │   ├── services/         # CV extractor, matching engine
│   │   └── core/             # Database, security, dependencies
│   ├── ai_module/            # NLP, matching sémantique, chatbot
│   ├── alembic/              # Migrations BDD
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── app/              # 17 pages (Next.js App Router)
│   │   ├── components/       # 9 composants réutilisables
│   │   ├── services/         # 10 services API (Axios)
│   │   ├── hooks/            # useApi, useTheme
│   │   └── utils/            # errorHandler
│   ├── jest.config.js        # Configuration tests
│   └── package.json
│
├── docker-compose.yml
└── .env.example
```

---

## 🔵 Parcours Recruteur

```
Login → Critères de poste → Matching → Explorer candidats → Chatbot IA → Shortlist → Export
```

| Page | Route | Description |
|---|---|---|
| Dashboard | `/recruiter/dashboard` | 2 modes : recherche classique + génération IA |
| Candidats | `/candidates` | Liste avec recherche, favoris, suppression |
| Détail candidat | `/candidates/[id]` | Profil complet avec données NER extraites |
| Compétences | `/skills` | CRUD dictionnaire de compétences |
| Critères de poste | `/jobs` | Créer critères avec compétences pondérées |
| Matching | `/matching` | Critères + sliders → classement par score |
| Chatbot | `/recruiter/chatbot` | Questions IA (expliquer, comparer, explorer, ajuster) |
| Shortlist | `/recruiter/shortlist` | Candidats favoris avec détails |
| Export | `/recruiter/export` | Export PDF, CSV, Excel avec options |

## 🟢 Parcours Candidat

```
Login → Upload CV → Analyse IA → Profil généré → Stockage en base
```

| Page | Route | Description |
|---|---|---|
| Dashboard | `/candidate/dashboard` | Parcours en étapes avec progression |
| Upload CV | `/candidate/upload` | Drag & drop PDF avec extraction automatique |
| Mon profil | `/candidate/profile` | Profil structuré extrait du CV (NER) |
| Éditer profil | `/candidate/profile/edit` | Modifier ses informations |

---

## 🔌 API Backend — Routes complètes

### Authentification
```
POST /api/auth/register     # Inscription (email, password, full_name, role)
POST /api/auth/login        # Connexion → JWT token
GET  /api/auth/me           # Utilisateur courant (protégé)
```

### Candidats
```
GET    /api/candidates/           # Liste des candidats
POST   /api/candidates/           # Créer un candidat
GET    /api/candidates/me/profile # Mon profil (candidat authentifié)
POST   /api/candidates/upload     # Upload CV (PDF)
GET    /api/candidates/{id}       # Détail candidat
PUT    /api/candidates/{id}       # Modifier candidat
DELETE /api/candidates/{id}       # Supprimer candidat
```

### Compétences
```
GET    /api/skills/        # Liste (filtre par catégorie: tech/soft/language)
POST   /api/skills/        # Créer une compétence
DELETE /api/skills/{id}    # Supprimer
```

### Critères de poste
```
GET    /api/criteria/      # Liste des critères
POST   /api/criteria/      # Créer critères avec compétences pondérées
PUT    /api/criteria/{id}  # Modifier
DELETE /api/criteria/{id}  # Supprimer
```

### Matching
```
POST /api/matching/criteria               # Créer critères via matching
POST /api/matching/search/{criteria_id}   # Recherche candidats
POST /api/matching/criteria/{criteria_id}/results  # Lancer le matching
GET  /api/matching/criteria/{criteria_id}/results  # Résultats classés
POST /api/matching/generate-and-match     # Mode IA: profil idéal → matching
POST /api/matching/calculate/{cand}/{crit} # Calcul individuel
```

### Favoris
```
GET    /api/favorites/              # Liste des favoris
POST   /api/favorites/{candidate_id} # Ajouter aux favoris
DELETE /api/favorites/{candidate_id} # Retirer
```

### Chatbot
```
POST /api/chat    # Envoyer un message (avec contexte)
```

### Export
```
POST /api/export/csv    # Export CSV
POST /api/export/excel  # Export Excel
POST /api/export/pdf    # Export PDF
```

---

## 🧪 Tests

```bash
# Frontend (63 tests)
cd frontend && npm test

# Backend
cd backend && python -m pytest tests/
```

---

## ⚙️ Variables d'environnement

Copier `.env.example` → `.env` et configurer :

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_talent_finder
SECRET_KEY=your-secret-key-minimum-32-characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALLOWED_ORIGINS=http://localhost:3000
ANTHROPIC_API_KEY=sk-ant-...    # Optionnel (chatbot fonctionne en fallback)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 📊 Stack technique

| Composant | Technologie |
|---|---|
| Backend | FastAPI, SQLAlchemy, PostgreSQL, Alembic |
| Auth | JWT (python-jose), bcrypt/argon2 (passlib) |
| IA / NLP | spaCy, scikit-learn, transformers, fuzzywuzzy |
| Chatbot | Anthropic Claude API (avec fallback rule-based) |
| Export | ReportLab (PDF), openpyxl (Excel), csv |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS |
| Tests | Jest (frontend), pytest (backend) |
| Deploy | Docker Compose, Railway |

