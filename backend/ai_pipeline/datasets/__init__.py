"""Dataset utilities: real CV loading, synthetic generation, augmentation."""
from .augmentation import (
    AugmentationConfig,
    CompositeAugmenter,
    SectionShuffler,
    SentenceDropper,
    SkillSynonymAugmenter,
)
from .data_loader import DataLoader, MatchingRecord
from .real_cv_loader import CVRecord, RealCVLoader
from .real_cv_pair_builder import RealCVExample, RealCVPairBuilder
from .synthetic_generator import JOB_ARCHETYPES, SyntheticExample, SyntheticGenerator

__all__ = [
    # --- Données réelles (nouveau) ---
    "RealCVLoader",
    "CVRecord",
    "RealCVPairBuilder",
    "RealCVExample",
    # --- Données synthétiques (legacy) ---
    "SyntheticGenerator",
    "SyntheticExample",
    "JOB_ARCHETYPES",
    # --- Chargement & augmentation ---
    "DataLoader",
    "MatchingRecord",
    "CompositeAugmenter",
    "AugmentationConfig",
    "SkillSynonymAugmenter",
    "SectionShuffler",
    "SentenceDropper",
]
