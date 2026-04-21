# AI Talent Finder

Plateforme de recrutement IA : analyse de CV (PDF) → extraction NLP des compétences →
matching pondéré personnalisable → chatbot IA pour exploration des candidats.

**Équipe ESISA-TechForge4** — SY El Hadji Bassirou • DORE Gopou Junior • YANI Ilyass • YOUBI Omar

---

## Stack

| Couche       | Technologies                                                          |
| ------------ | --------------------------------------------------------------------- |
| Frontend     | Next.js (App Router), TypeScript, Tailwind CSS, React Query, Zustand  |
| Backend      | FastAPI, Python 3.11, SQLAlchemy 2.0, Alembic, Pydantic v2            |
| Base         | PostgreSQL 16                                                         |
| IA / NLP     | spaCy (`fr_core_news_md`), scikit-learn, RapidFuzz, Anthropic Claude  |
| Auth         | JWT (python-jose), bcrypt                                             |
| Conteneurs   | Docker + Docker Compose, GitHub Actions CI                            |

LLM par défaut : `claude-sonnet-4-6` (configurable via `LLM_MODEL`).

---

## Démarrage rapide (Docker)

Prérequis : Docker Desktop, et une clé API Anthropic.

```bash
cp .env.example .env
# Éditez .env : mettez au minimum LLM_API_KEY et SECRET_KEY.

docker compose up --build
```

- Frontend : http://localhost:3000
- Backend (Swagger) : http://localhost:8000/docs
- Health check : http://localhost:8000/health

Premier démarrage : appliquer les migrations dans un autre terminal :

```bash
docker compose exec backend alembic upgrade head
```

---

## Démarrage manuel (sans Docker)

### Backend

```bash
cd backend
python -m venv venv
# Windows : venv\Scripts\activate
source venv/bin/activate
pip install -r requirements.txt
python -m spacy download fr_core_news_md
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Variables d'environnement

Toutes les variables sont documentées dans [.env.example](./.env.example).
Indispensables pour démarrer :

| Variable        | Rôle                                              |
| --------------- | ------------------------------------------------- |
| `DATABASE_URL`  | DSN PostgreSQL                                    |
| `SECRET_KEY`    | Clé JWT (>= 32 caractères aléatoires)             |
| `LLM_API_KEY`   | Clé API Anthropic                                 |
| `LLM_MODEL`     | Modèle Claude (par défaut `claude-sonnet-4-6`)    |
| `SPACY_MODEL`   | Modèle spaCy (par défaut `fr_core_news_md`)       |

---

## Arborescence

```
ai-talent-finder/
├── backend/
│   ├── app/
│   │   ├── api/         # Routes FastAPI
│   │   ├── core/        # Config, DB, security, deps
│   │   ├── models/      # SQLAlchemy
│   │   ├── schemas/     # Pydantic
│   │   └── services/    # Logique métier (NLP, matching, LLM, export)
│   ├── ai_module/       # Pipeline NLP + dictionnaire de compétences
│   ├── alembic/         # Migrations
│   └── tests/           # pytest
├── frontend/
│   └── src/
│       ├── app/         # Pages Next.js (App Router)
│       ├── components/  # UI + métier
│       ├── hooks/       # React Query / custom hooks
│       ├── lib/         # axios, utils
│       └── store/       # Zustand
├── docker-compose.yml
└── .github/workflows/   # CI
```

---

## Étapes du projet (cf. *Guide_Developpement_AI_Talent_Finder.pdf*)

| # | Étape                            | Statut |
| - | -------------------------------- | ------ |
| 0 | Prérequis                        | ✅     |
| 1 | Structure du projet              | ✅     |
| 2 | Backend FastAPI                  | ✅     |
| 3 | Authentification JWT             | ✅     |
| 4 | Frontend Next.js                 | ✅     |
| 5 | Gestion des CV / upload          | ✅     |
| 6 | Pipeline NLP                     | ✅     |
| 7 | Matching personnalisable         | ✅     |
| 8 | Chatbot IA + profil idéal        | ✅     |
| 9 | Shortlist / visualisation / export | ✅   |
| 10 | Conteneurisation & déploiement  | 🟡 en cours (Lot 1) |
| 11 | Sécurisation                    | 🟡 partielle |
| 12 | Tests & qualité                 | 🟡 partielle |

---

## Tests

```bash
# Backend
cd backend && pytest -v

# Frontend
cd frontend && npm test
```

---

## CI/CD

GitHub Actions ([.github/workflows/ci.yml](./.github/workflows/ci.yml)) exécute à chaque PR :

- lint + tests backend (avec PostgreSQL service)
- lint + build frontend
- build des images Docker

---

## Licence

MIT.
