"""Plain chat with Grok — no Live Search, no tools.

Use this for: reasoning, code generation, translation, summarization, anything
that does NOT need real-time external data. If you need X / web content, use
``search_x`` / ``search_web`` instead — they're cheaper than dumping search
results into a chat prompt.
"""

from __future__ import annotations

from typing import Any

from grok.api import DEFAULT_MODEL, call_responses, format_cost_footer


def chat(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    system_prompt: str | None = None,
    reasoning_effort: str | None = None,
    response_format: dict[str, Any] | None = None,
    max_turns: int | None = None,
    conv_id: str | None = None,
) -> str:
    """Single-turn chat. Returns Grok's text response.

    Pass the whole conversation as a formatted ``prompt`` string for
    multi-turn; use ``conv_id`` to reuse the prompt cache across calls.

    Args:
        prompt: User message. Required.
        model: Grok model ID. Defaults to the ``GROK_DEFAULT_MODEL`` env
            var, else ``grok-4.5`` (non-dated alias that tracks the latest
            stable version). Other options at https://docs.x.ai/docs/models
        system_prompt: Optional developer/system role instructions.
        reasoning_effort: ``none`` / ``low`` / ``medium`` / ``high``. Omit
            for the server default (``low``). ``none`` skips reasoning
            tokens entirely (cheapest/fastest); ``high`` for hard problems.
        response_format: JSON Schema dict. When set, Grok returns a strict
            JSON object matching the schema and this function returns the
            raw JSON string (no cost footer is appended in this mode).
            Note xAI rule: ``additionalProperties`` defaults to false; set
            it true explicitly if needed. Fields absent from ``required``
            are optional.
        max_turns: Cap on tool-using turns (harmless on plain chat).
        conv_id: Prompt-cache key — reuse across calls to hit cached input
            tokens (sets both the cache key and the conversation header).

    Returns:
        Plain text response, plus a trailing cost footer. In json mode
        (``response_format`` set) returns the raw JSON string with no footer.
    """
    if not prompt.strip():
        raise ValueError("prompt cannot be empty")

    result = call_responses(
        prompt=prompt,
        model=model,
        system_prompt=system_prompt,
        reasoning_effort=reasoning_effort,
        response_format_schema=response_format,
        max_turns=max_turns,
        conv_id=conv_id,
    )
    # In json mode the text IS a JSON string — appending a footer would
    # corrupt it. Cost stays available in the envelope, just not the string.
    if response_format is not None:
        return result["text"]
    return result["text"] + format_cost_footer(result["cost_usd"], model)
