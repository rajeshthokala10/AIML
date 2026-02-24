"""
FastAPI for AI-Medicine: used by React UI and programmatic access.
Endpoints: POST /chat, POST /chat/voice, POST /diet-plan, GET /health.
Swagger UI: /docs — ReDoc: /redoc — OpenAPI JSON: /openapi.json
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
import sys
sys.path.insert(0, str(ROOT))

# Production: serve frontend build from this directory (set by Docker / deployment)
FRONTEND_DIST = ROOT / "frontend_dist"
SERVE_FRONTEND = FRONTEND_DIST.is_dir() and (FRONTEND_DIST / "index.html").exists()
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000").strip()
if CORS_ORIGINS:
    _cors_list = [o.strip() for o in CORS_ORIGINS.split(",") if o.strip()]
else:
    _cors_list = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://127.0.0.1:3000"]

# Lazy imports: inference (torch/transformers) and tts_stt (whisper) load only when /chat or /chat/voice is used.
# This keeps API startup fast so /health and /diet-plan work immediately.
from backend.diet_plan import (
    build_chart_and_totals,
    build_chart_and_totals_from_selections,
    generate_ai_diet_suggestion,
    generate_recommendations,
    get_chart_headers,
    get_foods_for_dropdown,
)

app = FastAPI(
    title="AI-Medicine API",
    description="Personalized health advice (Telugu + English). Health Q&A (text/voice) and Diet Plan with South Indian foods.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DietPlanRequest(BaseModel):
    """Request body for diet plan: age, activity, language, and meals (text or list of food ids per slot)."""
    age: int = Field(30, ge=1, le=120, description="User age in years")
    activity: str = Field("Moderate", description="Activity level: Sedentary, Light, Moderate, Active, Very Active")
    lang: str = Field("en", description="Output language: en (English) or te (Telugu)")
    morning: str | list[str] = Field(default="", description="Breakfast: free text or list of food ids")
    mid_morning: str | list[str] = Field(default="", description="Mid-morning snack")
    lunch: str | list[str] = Field(default="", description="Lunch")
    evening: str | list[str] = Field(default="", description="Evening snack")
    dinner: str | list[str] = Field(default="", description="Dinner")
    late_night: str | list[str] = Field(default="", description="Late-night snack")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "age": 35,
                    "activity": "Moderate",
                    "lang": "en",
                    "morning": ["idli", "dosa", "chutney"],
                    "mid_morning": ["tea", "biscuit"],
                    "lunch": ["rice", "sambar", "dal", "potato_curry"],
                    "evening": ["banana"],
                    "dinner": ["rice", "curd", "potato_curry"],
                    "late_night": ["milk"],
                }
            ]
        }
    }


@app.get("/", include_in_schema=False)
def root():
    """Serve API info (dev) or redirect to frontend (production)."""
    if SERVE_FRONTEND:
        return FileResponse(FRONTEND_DIST / "index.html", media_type="text/html")
    return HTMLResponse(
        "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>AI-Medicine API</title></head><body style='font-family:system-ui;max-width:560px;margin:48px auto;padding:24px;'>"
        "<h1>AI-Medicine API</h1><p>Backend is running. <strong>Swagger:</strong> <a href='/docs'>/docs</a> | "
        "<strong>ReDoc:</strong> <a href='/redoc'>/redoc</a></p>"
        "<p><strong>To load the UI (Landing, Health Q&A, Diet Plan):</strong> in a separate terminal run "
        "<code>cd frontend && npm install && npm run dev</code>, then open <a href='http://localhost:5173'>http://localhost:5173</a>.</p>"
        "</body></html>",
        media_type="text/html",
    )


@app.get("/health", tags=["Health"], summary="Health check", response_description="API status")
def health():
    """Basic health check. Use this to validate the backend is running. Returns status ok."""
    return {"status": "ok"}


@app.post("/chat", tags=["Health Q&A"], summary="Text chat", response_description="Model response text")
def chat(question: str = Form(..., description="User question in Telugu or English"), lang: str = Form("te", description="Language: te (Telugu) or en (English)")):
    """Send a text question and get a text response. Lang selects output language (te/en). First call may load the model (1–2 min)."""
    from backend.inference import generate
    lang_code = "te" if lang == "te" else "en"
    reply = generate(question.strip(), lang=lang_code)
    return {"response": reply, "lang": lang_code}


@app.post("/chat/voice", tags=["Health Q&A"], summary="Voice/video chat", response_description="Audio file or JSON with response text")
async def chat_voice(
    file: UploadFile = File(..., description="Audio (e.g. .wav, .mp3) or video (.mp4, .webm); audio is extracted for video"),
    lang: str = Form("te", description="Language: te or en"),
    return_audio: bool = Form(True, description="If true, returns TTS audio; else JSON with response text"),
):
    """Upload audio or video. Speech is transcribed, sent to the model, and you get text and optional TTS audio. Lang: te or en."""
    from backend.inference import generate
    from backend.tts_stt import extract_audio_from_video, speech_to_text, text_to_speech
    suffix = Path(file.filename or "").suffix.lower()
    is_video = suffix in (".mp4", ".webm", ".mov", ".avi", ".mkv")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        path = tmp.name
    try:
        if is_video:
            path = extract_audio_from_video(path)
        lang_code = "te" if lang == "te" else "en"
        text_in = speech_to_text(path, language=lang_code)
        if not text_in.strip():
            return JSONResponse({"error": "Could not transcribe audio.", "response": ""}, status_code=400)
        reply = generate(text_in.strip(), lang=lang_code)
        if return_audio:
            audio_path = text_to_speech(reply, language=lang_code)
            return FileResponse(audio_path, media_type="audio/mpeg", filename="response.mp3")
        return {"response": reply, "input_text": text_in, "lang": lang_code}
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


@app.get("/diet-plan/foods", tags=["Diet Plan"], summary="List foods for dropdown", response_description="List of foods with id, name_en, name_te, label")
def diet_plan_foods(
    lang: str = Query("en", description="Language for labels: en or te"),
    meal_slot: str | None = Query(None, description="Filter by meal: morning, mid_morning, lunch, evening, dinner, late_night"),
):
    """Return foods for the UI dropdown. Optional meal_slot filters by time. South Indian foods only."""
    return {"foods": get_foods_for_dropdown(lang, meal_slot=meal_slot)}


@app.post("/diet-plan", tags=["Diet Plan"], summary="Get diet plan and chart", response_description="Chart, summary, recommendations, consumed/targets")
def diet_plan(body: DietPlanRequest):
    """Compute daily nutrition from age, activity, and meals. Meals can be free text or list of food ids per slot. Returns chart (EN/Telugu), summary, recommendations, and optional AI suggestion."""
    age = max(1, min(120, body.age or 30))
    activity = body.activity or "Moderate"
    lang = (body.lang or "en").lower()
    if lang not in ("en", "te"):
        lang = "en"

    use_selections = isinstance(body.morning, list)
    if use_selections:
        meals_dict = {
            "morning": body.morning or [],
            "mid_morning": body.mid_morning or [],
            "lunch": body.lunch or [],
            "evening": body.evening or [],
            "dinner": body.dinner or [],
            "late_night": body.late_night or [],
        }
        rows, consumed, targets = build_chart_and_totals_from_selections(age, activity, meals_dict, lang)
        headers = get_chart_headers(lang)
    else:
        rows, consumed, targets = build_chart_and_totals(
            age, activity,
            body.morning or "", body.mid_morning or "", body.lunch or "",
            body.evening or "", body.dinner or "", body.late_night or "",
        )
        headers = get_chart_headers(lang)
        if lang == "te":
            for row in rows:
                if len(row) > 1 and row[1] == "(subtotal)":
                    row[1] = "(ఉపమొత్తం)"
                if len(row) > 0 and row[0] == "TOTAL (day)":
                    row[0] = "మొత్తం (రోజు)"

    recommendations = generate_recommendations(consumed, targets, age, activity, lang)
    ai_suggestion = generate_ai_diet_suggestion(age, activity, consumed, targets, lang)
    if lang == "te":
        summary = (
            f"రోజువారీ మొత్తాలు: కేలరీలు {consumed['calories']} kcal, ప్రోటీన్ {consumed['protein_g']}g, "
            f"కార్బోహైడ్రేట్స్ {consumed['carbs_g']}g, ఫ్యాట్ {consumed['fat_g']}g, ఫైబర్ {consumed['fiber_g']}g. "
            f"లక్ష్యాలు (వయస్సు {age}, {activity}): కేలరీలు ~{targets['calories']} kcal."
        )
    else:
        summary = (
            f"Daily totals (consumed): Calories {consumed['calories']} kcal, Protein {consumed['protein_g']}g, "
            f"Carbs {consumed['carbs_g']}g, Fat {consumed['fat_g']}g, Fiber {consumed['fiber_g']}g. "
            f"Targets (age {age}, {activity}): Calories ~{targets['calories']} kcal, Protein ~{targets['protein_g']}g."
        )
    return {
        "chart": {"headers": headers, "rows": rows},
        "summary": summary,
        "recommendations": recommendations,
        "ai_suggestion": ai_suggestion or "",
        "consumed": consumed,
        "targets": targets,
    }


# --- Production: serve built frontend (SPA) when frontend_dist is present ---
if SERVE_FRONTEND:
    _assets_dir = FRONTEND_DIST / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="frontend_assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa_fallback(path: str):
        """Serve index.html for frontend routes (SPA); skip API and docs."""
        if path.startswith(("api/", "docs", "redoc", "openapi", "health")) or path.startswith("assets/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not found")
        # Serve root-level files (vite.svg, favicon.ico) if present
        if path and "." in path and (FRONTEND_DIST / path).is_file():
            return FileResponse(FRONTEND_DIST / path)
        return FileResponse(FRONTEND_DIST / "index.html", media_type="text/html")
