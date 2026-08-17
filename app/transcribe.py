from __future__ import annotations

from pathlib import Path

from openai import OpenAI

from . import config


def transcribe_audio(path: Path) -> str:
    if not config.OPENAI_API_KEY:
        raise RuntimeError("先在设置里填接口密钥。")

    kwargs = {"api_key": config.OPENAI_API_KEY}
    if config.OPENAI_BASE_URL:
        kwargs["base_url"] = config.OPENAI_BASE_URL
    client = OpenAI(**kwargs)

    with path.open("rb") as audio:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio,
        )
    return (result.text or "").strip()
