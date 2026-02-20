from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_SAFETENSORS_CONVERSION", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
# Prevents the background safetensors conversion thread that can raise JSONDecodeError
os.environ.setdefault("DISABLE_SAFETENSORS_CONVERSION", "1")

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


DEFAULT_MODEL_ID = "cssupport/t5-small-awesome-text-to-sql"


@dataclass(frozen=True)
class GenerationResult:
    sql: str
    raw: str


def _compact_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _strip_special_tokens(decoded: str) -> str:
    return decoded.replace("</s>", "").replace("<pad>", "").strip()


def _extract_first_select(text: str) -> str:
    """
    Attempts to extract the first reasonable SELECT statement from model output.
    Many small text-to-SQL models sometimes echo parts of the prompt.
    """
    m = re.search(r"(?is)\bselect\b.*", text)
    if not m:
        return text.strip()

    sql = m.group(0).strip()

    # Truncate if the model starts echoing schema/instructions.
    stop_markers = [
        "database schema",
        "relationships",
        "return a single",
        "tables:",
        "table schema",
        "sqlite",
    ]
    lower = sql.lower()
    cut_at = None
    for marker in stop_markers:
        idx = lower.find(marker)
        if idx != -1:
            cut_at = idx if cut_at is None else min(cut_at, idx)
    if cut_at is not None:
        sql = sql[:cut_at].strip()

    # Keep only the first line if it became multi-line garbage.
    sql = sql.splitlines()[0].strip()
    return sql


def _force_select_only(sql: str) -> str:
    sql = sql.strip().rstrip(";")
    return sql


def _looks_like_select(sql: str) -> bool:
    return bool(re.match(r"(?is)^\s*select\s+", sql))


def _replace_generic_table(sql: str, table_name: str) -> str:
    # Many WikiSQL demos emit "... FROM table ..."
    return re.sub(r"(?is)\bfrom\s+table\b", f"FROM {table_name}", sql)


def _is_peft_adapter_dir(model_id: str) -> bool:
    if not os.path.isdir(model_id):
        return False
    return (
        os.path.exists(os.path.join(model_id, "adapter_config.json"))
        or os.path.exists(os.path.join(model_id, "base_model_id.txt"))
    )


@lru_cache(maxsize=1)
def _load(model_id: str = DEFAULT_MODEL_ID):
    if _is_peft_adapter_dir(model_id):
        try:
            from peft import PeftModel
        except ImportError:
            raise ImportError("PEFT is required to load a fine-tuned adapter. Install with: pip install peft")
        base_id = DEFAULT_MODEL_ID
        base_path = os.path.join(model_id, "base_model_id.txt")
        if os.path.exists(base_path):
            with open(base_path) as f:
                base_id = f.read().strip()
        elif os.path.exists(os.path.join(model_id, "adapter_config.json")):
            import json
            with open(os.path.join(model_id, "adapter_config.json")) as f:
                base_id = json.load(f).get("base_model_name_or_path", base_id)
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForSeq2SeqLM.from_pretrained(base_id)
        model = PeftModel.from_pretrained(model, model_id)
        model.eval()
        return tokenizer, model
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_id)
    model.eval()
    return tokenizer, model


def generate_sql(
    question: str,
    schema_prompt: str,
    *,
    model_id: str = DEFAULT_MODEL_ID,
    max_new_tokens: int = 128,
    table_hint: Optional[str] = "employees",
    use_rag: bool = False,
    rag_examples_path: Optional[str] = None,
    rag_top_k: int = 3,
) -> GenerationResult:
    tokenizer, model = _load(model_id)

    # Optional RAG: prepend few-shot (query for: Q -> SQL) from similar examples
    if use_rag and rag_examples_path:
        try:
            from text2sql_demo.rag import get_similar_examples, build_few_shot_prompt
            similar = get_similar_examples(question, rag_examples_path, top_k=rag_top_k)
            if similar:
                prompt = build_few_shot_prompt(schema_prompt, question, similar)
            else:
                prompt = (
                    "tables:\n"
                    f"{schema_prompt}\n"
                    f"query for: {question}\n"
                )
        except Exception:
            prompt = (
                "tables:\n"
                f"{schema_prompt}\n"
                f"query for: {question}\n"
            )
    else:
        # This model family expects "tables:" + CREATE TABLE statements + "query for:"
        prompt = (
            "tables:\n"
            f"{schema_prompt}\n"
            f"query for: {question}\n"
        )

    inputs = tokenizer([prompt], return_tensors="pt", truncation=True)

    with torch.no_grad():
        output_ids = model.generate(
            input_ids=inputs["input_ids"],
            attention_mask=inputs.get("attention_mask", None),
            max_new_tokens=max_new_tokens,
            num_beams=4,
        )

    decoded = tokenizer.decode(output_ids[0], skip_special_tokens=False)
    raw = _strip_special_tokens(decoded)

    sql = _extract_first_select(raw)
    sql = _force_select_only(sql)
    if table_hint:
        sql = _replace_generic_table(sql, table_hint)
    sql = sql.strip()

    # If the model produced something not-SELECT, we still return it (for inspection),
    # but the UI will refuse to execute.
    return GenerationResult(sql=sql, raw=raw)


def validate_sql_for_execution(sql: str) -> Optional[str]:
    """
    Returns an error string if the SQL should NOT be executed, else None.
    """
    s = sql.strip()
    if not s:
        return "Empty SQL."

    # Reject multiple statements
    if ";" in s.rstrip(";"):
        return "Multiple statements detected. Only a single SELECT is allowed."

    if not _looks_like_select(s):
        return "Only SELECT queries are allowed to execute in this demo."

    # Basic denylist
    if re.search(r"(?is)\b(drop|delete|update|insert|alter|create|attach|detach|pragma)\b", s):
        return "Unsafe keyword detected. Only SELECT is allowed."

    return None

