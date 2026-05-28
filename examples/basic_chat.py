"""Example: plain chat with Grok, no Live Search.

Run: ``python examples/basic_chat.py``
Requires: ``XAI_API_KEY`` in env.
"""

from __future__ import annotations

from grok.tools.chat import chat


def main() -> None:
    answer = chat(
        prompt="Explain in two sentences what xAI's Live Search API is.",
        system_prompt="You are a concise technical writer. Avoid hype.",
    )
    print(answer)


if __name__ == "__main__":
    main()
