# AI-Medicine: Personalized Health Advice (Telugu + English)

Personalized health advice system for a **Telugu-first** backend, with **Telugu or English** UI. Supports **voice and video input** and **text + voice output**. Covers nutrition, basic diseases, medicines, and chronic problems with level-1 treatment advice.

---

## Quick Start

### React UI (recommended for best inputs and response display)

**Backend (port 8000) serves only the API and Swagger — it does not serve the React UI.** You must start the frontend in a **second terminal**; then open **http://localhost:5173** for the UI.

**One script (backend + frontend in background):** from `AI-Medicine` run `./run.sh`. Opens backend on 8000 and frontend on 5173; press **Ctrl+C** to stop both.

```bash
cd AI-Medicine
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd frontend && npm install && cd ..   # one-time

# Option A: single script (both in background)
./run.sh

# Option B: start backend and frontend separately (two terminals)
# See "Start backend and frontend separately" below.
```

Open **http://localhost:5173** — Health Q&A (language, text/voice input, response + audio) and **Diet Plan** (age, lifestyle, **dropdown multi-select** for food habits per meal; **Telugu or English** input and response; chart and recommendations in selected language; **AI-doctor theme**).

---

### Start backend and frontend separately

Use **two terminals** so you can see logs for each.

**Terminal 1 — Backend (FastAPI on port 8000):**

```bash
cd AI-Medicine
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uvicorn api:app --port 8000 --host 127.0.0.1
```

- API: **http://127.0.0.1:8000**
- Swagger: **http://127.0.0.1:8000/docs**

**Terminal 2 — Frontend (Vite/React on port 5173):**  
Run from the **frontend** folder (package.json is there, not in AI-Medicine root):

```bash
cd AI-Medicine/frontend
npm install   # one-time if not done
npm run dev
```

- UI: **http://localhost:5173**

Leave both terminals running. Stop with Ctrl+C in each.

**If the page is blank or loading for a long time:**
- The **API** starts quickly (no model load at startup). Ensure it’s running: `uvicorn api:app --port 8000` from the `AI-Medicine` folder.
- Open the **React app** at **http://localhost:5173** (not the API port 8000). If the frontend is not loading, start it in a second terminal: `cd frontend && npm install && npm run dev`.
- **Diet Plan** works immediately. The **first Health Q&A request** can take 1–2 minutes (AI model loads on first use); later requests are faster.

**If the backend keeps shutting down and reloading, or you see `OSError: [Errno 89] Operation canceled`:**  
Run **without** `--reload` for a stable server: `uvicorn api:app --port 8000`. Reload can trigger errno 89 when the process is canceled mid-load, and WatchFiles may still watch `.venv` or other dirs despite `--reload-exclude`. Always start uvicorn from the **AI-Medicine** directory.

**Network tab shows "Referrer Policy: strict-origin-when-cross-origin":**  
That is a normal response header, not an error. If the page is blank or fails to load: (1) Check the **Status** of the request to `http://localhost:5173/` — it should be **200**. (2) Open **Console** (F12 → Console) for JavaScript errors. (3) Ensure the frontend is started with `npm run dev` from the `frontend` folder.

### Gradio UI

```bash
cd AI-Medicine
pip install -r requirements.txt
python app.py             # Health Q&A → http://127.0.0.1:7860
python app_diet_plan.py   # Diet plan → http://127.0.0.1:7861
```

Open the Gradio URL. Select **Telugu** or **English**, use text/voice/video input, get text + voice response.

---

## API docs (Swagger) and testing

With the backend running (`uvicorn api:app --reload --port 8000`), use these URLs to validate and test the APIs:

| URL | Purpose |
|-----|--------|
| **http://localhost:8000/docs** | **Swagger UI** — interactive API docs; try endpoints (GET/POST) and see request/response schemas |
| **http://localhost:8000/redoc** | **ReDoc** — alternative API documentation |
| **http://localhost:8000/openapi.json** | **OpenAPI JSON** — machine-readable spec for tools/CLI |

**Basic API tests (Swagger UI):**

1. Open **http://localhost:8000/docs**.
2. **Health check:** Expand `GET /health` → **Try it out** → **Execute**. Expect `200` and `{"status": "ok"}`.
3. **Diet foods:** Expand `GET /diet-plan/foods` → **Try it out** → set `lang` (e.g. `en`), optionally `meal_slot` (e.g. `lunch`) → **Execute**. Expect `200` and a list of foods.
4. **Diet plan:** Expand `POST /diet-plan` → **Try it out** → use the example body (age, activity, lang, meal arrays) or edit it → **Execute**. Expect `200` and chart, summary, recommendations.
5. **Text chat:** Expand `POST /chat` → **Try it out** → set `question` and `lang` → **Execute**. (First call may be slow while the model loads.)

---

## Features

- **Backend**: Small Language Model (SLM) trained on **Telugu health content** (nutrition, basic diseases, medicines, chronic level-1 advice).
- **Input**: Text, **voice** (audio), or **video** (audio extracted → speech-to-text).
- **Output**: **Text** and **voice** (TTS in selected language).
- **UI**: Language selector **Telugu | English** for all interactions.
- **Data**: Open source — MedMCQA-Indic (Telugu), translated health FAQs, curated Telugu health corpus.

---

## Diet Plan (React UI at /diet-plan)

**Personalized diet plan** based on age, lifestyle, and daily food habits (morning to night). Outputs a **daily nutrition chart** (macros + micronutrients) and **recommendations** to modify routine.

- **React UI** (recommended): Open **http://localhost:5173/diet-plan**. **Dropdown multi-select** for each meal (Morning, Mid-morning, Lunch, Evening, Dinner, Late night); select multiple foods per meal. **Language**: Telugu or English — labels, chart headers, summary, and recommendations in the selected language. **AI-doctor theme**: teal/blue gradient background, white cards.
- **Gradio** (separate URL): run `python app_diet_plan.py` → **http://127.0.0.1:7861**
- **Inputs**: Age, activity level, food habits (dropdown selections or text).
- **Output**: Chart (English or Telugu) + summary + recommendations (English or Telugu).
- **Data**: Open source — `data/diet_plan/food_nutrients.json`; see [DATA_SOURCES_DIET.md](DATA_SOURCES_DIET.md).

```bash
python app_diet_plan.py   # Diet plan only → http://127.0.0.1:7861
```

---

## Project Structure

```
AI-Medicine/
├── README.md                 # This file
├── SYSTEM_DIAGRAMS.html      # High-level and low-level system diagrams (open in browser)
├── STEP_BY_STEP.md           # End-to-end build steps
├── DATA_SOURCES.md           # Open source Telugu health data
├── DATA_SOURCES_DIET.md      # Diet plan open source data (English)
├── requirements.txt
├── config/
│   ├── model.yaml            # SLM and inference settings
│   └── training.yaml         # Fine-tuning settings
├── data/
│   ├── raw/
│   ├── processed/
│   └── diet_plan/            # Food → nutrients (food_nutrients.json)
├── models/                   # Fine-tuned model checkpoints
├── scripts/
│   ├── prepare_telugu_health_data.py
│   ├── finetune_slm.py
│   └── download_slm.py
├── backend/
│   ├── model.py
│   ├── inference.py
│   ├── tts_stt.py            # Voice in/out (Telugu + English)
│   └── diet_plan.py          # Diet plan: parse meals, chart, recommendations
├── app.py                    # Gradio UI: language, voice/video, text+voice out (port 7860)
├── app_diet_plan.py          # Diet plan Gradio — separate URL (port 7861)
├── api.py                    # FastAPI: /chat, /chat/voice, /diet-plan (for React UI)
└── frontend/                 # React UI (Vite + Tailwind)
    ├── src/
    │   ├── pages/Health.tsx  # Health Q&A: language, text/voice input, response + audio
    │   ├── pages/DietPlan.tsx # Diet plan: age, lifestyle, meals → chart + recommendations
    │   └── api.ts            # API client
    └── package.json
```

---

## Deployment (Docker / AWS)

Run as a **single container** (API + frontend on port 8000):

```bash
docker compose up -d
# Open http://localhost:8000
```

**If you see `command not found: docker`:** install [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/), start it, then run the command again.

**Without Docker:** use the [Quick Start](#quick-start) above — from `AI-Medicine` run `./run.sh`, then open **http://localhost:5173** (backend on 8000, frontend on 5173).

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for packaging, Docker, and AWS (App Runner, ECS, EC2) best practices.

---

## Documentation

- **[STEP_BY_STEP.md](STEP_BY_STEP.md)** — End-to-end steps: data → training → backend → UI → deployment.
- **[DATA_SOURCES.md](DATA_SOURCES.md)** — Open source Telugu/Indic health datasets and how to use them.

---

## Disclaimer

This system provides **informational health advice only**, not medical diagnosis or treatment. Users must consult qualified healthcare providers for medical decisions. Use only for nutrition, basic wellness, and level-1 chronic management guidance within the scope described in the app.
