"""grok-mcp MCP server.

v0.1 ships 3 tools: chat / search_x / search_web. See README roadmap for
v0.2+ plans.
"""

from __future__ import annotations

import sys

from mcp.server.fastmcp import FastMCP

from grok.tools.chat import chat as _chat
from grok.tools.search_web import search_web as _search_web
from grok.tools.search_x import search_x as _search_x

mcp = FastMCP("grok")


@mcp.tool()
def chat(
    prompt: str,
    model: str = "grok-4.3",
    system_prompt: str | None = None,
) -> str:
    """Plain chat with Grok — no Live Search, no external tools.

    Use this for reasoning / code gen / translation / summarization. If you
    need real-time X or web content, use search_x / search_web instead —
    they're cheaper than dumping search results into a chat prompt.

    Args:
        prompt: User message. Required, non-empty.
        model: Grok model ID. Default grok-4.3. Other options at
            https://docs.x.ai/docs/models
        system_prompt: Optional developer/system role instructions.

    Returns:
        Plain text response. No citations.
    """
    return _chat(prompt=prompt, model=model, system_prompt=system_prompt)


@mcp.tool()
def search_x(
    query: str,
    allowed_x_handles: list[str] | None = None,
    excluded_x_handles: list[str] | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    enable_image_understanding: bool = False,
    enable_video_understanding: bool = False,
    model: str = "grok-4.3",
) -> str:
    """Search X (Twitter) via Grok Live Search with full xAI parameter surface.

    Use enable_video_understanding=True when target posts have attached
    video — Grok will transcribe / describe the video content instead of
    relying on body text alone. Catches engagement-farm patterns where
    body text and video say different things.

    Args:
        query: Search query or question. Required.
        allowed_x_handles: Restrict to these handles (max 20, no @ prefix).
            Mutually exclusive with excluded_x_handles.
        excluded_x_handles: Exclude these handles (max 20).
        from_date: ISO YYYY-MM-DD start of search window.
        to_date: ISO YYYY-MM-DD end of window (inclusive).
        enable_image_understanding: Analyze images in matching posts.
        enable_video_understanding: Analyze videos in matching posts.
            x_search-only feature.
        model: Grok model ID. Default grok-4.3.

    Returns:
        Answer text + markdown **Sources:** block.
    """
    return _search_x(
        query=query,
        allowed_x_handles=allowed_x_handles,
        excluded_x_handles=excluded_x_handles,
        from_date=from_date,
        to_date=to_date,
        enable_image_understanding=enable_image_understanding,
        enable_video_understanding=enable_video_understanding,
        model=model,
    )


@mcp.tool()
def search_web(
    query: str,
    allowed_domains: list[str] | None = None,
    excluded_domains: list[str] | None = None,
    enable_image_understanding: bool = False,
    enable_image_search: bool = False,
    model: str = "grok-4.3",
) -> str:
    """Search the web via Grok Live Search with full xAI parameter surface.

    Args:
        query: Search query or question. Required.
        allowed_domains: Restrict to these domains (max 5). Mutually
            exclusive with excluded_domains.
        excluded_domains: Exclude these domains (max 5).
        enable_image_understanding: Analyze images Grok encounters while
            browsing. Per xAI docs, this also enables image understanding
            for any x_search tool in the same request.
        enable_image_search: Let Grok search images and embed them as
            markdown ![alt](url) in the response.
        model: Grok model ID. Default grok-4.3.

    Returns:
        Answer text + markdown **Sources:** block.
    """
    return _search_web(
        query=query,
        allowed_domains=allowed_domains,
        excluded_domains=excluded_domains,
        enable_image_understanding=enable_image_understanding,
        enable_image_search=enable_image_search,
        model=model,
    )


def main() -> int:
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
