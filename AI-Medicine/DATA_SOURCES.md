# Open Source Data for AI-Medicine (Telugu Health)

This document lists **open source** datasets and sources used to train the backend on **Telugu health content** (nutrition, basic diseases, medicines, chronic level-1 advice).

---

## 1. Telugu / Indic Medical QA

### MedMCQA-Indic

- **Description**: Indic (including Telugu) medical multiple-choice QA. 50k+ samples; from MedMCQA (AIIMS/NEET PG style).
- **Languages**: Telugu (te), Hindi, Tamil, and other Indic languages.
- **Use**: Instruction-style QA for fine-tuning; filter by `lang == "te"` for Telugu-only.
- **License**: MIT (verify on Hugging Face).
- **Hugging Face**: Search for `medmcqa-indic` or `ai4bharat/medmcqa-indic`; Eka Care also hosts Indic version (e.g. `ekacare/MedMCQA-Indic`).
- **Format**: Typically question, options, correct answer; convert to `{"instruction": "question in Telugu", "output": "answer in Telugu"}`.

### NLP4Health-2025 (Multilingual Medical Dialogues)

- **Description**: 45k+ multi-turn patient–provider dialogues; 10 languages, may include Telugu.
- **Use**: If Telugu subset exists, use for dialogue-style health QA.
- **Reference**: ACL Anthology, NLP4Health workshop; check dataset card for Telugu availability.

---

## 2. Generic Telugu NLP (Optional)

### IndicLLMSuite / AI4Bharat

- **Description**: Pipelines and tools for Indic (including Telugu) data and LLMs.
- **Use**: Data prep, translation, or alignment of English health content to Telugu.
- **GitHub**: `ai4bharat/indicllmsuite` (or similar).

### Telugu Wikipedia / Health Articles

- **Description**: Open content; can scrape or use dumps for health-related articles.
- **Use**: Curate paragraphs for “definition” or “general advice” in Telugu; convert to QA if needed.
- **Caution**: Validate and align with medical guidelines; use only for general wellness/nutrition/level-1.

---

## 3. English Health QA (Translate to Telugu)

Use these to build **Telugu-only** training data by **translating** to Telugu and optionally back-translating for quality.

### MedQuAD

- **Description**: Medical question-answering pairs (English).
- **Use**: Translate Q&A to Telugu (NLLB, IndicTrans2); add to `telugu_health_train.jsonl`.

### PubMed QA / Medical FAQs

- **Description**: Biomedical and clinical QA (English).
- **Use**: Select nutrition, basic diseases, medicines, chronic level-1; translate to Telugu; format as instruction/output.

### Translation models

- **NLLB** (No Language Left Behind): Many-to-many; supports Telugu.
- **IndicTrans2**: English ↔ Indic (including Telugu).

---

## 4. Curated Telugu Health Content (Custom)

- **Government / public health**: AP, Telangana health department bulletins, nutrition guidelines (if openly available).
- **Open health FAQs**: Any CC-licensed or public-domain Telugu health FAQs; format as instruction + output.
- **Scope**: Nutrition, common ailments, OTC/first-line medicines, chronic disease level-1 advice only; exclude diagnosis and prescription.

---

## 5. Recommended Data Pipeline for This Project

1. **Primary**: MedMCQA-Indic — filter Telugu; convert to instruction/output; restrict topics to nutrition, basic diseases, medicines, chronic level-1.
2. **Secondary**: English MedQuAD (or similar) → translate to Telugu → add to training set.
3. **Optional**: NLP4Health Telugu subset (if available) for dialogue-style data.
4. **Optional**: Curated Telugu FAQs from open sources; add to `data/raw/` and include in `prepare_telugu_health_data.py`.

Output: **Single Telugu-only** instruction dataset (e.g. `data/processed/telugu_health_train.jsonl`) for SLM fine-tuning. No English in the training data so the model is “Telugu-only” for health content; UI still offers Telugu/English via language selector and optional translation at inference.
