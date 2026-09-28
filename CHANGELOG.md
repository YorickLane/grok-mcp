# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.4.0] — 2026-09-28

### Added
- Search trace on `search_x` / `search_web`: a line after the cost footer
  lists the server-side searches that ran and, for X Search, how many posts
  and profiles were fetched (`_searches: x_keyword_search, x_user_search ·
  4 posts, 0 profiles fetched_`). When X Search fetched nothing it adds
  `⚠ X Search fetched 0 posts — this answer is not based on any X post`.
  Live case that motivated it: 13 searches on a handle with no posts, and
  the model still answered "xAI has not announced anything about Grok 4.7".
  Counts come from the documented `usage.server_side_tool_usage_details`;
  sub-tool names come from `custom_tool_call` output items, which xAI does
  not document (observed live), so names may change while counts stay.
- `resolution="1.5k"` on `generate_image` (in the OpenAPI enum, not the docs
  prose; served live at $0.05/image).

### Changed
- `chat` / `search_x` / `search_web` / `run_code` no longer declare an MCP
  `outputSchema`. With one, FastMCP also sent `{"result": "<text>"}` as
  `structuredContent`, and Claude Code showed the model that JSON string
  (escaped newlines) instead of the markdown text. `generate_image` keeps
  structured output.
- Dependency floor `mcp>=1.28,<2`, as the SDK's v2 release notes advise for
  staying on the maintained 1.x line.
- CI checks `ruff format`.

## [0.3.1] — 2026-09-28

Catch-up with xAI API changes since 0.3.0. Payload shapes live-verified
against `https://api.x.ai` on 2026-09-28.

### Fixed
- `reasoning_effort` accepts `low` / `medium` / `high` / `xhigh`, the set for
  grok-4.5 and later. `none` was dropped: grok-4.7 answers it with HTTP 400
  ("This model does not support `reasoning_effort` value `none`"), and
  `xhigh` was rejected locally although the API accepts it. Docstrings no
  longer claim the server default is `low` — it is `high` on grok-4.5+.
- `generate_image` accepts the `21:9` and `5:2` aspect ratios (xAI added
  them in August).
- Dependency pin `mcp>=1.0.0,<2`: mcp 2.x removed `mcp.server.fastmcp`, so a
  fresh install failed at import (198797f).
- CI: ruff pinned `>=0.16,<0.17` after a new default rule (SIM117) turned CI
  red; actions bumped to the node24 majors (58095e7).

### Added
- `reasoning_effort` on `search_x` / `search_web`. Omitted by default
  (model default `high`). On one test query, two `low` runs took ~5 s
  and ~170 reasoning tokens each; two runs at the default took 8 s and 27 s
  (430 / 1,760 reasoning tokens).
- `quality` on `generate_image` (`low` / `medium` / `auto`,
  grok-imagine-image-2.0 only).
- Test that every library-layer parameter is also declared on the MCP layer.

### Changed
- Default text model `grok-4.7`, default image model
  `grok-imagine-image-2.0` (`grok-imagine-image-quality` retires
  2026-11-02) (a24b8b6).

### Removed
- The top-level `inline_citations` payload key. It is not in the
  `/v1/responses` schema; inline citations are on by default.

### Docs
- README: X Search per-post billing, when to use the Grok Build CLI instead,
  and the v0.3+ roadmap items moved to "Dropped".

## [0.3.0] — 2026-05-29

### Added — Tier A passthrough parameters (5 features)

All payload shapes below are Responses-API-specific (`/v1/responses`) and were
live-probe-verified against `https://api.x.ai/v1/responses` on 2026-05-29
(HTTP 200). The docs' prose sometimes describes the Chat-Completions shape,
which is wrong for this endpoint.

- `reasoning_effort` on `chat` — `none` / `low` / `medium` / `high`. Wires
  to nested `payload["reasoning"] = {"effort": ...}` (not a top-level
  `reasoning_effort` key). Omitted when None (server default `low`). Invalid
  values raise `ValueError`.
- `cost_in_usd_ticks` surfaced — every Responses + Images response carries
  `usage.cost_in_usd_ticks` (1e10 ticks = $1). Now exposed as `cost_ticks` /
  `cost_usd` in the parsed envelope, appended as a `_grok cost: $… · model_`
  footer to all text tools (`chat` / `search_x` / `search_web` / `run_code`),
  and added as `cost_ticks` / `cost_usd` keys on each `generate_image` dict.
  The footer is suppressed in `chat` json mode so the JSON return stays valid.
- `response_format` (JSON Schema) on `chat` — wires to
  `payload["text"] = {"format": {"type": "json_schema", "name", "schema",
  "strict": True}}`. Returns the raw JSON string (no cost footer).
- `max_turns` on `chat` / `search_x` / `search_web` — top-level
  `payload["max_turns"]`. Caps tool-using TURNS, not individual tool calls.
- `conv_id` (prompt caching) on `chat` / `search_x` / `search_web` — sets
  both `payload["prompt_cache_key"]` and the `x-grok-conv-id` request header.

### Changed
- Tests: 21 → 41 (all passing, mocked HTTP). New `tests/test_v030.py` adds
  payload-shape, cost-footer, json-mode, and validation coverage.

## [0.2.0] — 2026-05-28

### Added
- `run_code` — Grok code interpreter via Responses API. Use for math /
  stats / financial modeling / simulations where LLM arithmetic
  hallucinates.
- `generate_image` — Grok Imagine via OpenAI-compat `/v1/images/generations`
  endpoint. Full param surface: `n`, `aspect_ratio` (13 options), `resolution`
  (1k / 2k), `response_format` (url / b64_json). Default model
  `grok-imagine-image-quality` (the `-pro` variant was deprecated 2026-05-15).
- Tool count: 3 → 5. Tests: 14 → 21 (all passing, mocked).

## [0.1.0] — 2026-05-28

### Added
- Initial release. 3 tools: `chat` / `search_x` / `search_web`.
- Full xAI Live Search parameter surface for both search tools:
  `allowed/excluded_x_handles` (max 20, matches xAI cap), `from_date`,
  `to_date`, `enable_image_understanding`, `enable_video_understanding`
  (x_search), `enable_image_search` (web_search).
- Modular package layout: `grok/api.py` + `grok/tools/<tool>.py` (one tool
  per file).
- `pytest` suite — `tests/test_api.py` + `tests/test_tools.py`, mocked
  HTTP only. No live API hit required to run.
- GitHub Actions CI: ruff + pytest on push/PR.

### Differs from community alternatives
- Image and video understanding params actually exposed (most community
  Grok MCP servers omit these, leaving xAI capability dark).
- Handle cap 20, not 10 (matches xAI's actual API limit).
- Per-tool docstring describes when *not* to use the tool.
