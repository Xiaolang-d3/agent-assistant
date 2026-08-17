import os
import re
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
EXAMPLE_PATH = ROOT / ".env.example"

load_dotenv(ENV_PATH)


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


OPENAI_API_KEY = _env("OPENAI_API_KEY")
OPENAI_BASE_URL = _env("OPENAI_BASE_URL") or None
OPENAI_MODEL = _env("OPENAI_MODEL", "gpt-4o-mini")
TAVILY_API_KEY = _env("TAVILY_API_KEY")
SEARCH_PROVIDER = _env("SEARCH_PROVIDER", "auto").lower()
APP_HOST = _env("APP_HOST", "127.0.0.1")
APP_PORT = int(_env("APP_PORT", "8765"))

SETTING_KEYS = (
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "SEARCH_PROVIDER",
    "TAVILY_API_KEY",
)


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


def current_settings() -> dict[str, str]:
    return {
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "OPENAI_BASE_URL": OPENAI_BASE_URL or "",
        "OPENAI_MODEL": OPENAI_MODEL,
        "SEARCH_PROVIDER": SEARCH_PROVIDER or "auto",
        "TAVILY_API_KEY": TAVILY_API_KEY,
    }


def reload() -> None:
    load_dotenv(ENV_PATH, override=True)
    global OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
    global TAVILY_API_KEY, SEARCH_PROVIDER, APP_HOST, APP_PORT
    OPENAI_API_KEY = _env("OPENAI_API_KEY")
    OPENAI_BASE_URL = _env("OPENAI_BASE_URL") or None
    OPENAI_MODEL = _env("OPENAI_MODEL", "gpt-4o-mini")
    TAVILY_API_KEY = _env("TAVILY_API_KEY")
    SEARCH_PROVIDER = _env("SEARCH_PROVIDER", "auto").lower()
    APP_HOST = _env("APP_HOST", "127.0.0.1")
    APP_PORT = int(_env("APP_PORT", "8765"))


def save_settings(values: dict[str, str]) -> None:
    updates = {key: (values.get(key) or "").strip() for key in SETTING_KEYS}
    if ENV_PATH.exists():
        text = ENV_PATH.read_text(encoding="utf-8")
    elif EXAMPLE_PATH.exists():
        text = EXAMPLE_PATH.read_text(encoding="utf-8")
    else:
        text = ""
    ENV_PATH.write_text(_upsert_env_text(text, updates), encoding="utf-8")
    for key, value in updates.items():
        if value:
            os.environ[key] = value
        else:
            os.environ.pop(key, None)
    reload()


def _upsert_env_text(text: str, updates: dict[str, str]) -> str:
    seen: set[str] = set()
    patterns = {key: re.compile(rf"^\s*#?\s*{re.escape(key)}=") for key in updates}
    lines_out: list[str] = []
    for line in text.splitlines():
        matched = next((key for key, pat in patterns.items() if pat.match(line)), None)
        if matched is None:
            lines_out.append(line)
            continue
        if matched in seen:
            continue
        seen.add(matched)
        value = updates[matched]
        lines_out.append(f"{matched}={value}" if value else f"# {matched}=")
    for key, value in updates.items():
        if key in seen or not value:
            continue
        if lines_out and lines_out[-1] != "":
            lines_out.append("")
        lines_out.append(f"{key}={value}")
    return "\n".join(lines_out).rstrip() + "\n"
