# Text-to-SQL Benchmark: Before vs After QLoRA Fine-Tuning

This document describes how to measure the model on the employee DB, how to fine-tune with QLoRA (LoRA + optional 4-bit), and how to compare results.

---

## 1. Evaluation Setup

- **Eval set**: `data/eval_employee.jsonl` — 20 (question, gold_sql) pairs for the employee schema.
- **Metrics**:
  - **Exact match (%)**: predicted SQL equals gold SQL after normalizing whitespace and case.
  - **Execution match (%)**: predicted SQL runs on `data/employees.db` and returns the same result set as the gold SQL (order-independent).

---

## 2. Measure Current Benchmark (Before Fine-Tuning)

From the `text-sql` directory, with the same environment you use for `app.py`:

```bash
cd text-sql
python run_benchmark.py --output results_baseline.json
```

Example output:

```
Model: cssupport/t5-small-awesome-text-to-sql
Eval: .../data/eval_employee.jsonl (20 samples)
Exact match:     X/20 = XX.XX%
Execution match: Y/20 = YY.YY%
Results written to results_baseline.json
```

**Record these numbers** as the **Before** row in the comparison table below.

---

## 3. Fine-Tune with QLoRA (LoRA + Optional 4-bit)

### 3.1 Install training dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-train.txt
```

Optional (for 4-bit QLoRA): `pip install bitsandbytes`

### 3.2 Run fine-tuning

```bash
cd text-sql
python finetune_lora.py \
  --train_file data/train_employee.jsonl \
  --eval_file data/eval_employee.jsonl \
  --output_dir models/t5-text2sql-employee-lora \
  --epochs 3 \
  --batch_size 4
```

For **4-bit QLoRA** (saves GPU memory):

```bash
python finetune_lora.py --use_4bit --epochs 3 --output_dir models/t5-text2sql-employee-qlora
```

The script saves the **LoRA adapter** under `models/t5-text2sql-employee-lora` (and `base_model_id.txt` so inference can load base + adapter).

---

## 4. Compare Benchmark Results (Before vs After)

After you have both `results_baseline.json` and `results_after_lora.json`, run the comparison script:

```bash
cd text-sql
python compare_benchmark_results.py
```

This prints a table of **Exact match %**, **Execution match %**, and **Change** (after − before).

To get a **markdown table** you can paste into this file or a report:

```bash
python compare_benchmark_results.py --markdown
```

Example output:

```
# Benchmark comparison: before vs after fine-tuning

| Metric | Before (base model) | After (LoRA fine-tuned) | Change |
|--------|---------------------|-------------------------|--------|
| **Exact match %** | 0.00% | 0.00% | +0.00% |
| **Execution match %** | 5.00% | 5.00% | +0.00% |
| **Eval samples** | 20 | 20 | — |
```

You can also pass custom result files:

```bash
python compare_benchmark_results.py --before results_baseline.json --after results_after_lora.json [--markdown]
```

---

## 5. Measure Benchmark After Fine-Tuning (if not done yet)

Point the benchmark at the fine-tuned adapter (use the same eval set and DB):

```bash
cd text-sql
python run_benchmark.py \
  --model_id models/t5-text2sql-employee-lora \
  --output results_after_lora.json \
  --clear_cache
```

**Record** the printed exact match % and execution match % as the **After** row.

---

## 6. Comparison: Before vs After Fine-Tuning

Fill in after you run the two benchmarks (steps 2 and 4).

| Metric            | Before (base model) | After (LoRA fine-tuned) |
|-------------------|----------------------|--------------------------|
| **Exact match %** | _fill from step 2_   | _fill from step 4_      |
| **Execution match %** | _fill from step 2_ | _fill from step 4_       |
| **Eval samples**  | 20                   | 20                       |

### How to interpret

- **Exact match** is strict (SQL string must match after normalization). Small improvements here still matter.
- **Execution match** is what users care about: does the generated query return the correct rows? This usually improves more after fine-tuning on your schema and phrasings.

### Optional: Use fine-tuned model in the Gradio app

To use the LoRA adapter in the UI, set the environment variable before launching:

```bash
export TEXT2SQL_MODEL_ID=models/t5-text2sql-employee-lora
python app.py
```

(If you add support in `app.py` for `os.environ.get("TEXT2SQL_MODEL_ID")` and pass it to `generate_sql`, the app will use the fine-tuned model. Otherwise you can temporarily change `DEFAULT_MODEL_ID` in `text2sql_demo/model.py` to your adapter path.)

---

## 7. File Summary

| File | Purpose |
|------|---------|
| `data/eval_employee.jsonl` | Eval (question, gold_sql) pairs — used for benchmarking only. |
| `data/train_employee.jsonl` | Training (question, gold_sql) pairs — used for LoRA/QLoRA fine-tuning. |
| `run_benchmark.py` | Runs the model on the eval set; reports exact match % and execution match %. |
| `finetune_lora.py` | QLoRA-style fine-tuning (LoRA, optional 4-bit) with PEFT; saves adapter to `models/`. |
| `results_baseline.json` | Full benchmark results before fine-tuning (created by you). |
| `results_after_lora.json` | Full benchmark results after fine-tuning (created by you). |

---

## 8. Example Comparison (placeholder)

After you run both benchmarks, your table might look like:

| Metric            | Before (base model) | After (LoRA fine-tuned) |
|-------------------|----------------------|--------------------------|
| **Exact match %** | 15.00                | 35.00                    |
| **Execution match %** | 25.00             | 55.00                    |
| **Eval samples**  | 20                   | 20                       |

*(Replace with your actual numbers.)*

Improvements depend on the quality and size of `train_employee.jsonl` and the number of epochs. You can add more (question, gold_sql) pairs to the train set and re-run fine-tuning to improve the **After** column.
