"""Open the MVP in a desktop window."""

from __future__ import annotations

import threading
import time
import urllib.request

import uvicorn
import webview

from app.config import APP_HOST, APP_PORT
from app.main import app


def _serve() -> None:
    uvicorn.run(app, host=APP_HOST, port=APP_PORT, log_level="warning")


def _wait() -> None:
    url = f"http://{APP_HOST}:{APP_PORT}/api/health"
    for _ in range(80):
        try:
            urllib.request.urlopen(url, timeout=0.25)
            return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("Local server did not start.")


if __name__ == "__main__":
    threading.Thread(target=_serve, daemon=True).start()
    _wait()
    webview.create_window(
        "Agent Assistant",
        f"http://{APP_HOST}:{APP_PORT}",
        width=1080,
        height=740,
    )
    webview.start()
