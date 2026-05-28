"""Example: catch engagement-farm pattern via enable_video_understanding.

Anchor case (2026-05-28): a tweet whose body text says "Obsidian + Vellum"
but whose attached 13-second video actually shows "Obsidian + Claude +
Notion". Without ``enable_video_understanding`` we miss the contradiction
between body and video — both of which are part of the post's meaning.

Run: ``python examples/search_x_with_video.py``
Requires: ``XAI_API_KEY`` in env.
"""

from __future__ import annotations

from grok.tools.search_x import search_x


def main() -> None:
    answer = search_x(
        query=(
            "Look at cyrilXBT's tweet from 2026-05-27. Analyze the attached "
            "video. Does the body text and the video describe the same set "
            "of tools, or do they contradict?"
        ),
        allowed_x_handles=["cyrilXBT"],
        from_date="2026-05-27",
        to_date="2026-05-27",
        enable_video_understanding=True,
    )
    print(answer)


if __name__ == "__main__":
    main()
