"""Search the web via Grok Live Search.

Full xAI web_search parameter surface — including ``enable_image_search``
which embeds markdown ``![alt](url)`` in the response, useful for visual RAG.

API reference: https://docs.x.ai/docs/tools/web-search
"""

from __future__ import annotations

from grok.api import (
    DEFAULT_MODEL,
    build_tool_spec,
    call_responses,
    format_citations_md,
    format_cost_footer,
)


def search_web(
    query: str,
    *,
    allowed_domains: list[str] | None = None,
    excluded_domains: list[str] | None = None,
    enable_image_understanding: bool = False,
    enable_image_search: bool = False,
    max_turns: int | None = None,
    conv_id: str | None = None,
    model: str = DEFAULT_MODEL,
) -> str:
    """Search the web and return Grok's synthesized answer with citations.

    Args:
        query: Search query or question. Required.
        allowed_domains: Restrict search to these domains (max 5). Mutually
            exclusive with ``excluded_domains``.
        excluded_domains: Exclude these domains from search (max 5).
        enable_image_understanding: Analyze images Grok encounters while
            browsing (OCR / diagram reading). Per xAI docs this also enables
            image understanding for any x_search tool in the same request.
        enable_image_search: Let Grok search for relevant images and embed
            them as markdown ``![alt](url)`` in the response text. Useful
            when the consuming UI renders markdown.
        max_turns: Cap on tool-using turns. Limits TURNS, not individual
            tool calls — a single turn may fire multiple searches.
        conv_id: Prompt-cache key — reuse across calls to hit cached input
            tokens (sets both the cache key and the conversation header).
        model: Grok model ID. Defaults to the ``GROK_DEFAULT_MODEL`` env
            var, else ``grok-4.5`` (non-dated alias, tracks latest stable).

    Returns:
        Answer text followed by a markdown ``**Sources:**`` block and a
        trailing cost footer.

    Raises:
        ValueError: If ``allowed_domains`` and ``excluded_domains`` both set,
            or ``query`` empty.
        GrokAPIError: On non-2xx from xAI.
    """
    if not query.strip():
        raise ValueError("query cannot be empty")
    if allowed_domains and excluded_domains:
        raise ValueError(
            "allowed_domains and excluded_domains are mutually exclusive"
        )

    tool_spec = build_tool_spec(
        "web_search",
        allowed_domains=allowed_domains[:5] if allowed_domains else None,
        excluded_domains=excluded_domains[:5] if excluded_domains else None,
        enable_image_understanding=enable_image_understanding or None,
        enable_image_search=enable_image_search or None,
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
