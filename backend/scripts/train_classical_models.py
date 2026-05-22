"""Train classical ML models: LogisticRegression, RandomForest, XGBoost.

Usage:
    python train_classical_models.py --data path/to/dataset.csv --out models/

Dataset expected: CSV with columns `cv_text`, `job_text`, `label` (0/1)
"""
import argparse
import os
import csv
import joblib
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, accuracy_score

from app.services.feature_engineering import build_pair_features, fit_pair_vectorizer


def featurize(df):
    cv_texts = [row["cv_text"] for row in df]
    job_texts = [row["job_text"] for row in df]
    meta = fit_pair_vectorizer(cv_texts, job_texts)
    X = np.vstack([build_pair_features(cv, job, meta).ravel() for cv, job in zip(cv_texts, job_texts)])
    return X, meta


def load_dataset(path):
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = [row for row in reader]
    if not rows:
        raise SystemExit("Dataset is empty")
    for row in rows:
        if "cv_text" not in row or "job_text" not in row or "label" not in row:
            raise SystemExit("Dataset must contain cv_text, job_text, and label columns")
        row["label"] = int(row["label"])
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", default="models/classical")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    df = load_dataset(args.data)

    X, meta = featurize(df)
    y = np.array([row["label"] for row in df])

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

    # Logistic Regression
    log = LogisticRegression(max_iter=1000)
    log.fit(X_train, y_train)
    preds = log.predict_proba(X_val)[:, 1]
    print("Logistic AUC:", roc_auc_score(y_val, preds))
    joblib.dump(log, os.path.join(args.out, "logistic.joblib"))

    # Random Forest (single-threaded default for better portability on macOS/OpenMP mixes)
    rf = RandomForestClassifier(n_estimators=200, n_jobs=1)
    rf.fit(X_train, y_train)
    preds = rf.predict_proba(X_val)[:, 1]
    print("RandomForest AUC:", roc_auc_score(y_val, preds))
    joblib.dump(rf, os.path.join(args.out, "random_forest.joblib"))

    # XGBoost (optional, lazily imported to avoid environment crashes on systems
    # with conflicting OpenMP runtimes). Enable with ENABLE_XGBOOST=1.
    if os.getenv("ENABLE_XGBOOST", "0") == "1":
        try:
            import xgboost as xgb
            dtrain = xgb.DMatrix(X_train, label=y_train)
            dval = xgb.DMatrix(X_val, label=y_val)
            params = {"objective": "binary:logistic", "eval_metric": "auc"}
            bst = xgb.train(params, dtrain, num_boost_round=100, evals=[(dval, "val")])
            preds = bst.predict(dval)
            print("XGBoost AUC:", roc_auc_score(y_val, preds))
            bst.save_model(os.path.join(args.out, "xgboost.model"))
        except Exception as e:
            print(f"XGBoost unavailable or failed ({e}); skipping")
    else:
        print("XGBoost disabled by default (set ENABLE_XGBOOST=1 to enable)")

    # Save featurization meta for inference
    joblib.dump(meta, os.path.join(args.out, "pair_feature_meta.joblib"))


if __name__ == "__main__":
    main()
