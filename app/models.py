"""Fetch chat-capable model ids from an OpenAI-compatible API."""

from __future__ import annotations

import json

import httpx

_SKIP = ("whisper", "tts", "dall-e", "embedding", "moderation", "image", "audio-")
_PREFERRED = (
    "gpt",
    "o1",
    "o3",
    "o4",
    "claude",
    "qwen",
    "deepseek",
    "llama",
    "mistral",
    "gemini",
    "kimi",
    "glm",
    "chat",
    "yi-",
)
_DEFAULT_BASE = "https://api.openai.com/v1"


def list_models(api_key: str, base_url: str | None = None) -> dict:
    api_key = (api_key or "").strip()
    base_url = (base_url or "").strip() or _DEFAULT_BASE
    if not api_key:
        raise RuntimeError("先填接口密钥，再获取模型列表。")

    payload, resolved_base = _fetch_models_payload(api_key, base_url)
    unique = list(dict.fromkeys(_parse_model_ids(payload)))
    chat = [name for name in unique if _is_chat_model(name)]
    names = chat or unique
    if not names:
        raise RuntimeError("这个网关没有返回模型列表。")
    names.sort(key=_sort_key)
    return {"models": names, "base_url": resolved_base}


def _fetch_models_payload(api_key: str, base_url: str) -> tuple[object, str]:
    headers = {"Authorization": f"Bearer {api_key}"}
    urls = _candidate_urls(base_url)
    last_error: Exception | None = None
    for index, url in enumerate(urls):
        try:
            response = httpx.get(url, headers=headers, timeout=20.0, follow_redirects=True)
        except httpx.HTTPError as exc:
            last_error = RuntimeError("连不上这个网关，请检查地址。")
            if index == len(urls) - 1:
                raise last_error from exc
            continue
        if not _looks_like_json(response):
            last_error = RuntimeError("这个地址返回的是网页，请改成带 /v1 的网关。")
            continue
        if response.status_code >= 400:
            last_error = _http_error(response)
            if response.status_code in {401, 403} or index == len(urls) - 1:
                raise last_error
            continue
        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            last_error = RuntimeError("这个地址返回的不是接口数据，请改成带 /v1 的网关。")
            if index == len(urls) - 1:
                raise last_error from exc
            continue
        return payload, _base_from_models_url(url)
    if last_error:
        raise last_error
    raise RuntimeError("这个网关没有返回模型列表。")


def _candidate_urls(base_url: str) -> list[str]:
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return [f"{base}/models"]
    return [f"{base}/v1/models", f"{base}/models"]


def _base_from_models_url(url: str) -> str:
    if url.endswith("/models"):
        return url[: -len("/models")]
    return url.rstrip("/")


def _looks_like_json(response: httpx.Response) -> bool:
    ctype = (response.headers.get("content-type") or "").lower()
    if "json" in ctype:
        return True
    text = (response.text or "").lstrip()
    return text.startswith("{") or text.startswith("[")


def _parse_model_ids(payload: object) -> list[str]:
    rows: object = payload
    if isinstance(payload, dict):
        rows = payload.get("data")
        if rows is None:
            rows = payload.get("models")
        if isinstance(rows, dict):
            rows = rows.get("data") or rows.get("models") or []
    if not isinstance(rows, list):
        return []
    names: list[str] = []
    for item in rows:
        if isinstance(item, str):
            name = item.strip()
        elif isinstance(item, dict):
            name = str(item.get("id") or item.get("name") or item.get("model") or "").strip()
        else:
            name = str(getattr(item, "id", "") or "").strip()
        if name:
            names.append(name)
    return names


def _http_error(response: httpx.Response) -> RuntimeError:
    message = _error_message(response)
    status = response.status_code
    if status in {401, 403}:
        return RuntimeError(message or "密钥或网关被拒绝，请检查后再获取。")
    if status == 404:
        return RuntimeError(message or "这个地址没有模型列表接口。")
    if message:
        return RuntimeError(message)
    return RuntimeError(f"获取失败（HTTP {status}）")


def _error_message(response: httpx.Response) -> str:
    try:
        data = response.json()
    except json.JSONDecodeError:
        return ""
    if not isinstance(data, dict):
        return ""
    err = data.get("error")
    if isinstance(err, dict):
        return str(err.get("message") or "").strip()
    if isinstance(err, str):
        return err.strip()
    return str(data.get("message") or "").strip()


def _is_chat_model(name: str) -> bool:
    lower = name.lower()
    return not any(token in lower for token in _SKIP)


def _sort_key(name: str) -> tuple[int, str]:
    lower = name.lower()
    preferred = any(token in lower for token in _PREFERRED)
    return (0 if preferred else 1, lower)
