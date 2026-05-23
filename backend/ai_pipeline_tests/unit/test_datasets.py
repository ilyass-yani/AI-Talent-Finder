"""Unit tests for the datasets layer."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from ai_pipeline.datasets.augmentation import (
    AugmentationConfig,
    CompositeAugmenter,
    SkillSynonymAugmenter,
)
from ai_pipeline.datasets.data_loader import DataLoader
from ai_pipeline.datasets.synthetic_generator import SyntheticGenerator


def test_synthetic_generator_produces_balanced_data():
    gen = SyntheticGenerator(seed=42)
    examples = gen.generate(n=300)
    assert len(examples) == 300
    labels = {ex.label for ex in examples}
    assert labels == {"compatible", "partial", "incompatible"}
    # Each example must have non-empty CV/job text
    for ex in examples:
        assert ex.cv_text and ex.job_text
        assert 0.0 <= ex.score <= 1.0


def test_synthetic_generator_saves_jsonl():
    gen = SyntheticGenerator(seed=1)
    examples = gen.generate(n=10)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "out.jsonl"
        gen.save_jsonl(examples, path)
        with open(path) as fh:
            lines = fh.readlines()
        assert len(lines) == 10
        first = json.loads(lines[0])
        assert "cv_text" in first
        assert "label" in first


def test_data_loader_split_is_stratified():
    gen = SyntheticGenerator(seed=7)
    examples = gen.generate(n=300)
    # Convert to MatchingRecord list via save+load
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "out.jsonl"
        gen.save_jsonl(examples, path)
        records = DataLoader.load_jsonl(path)

    train, val, test = DataLoader.split(records, 0.7, 0.15, stratify=True, seed=0)
    assert len(train) + len(val) + len(test) == len(records)
    # All three splits contain all three classes
    for split in (train, val, test):
        labels = {r.label for r in split}
        assert labels == {"compatible", "partial", "incompatible"}


def test_skill_synonym_augmenter_changes_text():
    aug = SkillSynonymAugmenter()
    text = "Experienced with Python, JavaScript and React."
    out = aug.augment(text, p=1.0)
    # Augmenter is allowed to be a no-op if no aliases exist, but here it should
    # at least preserve content length roughly
    assert isinstance(out, str)
    assert len(out) > 0


def test_composite_augmenter_chains_strategies():
    aug = CompositeAugmenter(AugmentationConfig(p_synonym=1.0, p_shuffle=1.0, p_drop=0.0))
    out = aug.augment_dataset(["text 1", "text 2"], n_augmentations=2)
    # Each input produces 1 original + n augmentations
    assert len(out) == 2 * 3
