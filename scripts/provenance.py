#!/usr/bin/env python3
"""Step 5 — Emit with provenance.

Builds a single citation record. Call once per source per claim, then
attach the list to the final answer. If multiple sources disagree on the
claim or data_as_of date, flag the conflict rather than merging/averaging.
"""
import argparse
import json

VALID_VERDICTS = ("fresh", "aging", "stale", "unverifiable")
VALID_DATE_BASES = ("data_as_of", "published", "modified", "none")

_VERDICT_RANK = {"fresh": 3, "aging": 2, "stale": 1, "unverifiable": 0}
_CONFIDENCE_DOWNGRADE = {"high": "medium", "medium": "low", "low": "low"}


def build_provenance(
    source: str,
    url: str,
    data_date: str | None,
    verdict: str,
    claim: str | None = None,
    confidence: str | None = None,
    date_basis: str = "data_as_of",
    block_number: int | None = None,
) -> dict:
    norm_verdict = verdict.strip().lower()
    if norm_verdict not in VALID_VERDICTS:
        raise ValueError(
            f"Invalid verdict '{verdict}'. Must be one of: {', '.join(VALID_VERDICTS)}"
        )
    if date_basis not in VALID_DATE_BASES:
        raise ValueError(
            f"Invalid date_basis '{date_basis}'. Must be one of: {', '.join(VALID_DATE_BASES)}"
        )

    if confidence is None:
        base_conf = {
            "fresh": "high",
            "aging": "medium",
            "stale": "low",
            "unverifiable": "low",
        }[norm_verdict]
        if date_basis in ("published", "modified"):
            confidence = _CONFIDENCE_DOWNGRADE[base_conf]
        else:
            confidence = base_conf

    record = {
        "source": source,
        "url": url,
        "data_as_of": data_date if date_basis == "data_as_of" else None,
        "effective_date": data_date,
        "date_basis": date_basis if data_date else "none",
        "staleness_verdict": norm_verdict,
        "confidence": confidence,
        "claim": claim,
    }
    if block_number is not None:
        record["block_number"] = int(block_number)
    return record


def reconcile(records: list[dict]) -> dict:
    """Flag true disagreement (differing claims or differing data_as_of
    dates for the same claim). Differing staleness verdicts alone are not
    a conflict — recommend the freshest record.
    """
    if not records:
        return {
            "records": [],
            "conflict": False,
            "recommended_source": None,
            "recommend": "no sources provided",
        }

    claims = {r.get("claim").strip() for r in records if r.get("claim") and r.get("claim").strip()}
    data_dates = {
        r.get("data_as_of") or r.get("effective_date")
        for r in records
        if r.get("data_as_of") or r.get("effective_date")
    }
    verdicts = {r.get("staleness_verdict") for r in records}

    claim_conflict = len(claims) > 1
    date_conflict = len(claims) == 1 and len(data_dates) > 1
    conflict = claim_conflict or date_conflict

    best = max(
        records,
        key=lambda r: (
            _VERDICT_RANK.get(r.get("staleness_verdict", "unverifiable"), 0),
            1 if r.get("date_basis") == "data_as_of" else 0,
            r.get("effective_date") or r.get("data_as_of") or "",
        ),
    )

    if conflict:
        reason = (
            "conflicting claims across sources"
            if claim_conflict
            else "conflicting data_as_of dates for the same claim"
        )
        recommend = f"{reason}; surface both records to the user and prefer '{best.get('source')}' ({best.get('staleness_verdict')})"
    elif len(verdicts) > 1:
        recommend = f"sources agree on claim; prefer freshest source '{best.get('source')}' ({best.get('staleness_verdict')})"
    else:
        recommend = "sources agree"

    return {
        "records": records,
        "conflict": conflict,
        "claim_conflict": claim_conflict,
        "date_conflict": date_conflict,
        "recommended_source": best.get("source"),
        "recommend": recommend,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--url", required=True)
    p.add_argument("--data-date", dest="data_date", default=None)
    p.add_argument("--verdict", required=True, choices=VALID_VERDICTS)
    p.add_argument("--claim", default=None)
    p.add_argument(
        "--date-basis",
        dest="date_basis",
        default="data_as_of",
        choices=VALID_DATE_BASES,
    )
    p.add_argument("--block-number", dest="block_number", type=int, default=None)
    args = p.parse_args()
    print(
        json.dumps(
            build_provenance(
                args.source,
                args.url,
                args.data_date,
                args.verdict,
                args.claim,
                date_basis=args.date_basis,
                block_number=args.block_number,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
