# Agent Assistant

## Branching

One branch, one feature. Do not merge voice, search, and the desktop shell together.

| Branch | Scope |
|---|---|
| `chore/bootstrap` | ignore, env example, dependencies, run docs |
| `feat/chat-search` | agent loop, search tool, chat API |
| `feat/voice-input` | transcription and talk button |
| `feat/desktop-shell` | desktop window only |

Stack only when a later branch cannot run without the earlier one. Commits use the repo owner's git identity, not Cursor.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Needs `OPENAI_API_KEY` in `.env`. Search defaults to DuckDuckGo.

Desktop: `python desktop.py`

Browser: `python -m app` then open http://127.0.0.1:8765

Hold the copper button to dictate; text lands in the input box for review.
