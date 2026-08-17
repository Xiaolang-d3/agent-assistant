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

```bash
python -m app
```

Then open http://127.0.0.1:8765. Type a question; the agent searches when it needs current facts.
