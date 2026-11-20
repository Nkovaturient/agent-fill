#!/usr/bin/env python3
"""agent-fill MCP server — exposes the five-step temporal grounding
pipeline (plus the single gated end-to-end runner) as MCP tools over stdio.

Run: python mcp_server/server.py
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from anchor_date import anchor
from fetch_and_verify import fetch_and_verify
from lag_prior import temporal_prior
from pipeline import run_pipeline as _run_pipeline
from provenance import build_provenance, reconcile
from staleness_score import staleness_score

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("agent-fill")


@mcp.tool()
def anchor_date(now_override: str | None = None, tz_name: str | None = None) -> dict:
    """Step 1: Get the trusted current date/time. Never trust the model's
    own belief about 'today'; call this first. Pass tz_name (e.g.
    'Asia/Kolkata') to also get local_date."""
    return anchor(now_override=now_override, tz_name=tz_name)


@mcp.tool()
def check_temporal_prior(
    query: str,
    current_date: str,
    info_type: str | None = None,
    period: str | None = None,
) -> dict:
    """Step 2: Classify the query's info type (prefer passing info_type
    and period explicitly), look up its publication lag, and decide if
    the requested data can exist yet (cannot_exist / may_exist /
    should_exist). If can_exist is false, stop and return the honest gap
    response."""
    cd = date.fromisoformat(current_date)
    return temporal_prior(query=query, current_date=cd, info_type=info_type, period=period)


@mcp.tool()
def fetch_source(url: str) -> dict:
    """Step 3: Fetch a public http/https URL and extract published_date,
    modified_date, data_as_of_date, and accessed_date separately."""
    return fetch_and_verify(url)


@mcp.tool()
def score_staleness(
    current_datetime: str,
    info_type: str,
    data_date: str | None = None,
    date_basis: str = "data_as_of",
) -> dict:
    """Step 4: Score a source's staleness (fresh/aging/stale/unverifiable)
    given its date, today's date/datetime, the domain's info_type, and
    which date is being scored (data_as_of, published, modified)."""
    return staleness_score(
        data_date=data_date,
        current_datetime=current_datetime,
        info_type=info_type,
        date_basis=date_basis,
    )


@mcp.tool()
def make_provenance(
    source: str,
    url: str,
    verdict: str,
    data_date: str | None = None,
    claim: str | None = None,
    date_basis: str = "data_as_of",
    block_number: int | None = None,
) -> dict:
    """Step 5: Build a provenance record for one source/claim. Attach one
    of these to every time-sensitive claim in the final answer."""
    return build_provenance(
        source=source,
        url=url,
        data_date=data_date,
        verdict=verdict,
        claim=claim,
        date_basis=date_basis,
        block_number=block_number,
    )


@mcp.tool()
def reconcile_sources(records: list[dict]) -> dict:
    """Step 5b: Given multiple provenance records, flag true claim or
    data_as_of conflicts and recommend the freshest record."""
    return reconcile(records)


@mcp.tool()
def run_pipeline(
    query: str,
    info_type: str | None = None,
    period: str | None = None,
    urls: list[str] | None = None,
    now_override: str | None = None,
    tz_name: str | None = None,
    block_number: int | None = None,
) -> dict:
    """Run all 5 temporal grounding steps end-to-end with the Step 2 gate
    enforced. Skips fetching automatically when existence == 'cannot_exist'
    or info_type == 'unknown'."""
    return _run_pipeline(
        query=query,
        info_type=info_type,
        period=period,
        urls=urls,
        now_override=now_override,
        tz_name=tz_name,
        block_number=block_number,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
