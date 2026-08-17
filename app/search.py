"""Web search tool backends.

This is the agent-facing search layer: it calls a search API, then
trims and formats results so they fit in the model context.
"""

from __future__ import annotations

import httpx

from . import config
from .config import search_backend


def web_search(query: str, max_results: int = 5) -> list[dict]:
    query = (query or "").strip()
    if not query:
        return []
    backend = search_backend()
    if backend == "tavily":
        return _tavily(query, max_results)
    return _ddg(query, max_results)


def _ddg(query: str, max_results: int) -> list[dict]:
    from ddgs import DDGS

    rows = []
    with DDGS() as client:
        for item in client.text(query, max_results=max_results):
            rows.append(
                {
                    "title": item.get("title") or "",
                    "url": item.get("href") or "",
                    "snippet": (item.get("body") or "")[:400],
                }
            )
    return rows


def _tavily(query: str, max_results: int) -> list[dict]:
    response = httpx.post(
        "https://api.tavily.com/search",
        json={
            "api_key": config.TAVILY_API_KEY,
            "query": query,
            "search_depth": "basic",
            "max_results": max_results,
            "include_answer": False,
        },
        timeout=20,
    )
    response.raise_for_status()
    rows = []
    for item in response.json().get("results", []):
        rows.append(
            {
                "title": item.get("title") or "",
                "url": item.get("url") or "",
                "snippet": (item.get("content") or "")[:400],
            }
        )
    return rows


def format_results(results: list[dict]) -> str:
    if not results:
        return "No search results."
    lines = []
    for i, item in enumerate(results, 1):
        lines.append(f"{i}. {item['title']}\n   {item['url']}\n   {item['snippet']}")
    return "\n".join(lines)
