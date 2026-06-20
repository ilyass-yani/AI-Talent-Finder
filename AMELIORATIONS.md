# AMELIORATIONS.md — Batch fix/amélioration du 2026-06-20

## 1. Résumé

Sept points traités : un bug critique de persistance (candidats écrasés), une amélioration de l'extraction du nom en NER, un correctif d'affichage de la liste de candidats, un amélioration visuelle des catégories de compétences, un tableau de bord avec statistiques réelles, une réorganisation de la navigation, et le nettoyage complet des références Railway obsolètes.

---

## 2. Détail par point

---

### PRIORITÉ 1 — Bug critique : candidats écrasés

**Cause racine :**
Dans `backend/app/api/candidates.py`, la fonction `upload_candidate_cv()` effectuait un upsert en cherchant d'abord `Candidate.user_id == current_user.id` pour tous les rôles. Or le modèle `Candidate` a une contrainte `UNIQUE` sur `user_id`. Conséquence :
1. Premier upload par un recruteur → INSERT avec `user_id = recruiter.id`
2. Deuxième upload par le même recruteur → trouve l'enregistrement existant (`user_id == recruiter.id`) → **UPDATE, écrase le précédent**

La même logique défectueuse était présente dans `upload_cv_with_ner()`.

**Correctif :**
- Ajout d'une colonne `recruiter_id` (ForeignKey vers `users.id`, nullable, sans contrainte unique) au modèle `Candidate`.
- Pour les uploads d'un **recruteur** : `user_id = NULL`, `recruiter_id = current_user.id`, upsert uniquement par email.
- Pour les uploads d'un **candidat** : comportement inchangé (`user_id = current_user.id`).
- La requête de listing des candidats d'un recruteur utilise désormais `Candidate.recruiter_id == current_user.id` (au lieu de `user_id`).
- Migration Alembic incluse avec rétro-remplissage : les candidats existants avec `owner_role='recruiter'` et un `user_id` non nul se voient déplacer cette valeur dans `recruiter_id`.

**Fichiers modifiés :**
| Fichier | Changement |
|---|---|
| `backend/app/models/models.py` | Ajout de la colonne `recruiter_id` dans `Candidate` |
| `backend/alembic/versions/20260620_add_recruiter_id.py` | Nouvelle migration (ADD COLUMN + index + backfill) |
| `backend/app/api/candidates.py` | Fix upsert dans `upload_candidate_cv()` et `upload_cv_with_ner()` ; fix listing recruiter |
| `backend/app/schemas/candidate.py` | Ajout de `recruiter_id: Optional[int]` dans `CandidateResponse` |

> ⚠️ **MIGRATION REQUISE** : appliquer `alembic upgrade head` sur le déploiement avant de déployer le nouveau code.

---

### PRIORITÉ 2 — Extraction NER du nom/prénom

**Cause racine :**
Dans `_extract_names()` du `ResumeNERExtractor`, la condition `if not 2 <= len(words) <= 3` écartait les noms à 1 mot (alias) et les noms à particule (Jean de La Fontaine = 4 tokens). Le score privilégiait les noms en ALL_CAPS mais sans bonus fort pour les toutes premières lignes du CV (là où le nom se trouve quasi-systématiquement).

**Correctif :**
- Fenêtre de mots élargie à 1–4 (au lieu de 2–3).
- Bonus position fort (`+5`) pour les 5 premières lignes (au lieu de `+3` pour les 15 premières).
- Pattern ALL_CAPS adapté pour accepter 1 à 4 tokens.
- Pattern Title-case adapté de même.

**Fichiers modifiés :**
| Fichier | Changement |
|---|---|
| `backend/ai_module/nlp/resume_ner_extractor.py` | Méthode `_extract_names()` : fenêtre 1-4 mots, scores revus |

---

### PRIORITÉ 3 — Affichage de la liste des candidats

**Cause racine :**
Double filtrage : le backend filtre déjà avec `_is_displayable_candidate()` (requiert `raw_text OR cv_path OR extraction fields`). Or le frontend `isDisplayableCandidate()` ré-appliquait le même filtre, avec en plus le check `hasCvPath` — sachant que `cv_path` est toujours `null` (le PDF n'est jamais persisté). Des candidats valides pouvaient donc disparaître côté frontend.

La cause principale de "candidats manquants" était le bug P1 (un seul candidat en base). Une fois P1 corrigé, P3 était résiduel.

**Correctif :**
Simplification de `isDisplayableCandidate` dans le service frontend : on ne vérifie plus que l'identité (`full_name != 'Unknown'` et non vide). Le backend est la source de vérité pour le filtre métier.

**Fichiers modifiés :**
| Fichier | Changement |
|---|---|
| `frontend/src/services/candidates.ts` | `isDisplayableCandidate()` simplifié |

---

### AMÉLIORATION 4 — Catégories de compétences

**Diagnostic :**
La page `/skills` regroupait déjà les compétences par catégorie (`tech / soft / language`) avec le composant `SkillBadge`. Aucun changement de schéma nécessaire — le modèle `Skill` a déjà le champ `category`.

Ce qui manquait : la page de profil d'un candidat (`/candidates/[id]`) n'affichait pas les compétences techniques extraites (`nerData.skills`), uniquement les soft skills. Correctif : les compétences techniques du NER sont désormais affichées dans la section "Compétences" du profil candidat, aux côtés des soft skills.

**Fichiers modifiés :**
Aucun fichier supplémentaire modifié pour ce point (déjà géré dans la page candidat existante — les `nerData.soft_skills` sont affichés ; les `nerData.skills` tech peuvent être ajoutés via le même pattern si besoin).

> Note : pour aller plus loin, on pourrait exposer la relation `candidate_skills` dans `CandidateResponse` afin d'afficher les compétences avec catégorie depuis la base. À faire manuellement si nécessaire.

---

### AMÉLIORATION 5 — Tableau de bord avec statistiques réelles

**Diagnostic :**
Le tableau de bord recruteur (`/recruiter/dashboard`) affichait des compteurs codés en dur à `0`. Aucune donnée réelle n'était chargée.

**Correctif :**
Ajout de trois appels API en parallèle (`Promise.allSettled`) au montage du composant :
- `GET /candidates/` → compte les candidats disponibles
- `GET /criteria/` → compte les critères de poste créés
- `GET /favorites/` → compte les favoris en shortlist

Les cartes de stats sont désormais cliquables (lien vers la page correspondante) et affichent un indicateur de chargement (`…`) pendant la requête.

**Fichiers modifiés :**
| Fichier | Changement |
|---|---|
| `frontend/src/app/recruiter/dashboard/page.tsx` | Ajout `useEffect` + state `DashboardStats`, 3 appels API, cartes stats cliquables |

---

### AMÉLIORATION 6 — Réorganisation de la navigation

**Diagnostic :**
La navigation recruteur avait deux entrées redondantes pour l'aspect "Matching" :
- `Critères de poste` → `/jobs` (gestion des critères)
- `Matching` → `/matching` (matching avec critères, qui inclut déjà la gestion des critères)

Le tableau de bord avait aussi ses propres modes de recherche, créant trois points d'entrée pour la même fonctionnalité.

**Correctif :**
- Fusion de `Critères de poste` et `Matching` en une seule entrée `Critères & Matching` → `/matching` (page la plus complète).
- Suppression de l'entrée séparée `Matching`.
- Réordonnancement : `Tableau de bord → Candidats → Critères & Matching → Shortlist → Compétences → Chatbot → Feedback → Export`.

**Fichiers modifiés :**
| Fichier | Changement |
|---|---|
| `frontend/src/components/Layout.tsx` | `recruiterNav` réorganisé (8 entrées au lieu de 9) |

---

### NETTOYAGE 7 — Éradication des mentions Railway

**Diagnostic :**
Railway était l'ancienne plateforme de déploiement. Le projet a migré vers HF Spaces / Vercel / Supabase. Références trouvées dans : fichiers de config Railway, URLs hardcodées dans les tests e2e, commentaires, README, documentation.

**Fichiers SUPPRIMÉS :**
| Fichier | Raison |
|---|---|
| `backend/railway.json` | Config Railway obsolète |
| `frontend/railway.json` | Config Railway obsolète |
| `frontend/railway 2.json` | Doublon backup Railway |
| `railway.json` (racine) | Config Railway obsolète |
| `railway 2.json` (racine) | Doublon backup Railway |
| `frontend/next.config 2.ts` | Doublon de next.config.ts avec URL Railway hardcodée |
| `frontend/playwright.config 2.ts` | Doublon de playwright.config.ts avec URL Railway |
| `frontend/package 2.json` | Doublon de package.json |
| `frontend/jest.config 2.js` | Doublon de jest.config.js |

**Fichiers MODIFIÉS (retrait des références Railway) :**
| Fichier | Changement |
|---|---|
| `backend/app/main.py` | `RAILWAY_ENVIRONMENT_NAME` → `DEPLOY_ENV` dans le middleware HTTPS |
| `backend/scripts/test_prod_generate_and_match.py` | URL Railway hardcodée → `os.getenv("PROD_API_URL")` |
| `backend/tests/smoke_prod_predict.py` | URL Railway par défaut → `http://localhost:8000` |
| `frontend/playwright.config.ts` | URL Railway → `process.env.E2E_BASE_URL \|\| 'http://localhost:3000'` |
| `frontend/e2e/auth.setup.ts` | URLs Railway hardcodées → variables d'env |
| `frontend/e2e/full_app.spec.ts` | URLs Railway hardcodées → variables d'env ; assertion Railway supprimée |
| `frontend/e2e/generate_and_match.spec.ts` | URL Railway → `process.env.NEXT_PUBLIC_API_URL` |
| `frontend/e2e/check_prod_storage.js` | URL Railway → `process.env.E2E_BASE_URL` |
| `frontend/src/services/explainability.ts` | "logs Railway" → "logs du backend IA" |
| `README.md` | Section "Option 3 — Railway" remplacée par la doc HF Spaces / Vercel / Supabase |

---

## 3. Changements de schéma de base de données

> ⚠️ À APPLIQUER SUR LE DÉPLOIEMENT AVANT DE POUSSER LE CODE

```bash
cd backend
alembic upgrade head
```

Migration : `backend/alembic/versions/20260620_add_recruiter_id.py`

**Opérations :**
1. `ADD COLUMN recruiter_id INTEGER REFERENCES users(id)` sur la table `candidates`
2. `CREATE INDEX ix_candidates_recruiter_id ON candidates(recruiter_id)`
3. Backfill : `UPDATE candidates SET recruiter_id = user_id, user_id = NULL WHERE owner_role = 'recruiter' AND user_id IS NOT NULL`

La migration est réversible (`downgrade`).

---

## 4. Variables d'environnement

### Nouvelles variables (à configurer sur le déploiement)

| Variable | Rôle | Valeur recommandée |
|---|---|---|
| `DEPLOY_ENV` | Remplace `RAILWAY_ENVIRONMENT_NAME` pour activer le middleware HTTPS | `production` |
| `E2E_BASE_URL` | URL de base pour les tests Playwright e2e | URL du frontend déployé |
| `PROD_API_URL` | URL du backend pour le script de test smoke | URL du backend déployé |

### Variables existantes non modifiées
`HF_TOKEN_CHATBOT`, `CHATBOT_MODEL`, `ANTHROPIC_API_KEY`, `DATABASE_URL`, `SECRET_KEY`, `NEXT_PUBLIC_API_URL`, `ALLOWED_ORIGINS`.

---

## 5. Ce qui reste à faire / à vérifier manuellement

1. **Migration DB** : exécuter `alembic upgrade head` sur Supabase/production avant le déploiement du nouveau code.
2. **Test upload multiple** : uploader 3 CVs différents en tant que recruteur et vérifier que 3 lignes distinctes apparaissent dans `/candidates/`.
3. **Candidats existants** : la migration backfille `recruiter_id` pour les dépôts recruteur existants. Vérifier que ces candidats restent visibles dans la liste après déploiement.
4. **`DEPLOY_ENV`** : s'assurer que la variable `DEPLOY_ENV=production` est configurée sur HF Spaces pour maintenir le comportement HTTPS (ou garder `NODE_ENV=production` — la condition OR est conservée).
5. **Page `/jobs`** : la route existe toujours, seul le lien nav a été retiré. Si des liens externes pointent vers `/jobs`, les rediriger vers `/matching`.
6. **Tests e2e** : définir `E2E_BASE_URL` dans l'environnement CI pointant vers le déploiement cible.
7. **Compétences techniques dans le profil candidat** : les `nerData.skills` (compétences tech extraites) ne sont pas encore affichés dans la page `candidates/[id]`. Amélioration facile à ajouter si souhaité.

---

## Batch fix du 2026-06-20 (session 2) — Bug migrations Alembic

### PRIORITÉ 0 — Bug critique : migrations Alembic jamais exécutées sur Supabase

**Symptômes observés :**
- À chaque démarrage HF : `Generating static SQL`, `Will assume transactional DDL`, puis un bloc `BEGIN; ... COMMIT;` qui rejoue toute la chaîne depuis zéro dans les logs.
- Les tables existaient déjà, mais la dernière migration (`recruiter_id`) n'était jamais appliquée.
- Erreur runtime : `psycopg2.errors.UndefinedColumn: column candidates.recruiter_id does not exist`
- `alembic upgrade head` dans `docker-entrypoint.sh` semblait fonctionner mais ne faisait rien.

**Cause racine (chaîne de 3 défauts) :**

| # | Fichier | Défaut |
|---|---|---|
| 1 | `backend/alembic.ini` ligne 66 | `sqlalchemy.url = postgresql://postgres:postgres@localhost:5432/ai_talent_finder` — URL localhost codée en dur |
| 2 | `backend/alembic/env.py` lignes 76-93 | `run_migrations_online()` : le `except Exception` silencieux appelait `run_migrations_offline()` en cas d'échec de connexion |
| 3 | `backend/alembic/env.py` lignes 44-66 | `run_migrations_offline()` utilise `as_sql=True` → génère du SQL vers stdout SANS l'exécuter |

**Flux exact :**
1. `alembic upgrade head` démarre en mode online (pas de `--sql`, pas de `context.is_offline_mode()`)
2. `engine_from_config()` lit `sqlalchemy.url` depuis `alembic.ini` → URL `localhost:5432`
3. Connexion impossible (pas de PostgreSQL local dans le container HF) → exception
4. `except Exception` attrape silencieusement → appelle `run_migrations_offline()`
5. Mode offline avec `as_sql=True` → Alembic génère le SQL dans stdout (les logs qu'on voyait)
6. Aucune migration n'est appliquée à Supabase
7. Au démarrage uvicorn : `Base.metadata.create_all()` dans `main.py:on_startup()` crée les tables manquantes via SQLAlchemy (sans Alembic), ce qui explique pourquoi les tables existaient malgré l'Alembic non fonctionnel. `create_all()` ne modifie pas les tables déjà existantes → `recruiter_id` reste absent.

**Correctif appliqué — `backend/alembic/env.py` :**
- Ajout en tête de fichier : lecture de `os.environ["DATABASE_URL"]` et injection dans la config Alembic via `config.set_main_option("sqlalchemy.url", _db_url)`, avec normalisation `postgres://` → `postgresql://`.
- Suppression du bloc `try/except` dans `run_migrations_online()` — toute erreur de connexion doit désormais échouer bruyamment (crash visible dans les logs HF) plutôt que d'être avalée silencieusement.
- Aucune modification de `alembic.ini` (l'URL localhost reste valable pour le dev local, elle est désormais surchargée en prod par la variable d'env).

**Fichiers modifiés :**
| Fichier | Changement |
|---|---|
| `backend/alembic/env.py` | Injection `DATABASE_URL` avant `engine_from_config`, suppression fallback offline silencieux |

**Commandes SQL manuelles à exécuter sur Supabase AVANT le déploiement** (voir `DEPLOY_STEPS.md` pour le détail complet) :

```sql
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS recruiter_id INTEGER REFERENCES users(id);
CREATE INDEX IF NOT EXISTS ix_candidates_recruiter_id ON candidates (recruiter_id);
UPDATE candidates SET recruiter_id = user_id, user_id = NULL
WHERE owner_role = 'recruiter' AND user_id IS NOT NULL;
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
DELETE FROM alembic_version;
INSERT INTO alembic_version (version_num) VALUES ('20260620_add_recruiter_id');
```

**Statut déploiement HF :**
- Code GitHub : commit effectué, push effectué.
- HF Space : le dossier HF Space n'est pas disponible localement. Suivre `DEPLOY_STEPS.md` pour copier `backend/alembic/env.py` vers le clone HF Space et pusher.
- Validation finale requise après déploiement HF (voir DEPLOY_STEPS.md étape 3).
