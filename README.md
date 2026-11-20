# agent-fill

Temporal grounding for LLM agents. Anchors the real date, checks whether
requested data can exist yet (`cannot_exist` / `may_exist` / `should_exist`),
fetches and verifies sources with distinct `published_date`, `modified_date`,
`data_as_of_date`, and `accessed_date`, scores staleness against
domain-specific lag priors, and emits provenance on every claim.

See `SKILL.md` for the five-step protocol.

## Install

```bash
# Standalone CLI scripts
pip install -r requirements.txt

# Including the MCP server (pins mcp==1.9.4 / pydantic<2.10)
pip install -r mcp_server/requirements.txt
```

## Run end-to-end pipeline

```bash
python scripts/pipeline.py \
  --query "What is the latest version of requests?" \
  --info-type software_version \
  --url "https://pypi.org/project/requests/"
```

## Run individual steps standalone

```bash
python scripts/anchor_date.py --tz Asia/Kolkata
python scripts/lag_prior.py --query "Odisha agricultural statistics 2026" --date 2026-11-20 --info-type government_statistics --period 2026
python scripts/fetch_and_verify.py --url "https://pypi.org/project/requests/"
python scripts/staleness_score.py --data-date 2025-01-01 --current-date 2026-11-20 --info-type government_statistics
python scripts/provenance.py --source "PyPI" --url "https://pypi.org/project/requests/" --data-date 2026-06-01 --verdict aging --date-basis published
```

## Run eval suite

```bash
python evals/run_evals.py
```

## Run as MCP server

```bash
python mcp_server/server.py
```

Exposes 7 MCP tools: `run_pipeline`, `anchor_date`, `check_temporal_prior`,
`fetch_source`, `score_staleness`, `make_provenance`, `reconcile_sources`.

## License

MIT
