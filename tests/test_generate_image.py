"""Unit tests for generate_image input validation — no live HTTP."""

from __future__ import annotations

import pytest

from grok.tools.generate_image import generate_image


def test_empty_prompt_raises() -> None:
    with pytest.raises(ValueError, match="prompt cannot be empty"):
        generate_image("")


def test_invalid_aspect_ratio_raises() -> None:
    with pytest.raises(ValueError, match="aspect_ratio must be one of"):
        generate_image("a cat", aspect_ratio="7:11")


def test_valid_aspect_ratio_accepted() -> None:
    # Won't actually call API — we mock at the http boundary in api.py.
    # Here we just validate that 16:9 doesn't trigger the enum guard.
    from unittest.mock import patch

    with patch("grok.tools.generate_image.call_images_generations") as mock_call:
        mock_call.return_value = [{"url": "https://example.com/img.jpg"}]
        result = generate_image("test", aspect_ratio="16:9")
        assert result == [{"url": "https://example.com/img.jpg"}]
        mock_call.assert_called_once()
        kwargs = mock_call.call_args.kwargs
        assert kwargs["aspect_ratio"] == "16:9"


def test_invalid_resolution_raises() -> None:
    with pytest.raises(ValueError, match="resolution must be one of"):
        generate_image("a cat", resolution="4k")


def test_invalid_response_format_raises() -> None:
    with pytest.raises(ValueError, match="response_format must be one of"):
        generate_image("a cat", response_format="webp")


def test_n_clamped_to_range() -> None:
    from unittest.mock import patch

    with patch("grok.tools.generate_image.call_images_generations") as mock_call:
        mock_call.return_value = []
        generate_image("test", n=999)
        assert mock_call.call_args.kwargs["n"] == 10
        generate_image("test", n=0)
        assert mock_call.call_args.kwargs["n"] == 1
        generate_image("test", n=-5)
        assert mock_call.call_args.kwargs["n"] == 1
