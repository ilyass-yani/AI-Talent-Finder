"""
Training script for BERT embeddings fine-tuning for CV-Job matching
Usage:
    python train/train_bert_embeddings.py --cv-data cv_samples.json --job-data jobs.json
"""

import argparse
import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_module.matching.bert_embeddings import BertEmbedder, BertMatcher
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_json_data(path: str) -> List:
    """Load data from JSON file."""
    if not Path(path).exists():
        logger.warning(f"⚠️ File not found: {path}")
        return []
    
    with open(path) as f:
        return json.load(f)


def generate_synthetic_pairs() -> Tuple[List[str], List[str]]:
    """Generate synthetic CV and job texts for demonstration."""
    logger.info("📊 Generating synthetic training data...")
    
    cv_samples = [
        "Senior Python Developer with 8 years experience. Expertise in FastAPI, Django, PostgreSQL, Docker, Kubernetes. Led team of 5 engineers.",
        "Full Stack Developer - React, Node.js, MongoDB. 4 years building scalable web applications. Passionate about clean code.",
        "Data Scientist with PhD in ML. TensorFlow, PyTorch, Scikit-learn. Published papers on NLP. 6 years industry experience.",
        "DevOps Engineer specialized in AWS, Kubernetes, Terraform. Automated CI/CD pipelines. 5 years infrastructure automation.",
        "Java Backend Developer with Spring Boot expertise. Microservices architecture, event-driven systems. 7 years experience.",
    ]
    
    job_descriptions = [
        "Senior Python Developer - FastAPI, PostgreSQL required. Team lead. Docker/K8s nice-to-have.",
        "Full Stack React/Node Developer - 3+ years. MongoDB/SQL experience required.",
        "ML Engineer - TensorFlow/PyTorch. Research publication history preferred.",
        "DevOps/SRE - AWS/Kubernetes, Terraform infrastructure as code required.",
        "Senior Java Spring Boot Engineer - Microservices, event streaming (Kafka)",
    ]
    
    return cv_samples * 10, job_descriptions * 10  # Repeat for training


def evaluate_embeddings(embedder: BertEmbedder, cv_texts: List[str], job_texts: List[str]) -> Dict:
    """Evaluate embedding quality."""
    logger.info("📊 Evaluating embedding quality...")
    
    # Generate embeddings
    cv_embeddings = embedder.embed_batch(cv_texts[:5])
    job_embeddings = embedder.embed_batch(job_texts[:5])
    
    # Compute similarities
    similarities = []
    for cv_emb in cv_embeddings:
        for job_emb in job_embeddings:
            sim = embedder.cosine_similarity(cv_emb, job_emb)
            similarities.append(sim)
    
    # Stats
    similarities = np.array(similarities)
    
    return {
        "mean_similarity": float(similarities.mean()),
        "std_similarity": float(similarities.std()),
        "min_similarity": float(similarities.min()),
        "max_similarity": float(similarities.max()),
        "embedding_dim": embedder.embedding_dim,
    }


def save_embeddings(embeddings: np.ndarray, labels: List[str], output_path: str):
    """Save embeddings and labels for later use."""
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save embeddings
    embeddings_file = output_dir / "embeddings.npy"
    np.save(embeddings_file, embeddings)
    
    # Save labels
    labels_file = output_dir / "labels.json"
    with open(labels_file, "w") as f:
        json.dump(labels, f)
    
    logger.info(f"💾 Saved embeddings to {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Train BERT embeddings for CV-Job matching")
    parser.add_argument("--cv-data", type=str, default=None, help="Path to CV samples JSON")
    parser.add_argument("--job-data", type=str, default=None, help="Path to job descriptions JSON")
    parser.add_argument("--model", type=str, default="distilbert-base-multilingual-cased", help="BERT model name")
    parser.add_argument("--output", type=str, default="models/bert_embeddings", help="Output directory")
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic data for demo")
    parser.add_argument("--build-index", action="store_true", help="Build FAISS index")
    
    args = parser.parse_args()
    
    # Load or generate data
    if args.synthetic or (not args.cv_data and not args.job_data):
        logger.info("🔧 Using synthetic data for demonstration...")
        cv_texts, job_texts = generate_synthetic_pairs()
    else:
        cv_texts = load_json_data(args.cv_data) if args.cv_data else []
        job_texts = load_json_data(args.job_data) if args.job_data else []
    
    if not cv_texts or not job_texts:
        logger.error("No data available for training")
        return
    
    logger.info(f"📊 Training with {len(cv_texts)} CVs and {len(job_texts)} jobs")
    
    # Initialize embedder
    logger.info(f"🚀 Initializing {args.model}...")
    embedder = BertEmbedder(model_name=args.model)
    
    # Generate embeddings
    logger.info("📊 Generating CV embeddings...")
    cv_embeddings = embedder.embed_batch(cv_texts)
    
    logger.info("📊 Generating job embeddings...")
    job_embeddings = embedder.embed_batch(job_texts)
    
    # Evaluate
    eval_result = evaluate_embeddings(embedder, cv_texts, job_texts)
    logger.info(f"📈 Evaluation results:")
    for key, value in eval_result.items():
        logger.info(f"   {key}: {value:.4f}")
    
    # Save embeddings
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)
    
    np.save(output_path / "cv_embeddings.npy", cv_embeddings)
    np.save(output_path / "job_embeddings.npy", job_embeddings)
    
    with open(output_path / "cv_samples.json", "w") as f:
        json.dump(cv_texts, f)
    
    with open(output_path / "job_samples.json", "w") as f:
        json.dump(job_texts, f)
    
    # Build FAISS index if requested
    if args.build_index:
        logger.info("🔍 Building FAISS index...")
        matcher = BertMatcher(model_name=args.model)
        matcher.build_index(job_texts)
        logger.info("✅ FAISS index built")
    
    # Save config
    config = {
        "model": args.model,
        "embedding_dim": eval_result["embedding_dim"],
        "num_cv_samples": len(cv_texts),
        "num_job_samples": len(job_texts),
        "evaluation": eval_result,
    }
    
    with open(output_path / "config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    logger.info(f"✅ Training completed. Outputs saved to {args.output}")
    logger.info(f"   - CV embeddings: cv_embeddings.npy ({cv_embeddings.shape})")
    logger.info(f"   - Job embeddings: job_embeddings.npy ({job_embeddings.shape})")
    logger.info(f"   - Model config: config.json")


if __name__ == "__main__":
    main()
