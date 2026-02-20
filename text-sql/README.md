# Text-to-SQL (Employee DB) + Gradio UI

This is a small demo app that converts natural language into SQL using a small open model and runs it against a sample SQLite employee database. It supports LoRA fine-tuning, **RAG at inference** (few-shot from similar examples), and **human feedback learning** (merge corrections and re-fine-tune).

## Setup

```bash
cd text-sql
python -m venv .venv
source .venv/bin/activate   # or: .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

For fine-tuning and RAG:

```bash
pip install -r requirements-train.txt   # LoRA / QLoRA
pip install sentence-transformers        # RAG at inference (or already in requirements.txt)
```

---

## Running steps (full workflow)

### 1. Run the app (no fine-tuning)

```bash
python app.py
```

Open the Gradio URL in your browser. RAG is on by default if `data/train_employee.jsonl` exists (few-shot from similar questions).

### 2. Baseline benchmark (before fine-tuning)

```bash
python run_benchmark.py --output results_baseline.json
```

### 3. Fine-tune with LoRA

```bash
python finetune_lora.py --output_dir models/t5-text2sql-employee-lora
```

Optional: `--epochs 8 --lora_r 32 --lora_alpha 64` for stronger training; `--use_4bit` for QLoRA (saves memory).

### 4. Benchmark after fine-tuning (with optional RAG)

```bash
python run_benchmark.py --model_id models/t5-text2sql-employee-lora --output results_after_lora.json --clear_cache
```

With RAG (few-shot from similar examples):

```bash
python run_benchmark.py --model_id models/t5-text2sql-employee-lora --use_rag --rag_examples data/train_employee.jsonl --rag_top_k 3 --output results_after_lora.json --clear_cache
```

### 5. Compare baseline vs after LoRA

```bash
python compare_benchmark_results.py
```

### 6. Use fine-tuned model in the app

```bash
export TEXT2SQL_MODEL_ID=models/t5-text2sql-employee-lora
python app.py
```

### 7. Human feedback: collect corrections, merge, re-fine-tune

**App flow:** (1) Ask a question → click **Generate (and Execute)** → SQL runs and **results are shown** (Generated SQL + Query Result table). (2) **After reviewing the results**, use **Correct** or **Incorrect**; if Incorrect, optionally type the correct SQL. Feedback is used for re-training.

1. In the app, run a query first so you see the generated SQL and the result table.
2. Then use **Correct** or **Incorrect** (and optional correct SQL). Feedback is saved to `data/feedback.jsonl`.
3. Merge feedback into training data and re-fine-tune:

```bash
python merge_feedback_into_train.py --feedback data/feedback.jsonl --train data/train_employee.jsonl --output data/train_with_feedback.jsonl
python finetune_lora.py --train_file data/train_with_feedback.jsonl --output_dir models/t5-text2sql-employee-lora
```

4. Re-run benchmark and compare again.

See **[IMPROVING_ACCURACY.md](IMPROVING_ACCURACY.md)** for more ways to improve execution match and **[BENCHMARK_RESULTS.md](BENCHMARK_RESULTS.md)** for full benchmark details.

---

## How to check execution accuracy

Execution accuracy is the % of eval questions where the model’s SQL **runs** and returns the **same result** as the gold SQL.

1. **Run the benchmark** (before or after fine-tuning):

   ```bash
   # Baseline (no fine-tuning)
   python run_benchmark.py --output results_baseline.json

   # After fine-tuning (optional: with RAG)
   python run_benchmark.py --model_id models/t5-text2sql-employee-lora --use_rag --output results_after_lora.json --clear_cache
   ```

2. **Read the numbers in the terminal:**
   - **Exact match** = % of queries where generated SQL string equals gold SQL (strict).
   - **Execution match** = % of queries where generated SQL runs and result set matches gold (what we care about).

   Example output:
   ```
   Model: models/t5-text2sql-employee-lora
   Eval: data/eval_employee.jsonl (20 samples)
   Exact match:     3/20 = 15.00%
   Execution match: 4/20 = 20.00%
   ```

3. **Inspect per-question results:** Open the output JSON (e.g. `results_after_lora.json`). Each `results[]` entry has `question`, `gold_sql`, `pred_sql`, `execution_match`, and `exec_note` (e.g. `match`, `result_mismatch`, or `pred_error: no such column: X`).

4. **Compare before vs after:**
   ```bash
   python compare_benchmark_results.py
   ```

---

## Benchmark (measure accuracy)

To measure **exact match** and **execution match** on the eval set:

```bash
python run_benchmark.py --output results_baseline.json
```

## Fine-tuning (QLoRA / LoRA)

To fine-tune the model on your employee schema with LoRA (optionally 4-bit QLoRA):

```bash
pip install -r requirements-train.txt
python finetune_lora.py --output_dir models/t5-text2sql-employee-lora
```

Then re-run the benchmark with the adapter and compare results (see [BENCHMARK_RESULTS.md](BENCHMARK_RESULTS.md)).

## Notes

- The bundled database is `data/employees.db` (SQLite).
- For safety, the app only executes `SELECT ...` queries.
- To use a fine-tuned model in the Gradio app: `export TEXT2SQL_MODEL_ID=models/t5-text2sql-employee-lora` then `python app.py`.
