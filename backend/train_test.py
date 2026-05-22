"""Legacy training smoke script kept import-safe for pytest collection."""


def main() -> int:
    import os
    import sys

    import numpy as np
    import pandas as pd

    print('STEP1 load csv')
    csv_path = '../data/training_pairs.csv'
    if not os.path.exists(csv_path):
        print(f'Error: {csv_path} not found')
        return 1

    df = pd.read_csv(csv_path)
    print('rows', len(df), 'cols', df.columns.tolist())

    print('STEP2 import featurizer')
    from app.services.feature_engineering import build_pair_features, fit_pair_vectorizer
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split

    print('STEP3 fit vectorizer')
    subset_df = df.head(100).copy()
    cv_texts = subset_df['cv_text'].fillna('').astype(str).tolist()
    job_texts = subset_df['job_text'].fillna('').astype(str).tolist()
    meta = fit_pair_vectorizer(cv_texts, job_texts)

    print('STEP4 build few features')
    arr = []
    for cv, jb in zip(cv_texts, job_texts):
        features = build_pair_features(cv, jb, meta)
        arr.append(features.ravel())

    X = np.vstack(arr)
    y = subset_df['label'].astype(int).to_numpy()
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

    log = LogisticRegression(max_iter=500)
    log.fit(X_train, y_train)

    rf = RandomForestClassifier(n_estimators=50, n_jobs=1)
    rf.fit(X_train, y_train)

    print('DONE')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
