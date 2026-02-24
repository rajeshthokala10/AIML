"""
Speech-to-text (STT) and text-to-speech (TTS) for Telugu and English.
Voice/video input -> STT -> text; text output -> TTS -> voice.
"""
from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parent.parent

# Language codes: te = Telugu, en = English
Lang = Literal["te", "en"]


def extract_audio_from_video(video_path: str, output_path: str | None = None) -> str:
    """Extract audio from video (e.g. MP4) to WAV for STT."""
    try:
        import ffmpeg
    except ImportError:
        try:
            import subprocess
            out = output_path or tempfile.mktemp(suffix=".wav")
            subprocess.run(
                ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", out],
                check=True,
                capture_output=True,
            )
            return out
        except Exception as e:
            raise RuntimeError(f"ffmpeg not found or failed: {e}") from e
    out = output_path or tempfile.mktemp(suffix=".wav")
    (
        ffmpeg.input(video_path)
        .output(out, vn=None, acodec="pcm_s16le", ar="16000", ac=1)
        .overwrite_output()
        .run(quiet=True)
    )
    return out


def speech_to_text(audio_path: str, language: Lang = "te") -> str:
    """Transcribe audio (or extracted video audio) to text. language: 'te' (Telugu) or 'en' (English)."""
    import whisper
    model = whisper.load_model("base")  # or "small" for better Telugu
    result = model.transcribe(audio_path, language="te" if language == "te" else "en", fp16=False)
    return (result.get("text") or "").strip()


def text_to_speech(text: str, language: Lang = "te", output_path: str | None = None) -> str:
    """Synthesize text to speech (Telugu or English). Returns path to WAV file."""
    try:
        from gtts import gTTS
    except ImportError:
        raise ImportError("pip install gTTS for TTS")
    # gTTS: tl = Telugu, en = English
    lang_code = "te" if language == "te" else "en"
    tts = gTTS(text=text, lang=lang_code, slow=False)
    path = output_path or tempfile.mktemp(suffix=".mp3")
    tts.save(path)
    return path


def text_to_speech_bytes(text: str, language: Lang = "te") -> bytes:
    """Synthesize text to speech and return audio bytes (e.g. for streaming)."""
    from gtts import gTTS
    lang_code = "te" if language == "te" else "en"
    tts = gTTS(text=text, lang=lang_code, slow=False)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    return buf.getvalue()
