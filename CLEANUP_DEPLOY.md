# Nettoyage du repo de déploiement

> Applique les commandes ci-dessous depuis la **racine** du repo `ai-talent-finder-backend`
> (ou le répertoire qui correspond à `backend/` du repo principal).
> Elles suppriment les fichiers temporaires/obsolètes qui ont été retirés du repo source.

---

## 1. Fichiers .md obsolètes (racine du repo déploiement = `backend/`)

```bash
rm -f FINETUNE_README.md
```

---

## 2. Fichiers de test temporaires à la racine (`backend/`)

```bash
rm -f \
  e2e_test.py \
  test_etapes_5_6_7.py \
  test_etapes_simple.py \
  test_chatbot_recruiter_scenarios.py \
  test_cv_benchmark.py \
  test_semantic_matching.py \
  test_ai_model.py \
  test_api_semantic_matching.py \
  test_ner_integration.py \
  test_chatbot_fallback_scenarios.py \
  test_phase1_integration.py \
  seed_minimal_recruiter_test.py \
  test_client.py \
  test_e2e_recruiter_flow.py \
  seed_test_users.py \
  validate_backend_final.py \
  validate_backend_runtime.py \
  run_all_tests.py \
  run_representative_tests.py
```

---

## 3. Correctifs à vérifier / copier depuis le repo source

Ces fichiers ont été **modifiés** côté source. Vérifie qu'ils sont bien synchronisés
dans le repo de déploiement (copie si nécessaire) :

| Fichier | Changement |
|---------|-----------|
| `app/main.py` | Alias `HF_TOKEN_CHATBOT` → `HF_TOKEN` au démarrage + warning `create_all` |
| `alembic.ini` | Commentaire sur l'URL localhost (pas de changement fonctionnel) |
| `check_before_deploy.py` | **Nouveau** — script de vérification pré-déploiement |

---

## 4. Script de vérification pré-déploiement (nouveau fichier)

Le fichier `check_before_deploy.py` a été ajouté à la racine de `backend/`.
À **copier** dans le repo de déploiement, puis exécuter avant chaque push :

```bash
python check_before_deploy.py
```

Il vérifie que les correctifs critiques (`_can_access_profile`, `recruiter_id`,
`cascade`, `HF_TOKEN_CHATBOT`, `DATABASE_URL`) sont bien présents et que les
fichiers Python clés compilent sans erreur.

---

## 5. Fichiers conservés (ne pas supprimer)

- `README.md`
- `alembic/` (tout le répertoire)
- `app/` (tout le répertoire)
- `ai_module/` (tout le répertoire)
- `scripts/` (scripts utilitaires)
- `tests/` (suite de tests formelle)
- `requirements*.txt`
- `Dockerfile`, `docker-entrypoint.sh`
