Entraînement - instructions rapides

Prérequis

- Python 3.10+ venv activé pour le baseline
- Python 3.12 recommandé pour la phase 2 Siamese avec CPU PyTorch
- Installer: `pip install -r requirements-train.txt`

Requirements (exemples)

- sentence-transformers
- scikit-learn
- xgboost
- pandas

Exemples de commandes

0. Pipeline complet recommandé:

```bash
cd backend
source ../.venv/bin/activate
python scripts/build_final_matching_artifacts.py --db ./ai_talent_finder.db
```

Sorties:

- `../data/final_training_pairs.csv` : dataset mixte réel + synthétique
- `../data/final_training_review_sample.csv` : échantillon pour revue humaine
- `../models/final_match_model.joblib` : bundle final chargé par l'API
- `../reports/advanced_matching_report.json` : métriques + seuils recommandés

1. Export depuis la BDD (si vous avez accès):

```bash
cd backend
source ../.venv/bin/activate
python scripts/prepare_training_data.py --out ../data/training_pairs.csv --limit 5000
```

2. Entraînement baseline:

```bash
python train/train_baseline.py --data ../data/training_pairs_labeled.csv --out ../models/baseline_xgb.model
```

Phase 2 - Siamese / sentence-transformers

```bash
cd backend
source ../.venv/bin/activate
pip install -r requirements-train.txt
python train/train_siamese.py --data ../data/training_pairs.csv --output-dir ../models/siamese_model --epochs 1
```

Sorties générées:

- `../models/siamese_model/` : modèle fine-tuné sentence-transformers
- `../models/siamese_model/training_metadata.json` : métriques et paramètres de l'entraînement

Note:

- Si `torch` ou `sentence-transformers` manque, le script affiche un message d'installation clair.
- Dans ce workspace, `torch` n'est pas disponible pour Python 3.13; pour réellement lancer la phase 2, utilise un environnement Python compatible avec une wheel CPU PyTorch (par exemple Python 3.12) puis relance la commande ci-dessus.
- Les features baseline et API partagent la même implémentation dans `backend/app/services/feature_engineering.py`.
- Le bundle final utilisé en production est `../models/final_match_model.joblib` (avec seuils calibrés dans le bundle).
