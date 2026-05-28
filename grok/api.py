"""Thin xAI Responses API client.

Single entry point `call_responses()`. No SDK lock-in, no LangChain — direct
HTTP to `https://api.x.ai/v1/responses` so we stay in lockstep with xAI docs.

The `XAI_API_KEY` env var is read on every call (not cached) so key rotation
without server restart works.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

XAI_RESPONSES_URL = "https://api.x.ai/v1/responses"
DEFAULT_MODEL = "grok-4.3"
DEFAULT_TIMEOUT_S = 300.0


class GrokAPIError(RuntimeError):
    """xAI API returned a non-2xx response or an unparseable body."""

    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"xAI API {status}: {body[:500]}")
        self.status = status
        self.body = body


def _require_api_key() -> str:
    key = os.environ.get("XAI_API_KEY")
    if not key:
        raise GrokAPIError(
            0,
            "XAI_API_KEY env var not set. Get one from https://console.x.ai",
        )
    return key


def call_responses(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    system_prompt: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """POST to xAI Responses API and return the parsed envelope.

    Returns a dict with keys: ``text`` (concatenated output_text blocks),
    ``citations`` (list of {url, title} from url_citation annotations), and
    ``raw`` (the full JSON response for inspection / debugging).

    Live Search tool specs go in `tools`. Citations are auto-enabled when any
    tool of type ``web_search`` or ``x_search`` is present.
    """
    api_key = _require_api_key()

    input_items: list[dict[str, Any]] = []
    if system_prompt:
        input_items.append({"role": "developer", "content": system_prompt})
    input_items.append({"role": "user", "content": prompt})

    payload: dict[str, Any] = {
        "model": model,
        "input": input_items,
        "store": False,
    }
    if tools:
        payload["tools"] = tools
        search_types = {"web_search", "x_search"}
        if any(t.get("type") in search_types for t in tools):
            payload["inline_citations"] = True

    with httpx.Client(timeout=timeout_s) as client:
        resp = client.post(
            XAI_RESPONSES_URL,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )

    if resp.status_code >= 400:
        raise GrokAPIError(resp.status_code, resp.text)

    return _parse_envelope(resp.json())


def _parse_envelope(body: dict[str, Any]) -> dict[str, Any]:
    text_parts: list[str] = []
    citations: list[dict[str, str]] = []

    for item in body.get("output", []):
        if item.get("type") != "message":
            continue
        for block in item.get("content", []):
            if block.get("type") != "output_text":
                continue
            text_parts.append(block.get("text", ""))
            for ann in block.get("annotations", []):
                if ann.get("type") == "url_citation":
                    citations.append(
                        {
                            "url": ann.get("url", ""),
                            "title": ann.get("title", ""),
                        }
                    )

    return {
        "text": "\n".join(text_parts),
        "citations": citations,
        "raw": body,
    }


def build_tool_spec(tool_type: str, **params: Any) -> dict[str, Any]:
    """Construct a server-side tool spec for the Responses API.

    ``None`` values are filtered out so the request body stays clean.
    """
    spec: dict[str, Any] = {"type": tool_type}
    for key, value in params.items():
        if value is not None:
            spec[key] = value
    return spec


def format_citations_md(citations: list[dict[str, str]]) -> str:
    """Render a deduped markdown ``**Sources:**`` block, or empty string."""
    if not citations:
        return ""
    seen: set[str] = set()
    lines = ["", "**Sources:**"]
    for c in citations:
        url = c.get("url", "")
        if not url or url in seen:
            continue
        seen.add(url)
        title = c.get("title", "") or url
        lines.append(f"- [{title}]({url})")
    return "\n".join(lines) if len(lines) > 2 else ""
