"""Generate images via Grok Imagine.

Default model is ``grok-imagine-image-quality`` — ``-pro`` was deprecated
2026-05-15. The model name accepted any string at API level; we don't
enumerate AVAILABLE_MODELS (silent-fallback risk learned from upstream
fork hard-coding).

API reference: https://docs.x.ai/docs/model-capabilities/images/generation
"""

from __future__ import annotations

from typing import Any

from grok.api import call_images_generations

VALID_ASPECT_RATIOS = {
    "1:1",
    "16:9",
    "9:16",
    "4:3",
    "3:4",
    "3:2",
    "2:3",
    "2:1",
    "1:2",
    "19.5:9",
    "9:19.5",
    "20:9",
    "9:20",
    "auto",
}

VALID_RESOLUTIONS = {"1k", "2k"}
VALID_RESPONSE_FORMATS = {"url", "b64_json"}


def generate_image(
    prompt: str,
    *,
    model: str = "grok-imagine-image-quality",
    n: int = 1,
    aspect_ratio: str | None = None,
    resolution: str | None = None,
    response_format: str | None = None,
) -> list[dict[str, Any]]:
    """Generate ``n`` images from ``prompt`` via Grok Imagine.

    Returns a list of dicts. Each dict has:
      - ``url``: signed temporary URL (default; download / process promptly).
      - ``b64_json``: present only if ``response_format='b64_json'``.
      - ``revised_prompt``: Grok's interpreted prompt — diagnostic value
        when the output drifts from intent.

    Args:
        prompt: Text description. Required.
        model: Grok Imagine model. Default ``grok-imagine-image-quality``
            (``-pro`` deprecated 2026-05-15).
        n: Number of images (batch). Clamped to 1-10.
        aspect_ratio: One of ``1:1`` / ``16:9`` / ``9:16`` / ``4:3`` /
            ``3:4`` / ``3:2`` / ``2:3`` / ``2:1`` / ``1:2`` / ``19.5:9`` /
            ``9:19.5`` / ``20:9`` / ``9:20`` / ``auto``. Default unset
            (server picks).
        resolution: ``1k`` or ``2k``. Default unset.
        response_format: ``url`` (default, signed temporary) or
            ``b64_json`` (embedded base64, larger payload but no expiry).

    Returns:
        List of image-result dicts (length == ``n``).

    Raises:
        ValueError: On empty prompt or invalid enum values.
        GrokAPIError: On non-2xx from xAI.
    """
    if not prompt.strip():
        raise ValueError("prompt cannot be empty")
    if aspect_ratio is not None and aspect_ratio not in VALID_ASPECT_RATIOS:
        raise ValueError(
            f"aspect_ratio must be one of {sorted(VALID_ASPECT_RATIOS)}"
        )
    if resolution is not None and resolution not in VALID_RESOLUTIONS:
        raise ValueError(f"resolution must be one of {sorted(VALID_RESOLUTIONS)}")
    if response_format is not None and response_format not in VALID_RESPONSE_FORMATS:
        raise ValueError(
            f"response_format must be one of {sorted(VALID_RESPONSE_FORMATS)}"
        )

    n = max(1, min(n, 10))

    return call_images_generations(
        prompt=prompt,
        model=model,
        n=n,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        response_format=response_format,
    )
