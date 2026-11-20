#!/usr/bin/env python3
"""Executable regression runner for evals/seed_cases.json."""
import json
import os
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from fetch_and_verify import fetch_and_verify
from lag_prior import temporal_prior
from pipeline import run_pipeline
from provenance import build_provenance, reconcile
from staleness_score import staleness_score


def _run_case(case: dict) -> tuple[bool, str]:
    kind = case["kind"]
    exp = case["expect"]

    if kind == "gate":
        cd = date.fromisoformat(case["now"][:10])
        res = temporal_prior(
            query=case["query"],
            current_date=cd,
            info_type=case.get("info_type"),
            period=case.get("period"),
        )
        if "info_type" in exp and res.get("info_type") != exp["info_type"]:
            return False, f"info_type={res.get('info_type')} != {exp['info_type']}"
        if "existence" in exp and res.get("existence") != exp["existence"]:
            return False, f"existence={res.get('existence')} != {exp['existence']}"
        if "can_exist" in exp and res.get("can_exist") != exp["can_exist"]:
            return False, f"can_exist={res.get('can_exist')} != {exp['can_exist']}"
        if "action_prefix" in exp and not str(res.get("action", "")).startswith(exp["action_prefix"]):
            return False, f"action='{res.get('action')}' does not start with '{exp['action_prefix']}'"
        return True, f"{res.get('info_type')} -> {res.get('existence')} ({res.get('action')})"

    if kind == "pipeline":
        res = run_pipeline(
            query=case["query"],
            info_type=case.get("info_type"),
            period=case.get("period"),
            urls=case.get("urls", []),
            now_override=case.get("now"),
            block_number=case.get("block_number"),
        )
        if "gated" in exp and res.get("gated") != exp["gated"]:
            return False, f"gated={res.get('gated')} != {exp['gated']}"
        if exp.get("has_block_warning"):
            warnings = res.get("warnings") or []
            if not any("block_number" in w for w in warnings):
                return False, f"expected block_number warning, got {warnings}"
        return True, f"gated={res.get('gated')}, warnings={len(res.get('warnings') or [])}"

    if kind == "staleness":
        res = staleness_score(
            data_date=case.get("data_date"),
            current_datetime=case["now"],
            info_type=case["info_type"],
            date_basis=case.get("date_basis", "data_as_of"),
        )
        if res.get("verdict") != exp["verdict"]:
            return False, f"verdict={res.get('verdict')} != {exp['verdict']}"
        return True, f"verdict={res.get('verdict')} ({res.get('note', '')[:50]})"

    if kind == "fetch":
        res = fetch_and_verify(case["url"])
        if res.get("fetched") != exp["fetched"]:
            return False, f"fetched={res.get('fetched')} != {exp['fetched']} (err={res.get('error')})"
        if "error_contains" in exp and exp["error_contains"] not in str(res.get("error", "")):
            return False, f"error='{res.get('error')}' missing '{exp['error_contains']}'"
        if exp.get("published_date_present") and not res.get("published_date"):
            return False, f"published_date missing in {res}"
        if exp.get("published_not_equal_accessed") and res.get("published_date") == res.get("accessed_date"):
            return False, f"published_date ({res.get('published_date')}) == accessed_date"
        if exp.get("data_as_of_stays_distinct") and res.get("data_as_of_date") == res.get("published_date"):
            return False, "data_as_of_date fell back to published_date"
        return True, (
            f"fetched={res.get('fetched')} pub={res.get('published_date')} "
            f"as_of={res.get('data_as_of_date')} acc={res.get('accessed_date')}"
        )

    if kind == "reconcile":
        built = [
            build_provenance(
                source=r["source"],
                url=r["url"],
                data_date=r.get("data_date"),
                verdict=r["verdict"],
                claim=r.get("claim"),
                date_basis=r.get("date_basis", "data_as_of"),
            )
            for r in case["records"]
        ]
        res = reconcile(built)
        if res.get("conflict") != exp["conflict"]:
            return False, f"conflict={res.get('conflict')} != {exp['conflict']}"
        if "recommended_source" in exp and res.get("recommended_source") != exp["recommended_source"]:
            return False, f"recommended_source={res.get('recommended_source')} != {exp['recommended_source']}"
        return True, f"conflict={res.get('conflict')}, recommended={res.get('recommended_source')}"

    return False, f"Unknown eval kind '{kind}'"


def main():
    cases_path = os.path.join(ROOT, "evals", "seed_cases.json")
    with open(cases_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    passed = 0
    failed = 0
    print(f"{'CASE ID':<36} {'STATUS':<8} DETAILS")
    print("-" * 92)
    for c in cases:
        ok, detail = _run_case(c)
        status = "PASS" if ok else "FAIL"
        print(f"{c['id']:<36} {status:<8} {detail}")
        if ok:
            passed += 1
        else:
            failed += 1

    print("-" * 92)
    print(f"Total: {passed + failed} | Passed: {passed} | Failed: {failed}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
