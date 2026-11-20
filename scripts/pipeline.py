#!/usr/bin/env python3
"""End-to-end gated temporal grounding pipeline (Steps 1–5).

Runs anchor -> temporal_prior -> (if allowed) fetch_and_verify ->
staleness_score -> build_provenance -> reconcile. Enforces the Step 2
gate so URLs are never fetched when existence == 'cannot_exist' or
info_type == 'unknown'.
"""
import argparse
import json
import os
import sys
from datetime import date
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from anchor_date import anchor
from fetch_and_verify import fetch_and_verify
from lag_prior import VALID_INFO_TYPES, temporal_prior
from provenance import build_provenance, reconcile
from staleness_score import staleness_score


def _pick_source_date(fetched: dict) -> tuple[str | None, str]:
    if fetched.get("data_as_of_date"):
        return fetched["data_as_of_date"], "data_as_of"
    if fetched.get("published_date"):
        return fetched["published_date"], "published"
    if fetched.get("modified_date"):
        return fetched["modified_date"], "modified"
    return None, "data_as_of"


def run_pipeline(
    query: str,
    info_type: str | None = None,
    period: str | None = None,
    urls: list[str] | None = None,
    now_override: str | None = None,
    tz_name: str | None = None,
    block_number: int | None = None,
) -> dict:
    anchored = anchor(now_override=now_override, tz_name=tz_name)
    effective_date_str = anchored.get("local_date") or anchored["current_date"]
    cd = date.fromisoformat(effective_date_str)

    prior = temporal_prior(query=query, current_date=cd, info_type=info_type, period=period)
    resolved_type = prior["info_type"]

    if prior.get("action") == "NEEDS_INFO_TYPE" or not prior.get("can_exist", False):
        return {
            "anchor": anchored,
            "prior": prior,
            "gated": True,
            "sources": [],
            "reconciliation": None,
        }

    url_list = urls or []
    sources_out: list[dict] = []
    prov_records: list[dict] = []
    warnings: list[str] = []

    if resolved_type == "blockchain_onchain" and block_number is None:
        warnings.append(
            "blockchain_onchain query has no block_number stamp; pass --block-number / block_number to anchor on-chain state."
        )

    for u in url_list:
        fetched = fetch_and_verify(u)
        if not fetched.get("fetched"):
            sources_out.append({"fetch": fetched, "staleness": None, "provenance": None})
            continue

        chosen_date, date_basis = _pick_source_date(fetched)
        score = staleness_score(
            data_date=chosen_date,
            current_datetime=anchored["current_datetime_utc"],
            info_type=resolved_type,
            date_basis=date_basis,
        )
        source_label = fetched.get("title") or urlparse(u).hostname or u
        prov = build_provenance(
            source=source_label,
            url=fetched.get("final_url") or u,
            data_date=chosen_date,
            verdict=score["verdict"],
            date_basis=date_basis if chosen_date else "none",
            block_number=block_number,
        )
        sources_out.append({"fetch": fetched, "staleness": score, "provenance": prov})
        prov_records.append(prov)

    reconciled = reconcile(prov_records) if prov_records else None
    result = {
        "anchor": anchored,
        "prior": prior,
        "gated": False,
        "sources": sources_out,
        "reconciliation": reconciled,
    }
    if warnings:
        result["warnings"] = warnings
    return result


def main():
    p = argparse.ArgumentParser(description="Run the 5-step agent-fill pipeline.")
    p.add_argument("--query", required=True)
    p.add_argument(
        "--info-type",
        dest="info_type",
        default=None,
        help=f"Explicit information type ({', '.join(VALID_INFO_TYPES)})",
    )
    p.add_argument(
        "--period",
        dest="period",
        default=None,
        help="Requested period: YYYY, YYYY-MM, or YYYY-MM-DD (omit for 'latest')",
    )
    p.add_argument(
        "--url",
        dest="urls",
        action="append",
        default=[],
        help="Source URL to fetch and verify (may be passed multiple times)",
    )
    p.add_argument("--now", dest="now_override", default=None)
    p.add_argument("--tz", dest="tz_name", default=None)
    p.add_argument("--block-number", dest="block_number", type=int, default=None)
    args = p.parse_args()
    out = run_pipeline(
        query=args.query,
        info_type=args.info_type,
        period=args.period,
        urls=args.urls,
        now_override=args.now_override,
        tz_name=args.tz_name,
        block_number=args.block_number,
    )
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
