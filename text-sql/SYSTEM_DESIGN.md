# Text-SQL System Design

**Diagram view:** Open [SYSTEM_DESIGN_DIAGRAMS.html](SYSTEM_DESIGN_DIAGRAMS.html) in a browser to see all diagrams rendered visually.

This document describes the architecture of the **text-sql** project: a Text-to-SQL application that converts natural language questions into SQLite queries using a small T5 model, with optional LoRA fine-tuning, RAG at inference, and human feedback learning.

---

## 1. Tech Stack Diagram

The following diagram shows all technologies used across the application layers.

```mermaid
flowchart TB
    subgraph UI["🖥️ Presentation Layer"]
        Gradio["Gradio (≥4.0)"]
    end

    subgraph App["⚙️ Application Layer"]
        Python["Python 3"]
        Pandas["Pandas"]
    end

    subgraph ML["🤖 ML / Inference Layer"]
        PyTorch["PyTorch"]
        Transformers["Transformers (Hugging Face)"]
        T5["T5 (Seq2Seq LM)"]
        PEFT["PEFT (LoRA/QLoRA)"]
        SentenceTransformers["sentence-transformers"]
    end

    subgraph Data["📦 Data & Storage"]
        SQLite["SQLite (sqlite3)"]
        JSONL["JSONL (train/eval/feedback)"]
    end

    subgraph Training["🔧 Training Pipeline"]
        Datasets["datasets (Hugging Face)"]
        Seq2SeqTrainer["Seq2SeqTrainer"]
        LoRA["LoRA Config"]
    end

    subgraph Support["📚 Support Libraries"]
        SentencePiece["sentencepiece"]
        Protobuf["protobuf"]
        Accelerate["accelerate"]
    end

    Gradio --> Python
    Python --> Pandas
    Python --> PyTorch
    Python --> Transformers
    Transformers --> T5
    Transformers --> PEFT
    PEFT --> LoRA
    Python --> SentenceTransformers
    Python --> SQLite
    Python --> JSONL
    Transformers --> SentencePiece
    Transformers --> Protobuf
    PyTorch --> Accelerate
    Training --> Datasets
    Training --> Seq2SeqTrainer
    Training --> PEFT
```

### Tech Stack Summary

| Layer | Technology | Purpose |
|-------|------------|---------|
| **UI** | Gradio | Web UI for questions, SQL output, results, and feedback |
| **Runtime** | Python 3 | Application and scripts |
| **Data display** | Pandas | Query results as DataFrames in Gradio |
| **ML framework** | PyTorch | Model execution and training |
| **NLP / Model** | Transformers | T5 model load/generate; Seq2Seq training |
| **Base model** | `cssupport/t5-small-awesome-text-to-sql` | Pre-trained text-to-SQL T5 |
| **Adaptation** | PEFT (LoRA/QLoRA) | Fine-tuned adapters, optional 4-bit |
| **RAG** | sentence-transformers | Embeddings for few-shot example retrieval |
| **Database** | SQLite (stdlib `sqlite3`) | Employee sample DB and query execution |
| **Training data** | JSONL | train/eval/feedback (question, gold_sql) |
| **Training** | datasets, Seq2SeqTrainer | Data loading and LoRA fine-tuning |
| **Support** | sentencepiece, protobuf, accelerate | Tokenization, serialization, distributed training |

---

## 2. High-Level System Diagram

End-to-end flow: user question → UI → app → model/DB/RAG → response.

```mermaid
flowchart LR
    subgraph User["User"]
        Q["Natural language question"]
        R["SQL + results / feedback"]
    end

    subgraph System["Text-SQL System"]
        UI["Gradio UI\n(app.py)"]
        App["App logic\n(schema, execute, feedback)"]
        Model["Text-to-SQL model\n(model.py)"]
        RAG["RAG (optional)\n(rag.py)"]
        DB["SQLite DB\n(db.py)"]
    end

    subgraph Data["Data & Models"]
        Schema["DB schema (prompt)"]
        Examples["train_employee.jsonl"]
        EmployeesDB["employees.db"]
        Adapter["LoRA adapter (optional)"]
    end

    Q --> UI
    UI --> App
    App --> Schema
    App --> RAG
    RAG --> Examples
    App --> Model
    Model --> Adapter
    App --> DB
    DB --> EmployeesDB
    DB --> UI
    Model --> UI
    UI --> R
```

### High-Level Flow (Steps)

1. **User** enters a natural language question in the Gradio UI.
2. **App** loads DB schema, optionally retrieves similar (question, SQL) examples via **RAG** from `train_employee.jsonl`.
3. **Model** receives schema + (optional) few-shot examples + question, generates SQL (using base T5 + optional LoRA adapter).
4. **App** validates SQL (SELECT-only), then **DB** runs it against `employees.db` and returns columns/rows.
5. **UI** shows generated SQL, result table, and status; user can mark Correct/Incorrect and optionally provide correct SQL.
6. **Feedback** is written to `feedback.jsonl`; `merge_feedback_into_train.py` and `finetune_lora.py` implement the human-feedback learning loop.

---

## 3. Low-Level System Diagram

Detailed components, files, and data flow.

```mermaid
flowchart TB
    subgraph Entry["Entry points"]
        app_py["app.py\n(Gradio server)"]
        run_benchmark["run_benchmark.py"]
        finetune_lora["finetune_lora.py"]
        merge_feedback["merge_feedback_into_train.py"]
        seed_db["seed_employee_db.py"]
        compare_bench["compare_benchmark_results.py"]
    end

    subgraph text2sql_demo["text2sql_demo package"]
        model_py["model.py\n• generate_sql()\n• validate_sql_for_execution()\n• _load() [PEFT/base]"]
        rag_py["rag.py\n• get_similar_examples()\n• build_few_shot_prompt()\n• SentenceTransformer embeddings"]
        db_py["db.py\n• init_employee_db()\n• run_select_query()"]
    end

    subgraph External_Models["External / saved artifacts"]
        HF_Model["HuggingFace: t5-small-awesome-text-to-sql"]
        LoRA_dir["models/t5-text2sql-employee-lora\n(adapter_config, weights)"]
    end

    subgraph Data_Files["Data files"]
        employees_db["data/employees.db\n(departments, employees, salaries)"]
        train_jsonl["data/train_employee.jsonl\n(question, gold_sql)"]
        eval_jsonl["data/eval_employee.jsonl"]
        feedback_jsonl["data/feedback.jsonl\n(question, predicted_sql, accepted, correct_sql)"]
    end

    subgraph Training_Flow["Training pipeline"]
        load_jsonl["load_jsonl(train_file)"]
        Dataset["Dataset (HuggingFace)"]
        DataCollator["DataCollatorForSeq2Seq"]
        LoraConfig["LoraConfig (PEFT)"]
        Trainer["Seq2SeqTrainer"]
        save_adapter["Save adapter + base_model_id.txt"]
    end

    app_py --> model_py
    app_py --> rag_py
    app_py --> db_py
    app_py --> feedback_jsonl
    model_py --> HF_Model
    model_py --> LoRA_dir
    rag_py --> train_jsonl
    db_py --> employees_db
    run_benchmark --> model_py
    run_benchmark --> db_py
    run_benchmark --> eval_jsonl
    finetune_lora --> model_py
    finetune_lora --> load_jsonl
    load_jsonl --> Dataset
    Dataset --> DataCollator
    finetune_lora --> LoraConfig
    DataCollator --> Trainer
    LoraConfig --> Trainer
    Trainer --> save_adapter
    save_adapter --> LoRA_dir
    merge_feedback --> feedback_jsonl
    merge_feedback --> train_jsonl
    seed_db --> db_py
    compare_bench --> eval_jsonl
```

### Low-Level Component Roles

| Component | File(s) | Responsibility |
|-----------|---------|----------------|
| **Web UI** | `app.py` | Gradio Blocks: question input, execute checkbox, schema/SQL/result/status, Correct/Incorrect feedback, examples. Calls `handle()` → model + db + feedback save. |
| **SQL generation** | `text2sql_demo/model.py` | Load base or PEFT adapter; build prompt (schema ± RAG few-shot); tokenize; beam decode; extract SELECT; validate for execution. |
| **RAG** | `text2sql_demo/rag.py` | Load JSONL examples; embed questions (sentence-transformers); cosine similarity; return top-k; build few-shot prompt. |
| **Database** | `text2sql_demo/db.py` | Create/seed SQLite schema; return schema string for prompt; run SELECT and return (columns, rows). |
| **Benchmark** | `run_benchmark.py` | Load eval JSONL; for each (question, gold_sql): generate SQL, compare exact/execution match; write results JSON. |
| **Fine-tuning** | `finetune_lora.py` | Load train/eval JSONL; build "tables:" + schema + "query for: Q" inputs; Seq2SeqTrainer + LoRA; save adapter and base_model_id.txt. |
| **Feedback loop** | `merge_feedback_into_train.py` | Read feedback.jsonl; merge corrections (correct_sql or accepted predicted_sql) into training JSONL for re-fine-tuning. |
| **Comparison** | `compare_benchmark_results.py` | Compare baseline vs after-LoRA result JSONs. |

### Environment / Configuration

- `TEXT2SQL_MODEL_ID`: path or ID for model (e.g. `models/t5-text2sql-employee-lora`).
- `TEXT2SQL_RAG_EXAMPLES`: path to JSONL for RAG (default `data/train_employee.jsonl`).
- DB path: `data/employees.db` (overridable in scripts).

---

## 4. Data Flow Summary

```mermaid
sequenceDiagram
    participant U as User
    participant G as Gradio (app.py)
    participant M as model.py
    participant R as rag.py
    participant D as db.py
    participant SQLite as employees.db

    U->>G: Question + Execute?
    G->>D: init_employee_db()
    D->>SQLite: CREATE IF NOT EXISTS, seed
    D-->>G: schema_prompt
    G->>R: get_similar_examples(question) [if RAG]
    R-->>G: few-shot examples
    G->>M: generate_sql(schema, question, rag=...)
    M-->>G: SQL string
    G->>M: validate_sql_for_execution(SQL)
    alt Execute and valid
        G->>D: run_select_query(db_path, SQL)
        D->>SQLite: SELECT
        SQLite-->>D: rows
        D-->>G: columns, rows
    end
    G-->>U: Schema, SQL, table, status
    U->>G: Correct / Incorrect (+ correct_sql)
    G->>G: save_feedback() → feedback.jsonl
```

---

This file is the single system design document for **text-sql**, containing tech stack, high-level and low-level architecture, and main data flows.
