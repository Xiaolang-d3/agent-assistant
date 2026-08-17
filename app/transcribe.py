from __future__ import annotations

from pathlib import Path

from openai import OpenAI

from .config import OPENAI_API_KEY, OPENAI_BASE_URL


def transcribe_audio(path: Path) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("Set OPENAI_API_KEY to enable voice transcription.")

    kwargs = {"api_key": OPENAI_API_KEY}
    if OPENAI_BASE_URL:
        kwargs["base_url"] = OPENAI_BASE_URL
    client = OpenAI(**kwargs)

    with path.open("rb") as audio:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio,
        )
    return (result.text or "").strip()
