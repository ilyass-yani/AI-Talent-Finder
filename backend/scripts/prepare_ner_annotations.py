#!/usr/bin/env python3
"""Prepare annotated NER data for recruiter-domain fine-tuning.

The script supports two modes:
- `template`: tokenize texts and emit O labels for manual annotation.
- `bio`: convert provided span annotations into BIO token labels.

Input formats:
- JSONL or JSON list with records containing `text` and optionally `spans`
  where each span is `{start, end, label}`.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


@dataclass(frozen=True)
class BioSpan:
    start: int
    end: int
    label: str


TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def load_records(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)

    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []

    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in raw.splitlines() if line.strip()]

    payload = json.loads(raw)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    raise ValueError("Unsupported annotation file format")


def tokenize_with_offsets(text: str) -> List[Dict[str, Any]]:
    tokens = []
    for match in TOKEN_RE.finditer(text):
        tokens.append({"token": match.group(0), "start": match.start(), "end": match.end()})
    return tokens


def normalize_spans(spans: Iterable[Dict[str, Any]]) -> List[BioSpan]:
    normalized: List[BioSpan] = []
    for span in spans:
        try:
            normalized.append(
                BioSpan(
                    start=int(span["start"]),
                    end=int(span["end"]),
                    label=str(span["label"]),
                )
            )
        except Exception:
            continue
    return sorted(normalized, key=lambda item: (item.start, item.end))


def spans_to_bio(text: str, spans: Sequence[BioSpan]) -> Dict[str, Any]:
    tokens = tokenize_with_offsets(text)
    labels = ["O"] * len(tokens)

    for span in spans:
        first_label_index = None
        for index, token in enumerate(tokens):
            overlaps = token["start"] < span.end and token["end"] > span.start
            if not overlaps:
                continue
            prefix = "B-" if first_label_index is None else "I-"
            labels[index] = f"{prefix}{span.label.upper()}"
            if first_label_index is None:
                first_label_index = index

    return {
        "text": text,
        "tokens": [token["token"] for token in tokens],
        "ner_tags": labels,
    }


def build_template(text: str) -> Dict[str, Any]:
    tokens = tokenize_with_offsets(text)
    return {
        "text": text,
        "tokens": [token["token"] for token in tokens],
        "ner_tags": ["O"] * len(tokens),
    }


def prepare_annotations(records: Sequence[Dict[str, Any]], mode: str = "template") -> List[Dict[str, Any]]:
    prepared: List[Dict[str, Any]] = []
    for record in records:
        text = str(record.get("text", "")).strip()
        if not text:
            continue

        if mode == "bio":
            spans = normalize_spans(record.get("spans", []))
            prepared.append(spans_to_bio(text, spans))
        else:
            prepared.append(build_template(text))

    return prepared


def write_jsonl(records: Sequence[Dict[str, Any]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare annotated NER data")
    parser.add_argument("--input", required=True, help="Path to source JSON/JSONL file")
    parser.add_argument("--output", required=True, help="Output JSONL path")
    parser.add_argument("--mode", choices=["template", "bio"], default="template")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    records = load_records(input_path)
    prepared = prepare_annotations(records, mode=args.mode)
    write_jsonl(prepared, output_path)

    print(f"Prepared {len(prepared)} annotation records -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())