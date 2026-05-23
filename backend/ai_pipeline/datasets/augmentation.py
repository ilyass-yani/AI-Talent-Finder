"""Lightweight text augmentation for matching training data.

Provides three deterministic augmentation strategies that preserve semantic
content while increasing surface-form diversity:

  * :class:`SkillSynonymAugmenter` — swap canonical skills with their aliases
  * :class:`SectionShuffler` — shuffle independent CV sections (experiences,
    education) without breaking structure
  * :class:`SentenceDropper` — drop a random subset of sentences
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Dict, List

from ..preprocessing.skill_normalizer import SkillNormalizer


@dataclass
class AugmentationConfig:
    p_synonym: float = 0.4
    p_shuffle: float = 0.3
    p_drop: float = 0.2
    drop_ratio: float = 0.1
    seed: int = 42


class SkillSynonymAugmenter:
    """Replace canonical skill names with random aliases."""

    def __init__(self, normalizer: SkillNormalizer = None) -> None:
        self.normalizer = normalizer or SkillNormalizer()
        # Build canonical → aliases map
        self._reverse_map: Dict[str, List[str]] = {}
        for alias, canonical in self.normalizer.alias_map.items():
            self._reverse_map.setdefault(canonical, []).append(alias)

    def augment(self, text: str, p: float = 0.4, rng: random.Random = None) -> str:
        rng = rng or random.Random()
        out = text
        for canonical, aliases in self._reverse_map.items():
            if not aliases or rng.random() > p:
                continue
            alias = rng.choice(aliases)
            # Word-boundary substitution to avoid partial matches
            out = re.sub(rf"\b{re.escape(canonical)}\b", alias, out, flags=re.IGNORECASE)
        return out


class SectionShuffler:
    """Shuffle bullet-pointed list items within a paragraph."""

    def augment(self, text: str, p: float = 0.3, rng: random.Random = None) -> str:
        rng = rng or random.Random()
        if rng.random() > p:
            return text
        lines = text.split("\n")
        # Identify bullet runs (consecutive lines starting with "- ")
        out_lines: List[str] = []
        buffer: List[str] = []
        for line in lines:
            if line.lstrip().startswith(("- ", "• ", "* ")):
                buffer.append(line)
            else:
                if buffer:
                    rng.shuffle(buffer)
                    out_lines.extend(buffer)
                    buffer = []
                out_lines.append(line)
        if buffer:
            rng.shuffle(buffer)
            out_lines.extend(buffer)
        return "\n".join(out_lines)


class SentenceDropper:
    """Randomly drop a fraction of non-bullet sentences (CV padding text)."""

    def augment(
        self,
        text: str,
        p: float = 0.2,
        drop_ratio: float = 0.1,
        rng: random.Random = None,
    ) -> str:
        rng = rng or random.Random()
        if rng.random() > p:
            return text
        lines = text.split("\n")
        out = []
        for line in lines:
            # Never drop bullets (they often carry skills)
            if line.lstrip().startswith(("- ", "• ", "* ")):
                out.append(line)
                continue
            if rng.random() < drop_ratio:
                continue
            out.append(line)
        return "\n".join(out)


class CompositeAugmenter:
    """Chain all augmenters with configurable probabilities."""

    def __init__(self, config: AugmentationConfig = None) -> None:
        self.config = config or AugmentationConfig()
        self.synonym = SkillSynonymAugmenter()
        self.shuffler = SectionShuffler()
        self.dropper = SentenceDropper()
        self.rng = random.Random(self.config.seed)

    def augment(self, text: str) -> str:
        out = self.synonym.augment(text, p=self.config.p_synonym, rng=self.rng)
        out = self.shuffler.augment(out, p=self.config.p_shuffle, rng=self.rng)
        out = self.dropper.augment(
            out,
            p=self.config.p_drop,
            drop_ratio=self.config.drop_ratio,
            rng=self.rng,
        )
        return out

    def augment_dataset(self, texts: List[str], n_augmentations: int = 1) -> List[str]:
        out: List[str] = []
        for t in texts:
            out.append(t)
            for _ in range(n_augmentations):
                out.append(self.augment(t))
        return out
