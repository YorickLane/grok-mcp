"""Unit tests for v0.5 — MCP SDK 2.x and packaging. Mocked HTTP, no live API.

Tool calls go through the SDK's in-process Client, so results carry the same
is_error / structured_content a stdio client receives.
"""

from __future__ import annotations

import asyncio
import importlib
import sys
import tomllib
from pathlib import Path
from unittest.mock import patch

import httpx
from mcp import Client, StdioServerParameters

from grok import server
from tests.test_v030 import _mock_response, _patched_client

REPO = Path(__file__).parents[1]
PYPROJECT = tomllib.loads((REPO / "pyproject.toml").read_text())


def _call(name: str, arguments: dict):
    async def go():
        async with Client(server.mcp) as client:
            return await client.call_tool(name, arguments)

    return asyncio.run(go())


def _error_text(name: str, arguments: dict) -> str:
    result = _call(name, arguments)
    assert result.is_error
    return result.content[0].text


def test_console_script_target_is_in_the_wheel() -> None:
    """grok-mcp pointed at a top-level server.py the wheel never shipped, so
    `uvx --from <wheel> grok-mcp` died with No module named 'server'."""
    module, attr = PYPROJECT["project"]["scripts"]["grok-mcp"].split(":")
    packages = PYPROJECT["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
    assert module.split(".")[0] in packages
    assert callable(getattr(importlib.import_module(module), attr))


def test_root_server_py_still_launches() -> None:
    """Existing registrations run `python <repo>/server.py` over stdio."""

    async def go():
        params = StdioServerParameters(command=sys.executable, args=[str(REPO / "server.py")])
        async with Client(params) as client:
            return await client.list_tools()

    names = {t.name for t in asyncio.run(go()).tools}
    assert names == {"chat", "search_x", "search_web", "run_code", "generate_image"}


def test_text_tool_result_is_plain_text() -> None:
    ctx, _ = _patched_client(_mock_response(text="line 1\nline 2"))
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        result = _call("chat", {"prompt": "hi"})
    assert not result.is_error
    assert result.structured_content is None
    assert result.content[0].text.startswith("line 1\nline 2")


# mcp >= 2.1 hands the model only "Error executing tool <name>" for any exception
# other than ToolError; these failures must keep their message.


def test_value_error_reaches_the_model() -> None:
    assert "prompt cannot be empty" in _error_text("chat", {"prompt": ""})


def test_api_error_reaches_the_model() -> None:
    with patch.dict("os.environ", {"XAI_API_KEY": ""}):
        assert "XAI_API_KEY env var not set" in _error_text("search_x", {"query": "q"})


def test_network_error_reaches_the_model() -> None:
    ctx, client = _patched_client(_mock_response())
    client.post.side_effect = httpx.ReadTimeout("timed out")
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        assert "timed out" in _error_text("search_web", {"query": "q"})


def test_package_version_matches_pyproject() -> None:
    """grok.__version__ sat at 0.3.0 through the 0.3.1 and 0.4.0 releases."""
    import tomllib
    from pathlib import Path

    import grok

    pyproject = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text())
    assert grok.__version__ == pyproject["project"]["version"]
