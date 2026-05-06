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
from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, recall_score

script_dir = Path(__file__).resolve().parent
repo_root = script_dir.parent.parent
if str(repo_root / 'backend') not in sys.path:
    sys.path.insert(0, str(repo_root / 'backend'))

from app.services.normalization import normalize_text
from app.services.feature_engineering import build_pair_features_dataframe


def build_features(df):
    cv_text = df['cv_text'].fillna('').map(normalize_text)
    job_text = df['job_text'].fillna('').map(normalize_text)
    frame = df.copy()
    frame['cv_text'] = cv_text
    frame['job_text'] = job_text
    X, meta = build_pair_features_dataframe(frame[['cv_text', 'job_text']])
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
    if probs is not None:
        try:
            print('ROC AUC:', roc_auc_score(y, probs))
        except Exception:
            pass


def main(args):
    df = pd.read_csv(args.data)
    # if label not in {0,1}, try to coerce
    df['label'] = df['label'].astype(int)
    df['cv_text'] = df['cv_text'].fillna('').map(normalize_text)
    df['job_text'] = df['job_text'].fillna('').map(normalize_text)

    # quick balance: keep fraction if too large
    if len(df) > 20000:
        df = df.sample(20000, random_state=42)

    X, meta = build_features(df)
    y = df['label'].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=42, stratify=y)

    model = train_model(X_train, y_train)

    evaluate(model, X_train, y_train, 'train')
    evaluate(model, X_test, y_test, 'test')

    # save model and meta
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    joblib.dump({'model': model, 'meta': meta}, args.out)
    print('Saved model to', args.out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    main(args)
