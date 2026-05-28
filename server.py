"""grok-mcp MCP server.

v0.2 ships 5 tools: chat / search_x / search_web / run_code / generate_image.
See README roadmap for v0.3+ plans.
"""

from __future__ import annotations

import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from grok.tools.chat import chat as _chat
from grok.tools.generate_image import generate_image as _generate_image
from grok.tools.run_code import run_code as _run_code
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


@mcp.tool()
def run_code(
    prompt: str,
    model: str = "grok-4.3",
) -> str:
    """Execute Python via Grok's sandboxed code interpreter.

    Use for problems where the LLM would otherwise hallucinate numbers:
    compound interest, t-tests, regressions, Sharpe ratios, simulations.
    The sandbox has NumPy / Pandas / Matplotlib / SciPy pre-installed but
    no network and no persistent file I/O.

    Args:
        prompt: Plain-language description of what to compute. Include
            data inline, not as a file.
        model: Grok model ID. Default grok-4.3.

    Returns:
        Grok's text answer with numeric results and embedded reasoning.
    """
    return _run_code(prompt=prompt, model=model)


@mcp.tool()
def generate_image(
    prompt: str,
    model: str = "grok-imagine-image-quality",
    n: int = 1,
    aspect_ratio: str | None = None,
    resolution: str | None = None,
    response_format: str | None = None,
) -> list[dict[str, Any]]:
    """Generate images from text via Grok Imagine.

    Default model is grok-imagine-image-quality (the -pro variant was
    deprecated 2026-05-15). URLs returned are signed temporary; download
    promptly or request response_format='b64_json' for embedded payload.

    Args:
        prompt: Text description of the image. Required.
        model: Grok Imagine model. Default grok-imagine-image-quality.
        n: Number of images (1-10, batch in one request).
        aspect_ratio: One of 1:1 / 16:9 / 9:16 / 4:3 / 3:4 / 3:2 / 2:3 /
            2:1 / 1:2 / 19.5:9 / 9:19.5 / 20:9 / 9:20 / auto.
        resolution: 1k or 2k.
        response_format: url (default, signed) or b64_json (embedded).

    Returns:
        List of dicts each containing url (or b64_json) and revised_prompt.
    """
    return _generate_image(
        prompt=prompt,
        model=model,
        n=n,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        response_format=response_format,
    )


def main() -> int:
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
