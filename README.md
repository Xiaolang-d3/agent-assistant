# Agent Assistant

Local agent assistant. Features land on separate branches.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Put `OPENAI_API_KEY` in `.env`. Compatible gateways can set `OPENAI_BASE_URL` and `OPENAI_MODEL`.

Search defaults to DuckDuckGo. Set `TAVILY_API_KEY` to use Tavily instead.

Native desktop (PySide6, not a webview):

```bash
python -m desktop_app
```

Browser UI is still available with `python -m app`.
