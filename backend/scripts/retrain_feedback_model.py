"""Phase 3: Model Retraining Pipeline - Learn from recruiter feedback."""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import argparse

try:
    import numpy as np
    import pandas as pd
    from sklearn.model_selection import train_test_split
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    import joblib
except ImportError:
    np = None
    pd = None


class ModelRetrainingPipeline:
    """
    Retrain matching model using recruiter feedback.
    
    Incorporates:
    - Recruiter overrides as training signals
    - Corrected labels from hiring outcomes
    - Feedback-based feature importance
    """

    def __init__(self, model_path: Optional[Path] = None):
        """Initialize retraining pipeline."""
        self.model_path = model_path or (
            Path(__file__).resolve().parents[4] / "models" / "final_match_model.joblib"
        )
        self.model = None
        self.scaler = None
        self.feature_names = None
        self._load_model()

    def _load_model(self) -> None:
        """Load existing model bundle."""
        if self.model_path.exists() and joblib:
            try:
                bundle = joblib.load(self.model_path)
                self.model = bundle.get("model")
                self.scaler = bundle.get("scaler")
                self.feature_names = bundle.get("feature_names", [])
                print(f"Loaded model from {self.model_path}")
            except Exception as e:
                print(f"Warning: Could not load model: {e}")

    def prepare_features(self, retraining_data: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare features and labels from feedback data.
        
        Returns:
            X (features), y (labels)
        """
        if not np:
            print("NumPy not available; cannot prepare features")
            return None, None

        features_list = []
        labels = []

        for record in retraining_data:
            try:
                # Extract features from CV and job description
                feature_vector = self._extract_features(record)
                features_list.append(feature_vector)

                # Label: 1 = accepted by recruiter, 0 = rejected
                label = 1 if record.get("label") == 1 else 0
                labels.append(label)
            except Exception as e:
                print(f"Warning: Could not process record: {e}")
                continue

        if not features_list:
            print("No valid features extracted")
            return None, None

        X = np.array(features_list)
        y = np.array(labels)
        return X, y

    def _extract_features(self, record: Dict) -> List[float]:
        """Extract feature vector from candidate+job record."""
        cv_text = record.get("cv_text", "").lower()
        job_text = record.get("job_description", "").lower()

        features = []

        # 1. Skill match ratio
        job_skills = self._parse_skills(job_text)
        cv_skills = self._parse_skills(cv_text)
        skill_overlap = (
            len(set(cv_skills) & set(job_skills)) / len(job_skills)
            if job_skills
            else 0
        )
        features.append(skill_overlap)

        # 2. Experience years (heuristic)
        experiences = cv_text.count("years of experience") + cv_text.count("yrs")
        features.append(min(experiences / 10, 1.0))  # Normalize to 0-1

        # 3. Education level
        edu_score = 0
        if "phd" in cv_text or "doctorate" in cv_text:
            edu_score = 1.0
        elif "master" in cv_text or "m.s." in cv_text:
            edu_score = 0.8
        elif "bachelor" in cv_text or "b.s." in cv_text:
            edu_score = 0.6
        features.append(edu_score)

        # 4. Language proficiency
        lang_count = sum(
            1
            for lang in ["fluent", "native", "bilingual", "multilingual"]
            if lang in cv_text
        )
        features.append(min(lang_count / 3, 1.0))

        # 5. Certification count
        certs = sum(
            1
            for cert in [
                "aws",
                "gcp",
                "azure",
                "kubernetes",
                "docker",
                "certified",
            ]
            if cert in cv_text
        )
        features.append(min(certs / 3, 1.0))

        # 6. Company tier (heuristic)
        prestigious_companies = [
            "google",
            "microsoft",
            "apple",
            "amazon",
            "facebook",
            "ibm",
            "netflix",
        ]
        company_tier = (
            1.0
            if any(company in cv_text for company in prestigious_companies)
            else 0.5
        )
        features.append(company_tier)

        # 7. Model score from record
        model_score = record.get("score", 0.5)
        features.append(model_score)

        return features

    def _parse_skills(self, text: str) -> List[str]:
        """Extract skill mentions from text."""
        skill_keywords = [
            "python",
            "javascript",
            "java",
            "c++",
            "docker",
            "kubernetes",
            "aws",
            "react",
            "angular",
            "sql",
            "nosql",
            "git",
            "jenkins",
            "ci/cd",
        ]
        return [skill for skill in skill_keywords if skill in text.lower()]

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        test_size: float = 0.2,
        n_estimators: int = 100,
    ) -> Dict[str, Any]:
        """
        Retrain model on feedback data.
        
        Args:
            X: Feature matrix
            y: Labels (1=accepted, 0=rejected)
            test_size: Train/test split ratio
            n_estimators: Number of boosting rounds
        
        Returns:
            Metrics dictionary
        """
        if X is None or y is None or not np:
            return {"status": "error", "message": "Invalid data or NumPy not available"}

        # Validate label variety before training
        try:
            unique_labels = np.unique(y)
        except Exception:
            return {"status": "error", "message": "Could not determine unique labels"}

        if len(unique_labels) < 2:
            return {
                "status": "skipped",
                "reason": "Insufficient label variety: need at least 2 classes to train",
                "unique_labels": unique_labels.tolist() if hasattr(unique_labels, 'tolist') else list(unique_labels),
            }

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )

        # Validate training split has multiple classes
        train_unique = np.unique(y_train)
        if len(train_unique) < 2:
            return {
                "status": "skipped",
                "reason": f"Training set resulted in single class after split. Train classes: {train_unique.tolist()}",
                "unique_labels": train_unique.tolist() if hasattr(train_unique, 'tolist') else list(train_unique),
            }

        # Scale features
        if not self.scaler:
            self.scaler = StandardScaler()
            X_train = self.scaler.fit_transform(X_train)
        else:
            X_train = self.scaler.transform(X_train)

        X_test = self.scaler.transform(X_test)

        # Train model
        print(f"Training model on {len(X_train)} samples...")
        model = GradientBoostingClassifier(
            n_estimators=n_estimators,
            learning_rate=0.05,
            max_depth=5,
            random_state=42,
        )
        model.fit(X_train, y_train)

        # Evaluate
        train_score = model.score(X_train, y_train)
        test_score = model.score(X_test, y_test)

        # Get feature importance
        feature_names = [
            "skill_match_ratio",
            "experience_years",
            "education_level",
            "language_proficiency",
            "certifications",
            "company_tier",
            "model_score",
        ]
        feature_importance = list(zip(feature_names, model.feature_importances_))
        feature_importance.sort(key=lambda x: x[1], reverse=True)

        metrics = {
            "status": "success",
            "train_accuracy": float(train_score),
            "test_accuracy": float(test_score),
            "samples": len(X),
            "feature_importance": feature_importance,
            "trained_at": datetime.utcnow().isoformat(),
        }

        self.model = model
        return metrics

    def save_model(self, output_path: Optional[Path] = None) -> str:
        """Save retrained model."""
        if not self.model:
            return "No model to save"

        output_path = output_path or self.model_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if joblib:
            try:
                bundle = {
                    "model": self.model,
                    "scaler": self.scaler,
                    "feature_names": [
                        "skill_match_ratio",
                        "experience_years",
                        "education_level",
                        "language_proficiency",
                        "certifications",
                        "company_tier",
                        "model_score",
                    ],
                    "trained_at": datetime.utcnow().isoformat(),
                    "version": "phase3_feedback_v1",
                }
                joblib.dump(bundle, output_path)
                return f"Model saved to {output_path}"
            except Exception as e:
                return f"Error saving model: {e}"
        
        return "Joblib not available"

    def evaluate_on_feedback(
        self, feedback_records: List[Dict]
    ) -> Dict[str, Any]:
        """
        Evaluate model improvements from retraining.
        
        Compare model predictions vs recruiter decisions.
        """
        if not self.model or not feedback_records:
            return {"status": "error"}

        correct_before = 0
        correct_after = 0

        for record in feedback_records:
            X, _ = self.prepare_features([record])
            if X is None:
                continue

            # Model prediction (before retraining)
            model_pred = record.get("model_predicted_decision", "rejected")
            recruiter_decision = record.get("recruiter_decision", "rejected")

            if model_pred == recruiter_decision:
                correct_before += 1

            # New prediction
            try:
                X_scaled = self.scaler.transform(X) if self.scaler else X
                new_pred_prob = self.model.predict_proba(X_scaled)[0][1]
                new_pred = "accepted" if new_pred_prob >= 0.5 else "rejected"

                if new_pred == recruiter_decision:
                    correct_after += 1
            except Exception:
                pass

        accuracy_before = correct_before / len(feedback_records)
        accuracy_after = correct_after / len(feedback_records)
        improvement = accuracy_after - accuracy_before

        return {
            "status": "success",
            "accuracy_before": round(accuracy_before, 3),
            "accuracy_after": round(accuracy_after, 3),
            "improvement": round(improvement, 3),
            "samples_evaluated": len(feedback_records),
        }

    def export_retraining_report(self, metrics: Dict, output_dir: Path) -> str:
        """Export retraining metrics report."""
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / f"retrain_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(report_path, "w") as f:
                json.dump(metrics, f, indent=2, default=str)
            return str(report_path)
        except Exception as e:
            return f"Error exporting report: {e}"


def main():
    """CLI for model retraining."""
    parser = argparse.ArgumentParser(
        description="Retrain matching model using recruiter feedback"
    )
    parser.add_argument(
        "--feedback-data",
        type=str,
        required=True,
        help="Path to feedback data JSON/JSONL",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./models",
        help="Output directory for retrained model",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=100,
        help="Number of boosting rounds",
    )
    parser.add_argument(
        "--evaluate-only",
        action="store_true",
        help="Evaluate only, don't retrain",
    )
    args = parser.parse_args()

    # Load feedback data
    feedback_data = []
    try:
        with open(args.feedback_data) as f:
            for line in f:
                feedback_data.append(json.loads(line))
    except FileNotFoundError:
        print(f"Error: {args.feedback_data} not found")
        return

    print(f"Loaded {len(feedback_data)} feedback records")

    # Initialize pipeline
    pipeline = ModelRetrainingPipeline()

    if args.evaluate_only:
        # Evaluate without retraining
        eval_metrics = pipeline.evaluate_on_feedback(feedback_data)
        print("\n=== Evaluation Results ===")
        print(json.dumps(eval_metrics, indent=2))
    else:
        # Prepare and retrain
        X, y = pipeline.prepare_features(feedback_data)
        if X is not None:
            metrics = pipeline.train(X, y, n_estimators=args.epochs)
            print("\n=== Training Metrics ===")
            print(json.dumps(metrics, indent=2, default=str))

            # Save model
            save_msg = pipeline.save_model()
            print(f"\n{save_msg}")

            # Export report
            report_path = pipeline.export_retraining_report(
                metrics, Path(args.output_dir)
            )
            print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
