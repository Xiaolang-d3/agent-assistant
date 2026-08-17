"""Minimal tool-calling agent loop.

Uses OpenAI chat completions by default. Claude models on gateways
like PackyAPI only accept the Anthropic messages protocol.
"""

from __future__ import annotations

import json

import httpx
from openai import OpenAI

from . import config
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

ANTHROPIC_TOOLS = [
    {
        "name": "web_search",
        "description": "Search the live web. Use for current events, docs, facts, or unknown topics.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query in the most useful language for the topic.",
                }
            },
            "required": ["query"],
        },
    }
]


class _ProtocolUnsupported(RuntimeError):
    """Gateway rejected chat completions for this model."""


def _client() -> OpenAI:
    if not config.OPENAI_API_KEY:
        raise RuntimeError("先在设置里填接口密钥。")
    kwargs = {"api_key": config.OPENAI_API_KEY}
    if config.OPENAI_BASE_URL:
        kwargs["base_url"] = config.OPENAI_BASE_URL
    return OpenAI(**kwargs)


def run_agent(history: list[dict], user_text: str) -> dict:
    if _prefer_messages(config.OPENAI_MODEL):
        return _run_messages(history, user_text)
    try:
        return _run_chat(history, user_text)
    except _ProtocolUnsupported:
        return _run_messages(history, user_text)


def _prefer_messages(model: str) -> bool:
    return "claude" in (model or "").lower()


def _run_chat(history: list[dict], user_text: str) -> dict:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in history[-16:]:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_text.strip()})

    client = _client()
    steps: list[dict] = []

    try:
        for _ in range(4):
            response = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
            choice = response.choices[0].message
            tool_calls = choice.tool_calls or []

            if not tool_calls:
                return {
                    "reply": (choice.content or "").strip() or "没有得到回复。",
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
    except Exception as exc:  # noqa: BLE001
        if _is_protocol_unsupported(exc):
            raise _ProtocolUnsupported from exc
        raise RuntimeError(_friendly_error(exc)) from exc

    return {
        "reply": "搜索轮次过多，请把问题问得更具体一些。",
        "steps": steps,
    }


def _run_messages(history: list[dict], user_text: str) -> dict:
    if not config.OPENAI_API_KEY:
        raise RuntimeError("先在设置里填接口密钥。")

    messages: list[dict] = []
    for item in history[-16:]:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_text.strip()})

    url = _messages_url(config.OPENAI_BASE_URL)
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "x-api-key": config.OPENAI_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    steps: list[dict] = []

    try:
        for _ in range(4):
            payload = {
                "model": config.OPENAI_MODEL,
                "max_tokens": 4096,
                "system": SYSTEM_PROMPT,
                "messages": messages,
                "tools": ANTHROPIC_TOOLS,
            }
            response = httpx.post(url, headers=headers, json=payload, timeout=90.0)
            if response.status_code >= 400:
                raise RuntimeError(_http_error_text(response))
            try:
                data = response.json()
            except json.JSONDecodeError as exc:
                raise RuntimeError("网关没有返回可用的模型回复。") from exc
            if not isinstance(data, dict):
                raise RuntimeError("网关返回的回复格式无法识别。")
            blocks = data.get("content") or []
            tool_uses = [block for block in blocks if isinstance(block, dict) and block.get("type") == "tool_use"]
            text = _text_from_content(blocks)

            if not tool_uses:
                return {"reply": text or "没有得到回复。", "steps": steps}

            messages.append({"role": "assistant", "content": blocks})
            results_blocks = []
            for block in tool_uses:
                query = str((block.get("input") or {}).get("query") or "").strip()
                results = web_search(query)
                steps.append({"type": "search", "query": query, "results": results})
                results_blocks.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.get("id") or "",
                        "content": format_results(results),
                    }
                )
            messages.append({"role": "user", "content": results_blocks})
    except httpx.HTTPError as exc:
        raise RuntimeError("连不上这个网关，请检查地址。") from exc

    return {
        "reply": "搜索轮次过多，请把问题问得更具体一些。",
        "steps": steps,
    }


def _messages_url(base_url: str | None) -> str:
    base = (base_url or "https://api.anthropic.com/v1").rstrip("/")
    return f"{base}/messages"


def _text_from_content(content: object) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    parts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text") or ""))
    return "\n".join(parts).strip()


def _is_protocol_unsupported(exc: Exception) -> bool:
    body = _error_body(exc)
    err = body.get("error") if isinstance(body, dict) else None
    if isinstance(err, dict) and err.get("code") == "protocol_not_supported":
        return True
    text = _friendly_error(exc)
    return "protocol_not_supported" in text or "不支持 chat completions" in text


def _error_body(exc: Exception) -> dict:
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        return body
    if isinstance(body, str):
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}
    return {}


def _friendly_error(exc: Exception) -> str:
    body = _error_body(exc)
    err = body.get("error") if body else None
    if isinstance(err, dict):
        message = str(err.get("message") or "").strip()
        if message:
            return message
    if isinstance(err, str) and err.strip():
        return err.strip()
    text = str(exc).strip()
    return text.split("\n", 1)[0][:240] or "请求失败。"


def _http_error_text(response: httpx.Response) -> str:
    try:
        data = response.json()
    except json.JSONDecodeError:
        data = {}
    err = data.get("error") if isinstance(data, dict) else None
    if isinstance(err, dict) and err.get("message"):
        return str(err["message"]).strip()
    if isinstance(err, str) and err.strip():
        return err.strip()
    if isinstance(data, dict) and data.get("message"):
        return str(data["message"]).strip()
    return f"请求失败（HTTP {response.status_code}）"


def _read_query(raw: str) -> str:
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return raw
    return str(data.get("query") or raw).strip()
