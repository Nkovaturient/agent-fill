---
name: agent-fill
description: >
  Use before answering any query about current, recent, "latest", or
  time-sensitive information (stats, prices, versions, policies, news,
  on-chain state). Anchors the real query date, checks whether the
  requested data could plausibly exist yet, fetches and verifies sources,
  and labels every claim with its data-as-of date and a staleness verdict.
  Prevents confident answers built on outdated or nonexistent data.
---

# agent-fill

Temporal grounding for LLM agents. Five steps, run in order, before any
time-sensitive claim leaves the agent.

## Why

LLMs have no internal clock. They confuse "not in my training data" with
"doesn't exist," and they confuse a page's access date with its data's
publication date. This produces confident wrong answers (confabulation),
answers to the wrong question (deflection), and citations of stale
documents as if current. See `references/failure-modes.md`.

## Valid `info_type` values

The calling agent **must** classify the query and pass `--info-type` (or
`info_type` in MCP) plus `--period` (`YYYY`, `YYYY-MM`, `YYYY-MM-DD`, or
omit for "latest available"):

- `social_media_news` (0 mo lag, 24h fresh window)
- `financial_market_data` (0 mo lag, 60s fresh window)
- `blockchain_onchain` (0 mo lag, 60s fresh window; always pass `--block-number`)
- `software_version` (0–1 mo lag)
- `corporate_filings` (1–3 mo lag)
- `healthcare_policy` (3–12 mo lag)
- `government_statistics` (6–18 mo lag)
- `academic_papers` (12–36 mo lag)
- `national_census_survey` (60–120 mo lag)
- `reference_textbook` (120–240 mo lag)

If `--info-type` is omitted and the keyword fallback cannot match, Step 2
returns `info_type: "unknown"` and `action: "NEEDS_INFO_TYPE"` instead of
guessing.

## The five steps

1. **Anchor** — get the real current UTC (and optional local `--tz`)
   date/time. Never trust the model's belief about "today." Run
   `scripts/anchor_date.py`.

2. **Prior** — look up the domain's min/typical/max lag in
   `references/lag_matrix.json` and evaluate existence:
   - `cannot_exist`: period end is in the future or within `min_months`.
     **Stop.** Do not fetch. Return the gap response template below.
   - `may_exist`: between `min_months` and `typical_months`. Proceed, but
     flag that any release may be preliminary.
   - `should_exist`: past `typical_months` (or no fixed period requested).
     Proceed and verify recency.

3. **Fetch & extract** — fetch public `http`/`https` sources (SSRF-guarded,
   2 MB cap) and pull distinct `published_date`, `modified_date`,
   `data_as_of_date`, and `accessed_date` along with `date_sources`.
   `data_as_of_date` never falls back to `published_date`. Run
   `scripts/fetch_and_verify.py`.

4. **Score staleness** — compare the source's date against the
   `info_type` thresholds in `references/lag_matrix.json` to get a
   verdict: `fresh`, `aging`, `stale`, or `unverifiable` (including future
   dates). When scored on `published` rather than `data_as_of`, the
   verdict is marked `is_upper_bound: true`. Run
   `scripts/staleness_score.py`.

5. **Emit with provenance** — attach source, `data_as_of`, `date_basis`,
   `staleness_verdict`, and (for on-chain data) `block_number` to every
   claim. Reconcile multiple sources via `reconcile`: flag true claim or
   `data_as_of` conflicts and recommend the freshest record. Run
   `scripts/provenance.py`.

## Honest gap-response template (`cannot_exist`)

When Step 2 returns `existence: "cannot_exist"`:

> Data for **[requested_period_label]** in **[info_type]** is not yet
> published as of **[current_date]** (typical publication lag:
> **[lag_months] months**; expected release around
> **[expected_release_date]**). The most recent complete period plausibly
> available is around **[expected_latest_data_date]** or earlier.

## Default entry point (end-to-end pipeline)

```bash
python scripts/pipeline.py \
  --query "What is the latest version of requests?" \
  --info-type software_version \
  --url "https://pypi.org/project/requests/"
```

## Individual step CLI (manual path)

```bash
python scripts/anchor_date.py --tz Asia/Kolkata
python scripts/lag_prior.py --query "current RBI repo rate" --date 2026-11-20 --info-type financial_market_data
python scripts/fetch_and_verify.py --url "https://pypi.org/project/requests/"
python scripts/staleness_score.py --data-date 2025-03-01 --current-date 2026-11-20 --info-type government_statistics --date-basis data_as_of
python scripts/provenance.py --source "RBI" --url "https://rbi.org.in" --data-date 2025-03-01 --verdict stale --date-basis data_as_of
```

Or load `mcp_server/server.py` as an MCP server (`run_pipeline`,
`anchor_date`, `check_temporal_prior`, `fetch_source`, `score_staleness`,
`make_provenance`, `reconcile_sources`).

## Files

- `references/lag_matrix.json` — canonical publication-lag priors by domain.
- `references/lag-matrix.md` — guidance on overriding lag priors.
- `references/failure-modes.md` — the five failure classes this skill targets.
- `scripts/` — `pipeline.py` plus the five standalone step scripts.
- `mcp_server/` — same pipeline exposed as 7 MCP tools.
- `evals/seed_cases.json` & `evals/run_evals.py` — executable regression suite.
