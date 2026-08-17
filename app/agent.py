"""Minimal tool-calling agent loop.

The model may call `web_search`. We execute the tool, append the
result, and ask the model again until it answers in plain text.
"""

from __future__ import annotations

from openai import OpenAI

from .config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
from .search import format_results, web_search

SYSTEM_PROMPT = """You are Agent Assistant, a desktop research partner.
You can search the live web with the web_search tool.
Use search when the user asks about current facts, docs, news, or anything you are not sure about.
After searching, answer in the user's language. Cite source titles briefly when you used the web.
Keep answers concise unless the user asks for depth."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the live web. Use for current events, docs, facts, or unknown topics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query in the most useful language for the topic.",
                    }
                },
                "required": ["query"],
            },
        },
    }
]


def _client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise RuntimeError("Set OPENAI_API_KEY in .env before chatting.")
    kwargs = {"api_key": OPENAI_API_KEY}
    if OPENAI_BASE_URL:
        kwargs["base_url"] = OPENAI_BASE_URL
    return OpenAI(**kwargs)


def run_agent(history: list[dict], user_text: str) -> dict:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in history[-16:]:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_text.strip()})

    client = _client()
    steps: list[dict] = []

    for _ in range(4):
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        choice = response.choices[0].message
        tool_calls = choice.tool_calls or []

        if not tool_calls:
            return {
                "reply": (choice.content or "").strip() or "I have nothing to add.",
                "steps": steps,
            }

        messages.append(
            {
                "role": "assistant",
                "content": choice.content or "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in tool_calls
                ],
            }
        )

        for call in tool_calls:
            query = _read_query(call.function.arguments)
            results = web_search(query)
            steps.append({"type": "search", "query": query, "results": results})
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": format_results(results),
                }
            )

    return {
        "reply": "Search loop stopped after too many tool calls. Try a narrower question.",
        "steps": steps,
    }


def _read_query(raw: str) -> str:
    import json

    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return raw
    return str(data.get("query") or raw).strip()
