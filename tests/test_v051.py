"""Unit tests for v0.5.1 — clearer errors for a non-JSON 2xx body and a
non-ASCII conv_id. Mocked HTTP, no live API.
"""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from grok.api import XAI_IMAGES_URL, GrokAPIError, call_images_generations, call_responses
from tests.test_v030 import _mock_response, _patched_client
from tests.test_v050 import _error_text


def _html_response(url: str) -> httpx.Response:
    return httpx.Response(
        200, content=b"<html>proxy login</html>", request=httpx.Request("POST", url)
    )


def test_non_json_2xx_body_reaches_the_model_as_api_error() -> None:
    """A 2xx HTML page used to reach the model as `Expecting value: line 1
    column 1 (char 0)`, which doesn't say the xAI response was the problem."""
    ctx, _ = _patched_client(_html_response("https://api.x.ai/v1/responses"))
    with ctx, patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}):
        text = _error_text("chat", {"prompt": "hi"})
    assert "xAI API 200" in text
    assert "proxy login" in text


def test_non_json_2xx_body_from_images_is_api_error() -> None:
    ctx, _ = _patched_client(_html_response(XAI_IMAGES_URL))
    with (
        ctx,
        patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}),
        pytest.raises(GrokAPIError, match="xAI API 200"),
    ):
        call_images_generations("a cat")


def test_non_ascii_conv_id_rejected_before_request() -> None:
    """httpx sends headers as ASCII, so a non-ASCII conv_id used to fail with
    `'ascii' codec can't encode characters ...`."""
    ctx, client = _patched_client(_mock_response())
    with (
        ctx,
        patch.dict("os.environ", {"XAI_API_KEY": "FAKE"}),
        pytest.raises(ValueError, match="conv_id must be ASCII"),
    ):
        call_responses("hi", conv_id="会话一")
    client.post.assert_not_called()
