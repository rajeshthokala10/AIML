#!/usr/bin/env python3
"""
QLoRA-style fine-tuning: LoRA (optionally 4-bit quantized) on T5 text-to-SQL model.
Usage:
  python finetune_lora.py [--train_file data/train_employee.jsonl] [--eval_file data/eval_employee.jsonl] [--output_dir models/t5-text2sql-employee-lora] [--use_4bit]
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import subprocess
import torch
try:
    from datasets import Dataset
except ModuleNotFoundError:
    print("Installing missing dependency 'datasets' (and peft) into current environment...")
    subprocess.run([sys.executable, "-m", "pip", "install", "datasets", "peft"], check=True)
    from datasets import Dataset
from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    DataCollatorForSeq2Seq,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
)

# Optional 4-bit for QLoRA
try:
    from transformers import BitsAndBytesConfig
    HAS_BITSANDBYTES = True
except ImportError:
    HAS_BITSANDBYTES = False

from peft import LoraConfig, get_peft_model, TaskType

# Ensure text2sql_demo is importable
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

SCHEMA_PROMPT = (
    "CREATE TABLE departments (dept_id INTEGER PRIMARY KEY, dept_name TEXT, location TEXT); "
    "CREATE TABLE employees (emp_id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT, title TEXT, hire_date TEXT, dept_id INTEGER, email TEXT, "
    "FOREIGN KEY (dept_id) REFERENCES departments(dept_id)); "
    "CREATE TABLE salaries (emp_id INTEGER, effective_date TEXT, salary INTEGER, "
    "FOREIGN KEY (emp_id) REFERENCES employees(emp_id));"
)

DEFAULT_MODEL_ID = "cssupport/t5-small-awesome-text-to-sql"
MAX_INPUT_LENGTH = 512
MAX_TARGET_LENGTH = 256


def load_jsonl(path: str) -> list[dict]:
    out = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def build_input_text(question: str) -> str:
    return (
        "tables:\n"
        f"{SCHEMA_PROMPT}\n"
        f"query for: {question}\n"
    )


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_id", default=DEFAULT_MODEL_ID, help="Base model")
    parser.add_argument("--train_file", default="data/train_employee.jsonl")
    parser.add_argument("--eval_file", default="data/eval_employee.jsonl")
    parser.add_argument("--output_dir", default="models/t5-text2sql-employee-lora")
    parser.add_argument("--use_4bit", action="store_true", help="Use 4-bit quantization (QLoRA)")
    parser.add_argument("--epochs", type=int, default=6, help="More epochs (e.g. 6–10) improve execution match")
    parser.add_argument("--batch_size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=5e-4)
    parser.add_argument("--lora_r", type=int, default=16, help="LoRA rank; higher = more capacity")
    parser.add_argument("--lora_alpha", type=int, default=32, help="LoRA alpha (often 2x lora_r)")
    args = parser.parse_args()

    train_path = ROOT / args.train_file
    eval_path = ROOT / args.eval_file
    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if not train_path.exists():
        print(f"Train file not found: {train_path}", file=sys.stderr)
        sys.exit(1)

    # Load data
    train_data = load_jsonl(str(train_path))
    eval_data = load_jsonl(str(eval_path)) if eval_path.exists() else []

    train_inputs = [build_input_text(item["question"]) for item in train_data]
    train_targets = [item["gold_sql"] for item in train_data]
    eval_inputs = [build_input_text(item["question"]) for item in eval_data]
    eval_targets = [item["gold_sql"] for item in eval_data]

    tokenizer = AutoTokenizer.from_pretrained(args.model_id)

    def tokenize(examples, inputs_key="input_text", targets_key="target_text"):
        model_inputs = tokenizer(
            examples[inputs_key],
            max_length=MAX_INPUT_LENGTH,
            truncation=True,
            padding=False,
        )
        labels = tokenizer(
            examples[targets_key],
            max_length=MAX_TARGET_LENGTH,
            truncation=True,
            padding=False,
        )
        model_inputs["labels"] = [l for l in labels["input_ids"]]
        return model_inputs

    train_ds = Dataset.from_dict({
        "input_text": train_inputs,
        "target_text": train_targets,
    })
    train_ds = train_ds.map(
        lambda x: tokenize({"input_text": x["input_text"], "target_text": x["target_text"]}),
        batched=True,
        remove_columns=train_ds.column_names,
    )

    eval_ds = None
    if eval_inputs:
        eval_ds = Dataset.from_dict({
            "input_text": eval_inputs,
            "target_text": eval_targets,
        })
        eval_ds = eval_ds.map(
            lambda x: tokenize({"input_text": x["input_text"], "target_text": x["target_text"]}),
            batched=True,
            remove_columns=eval_ds.column_names,
        )

    # Load base model (optionally 4-bit for QLoRA)
    if args.use_4bit and HAS_BITSANDBYTES:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )
        model = AutoModelForSeq2SeqLM.from_pretrained(
            args.model_id,
            quantization_config=bnb_config,
            device_map="auto",
        )
    else:
        if args.use_4bit and not HAS_BITSANDBYTES:
            print("Warning: use_4bit requested but bitsandbytes not installed; using full precision.", file=sys.stderr)
        model = AutoModelForSeq2SeqLM.from_pretrained(args.model_id)

    # LoRA config for T5 (encoder-decoder)
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        target_modules=["q", "v"],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.SEQ_2_SEQ_LM,
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    data_collator = DataCollatorForSeq2Seq(
        tokenizer,
        model=model,
        padding=True,
        return_tensors="pt",
    )

    training_args = Seq2SeqTrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        weight_decay=0.01,
        logging_steps=10,
        save_strategy="epoch",
        eval_strategy="epoch" if eval_ds else "no",
        save_total_limit=2,
        fp16=torch.cuda.is_available(),
        report_to="none",
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=data_collator,
    )

    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    # Save base model id for inference (load base + this adapter)
    with open(output_dir / "base_model_id.txt", "w") as f:
        f.write(args.model_id)

    print(f"Fine-tuned adapter saved to {output_dir}")


if __name__ == "__main__":
    main()
