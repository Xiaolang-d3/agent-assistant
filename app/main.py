from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .agent import run_agent
from .config import ROOT, readiness
from .transcribe import transcribe_audio

WEB = ROOT / "web"

app = FastAPI(title="Agent Assistant")
app.mount("/static", StaticFiles(directory=WEB), name="static")


class ChatIn(BaseModel):
    message: str = Field(min_length=1)
    history: list[dict] = Field(default_factory=list)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


@app.get("/api/health")
def health() -> dict:
    return readiness()


@app.post("/api/chat")
def chat(body: ChatIn) -> dict:
    try:
        return run_agent(body.history, body.message)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...)) -> dict:
    suffix = Path(audio.filename or "speech.webm").suffix or ".webm"
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await audio.read())
            tmp_path = Path(tmp.name)
        text = transcribe_audio(tmp_path)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if "tmp_path" in locals() and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
    if not text:
        raise HTTPException(status_code=422, detail="Could not hear any speech.")
    return {"text": text}
