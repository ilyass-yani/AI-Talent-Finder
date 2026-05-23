Pipeline: Extraction -> Feature engineering -> Matching -> Scoring -> Decision finale

But: rendre l'extraction OCR/YELLOW prioritaire, documenter les options de feature engineering, matching, modélisation et finetuning, et fournir commandes pour exécuter localement.

1. Extraction (OCR / YELLOW)

- Par défaut le service favorise OCR quand nécessaire (`ocr_first`).
- Pour forcer l'utilisation d'OCR/YELLOW pour TOUTES les CVs:

  export CV_FORCE_OCR=true

  # Optionnel: CV_OCR_MODE=aggressive|ultra pour activer YELLOW/ultra preprocessing

- Commande d'extraction (script utilitaire):

  python backend/scripts/run_extraction.py --input uploads/cvs --out data/extracted_sample.jsonl --mode ocr --limit 10

2. Feature engineering

- Approche classique: `Bag-of-Words` (CountVectorizer) ou `TF-IDF` puis `TruncatedSVD`.
  Utiliser les helpers dans `backend/app/services/feature_engineering.py`:
  - `fit_pair_bow_vectorizer(...)` pour BOW
  - `fit_pair_vectorizer(...)` pour TF-IDF + SVD

- Approche recommandée: BERT embeddings via `backend/ai_module/matching/bert_embeddings.py`.
  Exemple rapide de génération:

  python backend/train/train_bert_embeddings.py --synthetic --build-index

3. Matching

- Options disponibles:
  - Similarité continue / heuristique (`continuous_similarity`) — rapide
  - Similarité vectorielle (TF-IDF / SVD ou BERT + FAISS) — plus précis
  - Modèle deep learning (Siamese / sentence-transformers) — recommandé pour gros dataset

4. Modélisation ML

- Baseline: `LogisticRegression` ou `RandomForest` (scripts `train_baseline.py`)
- Avancé: `XGBoost` / `Siamese` / `SentenceTransformers`
- Recommandation selon volume de données:
  - Peu de données: ML classique (LogReg / RF / XGBoost)
  - Beaucoup de données: Deep learning / fine-tuning

5. Fine-tuning LLM (optionnel pour génération/profil)

- Support implémenté: Mistral (LoRA / QLoRA), Qwen, LLaMA via l'infrastructure `backend/ai_module/nlp/mistral_finetuner.py`.
- Paramètres typiques: LoRA rank 16, alpha 32, use_8bit=True (QLoRA)
- Exemple:

  python backend/train/train_mistral_finetuner.py --synthetic --epochs 3 --output models/mistral_finetuned

6. Scoring & prise de décision

- Règles implémentées dans `backend/app/services/scoring.py`.
- Decision mapping: `accept` / `review` / `reject` selon score combiné.

7. FastAPI

- Endpoints prêts sous `/api/pipeline` et `/api/advanced/*`.
- Pour démarrer localement:

  cd backend
  source ../.venv/bin/activate
  uvicorn app.main:app --reload --port 8000

8. Scraping (Selenium)

- `backend/jobs/linkedin_scraper.py` met en place un `LinkedInJobScraper`.
- Exemple de lancement batch:

  python backend/train/train_scraper_pipeline.py --query "data scientist" --out data/scrapes.jsonl

9. Notes opérationnelles

- Le matching de production conserve par défaut le bundle `models/final_match_model.joblib`.
- Pour activer la génération IA (profile generator) mettre `USE_AI_PROFILE_GENERATOR=true` mais la valeur par défaut dans le repo est `false` pour éviter dépendances HF en prod.

---

Si tu veux, je peux:

- Lancer un run d'extraction sur un petit lot pour valider OCR/YELLOW
- Générer un exemple d'entraînement XGBoost avec les features TF-IDF
- Déployer un endpoint FastAPI minimal qui exécute tout le pipeline sur une paire CV+Job
