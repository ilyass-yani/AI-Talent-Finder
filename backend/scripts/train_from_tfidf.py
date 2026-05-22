#!/usr/bin/env python3
"""Train classical models (LR, RF, optional XGBoost) from TF-IDF+SVD features.

Labels are derived heuristically from extraction metadata when no gold labels exist.
"""
import argparse
import json
import os
import joblib
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score


def load_features(feature_dir: str):
    import pickle
    vect = pickle.load(open(Path(feature_dir) / 'tfidf_vectorizer.pkl', 'rb'))
    svd = pickle.load(open(Path(feature_dir) / 'svd.pkl', 'rb'))
    Xr = np.load(Path(feature_dir) / 'tfidf_svd.npy')
    return vect, svd, Xr


def build_labels_from_extracted(rows):
    # heuristic: label=1 if quality_score>=40 and raw_text_length>=200
    y = []
    for r in rows:
        q = float(r.get('quality_score', 0) or 0)
        l = int(r.get('raw_text_length', 0) or 0)
        y.append(1 if (q >= 40 and l >= 200) else 0)
    return np.array(y, dtype=int)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--extracted', required=True)
    parser.add_argument('--features', required=True)
    parser.add_argument('--out', default='models/classical_from_tfidf')
    args = parser.parse_args()

    p = Path(args.extracted)
    if not p.exists():
        raise SystemExit('extracted jsonl missing')

    rows = [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
    vect, svd, Xr = load_features(args.features)

    # Make sure Xr rows align with rows length; if mismatch, align on min
    n = min(len(rows), Xr.shape[0])
    X = Xr[:n]
    y = build_labels_from_extracted(rows)[:n]

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

    os.makedirs(args.out, exist_ok=True)

    # Logistic Regression
    log = LogisticRegression(max_iter=1000)
    log.fit(X_train, y_train)
    try:
        preds = log.predict_proba(X_val)[:, 1]
        print('Logistic AUC:', roc_auc_score(y_val, preds))
    except Exception:
        print('Logistic trained (no prob output)')
    joblib.dump(log, Path(args.out) / 'logistic.joblib')

    # Random Forest
    rf = RandomForestClassifier(n_estimators=200, n_jobs=1)
    rf.fit(X_train, y_train)
    preds = rf.predict_proba(X_val)[:, 1]
    print('RandomForest AUC:', roc_auc_score(y_val, preds))
    joblib.dump(rf, Path(args.out) / 'random_forest.joblib')

    # XGBoost optional
    if os.getenv('ENABLE_XGBOOST', '0') == '1':
        try:
            import xgboost as xgb
            dtrain = xgb.DMatrix(X_train, label=y_train)
            dval = xgb.DMatrix(X_val, label=y_val)
            params = {'objective': 'binary:logistic', 'eval_metric': 'auc'}
            bst = xgb.train(params, dtrain, num_boost_round=100, evals=[(dval, 'val')])
            preds = bst.predict(dval)
            print('XGBoost AUC:', roc_auc_score(y_val, preds))
            bst.save_model(str(Path(args.out) / 'xgboost.model'))
        except Exception as e:
            print('XGBoost failed:', e)

    # save feature meta pointers (vectorizer, svd) for inference
    joblib.dump({'features_dir': args.features}, Path(args.out) / 'feature_meta.joblib')
    print('Saved models to', args.out)


if __name__ == '__main__':
    main()
