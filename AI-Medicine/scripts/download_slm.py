#!/usr/bin/env python3
"""
Download base SLM for AI-Medicine (TinyLlama or similar).
Saves to models/slm_base by default.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", default="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
                        help="Hugging Face model ID")
    parser.add_argument("--save_dir", default="models/slm_base", help="Local save directory")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    save_dir = root / args.save_dir
    save_dir.mkdir(parents=True, exist_ok=True)

    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"Downloading {args.model_name} -> {save_dir}")
    tokenizer = AutoTokenizer.from_pretrained(args.model_name, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(args.model_name, trust_remote_code=True)
    tokenizer.save_pretrained(save_dir)
    model.save_pretrained(save_dir)
    print("Done.")


if __name__ == "__main__":
    main()
