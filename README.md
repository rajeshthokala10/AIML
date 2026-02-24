# AIML

Repository for AI/ML projects and demos.

---

## Projects

### [AI-Medicine](AI-Medicine/) — Personalized health advice (Telugu + English)

Personalized health advice for a **Telugu-trained** backend: nutrition, basic diseases, medicines, chronic level-1. **Input:** text, voice, or video. **Output:** text + voice. **UI:** Telugu or English.

- **SLM** (e.g. TinyLlama) fine-tuned on **Telugu health content** (open source: MedMCQA-Indic, custom FAQs).
- **Voice/video** → Whisper STT → model → text + TTS (Telugu/English).

Quick start:

```bash
cd AI-Medicine
pip install -r requirements.txt
python scripts/prepare_telugu_health_data.py
python app.py
```

See **[AI-Medicine/README.md](AI-Medicine/README.md)** and **[AI-Medicine/STEP_BY_STEP.md](AI-Medicine/STEP_BY_STEP.md)** for end-to-end steps, data sources, and optional fine-tuning.

---

### [text-sql](text-sql/) — Text-to-SQL with LoRA fine-tuning

Natural language → SQL using a small T5 model (`cssupport/t5-small-awesome-text-to-sql`), Gradio UI, and a SQLite employee database. Includes:

- **LoRA / QLoRA fine-tuning** on your schema
- **RAG at inference** (few-shot from similar question–SQL examples)
- **Human feedback learning** (collect corrections, merge into training, re-fine-tune)
- **Benchmarks**: exact match and execution match on an eval set

Quick start:

```bash
cd text-sql
pip install -r requirements.txt
python app.py
```

See **[text-sql/README.md](text-sql/README.md)** for full setup, running steps, and fine-tuning.

---

## text-sql: Benchmark results (before vs after fine-tuning)

Evaluation on **20 questions** from `data/eval_employee.jsonl` (employee schema: departments, employees, salaries).

| Metric              | Before fine-tuning (baseline) | After LoRA fine-tuning |
|---------------------|-------------------------------|--------------------------|
| **Model**           | `cssupport/t5-small-awesome-text-to-sql` | Same base + LoRA adapter (`models/t5-text2sql-employee-lora`) |
| **Exact match**      | 0 / 20 (**0%**)              | 3 / 20 (**15%**)        |
| **Execution match** | 1 / 20 (**5%**)               | 4 / 20 (**20%**)        |

- **Exact match**: generated SQL string equals gold SQL.
- **Execution match**: generated SQL runs and returns the same result set as gold (recommended metric).

Fine-tuning improves execution accuracy by teaching the model the exact schema (e.g. `emp_id`, `dept_name`) and reducing wrong column/table names from pre-training. RAG at inference (few-shot from similar examples) can improve results further; see [text-sql/IMPROVING_ACCURACY.md](text-sql/IMPROVING_ACCURACY.md).

To reproduce:

```bash
cd text-sql
# Baseline
python run_benchmark.py --output results_baseline.json
# Fine-tune (then benchmark again)
python finetune_lora.py --output_dir models/t5-text2sql-employee-lora
python run_benchmark.py --model_id models/t5-text2sql-employee-lora --output results_after_lora.json --clear_cache
python compare_benchmark_results.py
```

Results are also stored in `text-sql/results_baseline.json` and `text-sql/results_after_lora.json`.
