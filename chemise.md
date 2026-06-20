# chemise.md — Documentation des changements et état du programme

**Projet :** AI-Talent-Finder  
**Date de rédaction :** 2026-06-20  
**Auteur :** Claude (session correctif migrations Alembic)

---

## 1. Ce qui a changé dans cette session

### Fichier modifié : `backend/alembic/env.py`

**Problème résolu :** Les migrations Alembic n'étaient jamais appliquées réellement à la base Supabase depuis au moins plusieurs semaines. Le SQL était généré et affiché dans les logs mais jamais exécuté.

**Ce qui était cassé (avant) :**

```python
# run_migrations_online() dans l'ancien env.py
try:
    connectable = engine_from_config(...)  # lit localhost:5432 depuis alembic.ini
    ...
except Exception:
    run_migrations_offline()  # ← avale l'erreur et génère du SQL vers stdout
```

La fonction `run_migrations_offline()` contient `as_sql=True`, ce qui fait que le SQL
est écrit dans stdout au lieu d'être exécuté sur la base.

**Ce qui est corrigé (après) :**

```python
# Début du nouveau env.py
_db_url = os.environ.get("DATABASE_URL", "").strip()
if _db_url:
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    config.set_main_option("sqlalchemy.url", _db_url)
```

`DATABASE_URL` (variable d'env Supabase) est injectée dans la config Alembic AVANT
que `engine_from_config()` ne lise `sqlalchemy.url`. Plus de connexion à localhost,
plus de fallback silencieux vers le mode offline.

**Fichiers créés dans cette session :**

| Fichier | But |
|---|---|
| `DEPLOY_STEPS.md` | Guide étape-par-étape pour déployer le correctif (SQL Supabase + push HF) |
| `chemise.md` | Ce document |

---

## 2. Architecture globale du programme

### Backend (FastAPI + SQLAlchemy + Alembic)

**Déploiement :** Hugging Face Spaces (Docker). Repo HF Space séparé du repo GitHub.  
**Base de données :** PostgreSQL sur Supabase, accédée via `DATABASE_URL` (variable d'env).

```
backend/
├── app/
│   ├── main.py               ← Application FastAPI, startup hook (create_all)
│   ├── core/
│   │   ├── database.py       ← engine, SessionLocal, Base (lit DATABASE_URL)
│   │   └── ...
│   ├── api/
│   │   ├── candidates.py     ← Upload CV, liste candidats, logique recruiter_id
│   │   ├── auth.py           ← Login/register
│   │   ├── matching.py       ← Matching IA
│   │   └── ...
│   └── models/
│       └── models.py         ← Modèles SQLAlchemy (Candidate, User, etc.)
├── alembic/
│   ├── env.py                ← ← MODIFIÉ — injecte DATABASE_URL
│   └── versions/             ← Chaîne de migrations
│       ├── 53a6f0317e90_initial_models.py          (root)
│       ├── 4402afc8b225_add_candidates_table.py
│       ├── 000001_create_all_tables.py
│       ├── add_ner_extraction_columns.py
│       ├── 20260513_create_recruiter_feedback.py
│       ├── 20260615_add_admin_fields.py
│       ├── 20260617_add_profile_visibility.py
│       └── 20260620_add_recruiter_id.py             (head)
├── alembic.ini               ← URL localhost (dev local) — surchargée en prod par env.py
├── Dockerfile
└── docker-entrypoint.sh      ← alembic upgrade head → uvicorn
```

**Chaîne de migrations (ordre) :**
```
53a6f0317e90 → 4402afc8b225 → 000001_create_all_tables → add_ner_extraction
→ 20260513_create_recruiter_feedback → 20260615_add_admin_fields
→ 20260617_add_profile_visibility → 20260620_add_recruiter_id  (HEAD)
```

### Frontend (Next.js)

**Déploiement :** Vercel  
**URL backend :** `NEXT_PUBLIC_API_URL` (variable d'env Vercel)

```
frontend/
├── src/
│   ├── app/
│   │   ├── recruiter/        ← Pages recruteur (dashboard, upload, matching...)
│   │   └── ...
│   ├── services/
│   │   ├── candidates.ts     ← Appels API candidats
│   │   └── ...
│   └── components/
│       └── Layout.tsx        ← Navigation principale
```

---

## 3. Problèmes résolus dans les deux dernières sessions

| # | Problème | Statut |
|---|---|---|
| P0 | Migrations Alembic en mode offline : colonnes comme `recruiter_id` jamais ajoutées | **Corrigé** (cette session) |
| P1 | Candidats écrasés : chaque upload recruteur écrasait le précédent | **Corrigé** (session précédente) |
| P2 | NER : noms trop courts (1 mot) ou trop longs (4+ tokens) rejetés | **Corrigé** |
| P3 | Frontend masquait des candidats valides (double filtrage `cv_path`) | **Corrigé** |
| P4 | Dashboard recruteur : statistiques codées en dur à 0 | **Corrigé** |
| P5 | Navigation : entrées redondantes Critères/Matching | **Corrigé** |
| P6 | Références Railway obsolètes dans configs, tests, README | **Corrigé** |

---

## 4. Problèmes restants connus

### 4.1 Colonne `recruiter_id` absente physiquement dans Supabase

**Statut :** En attente d'exécution manuelle SQL + déploiement HF  
**Impact :** `POST /candidates/upload` et `GET /candidates/` retournent 500  
**Action requise :** Suivre `DEPLOY_STEPS.md` intégralement (SQL d'abord, push HF ensuite)

### 4.2 `Base.metadata.create_all()` redondant dans `main.py`

**Fichier :** `backend/app/main.py` ligne 82  
**Statut :** Non critique après la correction d'Alembic  
**Explication :** Après le correctif, Alembic crée les tables au démarrage via `upgrade head`.
`create_all()` tourne ensuite et ne fait rien (les tables existent déjà). Si Alembic échoue
(DATABASE_URL manquante, Supabase inaccessible), `create_all()` prend le relais mais
n'appliquera pas les colonnes nouvelles des migrations futures.  
**Recommandation :** À long terme, supprimer `create_all()` du startup et laisser Alembic
être la seule source de vérité pour le schéma. Pas urgent tant que le correctif est déployé.

### 4.3 Compétences techniques non affichées dans le profil candidat

**Fichier :** `frontend/src/app/recruiter/candidates/[id]/page.tsx` (ou équivalent)  
**Statut :** Fonctionnalité partielle — les soft skills NER sont affichés mais pas les
compétences tech extraites (`nerData.skills`)  
**Action requise :** Ajouter l'affichage de `nerData.skills` dans la section Compétences
du profil, sur le même pattern que `nerData.soft_skills`

### 4.4 Page `/jobs` toujours accessible mais sans lien nav

**Fichier :** `frontend/src/app/recruiter/jobs/...`  
**Statut :** La page existe, le lien de navigation a été retiré (fusionné dans `/matching`)  
**Impact :** Aucun si personne n'utilise l'URL directement. Pas de redirection en place.  
**Recommandation :** Ajouter un `redirect()` de `/jobs` vers `/matching` si des bookmarks existent.

### 4.5 Apostrophes typographiques potentielles dans des fichiers anciens

**Contexte :** Une précédente livraison de `resume_ner_extractor.py` avait des apostrophes
courbes (`'`) au lieu d'apostrophes ASCII (`'`) → SyntaxError au runtime.  
**Statut :** Corrigé pour ce fichier. Les autres fichiers n'ont pas été audités exhaustivement.  
**Commande de vérification rapide :**
```bash
grep -rn $'\xe2\x80\x98\|\xe2\x80\x99' backend/app/ backend/ai_module/
```
(retourne les lignes avec `'` ou `'` — doit être vide)

### 4.6 Chaîne de migrations non linéaire potentielle

**Statut :** Vérifié — la chaîne est bien linéaire (pas de branches).  
**Risque résiduel :** Si une future migration est créée avec `alembic revision` sans
préciser `--head`, elle pourrait créer une branche. Toujours utiliser `alembic revision --head head --autogenerate`.

---

## 5. Variables d'environnement requises sur HF Space

| Variable | Obligatoire | Description |
|---|---|---|
| `DATABASE_URL` | **Oui** | URL Supabase PostgreSQL (format `postgresql://...`) |
| `SECRET_KEY` | **Oui** | Clé JWT pour l'authentification |
| `HF_TOKEN_CHATBOT` | Non | Token HF pour le chatbot QWEN |
| `CHATBOT_MODEL` | Non | Modèle chatbot (défaut dans le code) |
| `ANTHROPIC_API_KEY` | Non | Pour les features Anthropic |
| `DEPLOY_ENV` | Recommandé | `production` pour activer le middleware HTTPS |

Si `DATABASE_URL` est absente, `database.py` bascule sur SQLite local et Alembic
n'injectera rien (condition `if _db_url:`) → les migrations ne tourneront pas mais
ne planteront pas non plus. Le log devra montrer l'avertissement SQLite.

---

## 6. Commandes utiles (développement local)

```bash
# Lancer le backend localement (avec .env à la racine du projet)
cd backend
uvicorn app.main:app --reload --port 8000

# Appliquer les migrations Alembic en local
cd backend
DATABASE_URL=postgresql://... alembic upgrade head

# Générer une nouvelle migration
cd backend
DATABASE_URL=postgresql://... alembic revision --head head --autogenerate -m "description"

# Vérifier la syntaxe Python des fichiers
python3 -m py_compile alembic/env.py

# Chercher les apostrophes typographiques
grep -rn $'\xe2\x80\x98\|\xe2\x80\x99' app/ ai_module/
```
