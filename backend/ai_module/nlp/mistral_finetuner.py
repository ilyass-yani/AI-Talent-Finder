"""
Mistral Fine-tuning with LoRA/QLoRA for Recruiter Chatbot
ÉTAPE 8: LLM Fine-tuning pour améliorer réponses contextualisées
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    BitsAndBytesConfig,
)

try:
    from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_kbit_training
    PEFT_AVAILABLE = True
except ImportError:
    PEFT_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Configuration for Mistral fine-tuning."""
    model_id: str = "mistralai/Mistral-7B-Instruct-v0.1"
    output_dir: str = "models/mistral_finetuned"
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 4
    per_device_eval_batch_size: int = 8
    gradient_accumulation_steps: int = 2
    learning_rate: float = 2e-4
    warmup_steps: int = 100
    weight_decay: float = 0.01
    max_seq_length: int = 2048
    use_8bit: bool = True  # QLoRA
    use_flash_attention: bool = True
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    lora_target_modules: List[str] = None
    
    def __post_init__(self):
        if self.lora_target_modules is None:
            self.lora_target_modules = ["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


class ChatbotDataset(Dataset):
    """Dataset for recruiter chatbot training pairs."""
    
    def __init__(self, data: List[Dict[str, str]], tokenizer, max_length: int = 2048):
        self.data = data
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        
        # Format: context + question + answer
        context = item.get("context", "")
        question = item.get("question", "")
        answer = item.get("answer", "")
        
        # Create prompt with context-aware format
        prompt = f"""[CONTEXT]
{context}

[QUESTION]
{question}

[ANSWER]
{answer}"""
        
        # Tokenize
        tokenized = self.tokenizer(
            prompt,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )
        
        return {
            "input_ids": tokenized["input_ids"].squeeze(),
            "attention_mask": tokenized["attention_mask"].squeeze(),
        }


class MistralFinetuner:
    """Fine-tune Mistral model for recruiter chatbot."""
    
    def __init__(self, config: TrainingConfig = None):
        if not PEFT_AVAILABLE:
            raise ImportError("peft is required. Install: pip install peft")
        
        self.config = config or TrainingConfig()
        self.model = None
        self.tokenizer = None
        self.trainer = None
        logger.info(f"🎯 Mistral Finetuner initialized with model: {self.config.model_id}")
    
    def load_model(self) -> Tuple[Any, Any]:
        """Load Mistral model with QLoRA configuration."""
        logger.info("📦 Loading Mistral model...")
        
        # QLoRA config: 4-bit quantization for memory efficiency
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=self.config.use_8bit,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        ) if self.config.use_8bit else None
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_id,
            trust_remote_code=True,
        )
        
        # Set pad token
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Load model
        self.model = AutoModelForCausalLM.from_pretrained(
            self.config.model_id,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
            attn_implementation="flash_attention_2" if self.config.use_flash_attention else "eager",
        )
        
        # Prepare model for k-bit training
        if self.config.use_8bit:
            self.model = prepare_model_for_kbit_training(self.model)
        
        logger.info("✅ Model loaded successfully")
        return self.model, self.tokenizer
    
    def apply_lora(self) -> Any:
        """Apply LoRA adapters to model."""
        logger.info("🔧 Applying LoRA adapters...")
        
        lora_config = LoraConfig(
            r=self.config.lora_r,
            lora_alpha=self.config.lora_alpha,
            lora_dropout=self.config.lora_dropout,
            bias="none",
            task_type=TaskType.CAUSAL_LM,
            target_modules=self.config.lora_target_modules,
        )
        
        self.model = get_peft_model(self.model, lora_config)
        
        # Print trainable params
        trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        all_params = sum(p.numel() for p in self.model.parameters())
        logger.info(f"📊 Trainable params: {trainable_params:,} / {all_params:,} ({100 * trainable_params / all_params:.2f}%)")
        
        return self.model
    
    def prepare_training_data(
        self,
        data: List[Dict[str, str]],
        test_size: float = 0.1,
    ) -> Tuple[ChatbotDataset, ChatbotDataset]:
        """Prepare training and evaluation datasets."""
        logger.info(f"📊 Preparing {len(data)} training examples...")
        
        # Split data
        split_idx = int(len(data) * (1 - test_size))
        train_data = data[:split_idx]
        eval_data = data[split_idx:]
        
        train_dataset = ChatbotDataset(train_data, self.tokenizer, self.config.max_seq_length)
        eval_dataset = ChatbotDataset(eval_data, self.tokenizer, self.config.max_seq_length)
        
        logger.info(f"✅ Train: {len(train_dataset)}, Eval: {len(eval_dataset)}")
        return train_dataset, eval_dataset
    
    def train(
        self,
        training_data: List[Dict[str, str]],
        eval_data: Optional[List[Dict[str, str]]] = None,
        save_steps: int = 100,
    ) -> Dict[str, Any]:
        """Fine-tune the model."""
        logger.info("🚀 Starting fine-tuning...")
        
        # Prepare datasets
        if eval_data is None:
            train_dataset, eval_dataset = self.prepare_training_data(training_data)
        else:
            train_dataset = ChatbotDataset(training_data, self.tokenizer, self.config.max_seq_length)
            eval_dataset = ChatbotDataset(eval_data, self.tokenizer, self.config.max_seq_length)
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=self.config.output_dir,
            overwrite_output_dir=True,
            num_train_epochs=self.config.num_train_epochs,
            per_device_train_batch_size=self.config.per_device_train_batch_size,
            per_device_eval_batch_size=self.config.per_device_eval_batch_size,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            learning_rate=self.config.learning_rate,
            warmup_steps=self.config.warmup_steps,
            weight_decay=self.config.weight_decay,
            save_strategy="steps",
            save_steps=save_steps,
            eval_strategy="steps",
            eval_steps=save_steps,
            logging_steps=10,
            save_total_limit=3,
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            greater_is_better=False,
            fp16=True,
            report_to=["tensorboard"],
        )
        
        # Create trainer
        self.trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            data_collator=lambda batch: {
                "input_ids": torch.stack([x["input_ids"] for x in batch]),
                "attention_mask": torch.stack([x["attention_mask"] for x in batch]),
            },
        )
        
        # Start training
        train_result = self.trainer.train()
        
        logger.info("✅ Fine-tuning completed")
        return {
            "train_loss": train_result.training_loss,
            "epoch": train_result.epoch,
        }
    
    def save(self, save_dir: str = None):
        """Save fine-tuned model and LoRA adapters."""
        if save_dir is None:
            save_dir = self.config.output_dir
        
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        
        # Save LoRA adapters
        self.model.save_pretrained(save_dir)
        
        # Save tokenizer
        self.tokenizer.save_pretrained(save_dir)
        
        # Save config
        config_path = Path(save_dir) / "training_config.json"
        with open(config_path, "w") as f:
            json.dump({
                "model_id": self.config.model_id,
                "lora_r": self.config.lora_r,
                "lora_alpha": self.config.lora_alpha,
                "max_seq_length": self.config.max_seq_length,
            }, f, indent=2)
        
        logger.info(f"💾 Model saved to {save_dir}")
    
    @staticmethod
    def load_fine_tuned(model_dir: str) -> Tuple[Any, Any]:
        """Load fine-tuned model with LoRA adapters."""
        logger.info(f"📦 Loading fine-tuned model from {model_dir}...")
        
        tokenizer = AutoTokenizer.from_pretrained(model_dir)
        
        # Load base model first
        config_path = Path(model_dir) / "training_config.json"
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                model_id = config.get("model_id", "mistralai/Mistral-7B-Instruct-v0.1")
        else:
            model_id = "mistralai/Mistral-7B-Instruct-v0.1"
        
        # Load base model with adapters
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            device_map="auto",
            trust_remote_code=True,
        )
        
        # Load LoRA adapters
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, model_dir)
        
        logger.info("✅ Fine-tuned model loaded")
        return model, tokenizer


def generate_response(
    model: Any,
    tokenizer: Any,
    context: str,
    question: str,
    max_new_tokens: int = 512,
) -> str:
    """Generate response using fine-tuned Mistral."""
    
    prompt = f"""[CONTEXT]
{context}

[QUESTION]
{question}

[ANSWER]
"""
    
    # Tokenize
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    
    # Generate
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            top_k=50,
            repetition_penalty=1.2,
        )
    
    # Decode
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Extract only the answer part
    if "[ANSWER]" in response:
        response = response.split("[ANSWER]")[1].strip()
    
    return response


if __name__ == "__main__":
    # Example usage
    config = TrainingConfig(
        num_train_epochs=1,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
    )
    
    finetuner = MistralFinetuner(config)
    
    # Load model
    finetuner.load_model()
    
    # Apply LoRA
    finetuner.apply_lora()
    
    # Example training data
    training_data = [
        {
            "context": "Job Criteria: Python, FastAPI, PostgreSQL, Docker. Candidate: John Doe with 5 years Python experience",
            "question": "Is this candidate a good match?",
            "answer": "Yes, John matches 4/4 required skills with strong Python background."
        },
    ]
    
    # Train
    finetuner.train(training_data)
    
    # Save
    finetuner.save()
