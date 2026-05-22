from backend.app.services.faiss_index import FaissIndex
import pandas as pd
import os
import sys

try:
    os.makedirs('models/faiss', exist_ok=True)
    csv_path = 'data/training_pairs.csv'
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found")
        sys.exit(1)
        
    df = pd.read_csv(csv_path)
    if 'cv_text' in df.columns:
        texts = df['cv_text'].fillna('').astype(str).tolist()[:1000]
    else:
        texts = df.iloc[:,0].fillna('').astype(str).tolist()[:1000]

    print(f'Encoding {len(texts)} documents...')
    fi = FaissIndex()
    fi.build_index(texts)
    fi.save('models/faiss/index', texts=texts)
    print('INDEX_SAVED')
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
