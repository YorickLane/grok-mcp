"""Search X (Twitter) via Grok Live Search.

Full xAI x_search parameter surface as of 2026-05-28 — including
``enable_image_understanding`` and ``enable_video_understanding`` which many
community Grok MCP servers omit. See README "vs alternatives" table.

API reference: https://docs.x.ai/docs/tools/x-search
"""

from __future__ import annotations

from grok.api import (
    build_tool_spec,
    call_responses,
    format_citations_md,
    format_cost_footer,
)


def search_x(
    query: str,
    *,
    allowed_x_handles: list[str] | None = None,
    excluded_x_handles: list[str] | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    enable_image_understanding: bool = False,
    enable_video_understanding: bool = False,
    max_turns: int | None = None,
    conv_id: str | None = None,
    model: str = "grok-4.3",
) -> str:
    """Search X posts and return Grok's synthesized answer with citations.

    ``enable_video_understanding`` is the big one: without it, posts with
    attached video are summarized from text/metadata only. With it, Grok can
    transcribe / describe the video content directly. Costs more per call
    but catches content that body text doesn't reveal.

    Args:
        query: Search query or question. Required, max 100k chars.
        allowed_x_handles: Restrict to these handles (max 20, no @ prefix).
            Mutually exclusive with ``excluded_x_handles``.
        excluded_x_handles: Exclude these handles (max 20).
        from_date: ISO date ``YYYY-MM-DD`` — start of search window.
        to_date: ISO date ``YYYY-MM-DD`` — end of search window (inclusive).
        enable_image_understanding: Analyze images in matching posts (OCR /
            chart reading / screenshot content). Default False.
        enable_video_understanding: Analyze videos in matching posts
            (transcript / scene description). x_search-only. Default False.
        max_turns: Cap on tool-using turns. Limits TURNS, not individual
            tool calls — a single turn may fire multiple searches.
        conv_id: Prompt-cache key — reuse across calls to hit cached input
            tokens (sets both the cache key and the conversation header).
        model: Grok model ID. Default ``grok-4.3``.

    Returns:
        Answer text followed by a markdown ``**Sources:**`` block and a
        trailing cost footer. Empty citations block if nothing was found.

    Raises:
        ValueError: If ``allowed_x_handles`` and ``excluded_x_handles`` both
            set, or ``query`` empty.
        GrokAPIError: On non-2xx from xAI.
    """
    if not query.strip():
        raise ValueError("query cannot be empty")
    if allowed_x_handles and excluded_x_handles:
        raise ValueError(
            "allowed_x_handles and excluded_x_handles are mutually exclusive"
        )

    tool_spec = build_tool_spec(
        "x_search",
        allowed_x_handles=allowed_x_handles[:20] if allowed_x_handles else None,
        excluded_x_handles=excluded_x_handles[:20] if excluded_x_handles else None,
        from_date=from_date,
        to_date=to_date,
        enable_image_understanding=enable_image_understanding or None,
        enable_video_understanding=enable_video_understanding or None,
    )

    result = call_responses(
        prompt=query,
        model=model,
        tools=[tool_spec],
        max_turns=max_turns,
        conv_id=conv_id,
    )
    return (
        result["text"]
        + format_citations_md(result["citations"])
        + format_cost_footer(result["cost_usd"], model)
    )
