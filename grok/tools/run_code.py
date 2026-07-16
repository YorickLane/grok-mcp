"""Execute Python code via Grok's sandboxed interpreter.

Grok writes and executes Python in a sandboxed environment with NumPy /
Pandas / Matplotlib / SciPy pre-installed. Use for: precise calculations
(skip LLM arithmetic mistakes), statistical analysis, financial modeling,
quantitative simulations.

xAI's name for this tool is ``code_interpreter`` in the Responses API
(OpenAI compat), ``code_execution`` in the xAI SDK. We use the Responses
API surface, so the wire-level tool name is ``code_interpreter``.

API reference: https://docs.x.ai/docs/tools/code-execution
"""

from __future__ import annotations

from grok.api import (
    DEFAULT_MODEL,
    build_tool_spec,
    call_responses,
    format_citations_md,
    format_cost_footer,
)


def run_code(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
) -> str:
    """Have Grok write + execute Python to answer ``prompt``.

    Use for problems where the LLM would otherwise hallucinate numbers:
    compound interest, t-tests, regressions, Sharpe ratios, simulations.

    Args:
        prompt: Plain-language description of what to compute. Include
            data inline (``[120000, 135000, ...]``), not as a file. The
            sandbox has no file I/O / no network.
        model: Grok model ID. Defaults to the ``GROK_DEFAULT_MODEL`` env
            var, else ``grok-4.5`` (non-dated alias, tracks latest stable).
            Reasoning models produce better code; non-reasoning models may
            hallucinate.

    Returns:
        Grok's text answer (with embedded reasoning + numeric results)
        followed by an empty citations block (code execution doesn't
        produce citations) and a trailing cost footer.

    Raises:
        ValueError: If ``prompt`` empty.
        GrokAPIError: On non-2xx from xAI.
    """
    if not prompt.strip():
        raise ValueError("prompt cannot be empty")

    tool_spec = build_tool_spec("code_interpreter")
    result = call_responses(prompt=prompt, model=model, tools=[tool_spec])
    return (
        result["text"]
        + format_citations_md(result["citations"])
        + format_cost_footer(result["cost_usd"], model)
    )
