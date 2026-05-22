#!/usr/bin/env python3
"""Train classical models on combined TF-IDF+SVD and BERT embeddings.

Expects:
- TF-IDF artifacts in `--tfidf-dir` (tfidf_svd.npy, tfidf_vectorizer.pkl, svd.pkl)
- BERT embeddings in `--bert-dir` (bert_embeddings.npy)
- extracted jsonl to derive heuristic labels
"""
import argparse
import json
import os
from pathlib import Path
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score


def load_array(p: Path, name: str):
    f = p / name
    if not f.exists():
        raise SystemExit(f'Missing {f}')
    return np.load(f)


def build_labels(rows):
    y = []
    for r in rows:
        q = float(r.get('quality_score', 0) or 0)
        l = int(r.get('raw_text_length', 0) or 0)
        y.append(1 if (q >= 40 and l >= 200) else 0)
    return np.array(y, dtype=int)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--extracted', required=True)
    parser.add_argument('--tfidf-dir', required=True)
    parser.add_argument('--bert-dir', required=True)
    parser.add_argument('--out', default='models/classical_combined')
    args = parser.parse_args()

    tfidf_dir = Path(args.tfidf_dir)
    bert_dir = Path(args.bert_dir)
    if not tfidf_dir.exists() or not bert_dir.exists():
        raise SystemExit('tfidf or bert dir missing')

    X_tfidf = load_array(tfidf_dir, 'tfidf_svd.npy')
    X_bert = load_array(bert_dir, 'bert_embeddings.npy')

    # Align lengths
    n = min(X_tfidf.shape[0], X_bert.shape[0])
    X = np.hstack([X_tfidf[:n], X_bert[:n]])

    rows = [json.loads(l) for l in Path(args.extracted).read_text(encoding='utf-8').splitlines() if l.strip()]
    y = build_labels(rows)[:n]

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

    os.makedirs(args.out, exist_ok=True)

    log = LogisticRegression(max_iter=1000)
    log.fit(X_train, y_train)
    try:
        preds = log.predict_proba(X_val)[:, 1]
        print('Logistic AUC:', roc_auc_score(y_val, preds))
    except Exception:
        print('Logistic trained')
    joblib.dump(log, Path(args.out) / 'logistic.joblib')

    rf = RandomForestClassifier(n_estimators=200, n_jobs=1)
    rf.fit(X_train, y_train)
    preds = rf.predict_proba(X_val)[:, 1]
    print('RandomForest AUC:', roc_auc_score(y_val, preds))
    joblib.dump(rf, Path(args.out) / 'random_forest.joblib')

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

    joblib.dump({'tfidf_dir': str(tfidf_dir), 'bert_dir': str(bert_dir)}, Path(args.out) / 'feature_meta.joblib')
    print('Saved combined models to', args.out)


if __name__ == '__main__':
    main()
