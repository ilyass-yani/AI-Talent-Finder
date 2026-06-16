# Module Administrateur — AI Talent Finder

Implémentation de la **partie Administrateur** basée sur le diagramme de cas
d'utilisation (`PFA.EAP`, package « Administrateur »).

Ce document décrit **tous les changements apportés** et **comment tout tester**.

---

## 1. Cas d'utilisation couverts

| Use case (diagramme) | Endpoint(s) backend | Page frontend |
|---|---|---|
| **S'authentifier** | `POST /api/auth/login` (existant) | `/auth/login` |
| **Gérer les utilisateurs (CRUD)** | `GET/POST/PATCH/DELETE /api/admin/users` | `/admin/users` |
| **Consulter les statistiques globales** | `GET /api/admin/stats` | `/admin/dashboard` |
| **Superviser les logs et performances** | `GET /api/admin/logs`, `GET /api/admin/health` | `/admin/monitoring` |
| **Configurer les paramètres du pipeline IA** | `GET/PUT /api/admin/pipeline-config`, `POST /api/admin/pipeline-config/reset` | `/admin/pipeline` |

Toutes les routes `/api/admin/*` exigent un utilisateur authentifié avec le rôle
`admin` (sinon **403 Forbidden**).

---

## 2. Changements — Backend (`backend/app/`)

### Nouveaux fichiers
| Fichier | Rôle |
|---|---|
| `api/admin.py` | Routeur `/api/admin/*` : users CRUD, stats, logs, health, pipeline-config. Protégé par `require_admin`. |
| `schemas/admin.py` | Schémas Pydantic (AdminUserCreate/Update/Response, GlobalStats, ActivityLog, SystemHealth, PipelineConfig…). |
| `core/settings_store.py` | Store de configuration du pipeline IA (poids + seuils), persisté en base et mis en cache mémoire. Source de vérité du scoring. |

### Fichiers modifiés
| Fichier | Modification |
|---|---|
| `models/models.py` | + modèles `SystemSetting` (config clé/valeur JSON) et `ActivityLog` (journal d'audit). |
| `core/dependencies.py` | + `require_admin` (garde rôle admin) et `log_activity()` (audit best-effort). |
| `services/scoring.py` | Les poids (50/20/15/10) et seuils (0.8/0.5) sont désormais lus depuis `settings_store` (valeurs par défaut **identiques** → comportement inchangé tant qu'un admin ne modifie rien). |
| `api/auth.py` | Journalise l'événement `auth.login` à chaque connexion. |
| `main.py` | Enregistre le routeur admin + précharge la config pipeline au démarrage. |
| `seed_test_users.py` | + compte admin de test (`admin@test.com`). |

### Modèle de données ajouté
```text
system_settings(id, key UNIQUE, value TEXT/JSON, updated_at, updated_by → users.id)
activity_logs(id, timestamp, level, action, user_id → users.id, detail)
```
Ces tables sont créées automatiquement au démarrage (`Base.metadata.create_all`).

### Paramètres du pipeline IA configurables
| Clé | Défaut | Description |
|---|---|---|
| `skill_weight` | 0.50 | Poids du recouvrement des compétences |
| `semantic_weight` | 0.20 | Poids de la similarité sémantique |
| `experience_weight` | 0.15 | Poids de l'expérience |
| `education_weight` | 0.10 | Poids de la formation |
| `perfect_match_bonus` | 0.05 | Bonus match parfait |
| `accept_threshold` | 0.80 | Score ≥ seuil → **Accepté** |
| `review_threshold` | 0.50 | Score ≥ seuil → **À revoir**, sinon **Rejeté** |

Validation : chaque valeur ∈ [0, 1] et `accept_threshold ≥ review_threshold`.

---

## 3. Changements — Frontend (`frontend/src/`)

### Nouveaux fichiers
| Fichier | Rôle |
|---|---|
| `services/admin.ts` | Client API admin (users, stats, logs, health, pipeline-config). |
| `components/AdminGuard.tsx` | Garde côté client : redirige les non-admins. |
| `app/admin/dashboard/page.tsx` | Statistiques globales (cartes, répartition par rôle, accès rapides). |
| `app/admin/users/page.tsx` | Tableau CRUD utilisateurs + modale création/édition + recherche/filtre. |
| `app/admin/monitoring/page.tsx` | Santé système, capacités IA, volumétrie, journal d'activité filtrable. |
| `app/admin/pipeline/page.tsx` | Sliders pour les poids/seuils + validation + reset. |

### Fichiers modifiés
| Fichier | Modification |
|---|---|
| `components/Layout.tsx` | + navigation admin (`adminNav`) et badge « Espace Administrateur ». |
| `app/auth/login/page.tsx` | Redirection des admins vers `/admin/dashboard` + compte admin dans l'encart de test. |

---

## 4. Prérequis

- **Backend** : Python 3.11, dépendances de `backend/requirements.txt`.
- **Frontend** : Node 18+, dépendances `frontend/package.json`.
- **Base de données** : l'app lit `DATABASE_URL` depuis le `.env` **racine**.
  Par défaut le projet pointe vers Postgres local
  (`postgresql://...@localhost:5432/ai_talent_finder`). Sans `DATABASE_URL`,
  fallback automatique vers SQLite (`backend/ai_talent_finder.db`).

> ⚠️ **Important — base de seed ≠ base de l'app**
> `seed_test_users.py` importe `app.core.database` directement : il **ne charge pas**
> le `.env` racine et tombe donc sur **SQLite**. L'app (`main.py`) charge le `.env`
> racine et utilise **Postgres**. Les deux peuvent donc viser des bases différentes.
> Pour créer l'admin **dans la base réellement utilisée par l'app**, voir §5.1.

---

## 5. Comment tester

### 5.1 Créer le compte administrateur (dans la base de l'app)

Option A — script de seed (⚠️ vise SQLite par défaut, voir avertissement ci-dessus) :
```bash
cd backend
PYTHONIOENCODING=utf-8 python seed_test_users.py
```

Option B — créer l'admin dans la base réellement utilisée par l'app (recommandé) :
```bash
cd backend
PYTHONIOENCODING=utf-8 python -c "
import sys; sys.path.insert(0,'.')
import app.main  # charge le .env racine -> bonne DB
from app.core.database import SessionLocal, Base, engine
from app.models.models import User, UserRole
from app.core.security import get_password_hash
Base.metadata.create_all(bind=engine)
db = SessionLocal()
if not db.query(User).filter(User.email=='admin@test.com').first():
    db.add(User(email='admin@test.com',
                hashed_password=get_password_hash('password123'),
                full_name='Admin Principal', role=UserRole.admin))
    db.commit(); print('Admin créé')
else:
    print('Admin déjà présent')
db.close()
"
```

**Identifiants de test** : `admin@test.com` / `password123`

### 5.2 Lancer l'application

Backend :
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```
Frontend (autre terminal) :
```bash
cd frontend
npm install   # première fois
npm run dev
```
Puis ouvrir http://localhost:3000/auth/login

### 5.3 Test manuel via l'interface

1. Se connecter avec `admin@test.com` / `password123` → redirection vers `/admin/dashboard`.
2. **Dashboard** : vérifier les compteurs et la répartition par rôle.
3. **Utilisateurs** (`/admin/users`) :
   - Créer un utilisateur (rôle au choix) → il apparaît dans la liste.
   - Modifier son nom / rôle / mot de passe.
   - Rechercher et filtrer par rôle.
   - Supprimer l'utilisateur. (Auto-suppression et suppression du dernier admin sont bloquées.)
4. **Logs & performances** (`/admin/monitoring`) : état DB, capacités IA, volumétrie, journal (filtrer par niveau).
5. **Pipeline IA** (`/admin/pipeline`) : déplacer les sliders, **Enregistrer**, vérifier le message de succès ; tester **Réinitialiser**. Un seuil d'acceptation < seuil de revue désactive le bouton.
6. **Contrôle d'accès** : se déconnecter, se connecter en recruteur (`bob@test.com` / `password123`) puis aller sur `/admin/dashboard` → redirection automatique hors de l'espace admin.

### 5.4 Test automatisé des endpoints (backend)

Test de bout en bout via `TestClient` (login, garde 403, CRUD, stats, config + validation, health, logs) :

```bash
cd backend
PYTHONIOENCODING=utf-8 python -c "
import sys; sys.path.insert(0,'.')
import app.main as m
from app.core.database import SessionLocal, Base, engine
from app.models.models import User, UserRole
from app.core.security import get_password_hash
Base.metadata.create_all(bind=engine)
db = SessionLocal()
if not db.query(User).filter(User.email=='admin@test.com').first():
    db.add(User(email='admin@test.com', hashed_password=get_password_hash('password123'),
                full_name='Admin', role=UserRole.admin)); db.commit()
db.close()
from fastapi.testclient import TestClient
with TestClient(m.app) as c:
    h = {'Authorization': 'Bearer ' + c.post('/api/auth/login', json={'email':'admin@test.com','password':'password123'}).json()['access_token']}
    # garde de rôle (recruteur -> 403)
    rec = c.post('/api/auth/login', json={'email':'bob@test.com','password':'password123'})
    if rec.status_code == 200:
        h2 = {'Authorization':'Bearer '+rec.json()['access_token']}
        assert c.get('/api/admin/stats', headers=h2).status_code == 403
    assert c.get('/api/admin/stats', headers=h).status_code == 200
    u = c.post('/api/admin/users', headers=h, json={'email':'tmp_x@test.com','password':'secret123','full_name':'Tmp','role':'recruiter'})
    assert u.status_code == 201; uid = u.json()['id']
    assert c.patch(f'/api/admin/users/{uid}', headers=h, json={'role':'candidate'}).json()['role'] == 'candidate'
    assert c.put('/api/admin/pipeline-config', headers=h, json={'accept_threshold':0.9,'review_threshold':0.4}).status_code == 200
    assert c.put('/api/admin/pipeline-config', headers=h, json={'accept_threshold':0.3,'review_threshold':0.5}).status_code == 422  # invalide
    assert c.post('/api/admin/pipeline-config/reset', headers=h).status_code == 200
    assert c.get('/api/admin/health', headers=h).json()['status'] == 'ok'
    assert c.delete(f'/api/admin/users/{uid}', headers=h).status_code == 204
    print('OK — tous les endpoints admin passent')
"
```

### 5.5 Test via cURL (serveur lancé sur :8000)

```bash
# 1) Login admin -> récupérer le token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"password123"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 2) Statistiques globales
curl -s http://localhost:8000/api/admin/stats -H "Authorization: Bearer $TOKEN"

# 3) Liste des utilisateurs
curl -s http://localhost:8000/api/admin/users -H "Authorization: Bearer $TOKEN"

# 4) Config du pipeline IA
curl -s http://localhost:8000/api/admin/pipeline-config -H "Authorization: Bearer $TOKEN"

# 5) Mettre à jour un poids/seuil
curl -s -X PUT http://localhost:8000/api/admin/pipeline-config \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"semantic_weight":0.25}'

# 6) Logs & santé
curl -s http://localhost:8000/api/admin/logs   -H "Authorization: Bearer $TOKEN"
curl -s http://localhost:8000/api/admin/health -H "Authorization: Bearer $TOKEN"
```

Doc interactive (Swagger) : http://localhost:8000/docs (section **admin**).

### 5.6 Non-régression du scoring (les défauts ne changent rien)

```bash
cd backend
PYTHONIOENCODING=utf-8 python -c "
import sys; sys.path.insert(0,'.')
from app.services.scoring import decide_match, MatchDecision
assert decide_match(0.85) == MatchDecision.ACCEPTED
assert decide_match(0.60) == MatchDecision.REVIEW
assert decide_match(0.30) == MatchDecision.REJECTED
print('OK — seuils par défaut préservés')
"
```

### 5.7 Vérifications frontend (qualité)

```bash
cd frontend
npx tsc --noEmit                       # typage : aucune erreur attendue
npx eslint src/app/admin src/components/AdminGuard.tsx src/services/admin.ts
npm run build                          # build de production
```

---

## 6. Résultats de vérification (déjà exécutés)

- ✅ Endpoints admin testés de bout en bout sur la base Postgres réelle :
  login (200), garde de rôle (403), CRUD users, stats, pipeline-config (PUT + validation 422 + reset), health, logs.
- ✅ Scoring : comportement par défaut **inchangé** (poids 50/20/15/10, seuils 0.8/0.5).
- ✅ Frontend : `tsc --noEmit` et ESLint sans erreur.

---

## 7. Récapitulatif des fichiers

```
backend/app/
├── api/admin.py                 (nouveau)
├── api/auth.py                  (modifié : log auth.login)
├── core/dependencies.py         (modifié : require_admin, log_activity)
├── core/settings_store.py       (nouveau)
├── main.py                      (modifié : routeur admin + preload config)
├── models/models.py             (modifié : SystemSetting, ActivityLog)
├── schemas/admin.py             (nouveau)
└── services/scoring.py          (modifié : poids/seuils configurables)
backend/seed_test_users.py       (modifié : compte admin)

frontend/src/
├── app/admin/dashboard/page.tsx     (nouveau)
├── app/admin/users/page.tsx         (nouveau)
├── app/admin/monitoring/page.tsx    (nouveau)
├── app/admin/pipeline/page.tsx      (nouveau)
├── app/auth/login/page.tsx          (modifié : redirection admin)
├── components/AdminGuard.tsx        (nouveau)
├── components/Layout.tsx            (modifié : nav + badge admin)
└── services/admin.ts                (nouveau)
```
