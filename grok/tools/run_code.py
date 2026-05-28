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

from grok.api import build_tool_spec, call_responses, format_citations_md


def run_code(
    prompt: str,
    *,
    model: str = "grok-4.3",
) -> str:
    """Have Grok write + execute Python to answer ``prompt``.

    Use for problems where the LLM would otherwise hallucinate numbers:
    compound interest, t-tests, regressions, Sharpe ratios, simulations.

    Args:
        prompt: Plain-language description of what to compute. Include
            data inline (``[120000, 135000, ...]``), not as a file. The
            sandbox has no file I/O / no network.
        model: Grok model ID. Default ``grok-4.3``. Reasoning models
            produce better code; non-reasoning models may hallucinate.

    Returns:
        Grok's text answer (with embedded reasoning + numeric results)
        followed by an empty citations block (code execution doesn't
        produce citations).

    Raises:
        ValueError: If ``prompt`` empty.
        GrokAPIError: On non-2xx from xAI.
    """
    if not prompt.strip():
        raise ValueError("prompt cannot be empty")

    tool_spec = build_tool_spec("code_interpreter")
    result = call_responses(prompt=prompt, model=model, tools=[tool_spec])
    return result["text"] + format_citations_md(result["citations"])
