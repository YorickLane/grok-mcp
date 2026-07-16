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
XAI_IMAGES_URL = "https://api.x.ai/v1/images/generations"

# Fallback default model. "grok-4.5" is a NON-DATED xAI alias: per
# https://docs.x.ai/developers/models, "<modelname> is aliased to the latest
# stable version" (dated IDs like grok-4.20-0309-* pin a release;
# <modelname>-latest tracks the newest, possibly non-stable, version).
# Using the plain alias means xAI upgrades the underlying model for us —
# no code change needed when a new stable grok-4.5 snapshot ships.
FALLBACK_DEFAULT_MODEL = "grok-4.5"


def resolve_default_model() -> str:
    """Single source of truth for the default text model.

    Reads ``GROK_DEFAULT_MODEL`` from the environment (empty string is
    treated as unset), falling back to :data:`FALLBACK_DEFAULT_MODEL`.
    """
    return os.environ.get("GROK_DEFAULT_MODEL") or FALLBACK_DEFAULT_MODEL


# Resolved once at import (i.e. server start) so tool signatures — and the
# MCP tool schemas generated from them — show the real default. Set
# GROK_DEFAULT_MODEL in the environment the server is launched with.
DEFAULT_MODEL = resolve_default_model()
DEFAULT_IMAGE_MODEL = "grok-imagine-image-quality"  # -pro deprecated 2026-05-15
DEFAULT_TIMEOUT_S = 300.0

# xAI Responses API accepts these reasoning effort levels (live-verified
# 2026-05-29). Note: nested as payload["reasoning"]["effort"], NOT a
# top-level "reasoning_effort" key (that's the Chat Completions shape).
VALID_REASONING_EFFORTS = {"none", "low", "medium", "high"}

# usage.cost_in_usd_ticks is an integer count of ticks; 1e10 ticks == $1.
COST_TICKS_PER_USD = 1e10


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
    reasoning_effort: str | None = None,
    response_format_schema: dict[str, Any] | None = None,
    max_turns: int | None = None,
    conv_id: str | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """POST to xAI Responses API and return the parsed envelope.

    Returns a dict with keys: ``text`` (concatenated output_text blocks),
    ``citations`` (list of {url, title} from url_citation annotations),
    ``cost_ticks`` (int usage.cost_in_usd_ticks, or None), ``cost_usd``
    (cost_ticks / 1e10, or None), and ``raw`` (the full JSON response for
    inspection / debugging).

    Live Search tool specs go in `tools`. Citations are auto-enabled when any
    tool of type ``web_search`` or ``x_search`` is present.

    v0.3 params (all None-filtered — the payload key is only set when the
    param is provided, mirroring ``build_tool_spec`` discipline):

    - ``reasoning_effort``: ``none`` / ``low`` / ``medium`` / ``high``.
      Sets ``payload["reasoning"] = {"effort": <value>}`` (nested — the
      top-level ``reasoning_effort`` key is the Chat-Completions shape and
      is WRONG for /v1/responses). Live-verified 2026-05-29.
    - ``response_format_schema``: a JSON Schema dict. Sets
      ``payload["text"]["format"]`` with ``type=json_schema``, ``strict=True``.
    - ``max_turns``: cap on tool-using turns (a single turn may fire
      multiple tools). Harmless on plain chat.
    - ``conv_id``: prompt-cache key. Sets both ``payload["prompt_cache_key"]``
      AND the ``x-grok-conv-id`` request header (both needed for caching).
    """
    api_key = _require_api_key()

    if reasoning_effort is not None and reasoning_effort not in VALID_REASONING_EFFORTS:
        raise ValueError(
            f"reasoning_effort must be one of {sorted(VALID_REASONING_EFFORTS)}, "
            f"got {reasoning_effort!r}"
        )

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
    if reasoning_effort is not None:
        payload["reasoning"] = {"effort": reasoning_effort}
    if response_format_schema is not None:
        payload["text"] = {
            "format": {
                "type": "json_schema",
                "name": "response",
                "schema": response_format_schema,
                "strict": True,
            }
        }
    if max_turns is not None:
        payload["max_turns"] = max_turns
    if conv_id is not None:
        payload["prompt_cache_key"] = conv_id

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    if conv_id is not None:
        headers["x-grok-conv-id"] = conv_id

    with httpx.Client(timeout=timeout_s) as client:
        resp = client.post(XAI_RESPONSES_URL, json=payload, headers=headers)

    if resp.status_code >= 400:
        raise GrokAPIError(resp.status_code, resp.text)

    return _parse_envelope(resp.json())


def _cost_from_usage(usage: dict[str, Any] | None) -> tuple[int | None, float | None]:
    """Extract (cost_ticks, cost_usd) from a usage block. Shared by both
    the Responses and Images endpoints. Returns (None, None) if absent."""
    if not usage:
        return None, None
    cost_ticks = usage.get("cost_in_usd_ticks")
    if cost_ticks is None:
        return None, None
    return cost_ticks, cost_ticks / COST_TICKS_PER_USD


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

    cost_ticks, cost_usd = _cost_from_usage(body.get("usage"))
    return {
        "text": "\n".join(text_parts),
        "citations": citations,
        "cost_ticks": cost_ticks,
        "cost_usd": cost_usd,
        "raw": body,
    }


def call_images_generations(
    prompt: str,
    *,
    model: str = DEFAULT_IMAGE_MODEL,
    n: int = 1,
    aspect_ratio: str | None = None,
    resolution: str | None = None,
    response_format: str | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> list[dict[str, Any]]:
    """POST to xAI Images Generations API and return the parsed image list.

    Returns a list of dicts with keys: ``url`` (signed temporary URL),
    ``b64_json`` (only if ``response_format='b64_json'``), and
    ``revised_prompt`` (model's interpreted prompt — useful for debugging
    why an output diverged from intent).

    Note this is the OpenAI-compat ``/v1/images/generations`` endpoint, not
    the Responses API. Different request shape, different response shape.
    """
    api_key = _require_api_key()

    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "n": n,
    }
    if aspect_ratio is not None:
        payload["aspect_ratio"] = aspect_ratio
    if resolution is not None:
        payload["resolution"] = resolution
    if response_format is not None:
        payload["response_format"] = response_format

    with httpx.Client(timeout=timeout_s) as client:
        resp = client.post(
            XAI_IMAGES_URL,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )

    if resp.status_code >= 400:
        raise GrokAPIError(resp.status_code, resp.text)

    body = resp.json()
    images = list(body.get("data", []))
    # Surface per-request cost on each image dict. cost_in_usd_ticks is for
    # the whole request, not per-image — documented as such in the tool
    # docstring. Keeps the list[dict] return type intact.
    cost_ticks, cost_usd = _cost_from_usage(body.get("usage"))
    for img in images:
        img["cost_ticks"] = cost_ticks
        img["cost_usd"] = cost_usd
    return images


def build_tool_spec(tool_type: str, **params: Any) -> dict[str, Any]:
    """Construct a server-side tool spec for the Responses API.

    ``None`` values are filtered out so the request body stays clean.
    """
    spec: dict[str, Any] = {"type": tool_type}
    for key, value in params.items():
        if value is not None:
            spec[key] = value
    return spec


def format_cost_footer(cost_usd: float | None, model: str) -> str:
    """Render a trailing cost footer for text-returning tools, or empty
    string when cost is unavailable. Appended to chat / search_x /
    search_web / run_code output so the consumer can budget-track.

    NOT appended in json mode (response_format active) — the returned text
    is then a raw JSON string and a footer would corrupt it.
    """
    if cost_usd is None:
        return ""
    return f"\n\n—\n_grok cost: ${cost_usd:.6f} · {model}_"


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
