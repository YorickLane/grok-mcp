# grok-mcp

> **Lean MCP server for xAI Grok.** Full Live Search parameter surface
> (including video understanding most community servers omit), modular
> architecture, explicit roadmap, MIT licensed.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-stdio-green.svg)](https://modelcontextprotocol.io/)
[![Status](https://img.shields.io/badge/status-v0.1.0%20early-orange.svg)](#roadmap)

## Why this exists

Community Grok MCP servers exist, but as of 2026-05-28 they're missing
parameters xAI shipped weeks ago. Concrete example:

> *2026-05-28.* I tried to analyze a tweet whose body said "Obsidian +
> Vellum" but whose attached 13-second video actually showed "Obsidian +
> Claude + Notion" — body and video contradicting each other, a classic
> engagement-farm pattern. Through the standard community Grok MCP server
> I got the body text fine, video content was opaque. xAI's
> `enable_video_understanding=true` parameter has existed since 2026-05-15;
> the server just hadn't wired it. Direct API call with the parameter
> enabled returned the full video transcript in 12 seconds. **The xAI
> capability was always there. The MCP wrapper was the gap.**

This server's design rule: **if the xAI API exposes it, the MCP exposes it.**

## What it ships (v0.1)

3 tools wired with the full xAI parameter surface as of 2026-05-28:

| Tool | Purpose | Cost-relevant params |
|---|---|---|
| `chat` | Plain chat with Grok — reasoning, codegen, translation | `model`, `system_prompt` |
| `search_x` | X (Twitter) Live Search | `allowed/excluded_x_handles` (cap 20), date range, **`enable_image_understanding`**, **`enable_video_understanding`** |
| `search_web` | Web Live Search | `allowed/excluded_domains` (cap 5), **`enable_image_understanding`**, **`enable_image_search`** (markdown embed) |

The bolded params are the ones most community servers omit.

## Differs from `wynandw87/claude-code-grok-mcp`

| | this | wynandw87 (v3.6.0, 2026-05-16) |
|---|---|---|
| Live Search media | image + video understanding wired | not exposed |
| Handle cap | 20 (matches xAI cap) | 10 (hardcoded) |
| `enable_image_search` markdown embed | yes | not exposed |
| Architecture | modular `grok/tools/` (one tool per file) | monolithic ~1700-line server.py |
| Tests | pytest, no live HTTP needed | none visible |
| Roadmap | explicit (see below) | none documented |
| Scope | search + chat first, growing | full surface incl. TTS / STT / video gen |

Both MIT. This is a clean reimplementation, not a fork.

## Quick start

```bash
git clone https://github.com/YorickLane/grok-mcp
cd grok-mcp
uv venv && uv pip install -e .

# Register with Claude Code (per-user, stdio transport)
claude mcp add -s user -t stdio grok \
  $(pwd)/.venv/bin/python3 $(pwd)/server.py
```

Set `XAI_API_KEY` in your shell env (get one at
[console.x.ai](https://console.x.ai)). The server reads the env var on
every call — key rotation works without restart.

Restart Claude Code; the three tools are now available as
`mcp__grok__chat`, `mcp__grok__search_x`, `mcp__grok__search_web`.

## Python library use

The package is importable directly without going through MCP:

```python
from grok.tools.search_x import search_x

answer = search_x(
    "What is cyrilXBT saying about Obsidian on 2026-05-27?",
    allowed_x_handles=["cyrilXBT"],
    from_date="2026-05-27",
    to_date="2026-05-27",
    enable_video_understanding=True,  # catch video content
)
print(answer)
```

## Roadmap

### v0.1 (current)
- [x] `chat`
- [x] `search_x` — full param surface
- [x] `search_web` — full param surface

### v0.2 (planned)
- [ ] `run_code` — Grok code interpreter
- [ ] `generate_image` — `grok-imagine` family
- [ ] Multi-turn chat with `session_id`

### v0.3 (planned, lower priority)
- [ ] `upload_file` + chat-with-files
- [ ] `edit_image` / multi-image edit

### Out of scope (no plans)
- TTS / STT — use OpenAI or ElevenLabs
- Voice agents — separate concern
- Persistent session storage beyond in-memory

## Pairing with `epistemics-mcp`

`epistemics-mcp` exposes verification primitives (probe an API, diff schemas,
build anti-stale prompts). The natural pattern is **probe before call, verify
after call**:

```python
# pre-call: catch xAI schema lag in my MCP
from epistemics.tools.probe_api import probe_api_endpoint
verdict = probe_api_endpoint(
    method="GET",
    url="https://docs.x.ai/docs/tools/x-search",
    expected_response_contains=["enable_video_understanding"],
)
# if verdict.match: schema still current; proceed
```

See [github.com/YorickLane/epistemics-mcp](https://github.com/YorickLane/epistemics-mcp).

## Development

```bash
uv pip install -e ".[dev]"
ruff check .
pytest -v
```

Tests mock `httpx` — no live API hits required.

## Disclaimer

This project is community-built, open-source, and **not affiliated with,
endorsed by, or sponsored by xAI Corp.** "Grok" is a trademark of xAI Corp.

## License

MIT — see [LICENSE](LICENSE).
