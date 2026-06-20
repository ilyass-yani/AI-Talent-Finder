# DEPLOY_STEPS.md — Déploiement du correctif migrations Alembic

**Date :** 2026-06-20  
**Bug corrigé :** migrations Alembic en mode offline (SQL généré mais non exécuté sur Supabase)

---

## ORDRE D'EXÉCUTION OBLIGATOIRE

⚠️ Respecter l'ordre ci-dessous. Si le SQL Supabase est exécuté APRÈS le déploiement,
le container plantera au démarrage (CREATE TABLE sur des tables existantes).

```
ÉTAPE 1 → SQL sur Supabase   (ajouter recruiter_id + estampiller alembic_version)
ÉTAPE 2 → Copie vers HF Space + commit + push HF
ÉTAPE 3 → Vérification des logs HF au démarrage
```

---

## ÉTAPE 1 — SQL à exécuter sur Supabase (console SQL Supabase ou psql)

### 1a. Diagnostic préalable (lecture seule, aucun risque)

```sql
-- Vérifier si alembic_version existe et son contenu
SELECT * FROM alembic_version;

-- Vérifier si recruiter_id existe déjà dans candidates
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'candidates' AND column_name = 'recruiter_id';
```

### 1b. Corrections à appliquer

Copier-coller le bloc complet dans la console SQL Supabase :

```sql
-- Ajouter la colonne recruiter_id si elle n'existe pas encore
ALTER TABLE candidates
    ADD COLUMN IF NOT EXISTS recruiter_id INTEGER REFERENCES users(id);

-- Créer l'index si absent
CREATE INDEX IF NOT EXISTS ix_candidates_recruiter_id ON candidates (recruiter_id);

-- Rétro-remplissage : déplacer user_id → recruiter_id pour les profils recruteur
-- (les candidats avec owner_role='recruiter' avaient user_id = id du recruteur)
UPDATE candidates
SET recruiter_id = user_id, user_id = NULL
WHERE owner_role = 'recruiter' AND user_id IS NOT NULL;

-- Créer et estampiller alembic_version à la tête de la chaîne
-- Cela indique à Alembic que TOUTES les migrations sont déjà appliquées
-- → il ne réessaiera pas de recréer les tables existantes au prochain démarrage
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
DELETE FROM alembic_version;
INSERT INTO alembic_version (version_num) VALUES ('20260620_add_recruiter_id');
```

### 1c. Vérification après exécution

```sql
-- Doit retourner : version_num = '20260620_add_recruiter_id'
SELECT * FROM alembic_version;

-- Doit retourner la colonne recruiter_id
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'candidates' AND column_name = 'recruiter_id';
```

---

## ÉTAPE 2 — Déploiement vers Hugging Face Space

Le repo GitHub et le repo HF Space sont distincts. Le push GitHub ne déclenche pas
le redéploiement HF. Suivre les étapes ci-dessous.

### 2a. Fichiers modifiés à copier vers le dossier du Space HF

Un seul fichier a été modifié dans ce correctif :

| Chemin dans le repo GitHub | Chemin dans le dossier HF Space |
|---|---|
| `backend/alembic/env.py` | `alembic/env.py` |

```bash
# Depuis la racine du repo GitHub, vers le clone du HF Space
# Adapter le chemin vers votre dossier HF Space local
cp backend/alembic/env.py /chemin/vers/ai-talent-finder-backend/alembic/env.py
```

### 2b. Commit et push vers HF Space

```bash
cd /chemin/vers/ai-talent-finder-backend

git add alembic/env.py
git commit -m "fix: alembic online mode - inject DATABASE_URL from env, remove offline fallback"
git push
```

### 2c. Surveiller les logs de démarrage HF

Dans les logs HF Space, au démarrage suivant vous devez voir :

```
==> Migrations Alembic
INFO  [alembic.runtime.migration] Context impl PostgreSQLImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> ...
==> Uvicorn sur le port 7860
```

**Ce que vous NE devez PLUS voir :**
- `Generating static SQL`
- `BEGIN;\n...\nCOMMIT;` (le gros bloc SQL vers stdout)

Si `alembic_version` était correctement estampillé à l'étape 1, vous verrez :
```
INFO  [alembic.runtime.migration] Running upgrade 20260617_... -> 20260620_add_recruiter_id
```
Ou simplement rien si déjà à la tête (déjà estampillé).

---

## ÉTAPE 3 — Validation fonctionnelle

Le bug est résolu quand :

1. Uploader 3 CV différents en tant que recruteur crée **3 lignes distinctes** dans `candidates`
2. Aucune erreur 500 sur `POST /candidates/upload` ni `GET /candidates/`
3. Requête SQL de vérification sur Supabase :

```sql
-- Doit montrer 3 lignes avec des recruiter_id remplis
SELECT id, full_name, recruiter_id, owner_role, created_at
FROM candidates
WHERE owner_role = 'recruiter'
ORDER BY created_at DESC
LIMIT 10;
```

---

## Résumé des causes racines du bug

| Symptôme | Cause |
|---|---|
| SQL affiché dans les logs mais non exécuté | `env.py` tombait en mode offline (`as_sql=True`) |
| Chute en mode offline à chaque démarrage | `run_migrations_online()` échouait sur `localhost:5432` (URL codée en dur dans `alembic.ini`) |
| Exception silencieuse | `except Exception: run_migrations_offline()` avalait l'erreur |
| Tables présentes malgré Alembic non fonctionnel | `Base.metadata.create_all()` dans `app/main.py:on_startup()` créait les tables via SQLAlchemy |
| `recruiter_id` absent | `create_all()` ne modifie pas les tables existantes, contrairement à Alembic |
