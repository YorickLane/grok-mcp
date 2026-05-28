# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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
