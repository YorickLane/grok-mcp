"""Unit tests for grok.api — pure logic, no live HTTP."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from grok.api import (
    DEFAULT_MODEL,
    FALLBACK_DEFAULT_MODEL,
    GrokAPIError,
    _parse_envelope,
    _require_api_key,
    build_tool_spec,
    format_citations_md,
    resolve_default_model,
)


def test_build_tool_spec_filters_none() -> None:
    spec = build_tool_spec(
        "x_search",
        from_date="2026-05-28",
        to_date=None,
        enable_video_understanding=True,
        irrelevant=None,
    )
    assert spec == {
        "type": "x_search",
        "from_date": "2026-05-28",
        "enable_video_understanding": True,
    }


def test_build_tool_spec_empty() -> None:
    assert build_tool_spec("web_search") == {"type": "web_search"}


def test_parse_envelope_text_and_citations() -> None:
    body = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "Karpathy joined Anthropic 2026-05-19.",
                        "annotations": [
                            {
                                "type": "url_citation",
                                "url": "https://techcrunch.com/2026/05/19/karpathy",
                                "title": "TechCrunch",
                            },
                        ],
                    },
                ],
            },
        ],
    }
    parsed = _parse_envelope(body)
    assert parsed["text"] == "Karpathy joined Anthropic 2026-05-19."
    assert parsed["citations"] == [
        {"url": "https://techcrunch.com/2026/05/19/karpathy", "title": "TechCrunch"},
    ]


def test_parse_envelope_skips_non_message_items() -> None:
    body = {
        "output": [
            {"type": "reasoning", "content": "ignored"},
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "kept"}],
            },
        ],
    }
    assert _parse_envelope(body)["text"] == "kept"


def test_format_citations_md_dedups() -> None:
    cites = [
        {"url": "https://a.com", "title": "A"},
        {"url": "https://a.com", "title": "A (dup)"},
        {"url": "https://b.com", "title": "B"},
    ]
    md = format_citations_md(cites)
    assert md.count("https://a.com") == 1
    assert "https://b.com" in md
    assert md.startswith("\n**Sources:**")


def test_format_citations_md_empty() -> None:
    assert format_citations_md([]) == ""


def test_require_api_key_missing() -> None:
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(GrokAPIError) as exc:
            _require_api_key()
        assert exc.value.status == 0
        assert "XAI_API_KEY" in str(exc.value)


def test_require_api_key_present() -> None:
    with patch.dict(os.environ, {"XAI_API_KEY": "FAKE-FOR-TEST"}):
        assert _require_api_key() == "FAKE-FOR-TEST"


def test_resolve_default_model_env_override() -> None:
    with patch.dict(os.environ, {"GROK_DEFAULT_MODEL": "grok-4.20-0309-reasoning"}):
        assert resolve_default_model() == "grok-4.20-0309-reasoning"


def test_resolve_default_model_fallback_when_unset() -> None:
    with patch.dict(os.environ, {}, clear=True):
        assert resolve_default_model() == FALLBACK_DEFAULT_MODEL


def test_resolve_default_model_empty_env_falls_back() -> None:
    with patch.dict(os.environ, {"GROK_DEFAULT_MODEL": ""}):
        assert resolve_default_model() == FALLBACK_DEFAULT_MODEL


def test_fallback_is_non_dated_alias() -> None:
    # Guard: the fallback must stay a non-dated alias (auto-tracks the
    # latest stable version per docs.x.ai/developers/models). A dated ID
    # like grok-4.20-0309-* would silently freeze the default.
    import re

    assert not re.search(r"-\d{4}$", FALLBACK_DEFAULT_MODEL)
    assert not FALLBACK_DEFAULT_MODEL.endswith("-latest")


def test_default_model_is_single_source_of_truth() -> None:
    # Every tool signature (library layer AND MCP layer) must take its
    # model default from grok.api.DEFAULT_MODEL — no hardcoded copies.
    import inspect

    import server
    from grok.tools.chat import chat
    from grok.tools.run_code import run_code
    from grok.tools.search_web import search_web
    from grok.tools.search_x import search_x

    for fn in (chat, search_x, search_web, run_code):
        assert inspect.signature(fn).parameters["model"].default == DEFAULT_MODEL

    for fn in (server.chat, server.search_x, server.search_web, server.run_code):
        assert inspect.signature(fn).parameters["model"].default == DEFAULT_MODEL
