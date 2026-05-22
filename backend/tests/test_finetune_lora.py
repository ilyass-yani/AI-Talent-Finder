from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "finetune_lora.py"
SPEC = spec_from_file_location("finetune_lora", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
finetune_lora = module_from_spec(SPEC)
sys.modules[SPEC.name] = finetune_lora
SPEC.loader.exec_module(finetune_lora)


def test_load_training_texts_supports_multiple_jsonl_formats(tmp_path: Path):
    dataset_path = tmp_path / "finetune.jsonl"
    dataset_path.write_text(
        """{"text": "Backend engineer with Python and FastAPI."}
{"prompt": "Extract skills", "completion": "Python, SQL"}
{"instruction": "Summarize", "input": "Python, Docker", "output": "Strong backend profile"}
""",
        encoding="utf-8",
    )

    texts = finetune_lora.load_training_texts(str(dataset_path))

    assert len(texts) == 3
    assert any("Python and FastAPI" in text for text in texts)
    assert any("Python, SQL" in text for text in texts)
    assert any("Strong backend profile" in text for text in texts)


def test_run_finetuning_dry_run_writes_metadata(tmp_path: Path):
    dataset_path = tmp_path / "finetune.jsonl"
    dataset_path.write_text(
        """{"prompt": "Extract skills", "completion": "Python, AWS"}
{"prompt": "Extract skills", "completion": "FastAPI, Docker"}
""",
        encoding="utf-8",
    )

    config = finetune_lora.FinetuneConfig(
        model="mistralai/Mistral-7B-Instruct-v0.3",
        data=str(dataset_path),
        output_dir=str(tmp_path / "out"),
        method="lora",
        max_length=256,
        epochs=1,
        batch_size=1,
        learning_rate=2e-4,
        gradient_accumulation_steps=1,
        warmup_ratio=0.03,
        test_split=0.0,
        seed=42,
        dry_run=True,
        target_family="mistral",
        target_modules=["q_proj", "v_proj"],
        use_gradient_checkpointing=False,
        trust_remote_code=False,
    )

    result = finetune_lora.run_finetuning(config)

    assert result["status"] == "dry_run"
    metadata_path = tmp_path / "out" / "finetune_metadata.json"
    assert metadata_path.exists()
    assert '"dataset_size": 2' in metadata_path.read_text(encoding="utf-8")
