"""Train a baseline model on CV-job pairs using TF-IDF + simple classifier.

Usage:
    source ../.venv/bin/activate
    python train/train_baseline.py --data ../../data/training_pairs.csv --out ../../models/baseline_model.joblib

This script attempts to use XGBoost; if not available, falls back to LogisticRegression.
"""
import argparse
import os
import sys
from pathlib import Path
import joblib
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, recall_score, f1_score

script_dir = Path(__file__).resolve().parent
repo_root = script_dir.parent.parent
if str(repo_root / 'backend') not in sys.path:
    sys.path.insert(0, str(repo_root / 'backend'))

from app.services.normalization import normalize_text
from app.services.feature_engineering import build_pair_features, fit_pair_vectorizer


def build_features(df, meta=None):
    frame = df.copy()
    frame['cv_text'] = frame['cv_text'].fillna('').map(normalize_text)
    frame['job_text'] = frame['job_text'].fillna('').map(normalize_text)

    if meta is None:
        meta = fit_pair_vectorizer(frame['cv_text'].tolist(), frame['job_text'].tolist())

    X = np.vstack([
        build_pair_features(row.cv_text, row.job_text, meta)
        for row in frame.itertuples(index=False)
    ])
    return X, meta


def train_model(X_train, y_train):
    try:
        from xgboost import XGBClassifier
        model = XGBClassifier(n_estimators=200, use_label_encoder=False, eval_metric='logloss')
        model.fit(X_train, y_train)
        return model
    except Exception:
        print('XGBoost not available, falling back to LogisticRegression')
        model = LogisticRegression(max_iter=1000)
        model.fit(X_train, y_train)
        return model


def evaluate(model, X, y, name='test'):
    preds = model.predict(X)
    probs = None
    try:
        probs = model.predict_proba(X)[:,1]
    except Exception:
        try:
            probs = model.decision_function(X)
        except Exception:
            probs = None

    print(f'== Evaluation ({name}) ==')
    print('Accuracy:', accuracy_score(y, preds))
    print('Precision:', precision_score(y, preds, zero_division=0))
    print('Recall:', recall_score(y, preds, zero_division=0))
    print('F1:', f1_score(y, preds, zero_division=0))
    if probs is not None:
        try:
            print('ROC AUC:', roc_auc_score(y, probs))
        except Exception:
            pass


def predict_scores(model, X):
    try:
        return model.predict_proba(X)[:, 1]
    except Exception:
        try:
            raw_scores = model.decision_function(X)
            return 1.0 / (1.0 + np.exp(-raw_scores))
        except Exception:
            return model.predict(X).astype(float)


def best_f1_threshold(scores, labels):
    best_threshold = 0.5
    best_f1 = -1.0
    for threshold in np.linspace(0.0, 1.0, 101):
        current_f1 = f1_score(labels, (scores >= threshold).astype(int), zero_division=0)
        if current_f1 > best_f1:
            best_f1 = current_f1
            best_threshold = float(threshold)
    return best_threshold


def main(args):
    df = pd.read_csv(args.data)
    # if label not in {0,1}, try to coerce
    df['label'] = df['label'].astype(int)

    # quick balance: keep fraction if too large
    if len(df) > 20000:
        df = df.sample(20000, random_state=42)

    train_df, test_df = train_test_split(df, test_size=0.15, random_state=42, stratify=df['label'])

    X_train, meta = build_features(train_df)
    X_test, _ = build_features(test_df, meta=meta)
    y_train = train_df['label'].values
    y_test = test_df['label'].values

    model = train_model(X_train, y_train)

    evaluate(model, X_train, y_train, 'train')
    evaluate(model, X_test, y_test, 'test')

    train_scores = predict_scores(model, X_train)
    test_scores = predict_scores(model, X_test)
    threshold = best_f1_threshold(test_scores, y_test)

    # save model and meta
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    joblib.dump(
        {
            'model': model,
            'meta': meta,
            'thresholds': {
                'accept_pct': 80.0,
                'review_pct': 50.0,
            },
            'metrics': {
                'train_accuracy': float(accuracy_score(y_train, (train_scores >= 0.5).astype(int))),
                'test_accuracy': float(accuracy_score(y_test, (test_scores >= 0.5).astype(int))),
                'test_best_f1_threshold': float(threshold),
            },
        },
        args.out,
    )
    print('Saved model to', args.out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    main(args)
