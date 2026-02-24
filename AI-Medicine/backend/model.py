"""
Load SLM (base or base + LoRA) for AI-Medicine.
Trained on Telugu health content; UI can use Telugu or English.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Optional PEFT for LoRA adapter
try:
    from peft import PeftModel
    HAS_PEFT = True
except ImportError:
    HAS_PEFT = False

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_ID = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"


def _load_config() -> dict:
    config_path = ROOT / "config" / "model.yaml"
    if not config_path.exists():
        return {}
    import yaml
    with open(config_path, "r") as f:
        return yaml.safe_load(f) or {}


def _is_adapter_dir(path: str) -> bool:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / path
    return (p / "adapter_config.json").exists() or (p / "base_model_id.txt").exists()


def load_model(
    model_id: Optional[str] = None,
    adapter_path: Optional[str] = None,
    device: Optional[str] = None,
):
    """Load tokenizer and model (base or base + LoRA)."""
    cfg = _load_config()
    model_id = model_id or cfg.get("model_name") or DEFAULT_MODEL_ID
    adapter_path = adapter_path or cfg.get("adapter_path")
    device = device or cfg.get("device", "auto")

    if adapter_path:
        ap = Path(adapter_path)
        if not ap.is_absolute():
            ap = ROOT / adapter_path
        if ap.exists() and HAS_PEFT:
            base_id = model_id
            if (ap / "base_model_id.txt").exists():
                with open(ap / "base_model_id.txt") as f:
                    base_id = f.read().strip()
            tokenizer = AutoTokenizer.from_pretrained(str(ap), trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(base_id, trust_remote_code=True)
            model = PeftModel.from_pretrained(model, str(ap))
            model.eval()
        else:
            tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True)
            model.eval()
    else:
        tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True)
        model.eval()

    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    return tokenizer, model, device
