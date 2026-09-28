"""Unit tests for v0.3.1 — mocked HTTP, no live API.

Covers: reasoning_effort on search_x / search_web, removal of the
undocumented ``inline_citations`` payload key, the 21:9 / 5:2 aspect ratios
and the ``quality`` parameter on generate_image.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from grok.api import build_tool_spec, call_responses
from tests.test_v030 import _mock_response, _patched_client


@pytest.mark.parametrize("tool_name", ["search_x", "search_web"])
def test_search_tools_pass_reasoning_effort(tool_name: str) -> None:
    module = __import__(f"grok.tools.{tool_name}", fromlist=[tool_name])
    tool = getattr(module, tool_name)
    resp = _mock_response()
    ctx, client = _patched_client(resp)
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        tool("q", reasoning_effort="low")
    payload = client.post.call_args.kwargs["json"]
    assert payload["reasoning"] == {"effort": "low"}


@pytest.mark.parametrize("tool_name", ["search_x", "search_web"])
def test_search_tools_omit_reasoning_by_default(tool_name: str) -> None:
    module = __import__(f"grok.tools.{tool_name}", fromlist=[tool_name])
    tool = getattr(module, tool_name)
    resp = _mock_response()
    ctx, client = _patched_client(resp)
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        tool("q")
    payload = client.post.call_args.kwargs["json"]
    assert "reasoning" not in payload


def test_search_payload_has_no_inline_citations_key() -> None:
    """Not in the /v1/responses schema; inline citations are on by default."""
    resp = _mock_response()
    ctx, client = _patched_client(resp)
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        call_responses("q", tools=[build_tool_spec("x_search")])
    payload = client.post.call_args.kwargs["json"]
    assert "inline_citations" not in payload


@pytest.mark.parametrize("ratio", ["21:9", "5:2"])
def test_new_aspect_ratios_accepted(ratio: str) -> None:
    from grok.tools.generate_image import generate_image

    with patch("grok.tools.generate_image.call_images_generations") as mock_call:
        mock_call.return_value = []
        generate_image("test", aspect_ratio=ratio)
    assert mock_call.call_args.kwargs["aspect_ratio"] == ratio


def test_quality_sets_payload_key() -> None:
    from grok.tools.generate_image import generate_image

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": []}
    ctx, client = _patched_client(resp)
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        generate_image("a cat", quality="medium")
    assert client.post.call_args.kwargs["json"]["quality"] == "medium"


def test_quality_omitted_by_default() -> None:
    from grok.tools.generate_image import generate_image

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": []}
    ctx, client = _patched_client(resp)
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        generate_image("a cat")
    assert "quality" not in client.post.call_args.kwargs["json"]


def test_invalid_quality_raises() -> None:
    """grok-imagine-image-2.0 answers "high" with HTTP 400 (live 2026-09-28)."""
    from grok.tools.generate_image import generate_image

    with pytest.raises(ValueError, match="quality must be one of"):
        generate_image("a cat", quality="high")


def test_mcp_layer_exposes_every_library_param() -> None:
    """server.py re-declares each tool; a param added to the library layer
    must also reach the MCP schema, or MCP clients can never set it."""
    import inspect

    import server
    from grok.tools import chat, generate_image, run_code, search_web, search_x

    for module in (chat, search_x, search_web, run_code, generate_image):
        name = module.__name__.rsplit(".", 1)[1]
        lib = set(inspect.signature(getattr(module, name)).parameters)
        mcp = set(inspect.signature(getattr(server, name)).parameters)
        assert lib == mcp, f"{name}: library-only {lib - mcp}, MCP-only {mcp - lib}"


def test_resolution_1_5k_accepted() -> None:
    """In the OpenAPI enum though the docs prose lists only 1k/2k; the API
    served it (HTTP 200, $0.05/image) on 2026-09-28."""
    from grok.tools.generate_image import generate_image

    with patch("grok.tools.generate_image.call_images_generations") as mock_call:
        mock_call.return_value = []
        generate_image("test", resolution="1.5k")
    assert mock_call.call_args.kwargs["resolution"] == "1.5k"
