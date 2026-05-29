# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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
