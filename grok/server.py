"""grok-mcp MCP server: chat / search_x / search_web / run_code / generate_image.

See README for the parameter surface and roadmap.
"""

from __future__ import annotations

import functools
import sys
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from grok.api import DEFAULT_IMAGE_MODEL, DEFAULT_MODEL, GrokAPIError
from grok.tools.chat import chat as _chat
from grok.tools.generate_image import generate_image as _generate_image
from grok.tools.run_code import run_code as _run_code
from grok.tools.search_web import search_web as _search_web
from grok.tools.search_x import search_x as _search_x

P = ParamSpec("P")
R = TypeVar("R")

mcp = MCPServer("grok")


def _report_errors(fn: Callable[P, R]) -> Callable[P, R]:
    """Re-raise expected failures as ToolError so their message reaches the model.

    mcp >= 2.1 shows the model only "Error executing tool <name>" for any other
    exception. Bad arguments, xAI API errors and network failures are expected,
    and their text says what to fix or retry.
    """

    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return fn(*args, **kwargs)
        except (ValueError, GrokAPIError, httpx.HTTPError) as exc:
            raise ToolError(str(exc)) from exc

    return wrapper


# Text tools opt out of structured output: with an outputSchema MCPServer also
# sends {"result": "<text>"} as structuredContent, and Claude Code shows the
# model that JSON string (escaped newlines) instead of the markdown text.


@mcp.tool(structured_output=False)
@_report_errors
def chat(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system_prompt: str | None = None,
    reasoning_effort: str | None = None,
    response_format: dict[str, Any] | None = None,
    max_turns: int | None = None,
    conv_id: str | None = None,
) -> str:
    """Plain chat with Grok — no Live Search, no external tools.

    Use this for reasoning / code gen / translation / summarization. If you
    need real-time X or web content, use search_x / search_web instead —
    they're cheaper than dumping search results into a chat prompt.

    Args:
        prompt: User message. Required, non-empty.
        model: Grok model ID. Defaults to the GROK_DEFAULT_MODEL env var,
            else grok-4.7 (non-dated alias: follows new grok-4.7 snapshots,
            not newer generations). Other options at https://docs.x.ai/docs/models
        system_prompt: Optional developer/system role instructions.
        reasoning_effort: low / medium / high / xhigh. Omit for the model
            default (high on grok-4.5+; reasoning cannot be disabled). Use
            "low" for the cheapest/fastest answers, "xhigh" (grok-4.6+) for
            the hardest problems.
        response_format: A JSON Schema dict to force structured output.
            When set, the return value is the raw JSON string matching the
            schema (no cost footer is appended). xAI rule:
            additionalProperties defaults to false — set it true if needed;
            fields not in "required" are optional.
        max_turns: Cap on tool-using turns (harmless on plain chat).
        conv_id: Prompt-cache key. Reuse the same conv_id across calls to
            hit cached input tokens (cheaper repeat calls).

    Returns:
        Plain text response with a trailing cost footer. In json mode
        (response_format set) returns the raw JSON string, no footer.
    """
    return _chat(
        prompt=prompt,
        model=model,
        system_prompt=system_prompt,
        reasoning_effort=reasoning_effort,
        response_format=response_format,
        max_turns=max_turns,
        conv_id=conv_id,
    )


@mcp.tool(structured_output=False)
@_report_errors
def search_x(
    query: str,
    allowed_x_handles: list[str] | None = None,
    excluded_x_handles: list[str] | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    enable_image_understanding: bool = False,
    enable_video_understanding: bool = False,
    max_turns: int | None = None,
    conv_id: str | None = None,
    reasoning_effort: str | None = None,
    model: str = DEFAULT_MODEL,
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
        max_turns: Cap on tool-using turns. Limits TURNS, not individual
            tool calls — one turn may fire multiple searches.
        conv_id: Prompt-cache key. Reuse across calls for cheaper repeats.
        reasoning_effort: low / medium / high / xhigh. Omit for the model
            default (high). "low" trims reasoning tokens; the per-post
            X Search fee is unaffected.
        model: Grok model ID. Defaults to the GROK_DEFAULT_MODEL env var,
            else grok-4.7 (non-dated alias, same-model snapshots only).

    Returns:
        Answer text + markdown **Sources:** block + trailing cost footer +
        a trace line of the searches that ran (warns if X Search fetched 0 posts).
    """
    return _search_x(
        query=query,
        allowed_x_handles=allowed_x_handles,
        excluded_x_handles=excluded_x_handles,
        from_date=from_date,
        to_date=to_date,
        enable_image_understanding=enable_image_understanding,
        enable_video_understanding=enable_video_understanding,
        max_turns=max_turns,
        conv_id=conv_id,
        reasoning_effort=reasoning_effort,
        model=model,
    )


@mcp.tool(structured_output=False)
@_report_errors
def search_web(
    query: str,
    allowed_domains: list[str] | None = None,
    excluded_domains: list[str] | None = None,
    enable_image_understanding: bool = False,
    enable_image_search: bool = False,
    max_turns: int | None = None,
    conv_id: str | None = None,
    reasoning_effort: str | None = None,
    model: str = DEFAULT_MODEL,
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
        max_turns: Cap on tool-using turns. Limits TURNS, not individual
            tool calls — one turn may fire multiple searches.
        conv_id: Prompt-cache key. Reuse across calls for cheaper repeats.
        reasoning_effort: low / medium / high / xhigh. Omit for the model
            default (high). "low" trims reasoning tokens; the per-call
            Web Search fee is unaffected.
        model: Grok model ID. Defaults to the GROK_DEFAULT_MODEL env var,
            else grok-4.7 (non-dated alias, same-model snapshots only).

    Returns:
        Answer text + markdown **Sources:** block + trailing cost footer +
        a trace line of the searches that ran (warns if X Search fetched 0 posts).
    """
    return _search_web(
        query=query,
        allowed_domains=allowed_domains,
        excluded_domains=excluded_domains,
        enable_image_understanding=enable_image_understanding,
        enable_image_search=enable_image_search,
        max_turns=max_turns,
        conv_id=conv_id,
        reasoning_effort=reasoning_effort,
        model=model,
    )


@mcp.tool(structured_output=False)
@_report_errors
def run_code(
    prompt: str,
    model: str = DEFAULT_MODEL,
) -> str:
    """Execute Python via Grok's sandboxed code interpreter.

    Use for problems where the LLM would otherwise hallucinate numbers:
    compound interest, t-tests, regressions, Sharpe ratios, simulations.
    The sandbox has NumPy / Pandas / Matplotlib / SciPy pre-installed but
    no network and no persistent file I/O.

    Args:
        prompt: Plain-language description of what to compute. Include
            data inline, not as a file.
        model: Grok model ID. Defaults to the GROK_DEFAULT_MODEL env var,
            else grok-4.7 (non-dated alias, same-model snapshots only).

    Returns:
        Grok's text answer with numeric results and embedded reasoning,
        plus a trailing cost footer.
    """
    return _run_code(prompt=prompt, model=model)


@mcp.tool()
@_report_errors
def generate_image(
    prompt: str,
    model: str = DEFAULT_IMAGE_MODEL,
    n: int = 1,
    aspect_ratio: str | None = None,
    resolution: str | None = None,
    response_format: str | None = None,
    quality: str | None = None,
) -> list[dict[str, Any]]:
    """Generate images from text via Grok Imagine.

    Default model is grok-imagine-image-2.0 (grok-imagine-image-quality is
    retired 2026-11-02). URLs returned are signed temporary; download
    promptly or request response_format='b64_json' for embedded payload.

    Args:
        prompt: Text description of the image. Required.
        model: Grok Imagine model. Default grok-imagine-image-2.0.
        n: Number of images (1-10, batch in one request).
        aspect_ratio: One of 1:1 / 16:9 / 9:16 / 4:3 / 3:4 / 3:2 / 2:3 /
            2:1 / 1:2 / 19.5:9 / 9:19.5 / 20:9 / 9:20 / 21:9 / 5:2 / auto.
        resolution: 1k / 1.5k / 2k (default 1k).
        response_format: url (default, signed) or b64_json (embedded).
        quality: low / medium / auto (grok-imagine-image-2.0 only). Omit for
            auto, which currently serves low for generation.

    Returns:
        List of dicts each containing url (or b64_json), revised_prompt,
        and cost_ticks / cost_usd (the per-request cost, repeated on each).
    """
    return _generate_image(
        prompt=prompt,
        model=model,
        n=n,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        response_format=response_format,
        quality=quality,
    )


def main() -> int:
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
