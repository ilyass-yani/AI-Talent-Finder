"""
Training script for Mistral fine-tuning with recruiter feedback data
Usage:
    python train/train_mistral_finetuner.py --data path/to/feedback.jsonl --output models/mistral_finetuned
"""

import argparse
import json
import logging
from pathlib import Path
from typing import List, Dict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_module.nlp.mistral_finetuner import MistralFinetuner, TrainingConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_training_data(data_path: str) -> List[Dict]:
    """Load training data from JSONL or JSON file."""
    path = Path(data_path)
    
    if not path.exists():
        logger.error(f"Data file not found: {data_path}")
        return []
    
    data = []
    
    if path.suffix == ".jsonl":
        with open(path) as f:
            for line in f:
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    elif path.suffix == ".json":
        with open(path) as f:
            file_data = json.load(f)
            if isinstance(file_data, list):
                data = file_data
            else:
                data = [file_data]
    
    else:
        logger.error(f"Unsupported file format: {path.suffix}")
        return []
    
    logger.info(f"✅ Loaded {len(data)} training examples from {data_path}")
    return data


def generate_synthetic_training_data() -> List[Dict]:
    """Generate synthetic training data if no real data available."""
    logger.info("📊 Generating synthetic training data...")
    
    templates = [
        {
            "context": "Job: Senior Python Developer | Skills: Python, FastAPI, Docker | Experience: 5+ years",
            "question": "Is this candidate qualified?",
            "answer": "Yes, the candidate has all required skills and sufficient experience.",
        },
        {
            "context": "Candidate: Jane Smith | Skills: JavaScript, React, Node.js | Experience: 3 years",
            "question": "What is the skill match for Frontend Developer role?",
            "answer": "Strong match. The candidate has expertise in React and Node.js, which are primary requirements.",
        },
        {
            "context": "Job: Data Scientist | Required: Python, SQL, TensorFlow | Candidate: John has Python and SQL but no TensorFlow",
            "question": "Should we reject this candidate?",
            "answer": "Not necessarily. TensorFlow can be learned. The core skills are there. Recommend for interview.",
        },
        {
            "context": "Candidate: Alex | Skills: Java, Spring, Microservices | Gap: No cloud deployment experience",
            "question": "What's the biggest gap?",
            "answer": "Cloud deployment experience (AWS/GCP). Recommend training or pair with cloud expert.",
        },
        {
            "context": "Role: Full Stack Developer | Candidate has: Frontend (React), Backend (Python) | Missing: DevOps",
            "question": "Is DevOps critical?",
            "answer": "DevOps is valuable but not critical for full stack. Strong frontend/backend skills compensate.",
        },
    ]
    
    return templates * 20  # Repeat to create 100 examples


def main():
    parser = argparse.ArgumentParser(description="Fine-tune Mistral for recruiter chatbot")
    parser.add_argument("--data", type=str, default=None, help="Path to training data (JSONL or JSON)")
    parser.add_argument("--output", type=str, default="models/mistral_finetuned", help="Output directory for fine-tuned model")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=4, help="Training batch size")
    parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate")
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic data if real data not available")
    
    args = parser.parse_args()
    
    # Load data
    if args.data and Path(args.data).exists():
        training_data = load_training_data(args.data)
    elif args.synthetic:
        training_data = generate_synthetic_training_data()
    else:
        logger.error("No training data provided and --synthetic not set")
        return
    
    if not training_data:
        logger.error("No training data available")
        return
    
    # Create config
    config = TrainingConfig(
        output_dir=args.output,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        learning_rate=args.lr,
    )
    
    # Initialize and train
    logger.info("🚀 Starting Mistral fine-tuning...")
    
    finetuner = MistralFinetuner(config)
    
    # Load model
    finetuner.load_model()
    
    # Apply LoRA
    finetuner.apply_lora()
    
    # Train
    result = finetuner.train(training_data)
    
    # Save
    finetuner.save()
    
    logger.info(f"✅ Fine-tuning completed. Model saved to {args.output}")
    logger.info(f"Train loss: {result.get('train_loss', 'N/A')}")


if __name__ == "__main__":
    main()
