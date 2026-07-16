"""Unit tests for v0.3 Tier A features — mocked HTTP, no live API.

Covers: reasoning_effort (F1), cost_in_usd_ticks surfacing (F2),
response_format json_schema (F3), max_turns (F4), conv_id caching (F5).

Payload shapes here were live-probe-verified against
https://api.x.ai/v1/responses on 2026-05-29 (both HTTP 200) — see the
v0.3 brief. Tests assert the EXACT Responses-API shapes (not the
Chat-Completions shapes the docs prose sometimes describes).
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from grok.api import call_responses, format_cost_footer


def _mock_response(
    *,
    text: str = "ok",
    usage: dict[str, Any] | None = None,
) -> MagicMock:
    """Build a fake httpx.Response with a Responses-API envelope."""
    body: dict[str, Any] = {
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": text}],
            },
        ],
    }
    if usage is not None:
        body["usage"] = usage
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = body
    return resp


def _patched_client(resp: MagicMock):
    """Return a patch context for httpx.Client whose post() returns resp.

    The returned object also exposes a `.post` MagicMock so callers can
    inspect call_args (json= payload, headers= dict).
    """
    client_instance = MagicMock()
    client_instance.post.return_value = resp
    client_instance.__enter__.return_value = client_instance
    client_instance.__exit__.return_value = False
    ctx = patch("grok.api.httpx.Client", return_value=client_instance)
    return ctx, client_instance


# ── Feature 1: reasoning_effort ──────────────────────────────────────


def test_reasoning_effort_sets_nested_key() -> None:
    resp = _mock_response()
    ctx, client = _patched_client(resp)
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        call_responses("hi", reasoning_effort="none")
    payload = client.post.call_args.kwargs["json"]
    assert payload["reasoning"] == {"effort": "none"}


def test_reasoning_effort_omitted_when_none() -> None:
    resp = _mock_response()
    ctx, client = _patched_client(resp)
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        call_responses("hi")
    payload = client.post.call_args.kwargs["json"]
    assert "reasoning" not in payload


def test_reasoning_effort_invalid_raises() -> None:
    with patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        with pytest.raises(ValueError, match="reasoning_effort"):
            call_responses("hi", reasoning_effort="extreme")


def test_reasoning_effort_all_valid_values() -> None:
    for value in ("none", "low", "medium", "high"):
        resp = _mock_response()
        ctx, client = _patched_client(resp)
        with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
            call_responses("hi", reasoning_effort=value)
        payload = client.post.call_args.kwargs["json"]
        assert payload["reasoning"] == {"effort": value}


# ── Feature 2: cost_in_usd_ticks surfacing ───────────────────────────


def test_parse_envelope_surfaces_cost() -> None:
    resp = _mock_response(usage={"cost_in_usd_ticks": 12345})
    ctx, _ = _patched_client(resp)
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        result = call_responses("hi")
    assert result["cost_ticks"] == 12345
    assert result["cost_usd"] == pytest.approx(12345 / 1e10)


def test_parse_envelope_cost_none_when_absent() -> None:
    resp = _mock_response()  # no usage block
    ctx, _ = _patched_client(resp)
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        result = call_responses("hi")
    assert result["cost_ticks"] is None
    assert result["cost_usd"] is None


def test_format_cost_footer_present() -> None:
    footer = format_cost_footer(0.000123, "grok-4.5")
    assert footer == "\n\n—\n_grok cost: $0.000123 · grok-4.5_"


def test_format_cost_footer_none_returns_empty() -> None:
    assert format_cost_footer(None, "grok-4.5") == ""


def test_chat_appends_cost_footer() -> None:
    from grok.tools.chat import chat

    resp = _mock_response(text="answer", usage={"cost_in_usd_ticks": 5000000})
    ctx, _ = _patched_client(resp)
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        out = chat("hi")
    assert out.startswith("answer")
    assert "_grok cost: $" in out


def test_search_web_appends_cost_footer() -> None:
    from grok.tools.search_web import search_web

    resp = _mock_response(text="result", usage={"cost_in_usd_ticks": 5000000})
    ctx, _ = _patched_client(resp)
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        out = search_web("q")
    assert "_grok cost: $" in out


def test_run_code_appends_cost_footer() -> None:
    from grok.tools.run_code import run_code

    resp = _mock_response(text="42", usage={"cost_in_usd_ticks": 5000000})
    ctx, _ = _patched_client(resp)
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        out = run_code("compute")
    assert "_grok cost: $" in out


def test_search_x_appends_cost_footer() -> None:
    from grok.tools.search_x import search_x

    resp = _mock_response(text="tweet", usage={"cost_in_usd_ticks": 5000000})
    ctx, _ = _patched_client(resp)
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        out = search_x("q")
    assert "_grok cost: $" in out


def test_generate_image_adds_cost_keys() -> None:
    """call_images_generations surfaces per-request cost on each dict."""
    from grok.tools.generate_image import generate_image

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "data": [{"url": "https://example.com/a.jpg"}],
        "usage": {"cost_in_usd_ticks": 700000000},
    }
    ctx, _ = _patched_client(resp)
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        out = generate_image("a cat")
    assert isinstance(out, list)
    assert out[0]["cost_ticks"] == 700000000
    assert out[0]["cost_usd"] == pytest.approx(700000000 / 1e10)


# ── Feature 3: response_format json_schema ───────────────────────────


def test_response_format_sets_text_format_key() -> None:
    schema = {"type": "object", "properties": {"n": {"type": "integer"}}}
    resp = _mock_response(text='{"n":42}')
    ctx, client = _patched_client(resp)
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        call_responses("give me 42", response_format_schema=schema)
    payload = client.post.call_args.kwargs["json"]
    fmt = payload["text"]["format"]
    assert fmt["type"] == "json_schema"
    assert fmt["schema"] == schema
    assert fmt["strict"] is True
    assert "name" in fmt


def test_response_format_omitted_when_none() -> None:
    resp = _mock_response()
    ctx, client = _patched_client(resp)
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        call_responses("hi")
    payload = client.post.call_args.kwargs["json"]
    assert "text" not in payload


def test_chat_json_mode_returns_valid_json_no_footer() -> None:
    """In json mode the return value must be parseable JSON, no cost footer."""
    from grok.tools.chat import chat

    schema = {"type": "object", "properties": {"n": {"type": "integer"}}}
    resp = _mock_response(text='{"n":42}', usage={"cost_in_usd_ticks": 5000000})
    ctx, _ = _patched_client(resp)
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        out = chat("give me 42", response_format=schema)
    parsed = json.loads(out)  # must not raise
    assert parsed == {"n": 42}
    assert "_grok cost: $" not in out


# ── Feature 4: max_turns ─────────────────────────────────────────────


def test_max_turns_sets_top_level_key() -> None:
    resp = _mock_response()
    ctx, client = _patched_client(resp)
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        call_responses("hi", max_turns=1)
    payload = client.post.call_args.kwargs["json"]
    assert payload["max_turns"] == 1


def test_max_turns_omitted_when_none() -> None:
    resp = _mock_response()
    ctx, client = _patched_client(resp)
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        call_responses("hi")
    payload = client.post.call_args.kwargs["json"]
    assert "max_turns" not in payload


# ── Feature 5: conv_id prompt caching ────────────────────────────────


def test_conv_id_sets_payload_and_header() -> None:
    resp = _mock_response()
    ctx, client = _patched_client(resp)
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        call_responses("hi", conv_id="conv-abc")
    payload = client.post.call_args.kwargs["json"]
    headers = client.post.call_args.kwargs["headers"]
    assert payload["prompt_cache_key"] == "conv-abc"
    assert headers["x-grok-conv-id"] == "conv-abc"


def test_conv_id_omitted_when_none() -> None:
    resp = _mock_response()
    ctx, client = _patched_client(resp)
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        call_responses("hi")
    payload = client.post.call_args.kwargs["json"]
    headers = client.post.call_args.kwargs["headers"]
    assert "prompt_cache_key" not in payload
    assert "x-grok-conv-id" not in headers
