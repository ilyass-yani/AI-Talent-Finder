# GPU Finetuning (LoRA / QLoRA)

Steps to run a full finetune on GPU:

1. Prepare an `accelerate` config (see `backend/accelerate_config_demo.yaml`).
2. Ensure the venv has `transformers`, `peft`, `accelerate`, `bitsandbytes`, and `datasets` installed. Example:

```
.venv/bin/pip install -r backend/requirements-extras.txt
.venv/bin/pip install peft bitsandbytes accelerate -U
```

3. Run the helper script in dry-run first, then without `--dry-run`:

```
./backend/scripts/run_finetune_gpu.sh --model mistralai/Mistral-7B-Instruct-v0.1 --data data/finetune_sample.jsonl --out models/mistral_finetuned --method qlora --epochs 3 --batch 4
```

Notes:

- Training large models requires appropriate GPU memory and CUDA drivers.
- When ready, remove `--dry-run` in `run_finetune_gpu.sh` or edit the command to perform the real run.
