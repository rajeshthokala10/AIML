"""
Inference for AI-Medicine: chat with SLM (Telugu health backend).
UI language can be Telugu or English; model is trained on Telugu health content.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from backend.model import load_model, _load_config

ROOT = Path(__file__).resolve().parent.parent


def _get_system_prompt(lang: str) -> str:
    cfg = _load_config()
    if lang == "te":
        return (cfg.get("system_prompt_te") or "").strip() or (
            "మీరు ఒక సాధారణ ఆరోగ్య సలహా సహాయకుడు. పోషకాహారం, సాధారణ అనారోగ్యాలు, మందులు మరియు దీర్ఘకాలిక సమస్యలకు మొదటి స్థాయి చికిత్స గురించి సమాచారం మాత్రమే ఇవ్వండి."
        )
    return (cfg.get("system_prompt_en") or "").strip() or (
        "You are a general health advice assistant. Provide information only on nutrition, basic illnesses, medicines, and level-1 treatment for chronic issues."
    )


def _build_prompt(system: str, user_message: str, tokenizer) -> str:
    """Chat-style prompt for TinyLlama/Chat models."""
    return f"<|system|>\n{system}\n<|user|>\n{user_message}\n<|assistant|>\n"


def generate(
    user_message: str,
    lang: str = "te",
    model_id: Optional[str] = None,
    adapter_path: Optional[str] = None,
    max_new_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
) -> str:
    """Generate health advice (Telugu health backend; lang = 'te' or 'en' for system prompt)."""
    cfg = _load_config()
    tokenizer, model, device = load_model(model_id=model_id, adapter_path=adapter_path)
    max_new_tokens = max_new_tokens or cfg.get("max_new_tokens", 512)
    temperature = temperature if temperature is not None else cfg.get("temperature", 0.7)
    do_sample = cfg.get("do_sample", True)
    top_p = cfg.get("top_p", 0.9)

    system = _get_system_prompt(lang)
    prompt = _build_prompt(system, user_message.strip(), tokenizer)
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024).to(device)

    import torch
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=do_sample,
            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
        )

    full = tokenizer.decode(out[0], skip_special_tokens=False)
    # Extract assistant reply after <|assistant|>
    m = re.search(r"<\|assistant\|>\s*(.*?)(?=<\|user\|>|<\|system\|>|$)", full, re.DOTALL)
    reply = (m.group(1).strip() if m else full).strip()
    reply = reply.replace("</s>", "").replace("<s>", "").strip()
    return reply
