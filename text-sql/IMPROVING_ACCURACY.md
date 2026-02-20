# How to Improve Execution Match After Fine-Tuning

If execution match stays low (e.g. 5%) after fine-tuning, the model is often **using wrong column or table names** from other schemas it saw during pre-training (e.g. `employee_id` instead of `emp_id`, `department` instead of `dept_name`). Here’s how to improve it.

---

## 1. Use the Updated Training Data and Defaults

- **Expanded train set** – `data/train_employee.jsonl` now includes extra “schema drilling” examples that use only your schema’s column names: `emp_id`, `first_name`, `last_name`, `dept_id`, `dept_name`, `location`, `title`, `hire_date`, `email`, `salary`, `effective_date`.
- **Stronger LoRA** – Defaults are now `--epochs 6`, `--lora_r 16`, `--lora_alpha 32` so the model has more capacity and training time.

Re-run fine-tuning with the new data and defaults (no need to pass extra flags):

```bash
cd text-sql
python finetune_lora.py --output_dir models/t5-text2sql-employee-lora
```

Then re-run the benchmark and comparison:

```bash
python run_benchmark.py --model_id models/t5-text2sql-employee-lora --output results_after_lora.json --clear_cache
python compare_benchmark_results.py
```

---

## 2. Add More Training Examples

Add more (question, gold_sql) pairs to `data/train_employee.jsonl` so the model sees your schema and phrasings often.

- **Copy eval questions into train** – For each line in `data/eval_employee.jsonl`, add the same (or a paraphrase) to `train_employee.jsonl` so the model is trained on the same questions it’s evaluated on.
- **Use only your column names** – In every `gold_sql`, use only:  
  `emp_id`, `first_name`, `last_name`, `title`, `hire_date`, `dept_id`, `email` (employees);  
  `dept_id`, `dept_name`, `location` (departments);  
  `emp_id`, `effective_date`, `salary` (salaries).
- **Simple + complex** – Include both simple queries (`SELECT * FROM employees`) and joins/aggregates so the model learns both.

One new example per line in JSONL format:

```json
{"question": "Your natural language question", "gold_sql": "SELECT ... your valid SQL ..."}
```

---

## 3. Train Longer and/or Stronger LoRA

- **More epochs** – Try 8–10 if 6 isn’t enough:  
  `python finetune_lora.py --epochs 10 --output_dir models/t5-text2sql-employee-lora`
- **Larger LoRA rank** – More trainable parameters:  
  `python finetune_lora.py --lora_r 32 --lora_alpha 64 --output_dir models/t5-text2sql-employee-lora`

---

## 4. Inspect What’s Going Wrong

Open `results_after_lora.json` and look at `results[].exec_note` and `results[].pred_sql`:

- **pred_error: no such column: X** – The model is generating column/table names that don’t exist (e.g. `employee_id` instead of `emp_id`). Add more training examples that use the correct name for that question type.
- **result_mismatch** – The SQL runs but returns different rows than the gold query. Either the logic is wrong (e.g. JOIN/WHERE) or the gold SQL might need to match the exact style you want; add training examples that produce the same result set.

Use these to decide which question types to add to `train_employee.jsonl` and which columns to reinforce.

---

## 5. Quick Checklist

| Step | Action |
|------|--------|
| 1 | Re-run fine-tuning with current `train_employee.jsonl` and defaults (6 epochs, LoRA r=16). |
| 2 | Re-run benchmark with the new adapter and compare again. |
| 3 | If execution match is still low, add 10–20 more (question, gold_sql) pairs to `train_employee.jsonl` (including eval questions or paraphrases). |
| 4 | Try `--epochs 10` and/or `--lora_r 32 --lora_alpha 64`. |
| 5 | Use `results_after_lora.json` to fix specific column/query errors with targeted training examples. |

Execution match should improve as the model sees your schema and phrasings more often and learns to output only valid column and table names.

---

## 6. RAG at Inference (Few-Shot from Similar Examples)

**RAG** retrieves similar (question, SQL) examples from your training (or feedback) data and prepends them to the prompt so the model sees few-shot context. This often improves accuracy without re-training.

- **App**: RAG is **on by default** if `data/train_employee.jsonl` exists. Set `TEXT2SQL_RAG_EXAMPLES` to another JSONL path if needed.
- **Benchmark**: Use `--use_rag` to evaluate with RAG:
  ```bash
  python run_benchmark.py --model_id models/t5-text2sql-employee-lora --use_rag --rag_examples data/train_employee.jsonl --rag_top_k 3 --output results_after_lora.json --clear_cache
  ```
- **Dependency**: `pip install sentence-transformers` (added in `requirements.txt`).

---

## 7. Human Feedback Learning (Learn from Corrections)

Users can mark answers as correct/incorrect and optionally provide the correct SQL. The app saves feedback to `data/feedback.jsonl`. You can merge corrections into training and **re-fine-tune** so the model learns from feedback.

1. **Collect feedback** – In the Gradio app, after each query use **Correct** or **Incorrect**. If Incorrect, optionally type the correct SQL.
2. **Merge into training data**:
   ```bash
   python merge_feedback_into_train.py --feedback data/feedback.jsonl --train data/train_employee.jsonl --output data/train_with_feedback.jsonl
   ```
3. **Re-fine-tune** on the merged file:
   ```bash
   python finetune_lora.py --train_file data/train_with_feedback.jsonl --output_dir models/t5-text2sql-employee-lora
   ```
4. Re-run the benchmark and compare. Repeat as you collect more feedback.
