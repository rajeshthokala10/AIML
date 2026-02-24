# AI-Medicine: End-to-End Step-by-Step Build Guide

This document gives a **step-by-step approach** to build the personalized health advice system: Telugu-trained backend, Telugu/English UI, voice/video input, text and voice output.

---

## Overview

| Step | Phase | What you do |
|------|--------|--------------|
| 1 | Setup | Create folder, install dependencies |
| 2 | Data | Source and prepare Telugu health content (open source) |
| 3 | Model | Choose and download SLM; optionally fine-tune on Telugu health |
| 4 | Backend | Inference API + STT/TTS (Telugu + English) |
| 5 | UI | Web app with language toggle, voice/video input, text+voice output |
| 6 | Deploy | Run locally or deploy for target customers |

---

## Step 1: Environment and Folder Setup

**1.1 Create project folder (already done)**

- Folder: `AIML/AI-Medicine/`

**1.2 Python environment**

```bash
cd AIML/AI-Medicine
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**1.3 Config**

- `config/model.yaml` — SLM name, max tokens, device.
- `config/training.yaml` — LoRA, epochs, batch size, paths to data.

---

## Step 2: Telugu Health Data (Open Source, Exclusive for Training)

Backend is trained on **Telugu content only** (nutrition, basic diseases, medicines, chronic level-1).

**2.1 Primary sources (Telugu / Indic)**

| Source | Content | Use |
|--------|---------|-----|
| **MedMCQA-Indic** (Hugging Face: `ai4bharat/medmcqa-indic` or similar Telugu subset) | Telugu medical QA (50k+ samples) | Fine-tune / instruction data |
| **NLP4Health-2025** (if Telugu subset available) | Multilingual medical dialogues | Dialogue-style QA |
| **Curated Telugu health FAQs** | Nutrition, basic diseases, medicines, chronic level-1 | Build from government/health sites (e.g. AP/Telangana health bulletins) |

**2.2 Fallback: English → Telugu**

- Use open source English health QA (e.g. MedQuAD, PubMed QA).
- Translate to Telugu with NLLB or IndicTrans2; validate and curate.
- Store as instruction pairs: `{"instruction": "...", "output": "..."}` in Telugu.

**2.3 Run data preparation**

```bash
python scripts/prepare_telugu_health_data.py --sources medmcqa_indic custom_faqs --output data/processed/telugu_health_train.jsonl
```

- Output: **Telugu-only** instruction/turn data in `data/processed/` for training.

**2.4 Data format for training**

- One JSONL per line: `{"instruction": "తెలుగు ప్రశ్న లేదా సూచన", "output": "తెలుగు జవాబు"}`  
- Optional: add `"input": ""` and system prompt in Telugu stating scope (nutrition, basic diseases, medicines, chronic level-1, not replacement for doctor).

---

## Step 3: Small Language Model (SLM) and Training

**3.1 Choose SLM**

- **TinyLlama-1.1B-Chat** — 1.1B params, good for LoRA fine-tuning, runs on CPU/small GPU.
- **SmolLM-360M-Instruct** — Smaller, faster; suitable for low-resource.
- **Phi-2 (2.7B)** — Better quality; use if you have ~8GB+ GPU.

**3.2 Download base model**

```bash
python scripts/download_slm.py --model_name TinyLlama/TinyLlama-1.1B-Chat-v1.0 --save_dir models/slm_base
```

**3.3 Fine-tune on Telugu health (LoRA)**

- Train **only** on the Telugu health data from Step 2.
- Use PEFT (LoRA) so training is feasible on a single GPU or CPU.

```bash
python scripts/finetune_slm.py --config config/training.yaml --train_file data/processed/telugu_health_train.jsonl --output_dir models/ai_medicine_telugu_lora
```

- `config/training.yaml`: LoRA rank/alpha, epochs, batch size, learning rate, max length.
- Save adapter + tokenizer in `models/ai_medicine_telugu_lora/`.

**3.4 Inference model path**

- Set in `config/model.yaml`: `model_path: models/ai_medicine_telugu_lora` (or `models/slm_base` if not fine-tuned).

---

## Step 4: Backend — Inference + Voice (STT/TTS)

**4.1 Load model**

- `backend/model.py`: Load base SLM + LoRA adapter (if present), tokenizer; run on CPU/CUDA from config.

**4.2 Text inference**

- `backend/inference.py`:  
  - Input: user message (Telugu or English from UI).  
  - Optional system prompt in Telugu: scope = nutrition, basic diseases, medicines, chronic level-1; not a substitute for doctor.  
  - Generate response (Telugu or English per user choice).  
  - Return text.

**4.3 Voice input (STT)**

- **Whisper** (open source): supports Telugu and English.
- `backend/tts_stt.py`:  
  - `speech_to_text(audio_path, language="te" or "en")` → text.  
  - For video: extract audio (e.g. ffmpeg) → WAV → same STT.

**4.4 Voice output (TTS)**

- **Telugu**: Coqui TTS or **Indic-TTS** (AI4Bharat) Telugu model.  
- **English**: Coqui TTS or gTTS.  
- `backend/tts_stt.py`: `text_to_speech(text, language="te" or "en")` → audio file or bytes.

**4.5 API (optional)**

- `api.py`: FastAPI endpoints: `/chat` (text), `/chat/voice` (upload audio/video → text + voice response).  
- Used by UI or external clients.

---

## Step 5: UI — Language, Voice/Video Input, Text + Voice Output

**5.1 Framework**

- **Gradio** (or Streamlit): quick web UI, file upload for audio/video.

**5.2 Language selector**

- Dropdown or tabs: **Telugu** | **English**.  
- All prompts, labels, and model I/O use this choice (STT language, TTS language, optional prompt language).

**5.3 Input modes**

- **Text**: Textbox → send to backend → show text response + optional “Play voice” button.  
- **Voice**: Upload audio (or record) → STT (Telugu/English) → backend → text response + TTS (Telugu/English).  
- **Video**: Upload video → extract audio → same as voice (STT → backend → text + TTS).

**5.4 Output**

- Always show **text** response.  
- Button or auto-play **voice** (TTS in selected language).

**5.5 Run app**

```bash
python app.py
# Open URL (e.g. http://127.0.0.1:7860)
```

---

## Step 6: End-to-End Flow (Summary)

1. **User** selects **Telugu** or **English** in UI.  
2. **User** provides input: **text**, **voice** (audio), or **video** (audio extracted).  
3. If voice/video → **STT** (Whisper, Telugu or English) → text.  
4. **Backend** (SLM trained on Telugu health) takes text + language; returns **text** answer (in chosen language if you add translation step, or keep Telugu and add optional on-the-fly translation).  
5. **UI** shows **text** and offers **voice** output via **TTS** (Telugu or English).  
6. Optional: **API** for programmatic access (same backend).

---

## Step 7: Deployment (High Level)

- **Local**: Run `python app.py` and use in LAN.  
- **Server**: Run behind reverse proxy (e.g. Nginx), use env vars for model path and API keys (if any).  
- **Disclaimer**: Show clearly in UI that this is informational only; users must consult doctors for medical decisions.

---

## File Checklist

- [ ] `requirements.txt` — Python deps (torch, transformers, peft, gradio, whisper, TTS, etc.).  
- [ ] `config/model.yaml` — SLM path, device, max tokens.  
- [ ] `config/training.yaml` — LoRA, data path, epochs.  
- [ ] `scripts/prepare_telugu_health_data.py` — Build Telugu-only train data.  
- [ ] `scripts/download_slm.py` — Download SLM.  
- [ ] `scripts/finetune_slm.py` — LoRA fine-tune on Telugu health.  
- [ ] `backend/model.py` — Load SLM + LoRA.  
- [ ] `backend/inference.py` — Chat/completion.  
- [ ] `backend/tts_stt.py` — STT (Whisper) + TTS (Telugu/English).  
- [ ] `app.py` — Gradio UI (language, text/voice/video, text+voice out).  
- [ ] `api.py` — Optional FastAPI.  
- [ ] `DATA_SOURCES.md` — Linked open source datasets and usage.

---

## Order of Execution (Recommended)

1. **Step 1** — Setup folder, venv, install deps, create configs.  
2. **Step 2** — Prepare Telugu health data; validate `telugu_health_train.jsonl`.  
3. **Step 3** — Download SLM; fine-tune with LoRA on Telugu data; set `model_path`.  
4. **Step 4** — Implement backend (model load, inference, STT, TTS).  
5. **Step 5** — Implement UI (language, input modes, text+voice output).  
6. **Step 6** — Test end-to-end in Telugu and English.  
7. **Step 7** — Deploy and add disclaimer.
