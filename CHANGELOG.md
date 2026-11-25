# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-11-25

### Added

- Five-step temporal grounding protocol in [`SKILL.md`](SKILL.md): anchor date, temporal prior gate, fetch and verify, staleness scoring, and provenance (inline + footer contracts).
- `references/lag_matrix.json` with domain publication lags and per–`info_type` `canonical_registries` (authoritative portal URLs for Contract B and real-time lookup).
- Python pipeline scripts under `scripts/` (`anchor_date.py`, `lag_prior.py`, `fetch_and_verify.py`, `staleness_score.py`, `provenance.py`, `pipeline.py`).
- Hatchling package `agent-fill` (`pyproject.toml` v0.1.0) with console entry points `agent-fill` and `agent-fill-mcp`.
- Stdio MCP server (`mcp_server/server.py`) exposing 7 tools: `run_pipeline`, `anchor_date`, `check_temporal_prior`, `fetch_source`, `score_staleness`, `make_provenance`, `reconcile_sources`; optional extra `pip install '.[mcp]'` pins `mcp==1.9.4` and `pydantic>=2.8,<2.10`.
- Eval regression suite: 10 deterministic cases (`evals/seed_cases.json`) and 5 LLM behavioral pressure scenarios (`evals/agent_scenarios.json`), run via `python evals/run_evals.py`.
- GitHub Actions workflow [`.github/workflows/evals.yml`](.github/workflows/evals.yml) on push/PR to `main` / `master`.
- GitHub Pages docs site at [`docs/index.html`](docs/index.html) ([https://nkovaturient.github.io/agent-fill/](https://nkovaturient.github.io/agent-fill/)).

### Notes

- Portable skill layout: symlink `SKILL.md` into Cursor (`.cursor/skills/agent-fill`) or Claude Code (`~/.claude/skills/agent-fill`) and register the MCP server via stdio; see [`docs/REGISTRY.md`](docs/REGISTRY.md).

[0.1.0]: https://github.com/Nkovaturient/agent-fill/releases/tag/v0.1.0