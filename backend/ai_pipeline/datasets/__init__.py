"""Dataset utilities: synthetic generation, loading, augmentation."""
from .augmentation import (
    AugmentationConfig,
    CompositeAugmenter,
    SectionShuffler,
    SentenceDropper,
    SkillSynonymAugmenter,
)
from .data_loader import DataLoader, MatchingRecord
from .synthetic_generator import JOB_ARCHETYPES, SyntheticExample, SyntheticGenerator

__all__ = [
    "SyntheticGenerator",
    "SyntheticExample",
    "JOB_ARCHETYPES",
    "DataLoader",
    "MatchingRecord",
    "CompositeAugmenter",
    "AugmentationConfig",
    "SkillSynonymAugmenter",
    "SectionShuffler",
    "SentenceDropper",
]
