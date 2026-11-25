# agent-fill

[![Evals](https://github.com/Nkovaturient/agent-fill/actions/workflows/evals.yml/badge.svg)](https://github.com/Nkovaturient/agent-fill/actions/workflows/evals.yml)

Portable temporal grounding skill and MCP server for LLM agents (Claude,
Cursor, custom runtimes). Anchors the real UTC/local date, gates queries
against domain publication lags (`cannot_exist` / `may_exist` /
`should_exist`), fetches and verifies sources with four distinct dates
(`published_date`, `modified_date`, `data_as_of_date`, `accessed_date`),
scores staleness, and enforces inline + footer provenance on every
time-sensitive claim.

See [`SKILL.md`](SKILL.md) for the complete 5-step protocol, 3-tier execution
modes (MCP -> CLI -> Native sandbox fallback), output contracts, worked
anecdotes, and rationalization counter-tables.

**Docs:** When [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site) is enabled for this repo, the live site is at [https://nkovaturient.github.io/agent-fill/](https://nkovaturient.github.io/agent-fill/) (served from [`docs/`](docs/index.html) on branch `main`). Enable it once: **Settings → Pages → Build and deployment → Source:** Deploy from a branch → **Branch:** `main` → **Folder:** `/docs` → Save.

## Install

**PyPI-style (recommended for one-command use):**

```bash
pip install .                    # core CLI + pipeline scripts bundled in the wheel
pip install '.[mcp]'             # adds MCP server deps (mcp==1.9.4, pydantic<2.10; see pyproject.toml)

# Editable checkout
pip install -e .
pip install -e '.[mcp]'
```

Console entry points: `agent-fill` (same as `python scripts/pipeline.py`) and
`agent-fill-mcp` (stdio MCP server). Module form: `python -m agent_fill`.

**Run without a local clone** (after the package is published or from Git):

```bash
uvx --from git+https://github.com/Nkovaturient/agent-fill agent-fill -- --help
pipx run --spec git+https://github.com/Nkovaturient/agent-fill agent-fill -- --help
```

**Contributor / requirements.txt workflow** (unchanged):

```bash
pip install -r requirements.txt

# MCP server only (same pins as pip install '.[mcp]')
pip install -r mcp_server/requirements.txt
```

### Add as a Skill in Cursor or Claude

```bash
# Cursor (project-scoped)
mkdir -p .cursor/skills && ln -s /path/to/agent-fill .cursor/skills/agent-fill

# Claude Code / Personal Cursor skill
mkdir -p ~/.cursor/skills && ln -s /path/to/agent-fill ~/.cursor/skills/agent-fill
```

## Run end-to-end pipeline

```bash
python scripts/pipeline.py \
  --query "What is the latest version of requests?" \
  --info-type software_version \
  --url "https://pypi.org/pypi/requests/json"
```

## Run individual steps standalone

```bash
python scripts/anchor_date.py --tz Asia/Kolkata
python scripts/lag_prior.py --query "Odisha agricultural statistics 2026" --date 2026-11-20 --info-type government_statistics --period 2026
python scripts/fetch_and_verify.py --url "https://pypi.org/pypi/requests/json"
python scripts/staleness_score.py --data-date 2025-01-01 --current-date 2026-11-20 --info-type government_statistics
python scripts/provenance.py --source "PyPI" --url "https://pypi.org/project/requests/" --data-date 2026-05-14 --verdict stale --date-basis published
```

## Run eval & pressure-scenario suite

```bash
python evals/run_evals.py
```

Validates 10 deterministic pipeline cases (`evals/seed_cases.json`) and 5
LLM behavioral pressure scenarios (`evals/agent_scenarios.json`).

## Run as MCP server

```bash
python mcp_server/server.py
```

Exposes 7 MCP tools: `run_pipeline`, `anchor_date`, `check_temporal_prior`,
`fetch_source`, `score_staleness`, `make_provenance`, `reconcile_sources`.

## License

MIT
