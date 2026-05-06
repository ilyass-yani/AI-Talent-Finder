#!/usr/bin/env python3
"""Quick baseline training POC: generates synthetic pairs and trains a simple model."""

import os
import json
from pathlib import Path
import numpy as np
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
import pickle

# Synthetic training data generation
def generate_synthetic_pairs(n=200):
    """Generate synthetic CV-job pairs with labels."""
    X, y = make_classification(n_samples=n, n_features=50, n_informative=30,
                               n_redundant=10, random_state=42)
    return X, y

def train_and_save(output_dir='../models'):
    output_path = Path(__file__).resolve().parents[1] / output_dir
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("[1/4] Generating synthetic training data (200 pairs)...")
    X, y = generate_synthetic_pairs(200)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("[2/4] Training Logistic Regression baseline...")
    lr_model = LogisticRegression(max_iter=1000, random_state=42)
    lr_model.fit(X_train, y_train)
    lr_score = lr_model.score(X_test, y_test)
    print(f"  ~ LR test accuracy: {lr_score:.3f}")
    
    print("[3/4] Training Random Forest baseline...")
    rf_model = RandomForestClassifier(n_estimators=50, max_depth=10, random_state=42)
    rf_model.fit(X_train, y_train)
    rf_score = rf_model.score(X_test, y_test)
    print(f"  ~ RF test accuracy: {rf_score:.3f}")
    
    print("[4/4] Saving models...")
    lr_path = output_path / 'baseline_lr_poc.pkl'
    rf_path = output_path / 'baseline_rf_poc.pkl'
    
    with open(lr_path, 'wb') as f:
        pickle.dump(lr_model, f)
    print(f"  Saved: {lr_path}")
    
    with open(rf_path, 'wb') as f:
        pickle.dump(rf_model, f)
    print(f"  Saved: {rf_path}")
    
    # Save metadata
    meta = {
        'model_type': 'baseline_poc',
        'n_training_samples': len(X_train),
        'n_features': X_train.shape[1],
        'lr_accuracy': float(lr_score),
        'rf_accuracy': float(rf_score),
        'timestamp': str(Path(__file__).stat().st_mtime)
    }
    meta_path = output_path / 'baseline_poc_metadata.json'
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)
    print(f"  Saved: {meta_path}")
    print("\n✅ Training complete!")

if __name__ == '__main__':
    train_and_save()
