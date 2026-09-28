"""Unit tests for v0.4 search trace — mocked HTTP, no live API.

Output item and usage shapes below are copied from live /v1/responses
calls on 2026-09-28 (x_search with enable_video_understanding, web_search).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from grok.api import _parse_envelope, format_search_trace
from tests.test_v030 import _patched_client

X_OUTPUT = [
    {"type": "reasoning", "summary": []},
    {"type": "custom_tool_call", "name": "x_keyword_search", "input": '{"query":"from:SpaceXAI"}'},
    {"type": "custom_tool_call", "name": "x_user_search", "input": '{"query":"SpaceXAI"}'},
    {
        "type": "custom_tool_call",
        "name": "view_x_video",
        "input": '{"video_url":"https://v/1.mp4"}',
    },
    {
        "type": "custom_tool_call",
        "name": "view_x_video",
        "input": '{"video_url":"https://v/2.mp4"}',
    },
    {"type": "message", "content": [{"type": "output_text", "text": "answer"}]},
]
WEB_OUTPUT = [
    {"type": "web_search_call", "status": "completed", "action": {"type": "search", "query": "a"}},
    {"type": "web_search_call", "status": "completed", "action": {"type": "search", "query": "b"}},
    {"type": "message", "content": [{"type": "output_text", "text": "answer"}]},
]


def _usage(**details: int) -> dict:
    return {"cost_in_usd_ticks": 600000000, "server_side_tool_usage_details": details}


def test_parse_envelope_collects_tool_calls_and_usage() -> None:
    env = _parse_envelope(
        {"output": X_OUTPUT, "usage": _usage(x_search_calls=2, x_posts_fetched=4)}
    )
    assert env["tool_calls"] == [
        "x_keyword_search",
        "x_user_search",
        "view_x_video",
        "view_x_video",
    ]
    assert env["tool_usage"] == {"x_search_calls": 2, "x_posts_fetched": 4}


def test_parse_envelope_names_web_search_calls() -> None:
    env = _parse_envelope({"output": WEB_OUTPUT, "usage": _usage(web_search_calls=2)})
    assert env["tool_calls"] == ["web_search", "web_search"]


def test_parse_envelope_empty_trace_without_tools() -> None:
    env = _parse_envelope({"output": [{"type": "message", "content": []}]})
    assert env["tool_calls"] == []
    assert env["tool_usage"] == {}


def test_trace_counts_calls_and_fetched_items() -> None:
    line = format_search_trace(
        ["x_keyword_search", "x_user_search", "view_x_video", "view_x_video"],
        {"x_search_calls": 2, "x_posts_fetched": 4, "x_users_fetched": 1},
    )
    assert line == (
        "\n_searches: x_keyword_search, x_user_search, view_x_video ×2"
        " · 4 posts, 1 profiles fetched_"
    )


def test_trace_warns_when_x_search_fetched_nothing() -> None:
    # The 2026-09-28 failure: 13 searches on a handle with no posts, and the
    # model still answered confidently.
    line = format_search_trace(
        ["x_keyword_search"] * 13,
        {"x_search_calls": 13, "x_posts_fetched": 0, "x_users_fetched": 0},
    )
    assert "x_keyword_search ×13" in line
    assert "fetched 0 posts" in line


def test_trace_no_warning_for_profile_only_results() -> None:
    line = format_search_trace(
        ["x_user_search"], {"x_search_calls": 1, "x_posts_fetched": 0, "x_users_fetched": 3}
    )
    assert "⚠" not in line


def test_trace_web_only_has_no_x_counts() -> None:
    line = format_search_trace(["web_search", "web_search"], {"web_search_calls": 2})
    assert line == "\n_searches: web_search ×2_"


def test_trace_empty_without_calls() -> None:
    assert format_search_trace([], {}) == ""


def _resp(output: list, usage: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"output": output, "usage": usage}
    return resp


def test_search_x_appends_trace_after_cost() -> None:
    from grok.tools.search_x import search_x

    ctx, _ = _patched_client(_resp(X_OUTPUT, _usage(x_search_calls=2, x_posts_fetched=4)))
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        out = search_x("q")
    assert out.index("_grok cost: $") < out.index("_searches: ")


def test_search_web_appends_trace() -> None:
    from grok.tools.search_web import search_web

    ctx, _ = _patched_client(_resp(WEB_OUTPUT, _usage(web_search_calls=2)))
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        out = search_web("q")
    assert "_searches: web_search ×2_" in out


def test_text_tools_have_no_output_schema() -> None:
    """With an outputSchema, FastMCP also sends {"result": "<text>"} as
    structuredContent, and Claude Code hands the model that JSON (newlines
    escaped) instead of the markdown text (observed 2026-09-28)."""
    import asyncio

    import server

    schemas = {t.name: t.outputSchema for t in asyncio.run(server.mcp.list_tools())}
    for name in ("chat", "search_x", "search_web", "run_code"):
        assert schemas[name] is None, name
