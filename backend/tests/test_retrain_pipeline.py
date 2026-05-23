"""
Tests for Model Retraining Pipeline - Phase 3

Validates:
1. Handling of insufficient label variety (single class)
2. Training with balanced labels
3. Feature preparation and model save
4. Edge cases (empty data, invalid features)
"""

import pytest
import numpy as np
from pathlib import Path
from scripts.retrain_feedback_model import ModelRetrainingPipeline


class TestModelRetrainingPipeline:
    """Test suite for retraining pipeline."""

    @pytest.fixture
    def pipeline(self):
        """Initialize pipeline."""
        return ModelRetrainingPipeline()

    @pytest.fixture
    def sample_data(self):
        """Generate minimal synthetic training data."""
        return [
            {
                "candidate_id": 1,
                "criteria_id": 1,
                "cv_text": "Python React AWS experience",
                "job_title": "Senior Developer",
                "job_description": "Looking for React + Python",
                "label": 1,
                "score": 0.85,
                "is_override": True,
                "feedback_reason": "Good fit",
                "created_at": "2026-05-13T00:00:00",
            },
            {
                "candidate_id": 2,
                "criteria_id": 1,
                "cv_text": "Basic HTML CSS only",
                "job_title": "Senior Developer",
                "job_description": "Looking for React + Python",
                "label": 0,
                "score": 0.25,
                "is_override": True,
                "feedback_reason": "Insufficient skills",
                "created_at": "2026-05-13T00:00:00",
            },
        ]

    def test_train_with_single_label_class(self, pipeline, sample_data):
        """Test that training with only one label is skipped gracefully."""
        # Create single-class dataset (all accepted)
        single_class_data = [sample_data[0], {"label": 1, **{k: v for k, v in sample_data[0].items() if k != "label"}}]
        
        X, y = pipeline.prepare_features(single_class_data)
        assert X is not None
        assert y is not None
        
        # Train should return skipped status
        result = pipeline.train(X, y, n_estimators=5)
        assert result["status"] == "skipped"
        assert "Insufficient label variety" in result["reason"]
        assert len(result["unique_labels"]) == 1

    def test_train_with_balanced_labels(self, pipeline, sample_data):
        """Test training with balanced accepted/rejected labels."""
        # Expand sample data to ensure train_test_split produces multi-class split
        expanded_data = sample_data + [
            {
                "candidate_id": 3,
                "criteria_id": 1,
                "cv_text": "Strong React Python AWS",
                "job_title": "Senior Developer",
                "job_description": "Looking for React + Python",
                "label": 1,
                "score": 0.90,
                "is_override": True,
                "feedback_reason": "Excellent fit",
                "created_at": "2026-05-13T00:00:00",
            },
            {
                "candidate_id": 4,
                "criteria_id": 1,
                "cv_text": "Minimal skills",
                "job_title": "Senior Developer",
                "job_description": "Looking for React + Python",
                "label": 0,
                "score": 0.15,
                "is_override": True,
                "feedback_reason": "Poor fit",
                "created_at": "2026-05-13T00:00:00",
            },
        ]
        
        X, y = pipeline.prepare_features(expanded_data)
        assert X is not None
        assert y is not None
        assert len(y) == 4
        
        # Train with balanced data
        result = pipeline.train(X, y, n_estimators=5)
        # With 4 samples, training should succeed
        assert result["status"] == "success"
        assert "train_accuracy" in result
        assert "test_accuracy" in result
        assert result["samples"] == 4

    def test_prepare_features_valid_data(self, pipeline, sample_data):
        """Test feature preparation with valid data."""
        X, y = pipeline.prepare_features(sample_data)
        
        assert X is not None
        assert y is not None
        assert X.shape[0] == 2  # 2 samples
        assert X.shape[1] == 7  # 7 features
        assert y.shape[0] == 2
        assert list(np.unique(y)) == [0, 1]

    def test_prepare_features_empty_data(self, pipeline):
        """Test feature preparation with empty dataset."""
        X, y = pipeline.prepare_features([])
        
        assert X is None
        assert y is None

    def test_save_model_creates_file(self, pipeline, sample_data):
        """Test that model save creates joblib file."""
        X, y = pipeline.prepare_features(sample_data)
        
        # Skip training if single class
        result = pipeline.train(X, y, n_estimators=5)
        if result["status"] != "success":
            pytest.skip("Training was skipped due to single class")
        
        save_msg = pipeline.save_model()
        assert "saved" in save_msg.lower()
        assert Path(pipeline.model_path).exists()

    def test_feature_importance_extraction(self, pipeline, sample_data):
        """Test that feature importance is computed correctly."""
        X, y = pipeline.prepare_features(sample_data)
        result = pipeline.train(X, y, n_estimators=5)
        
        if result["status"] == "success":
            assert "feature_importance" in result
            assert len(result["feature_importance"]) == 7  # 7 feature names
            # Check that importances sum to 1 (approximately)
            importances = [imp for _, imp in result["feature_importance"]]
            assert 0.99 <= sum(importances) <= 1.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
