import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


OPENAI_API_KEY = _env("OPENAI_API_KEY")
OPENAI_BASE_URL = _env("OPENAI_BASE_URL") or None
OPENAI_MODEL = _env("OPENAI_MODEL", "gpt-4o-mini")
TAVILY_API_KEY = _env("TAVILY_API_KEY")
SEARCH_PROVIDER = _env("SEARCH_PROVIDER", "auto").lower()
APP_HOST = _env("APP_HOST", "127.0.0.1")
APP_PORT = int(_env("APP_PORT", "8765"))


def search_backend() -> str:
    if SEARCH_PROVIDER == "tavily" and TAVILY_API_KEY:
        return "tavily"
    if SEARCH_PROVIDER == "ddg":
        return "ddg"
    if TAVILY_API_KEY:
        return "tavily"
    return "ddg"


def readiness() -> dict:
    return {
        "llm": bool(OPENAI_API_KEY),
        "model": OPENAI_MODEL,
        "search": search_backend(),
        "transcribe": bool(OPENAI_API_KEY),
    }
