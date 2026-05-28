"""Unit tests for tool input validation — no live HTTP."""

from __future__ import annotations

import pytest

from grok.tools.chat import chat
from grok.tools.run_code import run_code
from grok.tools.search_web import search_web
from grok.tools.search_x import search_x


def test_chat_empty_prompt_raises() -> None:
    with pytest.raises(ValueError, match="prompt cannot be empty"):
        chat("")


def test_chat_whitespace_prompt_raises() -> None:
    with pytest.raises(ValueError, match="prompt cannot be empty"):
        chat("   \n\t  ")


def test_search_x_empty_query_raises() -> None:
    with pytest.raises(ValueError, match="query cannot be empty"):
        search_x("")


def test_search_x_mutually_exclusive_handles_raises() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        search_x(
            "test",
            allowed_x_handles=["a"],
            excluded_x_handles=["b"],
        )


def test_search_web_empty_query_raises() -> None:
    with pytest.raises(ValueError, match="query cannot be empty"):
        search_web("")


def test_search_web_mutually_exclusive_domains_raises() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        search_web(
            "test",
            allowed_domains=["a.com"],
            excluded_domains=["b.com"],
        )


def test_run_code_empty_prompt_raises() -> None:
    with pytest.raises(ValueError, match="prompt cannot be empty"):
        run_code("")
