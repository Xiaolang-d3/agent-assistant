from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .agent import run_agent
from .config import ROOT, readiness

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
