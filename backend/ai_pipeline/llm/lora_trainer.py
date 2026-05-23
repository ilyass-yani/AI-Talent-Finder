"""LoRA / QLoRA / DoRA Fine-tuning pour matching CV/Job.

Pipeline complet :
    1. Charge le modèle de base (Mistral / Qwen / Llama) avec quantization 4-bit
    2. Configure LoRA / QLoRA / DoRA via PEFT
    3. Charge le dataset d'instructions
    4. Lance SFTTrainer (HuggingFace TRL) avec gradient checkpointing
    5. Sauvegarde l'adapter LoRA (quelques MB) + tokenizer

Comparaison :
    - LoRA   : ajoute des matrices low-rank ΔW = B·A. Entraînable, base figée.
    - QLoRA  : LoRA + base quantisée en 4-bit (NF4) → -75% VRAM
    - DoRA   : décompose W en magnitude + direction, fine-tune seulement la direction
               via LoRA → +1-2% en moyenne, même coût

Choix recommandé pour ce projet :
    - QLoRA sur Qwen2.5-1.5B  → ~6 GB VRAM, ~2h sur RTX 3060 12GB
    - QLoRA sur Mistral-7B    → ~12 GB VRAM, ~6h sur RTX 4090

Usage :
    >>> trainer = LoRATrainer(use_qlora=True, use_dora=False)
    >>> trainer.setup_model()
    >>> trainer.train(train_dataset, eval_dataset)
    >>> trainer.save("models/qlora_cv_matcher")
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from ai_pipeline.config import LLMConfig, get_config

logger = logging.getLogger(__name__)


def _ensure_dependencies():
    """Vérifie que les dépendances lourdes sont installées."""
    missing = []
    try:
        import torch  # noqa: F401
    except ImportError:
        missing.append("torch")
    try:
        import transformers  # noqa: F401
    except ImportError:
        missing.append("transformers")
    try:
        import peft  # noqa: F401
    except ImportError:
        missing.append("peft")
    try:
        import bitsandbytes  # noqa: F401
    except ImportError:
        missing.append("bitsandbytes")
    try:
        import trl  # noqa: F401
    except ImportError:
        missing.append("trl")
    try:
        import datasets  # noqa: F401
    except ImportError:
        missing.append("datasets")

    if missing:
        raise ImportError(
            f"Missing dependencies for LLM fine-tuning: {', '.join(missing)}\n"
            f"Install with: pip install {' '.join(missing)}"
        )


class LoRATrainer:
    """Fine-tune un LLM avec LoRA / QLoRA / DoRA pour matching CV/Job."""

    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        use_qlora: bool = True,
        use_dora: bool = False,
        use_rslora: bool = True,
    ) -> None:
        self.config = config or get_config().llm
        self.use_qlora = use_qlora
        self.use_dora = use_dora
        self.use_rslora = use_rslora

        self.model = None
        self.tokenizer = None
        self.peft_model = None

    # ------------------------------------------------------------------ #
    # Setup model + tokenizer
    # ------------------------------------------------------------------ #

    def setup_model(self) -> None:
        _ensure_dependencies()
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        logger.info(f"Loading base model: {self.config.base_model}")

        # ---------- Tokenizer ----------
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config.base_model,
            trust_remote_code=True,
            padding_side="right",  # right pour SFT, left pour génération
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # ---------- Quantization config (QLoRA) ----------
        bnb_config = None
        if self.use_qlora:
            from transformers import BitsAndBytesConfig
            compute_dtype = getattr(torch, self.config.bnb_4bit_compute_dtype)
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type=self.config.bnb_4bit_quant_type,
                bnb_4bit_compute_dtype=compute_dtype,
                bnb_4bit_use_double_quant=self.config.bnb_4bit_use_double_quant,
            )
            logger.info(f"QLoRA enabled: 4-bit NF4, compute dtype = {compute_dtype}")

        # ---------- Model ----------
        torch_dtype = torch.bfloat16 if self.config.bf16 else torch.float16
        self.model = AutoModelForCausalLM.from_pretrained(
            self.config.base_model,
            quantization_config=bnb_config,
            torch_dtype=torch_dtype,
            device_map="auto",
            trust_remote_code=True,
            attn_implementation="eager",  # plus stable que flash-attn sur tous setups
        )

        if self.use_qlora:
            from peft import prepare_model_for_kbit_training
            self.model = prepare_model_for_kbit_training(
                self.model,
                use_gradient_checkpointing=self.config.gradient_checkpointing,
            )

        # ---------- LoRA config ----------
        from peft import LoraConfig, TaskType, get_peft_model

        lora_config = LoraConfig(
            r=self.config.lora_r,
            lora_alpha=self.config.lora_alpha,
            lora_dropout=self.config.lora_dropout,
            bias=self.config.lora_bias,
            task_type=TaskType.CAUSAL_LM,
            target_modules=self.config.lora_target_modules,
            use_rslora=self.use_rslora,           # Rank-Stabilized LoRA
            use_dora=self.use_dora,               # DoRA
        )

        self.peft_model = get_peft_model(self.model, lora_config)
        self.peft_model.print_trainable_parameters()

        logger.info(
            f"PEFT setup complete: LoRA r={self.config.lora_r}, "
            f"alpha={self.config.lora_alpha}, dora={self.use_dora}, "
            f"rslora={self.use_rslora}, target_modules={self.config.lora_target_modules}"
        )

    # ------------------------------------------------------------------ #
    # Training
    # ------------------------------------------------------------------ #

    def train(
        self,
        train_dataset,
        eval_dataset=None,
        output_dir: Optional[str] = None,
    ) -> None:
        if self.peft_model is None:
            self.setup_model()

        from transformers import TrainingArguments
        from trl import SFTConfig, SFTTrainer

        output_dir = output_dir or self.config.output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # SFTConfig est une extension de TrainingArguments avec des params SFT
        sft_config = SFTConfig(
            output_dir=output_dir,
            num_train_epochs=self.config.num_train_epochs,
            per_device_train_batch_size=self.config.per_device_train_batch_size,
            per_device_eval_batch_size=self.config.per_device_eval_batch_size,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            gradient_checkpointing=self.config.gradient_checkpointing,
            optim=self.config.optim,
            learning_rate=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
            warmup_ratio=self.config.warmup_ratio,
            lr_scheduler_type=self.config.lr_scheduler_type,
            max_seq_length=self.config.max_seq_length,
            logging_steps=self.config.logging_steps,
            save_strategy=self.config.save_strategy,
            eval_strategy=self.config.eval_strategy if eval_dataset is not None else "no",
            save_total_limit=self.config.save_total_limit,
            bf16=self.config.bf16,
            fp16=self.config.fp16 and not self.config.bf16,
            seed=self.config.seed,
            report_to="none",
            packing=False,  # packing peut accélérer mais nécessite un masking attentif
            dataset_text_field="text",
        )

        trainer = SFTTrainer(
            model=self.peft_model,
            args=sft_config,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            tokenizer=self.tokenizer,
        )

        logger.info("Starting training...")
        trainer.train()
        logger.info("Training complete.")

        # Sauvegarde finale
        trainer.save_model(output_dir)
        self.tokenizer.save_pretrained(output_dir)

    # ------------------------------------------------------------------ #
    # Sauvegarde / chargement
    # ------------------------------------------------------------------ #

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        if self.peft_model is not None:
            self.peft_model.save_pretrained(str(path))
        if self.tokenizer is not None:
            self.tokenizer.save_pretrained(str(path))

    def merge_and_save(self, path: str | Path) -> None:
        """Fusionne les adapters LoRA dans le modèle de base et sauvegarde.

        Utile pour déploiement (pas besoin de PEFT à l'inférence) mais
        on perd la légèreté de l'adapter (~MB → plusieurs GB).
        """
        if self.peft_model is None:
            raise RuntimeError("Model not loaded. Call setup_model() first.")
        merged = self.peft_model.merge_and_unload()
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        merged.save_pretrained(str(path))
        if self.tokenizer is not None:
            self.tokenizer.save_pretrained(str(path))


# ---------------------------------------------------------------------- #
# Variantes pour exposer les API DoRA / QLoRA explicitement
# ---------------------------------------------------------------------- #

class QLoRATrainer(LoRATrainer):
    """Trainer QLoRA (4-bit base + LoRA). Recommandé en VRAM contrainte."""

    def __init__(self, config: Optional[LLMConfig] = None) -> None:
        super().__init__(config=config, use_qlora=True, use_dora=False, use_rslora=True)


class DoRATrainer(LoRATrainer):
    """Trainer DoRA (variante récente, généralement +1-2% qualité)."""

    def __init__(self, config: Optional[LLMConfig] = None, use_qlora: bool = True) -> None:
        super().__init__(config=config, use_qlora=use_qlora, use_dora=True, use_rslora=False)


if __name__ == "__main__":
    print("Available trainers:")
    print("  - LoRATrainer   (vanilla LoRA, fp16/bf16)")
    print("  - QLoRATrainer  (LoRA + 4-bit quantization)")
    print("  - DoRATrainer   (DoRA, peut être combiné avec QLoRA)")
    print()
    print("Usage:")
    print("  trainer = QLoRATrainer()")
    print("  trainer.setup_model()")
    print("  trainer.train(train_ds, eval_ds, output_dir='models/qlora_cv_matcher')")
