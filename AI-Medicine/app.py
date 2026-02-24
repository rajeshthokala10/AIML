"""
AI-Medicine: Personalized health advice UI.
- Language: Telugu | English
- Input: text, voice (audio), or video (audio extracted -> STT)
- Output: text + voice (TTS in selected language)
Backend: SLM trained on Telugu health content (nutrition, basic diseases, medicines, chronic level-1).
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import gradio as gr

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
import sys
sys.path.insert(0, str(ROOT))

from backend.inference import generate
from backend.tts_stt import (
    extract_audio_from_video,
    speech_to_text,
    text_to_speech,
    text_to_speech_bytes,
)


def chat_text(question: str, lang: str) -> tuple[str, str | None]:
    """Text input -> model -> text response. Returns (text_reply, path_to_audio or None)."""
    if not (question or "").strip():
        return "Please enter a question.", None
    lang_code = "te" if lang == "Telugu" else "en"
    reply = generate(question.strip(), lang=lang_code)
    try:
        audio_path = text_to_speech(reply, language=lang_code)
        return reply, audio_path
    except Exception:
        return reply, None


def chat_voice(audio_path: str | None, lang: str) -> tuple[str, str | None]:
    """Voice input (audio file) -> STT -> model -> text + TTS. Returns (text_reply, path_to_audio)."""
    if not audio_path:
        return "Please upload an audio file or record.", None
    lang_code = "te" if lang == "Telugu" else "en"
    try:
        text_in = speech_to_text(audio_path, language=lang_code)
    except Exception as e:
        return f"Speech recognition failed: {e}", None
    if not text_in.strip():
        return "Could not understand audio. Try again.", None
    reply = generate(text_in.strip(), lang=lang_code)
    try:
        audio_out = text_to_speech(reply, language=lang_code)
        return reply, audio_out
    except Exception:
        return reply, None


def chat_video(video_path: str | None, lang: str) -> tuple[str, str | None]:
    """Video input -> extract audio -> STT -> model -> text + TTS. Returns (text_reply, path_to_audio)."""
    if not video_path:
        return "Please upload a video file.", None
    try:
        audio_path = extract_audio_from_video(video_path)
    except Exception as e:
        return f"Could not extract audio from video: {e}", None
    return chat_voice(audio_path, lang)


with gr.Blocks(title="AI-Medicine: Personalized Health Advice", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# AI-Medicine: Personalized Health Advice")
    gr.Markdown(
        "**Scope:** Nutrition, basic diseases, medicines, chronic level-1 advice. "
        "This is informational only; consult a doctor for medical decisions."
    )

    lang = gr.Radio(
        choices=["Telugu", "English"],
        value="Telugu",
        label="Language (భాష / Language)",
    )

    with gr.Tabs():
        with gr.TabItem("Text"):
            text_in = gr.Textbox(
                label="Ask (text)",
                placeholder="e.g. పోషకాహారంలో ప్రోటీన్ ఎందుకు ముఖ్యం? / Why is protein important in diet?",
                lines=3,
            )
            text_btn = gr.Button("Get advice")
            text_out = gr.Textbox(label="Response (text)", lines=6)
            text_audio = gr.Audio(label="Response (voice)", type="filepath", visible=True)
            text_btn.click(
                fn=chat_text,
                inputs=[text_in, lang],
                outputs=[text_out, text_audio],
            )

        with gr.TabItem("Voice"):
            voice_in = gr.Audio(label="Record or upload audio", type="filepath", sources=["upload", "microphone"])
            voice_btn = gr.Button("Get advice from voice")
            voice_out = gr.Textbox(label="Response (text)", lines=6)
            voice_audio = gr.Audio(label="Response (voice)", type="filepath")
            voice_btn.click(
                fn=chat_voice,
                inputs=[voice_in, lang],
                outputs=[voice_out, voice_audio],
            )

        with gr.TabItem("Video"):
            video_in = gr.Video(label="Upload video (audio will be used)")
            video_btn = gr.Button("Get advice from video")
            video_out = gr.Textbox(label="Response (text)", lines=6)
            video_audio = gr.Audio(label="Response (voice)", type="filepath")
            video_btn.click(
                fn=chat_video,
                inputs=[video_in, lang],
                outputs=[video_out, video_audio],
            )

    gr.Markdown("---\n*Informational health advice only. Not a substitute for professional medical care.*")

if __name__ == "__main__":
    demo.launch()
