#!/usr/bin/env python3
"""
Fine-tune SLM on Telugu health data with LoRA.
Usage:
  python scripts/finetune_slm.py --config config/training.yaml
  python scripts/finetune_slm.py --train_file data/processed/telugu_health_train.jsonl --output_dir models/ai_medicine_telugu_lora
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")


def load_config(path: str) -> dict:
    import yaml
    with open(ROOT / path, "r") as f:
        return yaml.safe_load(f)


def load_jsonl(path: str) -> list[dict]:
    out = []
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / path
    if not p.exists():
        return out
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def format_instruction(inst: str, out: str, tokenizer) -> tuple[str, str]:
    """Format as chat: instruction -> output (Telugu health)."""
    text = f"<|user|>\n{inst}\n<|assistant|>\n{out}"
    return text, out


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/training.yaml")
    parser.add_argument("--train_file", default=None)
    parser.add_argument("--output_dir", default=None)
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--use_4bit", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    train_file = args.train_file or cfg.get("train_file", "data/processed/telugu_health_train.jsonl")
    output_dir = args.output_dir or cfg.get("output_dir", "models/ai_medicine_telugu_lora")
    output_dir = ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    train_data = load_jsonl(train_file)
    if not train_data:
        print(f"No data in {train_file}. Run prepare_telugu_health_data.py first.", file=sys.stderr)
        sys.exit(1)

    try:
        from datasets import Dataset
    except ImportError:
        print("pip install datasets", file=sys.stderr)
        sys.exit(1)

    from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
    from transformers import DataCollatorForLanguageModeling
    from peft import LoraConfig, get_peft_model, TaskType

    base_model = cfg.get("base_model", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Build dataset: concatenate instruction + output for causal LM
    max_len = cfg.get("max_length", 512)
    texts = []
    for row in train_data:
        inst = row.get("instruction", "")
        out = row.get("output", "")
        text = f"<|user|>\n{inst}\n<|assistant|>\n{out}"
        texts.append(text)

    def tokenize(examples):
        out = tokenizer(
            examples["text"],
            truncation=True,
            max_length=max_len,
            padding="max_length",
            return_tensors=None,
        )
        # Causal LM: labels = input_ids (Trainer will ignore padding in loss if configured)
        out["labels"] = [ids[:] for ids in out["input_ids"]]
        return out

    ds = Dataset.from_dict({"text": texts})
    ds = ds.map(tokenize, batched=True, remove_columns=["text"])
    ds.set_format("torch", columns=["input_ids", "attention_mask", "labels"])

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        trust_remote_code=True,
        load_in_4bit=args.use_4bit or cfg.get("use_4bit", False),
    )
    lora_config = LoraConfig(
        r=cfg.get("lora_r", 16),
        lora_alpha=cfg.get("lora_alpha", 32),
        lora_dropout=cfg.get("lora_dropout", 0.05),
        target_modules=cfg.get("target_modules", ["q_proj", "v_proj"]),
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, lora_config)

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=args.epochs or cfg.get("epochs", 3),
        per_device_train_batch_size=cfg.get("batch_size", 2),
        gradient_accumulation_steps=cfg.get("gradient_accumulation_steps", 4),
        learning_rate=cfg.get("learning_rate", 2e-5),
        warmup_ratio=cfg.get("warmup_ratio", 0.1),
        logging_steps=10,
        save_strategy="epoch",
        fp16=os.environ.get("CUDA_VISIBLE_DEVICES", "") != "",
    )
    collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=ds,
        data_collator=collator,
    )
    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    with open(output_dir / "base_model_id.txt", "w") as f:
        f.write(base_model)
    print(f"Saved adapter and tokenizer to {output_dir}")


if __name__ == "__main__":
    main()
