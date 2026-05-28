"""Plain chat with Grok — no Live Search, no tools.

Use this for: reasoning, code generation, translation, summarization, anything
that does NOT need real-time external data. If you need X / web content, use
``search_x`` / ``search_web`` instead — they're cheaper than dumping search
results into a chat prompt.
"""

from __future__ import annotations

from grok.api import call_responses


def chat(
    prompt: str,
    *,
    model: str = "grok-4.3",
    system_prompt: str | None = None,
) -> str:
    """Single-turn chat. Returns Grok's text response.

    Multi-turn conversation across calls isn't implemented in v0.1 — pass
    the whole conversation as a formatted ``prompt`` string instead. Native
    multi-turn (session_id) is on the v0.2 roadmap.

    Args:
        prompt: User message. Required.
        model: Grok model ID. Default ``grok-4.3``. Other options at
            https://docs.x.ai/docs/models
        system_prompt: Optional developer/system role instructions.

    Returns:
        Plain text response. No citations (chat has no search tools).
    """
    if not prompt.strip():
        raise ValueError("prompt cannot be empty")

    result = call_responses(
        prompt=prompt,
        model=model,
        system_prompt=system_prompt,
    )
    return result["text"]
