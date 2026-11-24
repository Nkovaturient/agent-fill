---
name: agent-fill
description: Use when answering any query about current, recent, "latest", or time-sensitive facts (statistics, market prices, software versions, clinical/government policies, corporate filings, news, or on-chain state), or when citing retrieved documents whose publication or data-as-of date may lag behind the present.
---

# agent-fill — Temporal Grounding Protocol

LLMs have no internal clock, conflate "not in training data" with "does not exist," and conflate a webpage's access date with its underlying data vintage. **Violating the letter of these 5 steps is violating the spirit of temporal grounding.**

---

## Execution Tiers (Pick Highest Available)

Resolve `<SKILL_DIR>` to the directory containing this `SKILL.md` (e.g., `.cursor/skills/agent-fill`, `~/.claude/skills/agent-fill`, or `./agent-fill`).

1. **Tier 1 — MCP Tools (Preferred)**: Call `run_pipeline` (or step tools `anchor_date`, `check_temporal_prior`, `fetch_source`, `score_staleness`, `make_provenance`, `reconcile_sources`) from the `agent-fill` MCP server.
2. **Tier 2 — Python CLI Scripts**: Run `python "<SKILL_DIR>/scripts/pipeline.py" ...` (or the 5 step scripts in `<SKILL_DIR>/scripts/`).
3. **Tier 3 — Native Sandbox Fallback (No MCP / No Shell)**: Execute the 5 steps manually using the host's system date header, the Quick Lag Reference table below, and native `WebFetch` / `WebSearch` tools while strictly enforcing every gate and output contract below.

---

## The Five Mandatory Steps

### Step 1: Anchor (`anchor_date`)
Read the real UTC clock (and local `--tz` when regional dates matter near midnight). Never guess "today" from training cutoff.

### Step 2: Prior Gate & Canonical Registry Lookup (`check_temporal_prior`)
You **must** classify the query into one `info_type` and extract the requested `period` (`YYYY`, `YYYY-MM`, `YYYY-MM-DD`, or omit for `"latest"`). Step 2 also returns `canonical_registries`—the authoritative primary portals/APIs for that domain:

| `info_type` | Min Lag | Typical Lag | Max Lag | Fresh Window | Authoritative Primary Registries (Real-Time Lookup Targets) |
|---|---|---|---|---|---|
| `social_media_news` | 0 mo | 0 mo | 0 mo | `86400s` (24h) | [Reuters](https://www.reuters.com), [AP News](https://apnews.com), [PIB India](https://pib.gov.in) |
| `financial_market_data` | 0 mo | 0 mo | 0 mo | `60s` | [RBI DBIE](https://data.rbi.org.in), [FRED](https://fred.stlouisfed.org), [CoinGecko API](https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_last_updated_at=true) |
| `blockchain_onchain` | 0 mo | 0 mo | 0 mo | `60s` + `block_number` | [DefiLlama API](https://api.llama.fi/protocols), [Etherscan](https://etherscan.io), [Beaconcha.in](https://beaconcha.in) |
| `software_version` | 0 mo | 1 mo | 1 mo | 1 mo | `https://pypi.org/pypi/<pkg>/json`, `https://registry.npmjs.org/<pkg>/latest`, `https://crates.io/api/v1/crates/<crate>` |
| `corporate_filings` | 1 mo | 3 mo | 3 mo | 3 mo | [SEC EDGAR Search](https://www.sec.gov/edgar/searchedgar/companysearch), [NSE Filings](https://www.nseindia.com/companies-listing/corporate-filings-announcements), [BSE Announcements](https://www.bseindia.com/corporates/ann.html) |
| `healthcare_policy` | 3 mo | 6 mo | 12 mo | 6 mo | [WHO Publications](https://www.who.int/publications), [Drugs@FDA](https://www.accessdata.fda.gov/scripts/cder/daf/), [ICMR India](https://www.icmr.gov.in) |
| `government_statistics` | 6 mo | 12 mo | 18 mo | 12 mo | [MoSPI India](https://www.mospi.gov.in), [DES Odisha](https://desorissa.nic.in), [Data.gov.in](https://www.data.gov.in), [World Bank Data](https://data.worldbank.org) |
| `academic_papers` | 12 mo | 18 mo | 36 mo | 18 mo | [Crossref REST API](https://api.crossref.org/works), [arXiv](https://arxiv.org), [PubMed NCBI](https://pubmed.ncbi.nlm.nih.gov) |
| `national_census_survey` | 60 mo | 84 mo | 120 mo | 84 mo | [Census of India](https://censusindia.gov.in), [U.S. Census Data](https://data.census.gov), [UN Data](https://data.un.org) |
| `reference_textbook` | 120 mo | 180 mo | 240 mo | 180 mo | [OpenAlex API](https://api.openalex.org/works), [NCBI Bookshelf](https://www.ncbi.nlm.nih.gov/books) |

**Gate states:**
- `cannot_exist` (period end is in the future, or `period_end + min_months > current_date`): **STOP IMMEDIATELY. Do not fetch or search.** Emit Contract B with clickable links from `canonical_registries` so the user can check the official agency directly.
- `NEEDS_INFO_TYPE` (`info_type` is `"unknown"`): **STOP.** Re-classify using the table above before fetching.
- `may_exist` (between `min_months` and `typical_months`): Proceed to Step 3, but label any found release as preliminary/early.
- `should_exist` (past `typical_months`, or `"latest"` requested): Proceed to Step 3.

### Step 3: Real-Time Discovery, Fetch & Four-Date Separation (`fetch_source`)
1. **Resolve exact URLs in real time**: If the user did not supply a URL, construct the direct registry endpoint for the entity (e.g., `https://pypi.org/pypi/<package>/json`, `https://api.llama.fi/protocol/<slug>`) or run a targeted `WebSearch` restricted to official/primary domains (`site:.gov.in`, `site:.gov`, `site:sec.gov`, `site:who.int`) to obtain the exact document URL. **Never invent or guess URL paths, and never use truncated `...` links.**
2. **Fetch & separate four dates**: Pass the discovered URL(s) to `fetch_source` / `fetch_and_verify.py` and keep four timestamps strictly separate:
   - `data_as_of_date`: The reference period the numbers actually measure (e.g., `"as of March 2025"`, `"FY 2024"`).
   - `published_date`: When the article, package, or report was released (`article:published_time`, JSON-LD `datePublished`, `<time datetime>`, or JSON registry `upload_time_iso_8601`).
   - `modified_date`: Last edit (`article:modified_time`, JSON-LD `dateModified`, HTTP `Last-Modified`).
   - `accessed_date`: Today's fetch timestamp.

**Hard Rule:** Never copy `published_date` or `accessed_date` into `data_as_of_date`. If a page has no explicit reference period, `data_as_of_date` is `null`.

### Step 4: Score Staleness (`score_staleness`)
Compare the source date against `info_type` thresholds:
- Verdicts: `fresh`, `aging`, `stale`, or `unverifiable`.
- **Future dates** (`data_date > current_datetime`): Always `unverifiable` (clock skew, typo, or projection).
- **Published fallback**: When `data_as_of_date` is `null` and you score on `published_date`, set `date_basis="published"` and `is_upper_bound=true` (confidence drops one tier because the underlying data is at least as old as the publication).

### Step 5: Emit with Live Clickable Provenance & Reconcile (`make_provenance`, `reconcile_sources`)
Attach a provenance record with the **exact fetched `final_url`** to every time-sensitive claim. When multiple sources exist:
- **True conflict**: Sources report different claims or different `data_as_of` dates for the same metric. Surface both with their exact URLs and recommend the freshest `data_as_of` source.
- **Verdict-only difference**: A primary registry (`fresh`) and a stale mirror (`stale`) reporting the exact same claim (`v2.34.2`) is **not** a conflict—cite the freshest source.

---

## Required Output Contracts

### Contract A — Answered Claims (`should_exist` / `may_exist`)
Every time-sensitive claim in prose **must** carry an inline stamp, followed by a `Provenance` block containing the **exact, non-truncated, clickable markdown link** that was fetched in Step 3:

```markdown
Python `requests` is at version **2.34.2** [published 2026-05-14, accessed 2026-11-24 — stale (upper bound)].

**Provenance**
- **Claim**: Latest `requests` release on PyPI = 2.34.2
  - Source: [requests · PyPI JSON Registry](https://pypi.org/pypi/requests/json) (human page: [pypi.org/project/requests](https://pypi.org/project/requests/))
  - Dates: `data_as_of=null` | `published=2026-05-14` | `accessed=2026-11-24` (`date_basis=published`, `is_upper_bound=true`)
  - Verdict: `stale` (confidence: `low` — no release within the 1-month `software_version` window, verified live)
```

*(For `blockchain_onchain`, include `block_number=<height>` in both the inline stamp and the Provenance bullet.)*

### Contract B — Honest Gap Response (`cannot_exist`)
When Step 2 gates the query, output **only** this structure (no speculative numbers) and include **clickable links to the official `canonical_registries`** returned by Step 2:

```markdown
Data for **2026** in **government_statistics** is not yet published as of **2026-11-24** (minimum lag: **6 months**, typical lag: **12 months**; expected release around **2027-12-31**).

- **Latest complete period plausibly available**: around **2025-11-24** (2024–25 agricultural cycle) or earlier.
- **Where to verify**: [Directorate of Economics & Statistics, Odisha](https://desorissa.nic.in) · [MoSPI India](https://www.mospi.gov.in) · [Data.gov.in](https://www.data.gov.in)
```

---

## Worked Anecdotes (Before vs. After)

### 1. The Non-Existent Yearbook (Temporal Confabulation)
- **Query** (on `2026-11-20`): *"What are the current agricultural statistics for Odisha in 2026?"*
- **Without `agent-fill`**: *"Odisha's 2026 foodgrain production reached 14.2 million tonnes, led by a 4% rise in Kharif rice yield..."* (Fabricated; 2026 agricultural year isn't compiled until late 2027).
- **With `agent-fill`**: `lag_prior.py --info-type government_statistics --period 2026` returns `existence: "cannot_exist"` (`min_months=6`, `typical_months=12` after `2026-12-31`) plus `canonical_registries`. Agent stops without fetching and returns Contract B with direct links to [DES Odisha](https://desorissa.nic.in) and [MoSPI](https://www.mospi.gov.in).

### 2. The Package Release Page (Published vs. Data-as-of vs. Accessed)
- **Query** (on `2026-11-20`): *"What is the latest version of Python `requests`?"*
- **Without `agent-fill`**: Answers *"2.31.0"* from training weights, or scrapes PyPI and cites *"as of November 20, 2026"* (conflating `accessed_date` with release date).
- **With `agent-fill`**: `pipeline.py --info-type software_version --url https://pypi.org/pypi/requests/json` extracts `published_date: 2026-05-14` (`json:pypi.urls.upload_time_iso_8601`), `data_as_of_date: null`, `accessed_date: 2026-11-20`, scores `stale` (`age_months: 6.27 > 1`, `date_basis: published`, `is_upper_bound: true`), and cites [https://pypi.org/pypi/requests/json](https://pypi.org/pypi/requests/json).

### 3. The DeFi TVL Snapshot (Block-Time Mismatch)
- **Query**: *"What is the current TVL of Aave v3?"*
- **Without `agent-fill`**: *"Aave v3 TVL is currently $18.4B."* (Unverifiable 12 seconds later, no source URL).
- **With `agent-fill`**: Agent queries [https://api.llama.fi/protocol/aave-v3](https://api.llama.fi/protocol/aave-v3) and stamps `[block #21254890, 2026-11-24T17:05:12Z — fresh]` with a link to [DefiLlama Aave v3](https://defillama.com/protocol/aave-v3) and [Etherscan Block #21254890](https://etherscan.io/block/21254890).

### 4. Disagreement Across Sources (RAG Recency Illusion)
- **Query**: *"What is Apple's FY2025 annual revenue?"*
- **Without `agent-fill`**: Blends a 2024 analyst forecast blog with the actual SEC filing.
- **With `agent-fill`**: `reconcile_sources` flags `claim_conflict: true` between the older blog (`stale`, `date_basis=published`) and Apple's Form 10-K on [SEC EDGAR (`CIK 0000320193`)](https://www.sec.gov/edgar/browse/?CIK=0000320193) (`fresh`, `data_as_of=2025-09-27`), surfaces both URLs, and recommends the SEC 10-K.

---

## Rationalization Counter-Table & Red Flags

| Agent Excuse | Reality |
|---|---|
| *"I already know the latest version/rate from training."* | Training weights have no clock. Always run Step 1–3 and fetch the live URL. |
| *"I'll cite the root homepage (`https://example.gov`) or `https://.../..."` without fetching."* | Forbidden. Every cited link in Contract A must be the exact `final_url` fetched in Step 3. |
| *"The webpage footer says `© 2026` or `Updated today`."* | Copyright years and template footers are not `data_as_of_date`. |
| *"No `data_as_of` is listed, so I'll use `published_date` as `data_as_of`."* | Forbidden. Leave `data_as_of=null`, set `date_basis="published"`, and mark `is_upper_bound=true`. |
| *"Step 2 said `cannot_exist`, but I'll do a quick search just in case."* | Hard gate violation. Emit Contract B with the official `canonical_registries` links instead. |

**Red Flags — STOP if you catch yourself about to:**
- Emit a claim without a clickable `[Source Title](https://...)` link verified in Step 3 (or `canonical_registries` in Contract B).
- Write `"currently"`, `"as of today"`, or `"recently"` without an `[as of YYYY-MM-DD — verdict]` stamp.
- Quote on-chain state without a block height or timestamp link.

---

## CLI Quick Reference

```bash
# End-to-end gated pipeline (recommended CLI entry point)
python "<SKILL_DIR>/scripts/pipeline.py" \
  --query "What is the latest version of requests?" \
  --info-type software_version \
  --url "https://pypi.org/pypi/requests/json"

# Step-by-step manual CLI
python "<SKILL_DIR>/scripts/anchor_date.py" --tz Asia/Kolkata
python "<SKILL_DIR>/scripts/lag_prior.py" --query "..." --date 2026-11-20 --info-type government_statistics --period 2026
python "<SKILL_DIR>/scripts/fetch_and_verify.py" --url "https://pypi.org/pypi/requests/json"
python "<SKILL_DIR>/scripts/staleness_score.py" --data-date 2025-03-01 --current-date 2026-11-20 --info-type government_statistics --date-basis data_as_of
python "<SKILL_DIR>/scripts/provenance.py" --source "RBI DBIE" --url "https://data.rbi.org.in" --data-date 2025-03-01 --verdict stale --date-basis data_as_of

# Regression & behavioral test suite
python "<SKILL_DIR>/evals/run_evals.py"
```

## Supporting Files
- `references/lag_matrix.json` — canonical lag priors and `canonical_registries` by domain.
- `references/lag-matrix.md` — guidance on overriding domain lag priors.
- `references/failure-modes.md` — the 5 failure modes (`confabulation`, `deflection`, `RAG recency illusion`, `agentic drift`, `block-time mismatch`).
- `evals/seed_cases.json` & `evals/agent_scenarios.json` — deterministic pipeline tests and LLM behavioral pressure scenarios.
