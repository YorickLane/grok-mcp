# grok-mcp

> **Lean MCP server for xAI Grok.** Full Live Search parameter surface
> (including video understanding most community servers omit), modular
> architecture, explicit roadmap, MIT licensed.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-stdio-green.svg)](https://modelcontextprotocol.io/)
[![Status](https://img.shields.io/badge/status-v0.4.0%20early-orange.svg)](#roadmap)

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

## What it ships (v0.4)

5 tools wired with the full xAI parameter surface as of 2026-09-28:

| Tool | Purpose | Key params |
|---|---|---|
| `chat` | Plain chat with Grok — reasoning, codegen, translation | `model`, `system_prompt`, **`reasoning_effort`**, **`response_format`** (JSON Schema), **`max_turns`**, **`conv_id`** (caching) |
| `search_x` | X (Twitter) Live Search | `allowed/excluded_x_handles` (cap 20), date range, **`enable_image_understanding`**, **`enable_video_understanding`**, `reasoning_effort`, `max_turns`, `conv_id` |
| `search_web` | Web Live Search | `allowed/excluded_domains` (cap 5), **`enable_image_understanding`**, **`enable_image_search`** (markdown embed), `reasoning_effort`, `max_turns`, `conv_id` |
| `run_code` | Grok code interpreter — math / stats / simulations | `model` |
| `generate_image` | Grok Imagine text-to-image | `model`, `n`, `aspect_ratio` (15), `resolution` (1k/1.5k/2k), `quality` (low/medium/auto), `response_format` (url/b64) |

The bolded params are the ones most community servers omit.

### Cost and search transparency

Every call surfaces its actual cost. xAI returns `usage.cost_in_usd_ticks`
(1e10 ticks = $1) on every response. Text tools append a footer
(`_grok cost: $0.001234 · grok-4.7_`); `generate_image` adds `cost_ticks` /
`cost_usd` to each returned dict. The footer is suppressed in `chat` json mode
(`response_format` set) so the returned JSON stays valid.

`search_x` / `search_web` add a trace line showing which searches ran and
what X Search fetched, and warn when an answer rests on zero posts:

```
_grok cost: $0.033496 · grok-4.7_
_searches: x_keyword_search ×6, x_semantic_search ×3, x_user_search · 0 posts, 0 profiles fetched_
_⚠ X Search fetched 0 posts — this answer is not based on any X post_
```

**X Search is billed per item fetched** (since 2026-09-21: $5 / 1k posts,
$10 / 1k user profiles, on top of tokens), so the cost of one `search_x` call
tracks how much it pulls. One test on 2026-09-28: unrestricted, a query
fetched 53 posts + 6 profiles and cost $0.40; the same topic restricted to
one handle fetched 4–9 posts and cost $0.03–0.07. Narrow with
`allowed_x_handles` / date windows; `reasoning_effort="low"` trims the token
part (grok-4.5+ default to `high`).

## Do you need this?

If you have a SuperGrok subscription, the [Grok Build CLI](https://docs.x.ai/build/overview)
already searches X and the web on your plan instead of per-call API billing:
`grok -p "..." --tools x_search,web_search`. Its model picks the search
arguments itself, so account and date limits are requests in the prompt, not
guarantees. Use this server when you need:

- hard filters — `allowed/excluded_x_handles`, `from_date` / `to_date`, domains
- video understanding on X posts
- per-call cost accounting, or plain pay-as-you-go with no subscription

## Differs from `wynandw87/claude-code-grok-mcp`

| | this | wynandw87 (v3.9.2, 2026-07-21) |
|---|---|---|
| Live Search media | image + video understanding wired | not exposed |
| Handle cap | 20 (xAI's enforced cap, live-verified) | 10 (hardcoded) |
| `enable_image_search` markdown embed | yes | not exposed |
| `reasoning_effort` | `chat`, `search_x`, `search_web` | not exposed |
| Architecture | modular `grok/tools/` (one tool per file) | monolithic ~2,700-line server.py |
| Tests | pytest, mocked HTTP | pytest (`test_server.py`), mocked HTTP |
| Scope | X / web search first; chat, code, image as extras | 18 tools incl. sessions, files, image / video gen + edit, TTS / STT |

Both MIT. This is a clean reimplementation, not a fork. Other Grok MCP
servers worth knowing (as of 2026-09): [LKbaba/Grok-mcp](https://github.com/LKbaba/Grok-mcp)
(most-starred; agentic search + multi-agent brainstorm) and
[merterbak/Grok-MCP](https://github.com/merterbak/Grok-MCP) (widest surface:
Files API, stateful chat, live model pricing).

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

### Default model

All text tools default to `grok-4.7` — a **non-dated xAI alias** that
xAI keeps pointed at the latest stable version of the model (per
[docs.x.ai/developers/models](https://docs.x.ai/developers/models):
`<modelname>` is aliased to the latest stable version;
`<modelname>-latest` to the newest version; dated IDs pin a release).
The alias follows new `grok-4.7` snapshots only; a newer generation
(`grok-4.8` …) needs a change to `FALLBACK_DEFAULT_MODEL`.

To override, set `GROK_DEFAULT_MODEL` in the environment the server is
launched with (read once at server start):

```bash
GROK_DEFAULT_MODEL=grok-4.20-0309-reasoning  # pin a dated release, or any other model ID
```

Restart Claude Code; the five tools are now available as
`mcp__grok__chat`, `mcp__grok__search_x`, `mcp__grok__search_web`,
`mcp__grok__run_code`, `mcp__grok__generate_image`.

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

### v0.1 — initial ship
- [x] `chat`
- [x] `search_x` — full param surface
- [x] `search_web` — full param surface

### v0.2
- [x] `run_code` — Grok code interpreter
- [x] `generate_image` — `grok-imagine` family with full param surface

### v0.3 — Tier A passthrough params
- [x] `reasoning_effort` on `chat` (none / low / medium / high)
- [x] cost surfacing — `cost_in_usd_ticks` on every call (footer + dict keys)
- [x] `response_format` JSON Schema on `chat` (strict structured output)
- [x] `max_turns` on `chat` / `search_x` / `search_web`
- [x] `conv_id` prompt caching on `chat` / `search_x` / `search_web`

### v0.4 (current) — search trace
- [x] `search_x` / `search_web` report which searches ran and what X Search fetched, with a warning when it fetched nothing
- [x] text tools return plain markdown (no `structuredContent` JSON wrapper)
- [x] `generate_image` `resolution="1.5k"`

### v0.3.1 — catch up with xAI API changes
- [x] `reasoning_effort` values follow grok-4.5+: `low` / `medium` / `high` / `xhigh` (`none` now returns HTTP 400)
- [x] `reasoning_effort` on `search_x` / `search_web`
- [x] `generate_image`: `21:9` / `5:2` aspect ratios, `quality`

### Dropped (2026-09-28)
These were planned for v0.3+ and are no longer planned: in the author's
usage every call goes to `search_x` / `search_web`, and xAI now covers each
one natively.
- Multi-turn chat — the Responses API chains turns with `previous_response_id` + `store: true` (kept 30 days)
- `upload_file` + chat-with-files — `input_file` accepts a public `file_url` directly, or a Files API `file_id`
- `edit_image` / multi-image edit — `POST /v1/images/edits`, up to 5 source images

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
