"""Siamese / fine-tunable sentence-transformers training scaffold.

This script trains a sentence-transformers model (Siamese) on pairs with labels.
It is guarded (imports only when available) and saves model to `models/siamese`.
"""
import argparse
import os

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="CSV with columns cv_text,job_text,label")
    parser.add_argument("--out", default="models/siamese")
    args = parser.parse_args()

    missing = []
    try:
        from sentence_transformers import SentenceTransformer, InputExample, losses
        from torch.utils.data import DataLoader
    except Exception:
        print("sentence-transformers not installed. Install via: pip install sentence-transformers")
        return

    import pandas as pd
    df = pd.read_csv(args.data)
    examples = []
    for _, row in df.iterrows():
        label = float(row.get("label", 0))
        examples.append(InputExample(texts=[row["cv_text"], row["job_text"]], label=label))

    model = SentenceTransformer('all-MiniLM-L6-v2')
    train_loader = DataLoader(examples, shuffle=True, batch_size=16)
    loss = losses.CosineSimilarityLoss(model)

    os.makedirs(args.out, exist_ok=True)
    model.fit(train_objectives=[(train_loader, loss)], epochs=1, warmup_steps=10)
    model.save(args.out)
    print("Saved siamese model to", args.out)


if __name__ == "__main__":
    main()
