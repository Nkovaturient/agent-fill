#!/usr/bin/env python3
"""Step 2 — Prior. Temporal Prior Protocol (TPP).

Classify the query's information type (preferring an explicit argument
from the calling agent), look up its publication-lag prior in
references/lag_matrix.json, and decide whether the requested period can
exist yet (`cannot_exist`, `may_exist`, `should_exist`).
"""
import argparse
import calendar
import json
import os
import re
from datetime import date
from dateutil.relativedelta import relativedelta

_MATRIX_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "references",
    "lag_matrix.json",
)


def load_lag_matrix() -> dict[str, dict]:
    with open(_MATRIX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


LAG_MATRIX = load_lag_matrix()
VALID_INFO_TYPES = tuple(LAG_MATRIX.keys())

# Ordered most-specific first; all patterns use word boundaries.
_KEYWORD_RULES: list[tuple[str, list[re.Pattern[str]]]] = [
    (
        "national_census_survey",
        [
            re.compile(r"\b(?:national\s+census|population\s+census|decennial\s+census|population\s+survey|economic\s+census|census)\b", re.I),
        ],
    ),
    (
        "blockchain_onchain",
        [
            re.compile(r"\b(?:on-chain|onchain|tvl|total\s+value\s+locked|gas\s+fee|smart\s+contract|block\s+number|block\s+height|defi)\b", re.I),
        ],
    ),
    (
        "financial_market_data",
        [
            re.compile(r"\b(?:stock\s+price|share\s+price|fx\s+rate|exchange\s+rate|market\s+cap|ticker|repo\s+rate|interest\s+rate|spot\s+price|bitcoin|btc|eth|crypto\s+price|price\s+of)\b", re.I),
        ],
    ),
    (
        "software_version",
        [
            re.compile(r"\b(?:version|release|changelog|sdk|library|package|pypi|npm|crate|api\s+version)\b", re.I),
        ],
    ),
    (
        "corporate_filings",
        [
            re.compile(r"\b(?:sec\s+filing|10-k|10-q|8-k|annual\s+report|quarterly\s+earnings|earnings\s+report)\b", re.I),
        ],
    ),
    (
        "healthcare_policy",
        [
            re.compile(r"\b(?:clinical\s+guideline|drug\s+approval|treatment\s+guideline|fda\s+approval|who\s+guidance)\b", re.I),
        ],
    ),
    (
        "academic_papers",
        [
            re.compile(r"\b(?:peer-reviewed|preprint|arxiv|journal\s+paper|systematic\s+review|meta-analysis)\b", re.I),
        ],
    ),
    (
        "reference_textbook",
        [
            re.compile(r"\b(?:textbook|reference\s+manual|encyclopedia)\b", re.I),
        ],
    ),
    (
        "government_statistics",
        [
            re.compile(r"\b(?:official\s+statistics|government\s+data|government\s+statistics|ministry|agricultural\s+statistics|agricultural\s+data|gdp\s+growth|unemployment\s+rate|cpi\s+inflation)\b", re.I),
        ],
    ),
    (
        "social_media_news",
        [
            re.compile(r"\b(?:breaking\s+news|headline|tweet|social\s+media\s+post|news)\b", re.I),
        ],
    ),
]


def classify_information_type(query: str, explicit_info_type: str | None = None) -> str:
    if explicit_info_type:
        norm = explicit_info_type.strip().lower()
        if norm in LAG_MATRIX:
            return norm
        return "unknown"
    for info_type, patterns in _KEYWORD_RULES:
        if any(p.search(query) for p in patterns):
            return info_type
    return "unknown"


def resolve_period(period_str: str | None, query: str) -> tuple[date | None, str | None]:
    """Resolve an explicit period ('YYYY', 'YYYY-MM', 'YYYY-MM-DD') or a
    4-digit year in the query to its period-end date. Returns (None, None)
    when the query asks for the latest available without naming a period.
    """
    raw = period_str.strip() if period_str else None
    if not raw:
        m = re.search(r"\b(19\d{2}|20\d{2}|21\d{2})\b", query)
        if m:
            raw = m.group(1)
    if not raw:
        return None, None

    if re.fullmatch(r"\d{4}", raw):
        year = int(raw)
        return date(year, 12, 31), raw
    if re.fullmatch(r"\d{4}-\d{2}", raw):
        year, month = map(int, raw.split("-"))
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, last_day), raw
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return date.fromisoformat(raw), raw
    raise ValueError(f"Unsupported period format '{raw}'. Use YYYY, YYYY-MM, or YYYY-MM-DD.")


def temporal_prior(
    query: str,
    current_date: date,
    info_type: str | None = None,
    period: str | None = None,
) -> dict:
    resolved_type = classify_information_type(query, info_type)
    if resolved_type == "unknown":
        return {
            "info_type": "unknown",
            "valid_info_types": list(VALID_INFO_TYPES),
            "current_date": current_date.isoformat(),
            "requested_period": period,
            "existence": "unknown",
            "can_exist": False,
            "reason": (
                "Could not classify information type from query alone. "
                "Pass --info-type / info_type explicitly from valid_info_types."
            ),
            "action": "NEEDS_INFO_TYPE",
        }

    spec = LAG_MATRIX[resolved_type]
    min_months = int(spec["min_months"])
    typical_months = int(spec["typical_months"])
    max_months = int(spec["max_months"])

    expected_latest = current_date - relativedelta(months=typical_months)
    earliest_plausible = current_date - relativedelta(months=min_months)
    period_end, period_label = resolve_period(period, query)

    if period_end is None:
        # "Latest available" query with no fixed period: proceed and hint expected vintage.
        return {
            "info_type": resolved_type,
            "lag_months": typical_months,
            "min_lag_months": min_months,
            "max_lag_months": max_months,
            "current_date": current_date.isoformat(),
            "requested_period": "latest",
            "expected_latest_data_date": expected_latest.isoformat(),
            "earliest_plausible_data_date": earliest_plausible.isoformat(),
            "existence": "should_exist",
            "can_exist": True,
            "best_available_hint": (
                f"Latest complete data for {resolved_type} is typically as of "
                f"~{expected_latest.isoformat()} (typical lag: {typical_months} months)."
            ),
            "action": "PROCEED — fetch and verify with recency check",
        }

    min_available_on = period_end + relativedelta(months=min_months)
    typical_available_on = period_end + relativedelta(months=typical_months)

    if period_end > current_date or (min_months > 0 and current_date < min_available_on):
        existence = "cannot_exist"
        can_exist = False
        action = "DO_NOT_FETCH — return honest gap response"
        reason = (
            f"Data for period {period_label} (ending {period_end.isoformat()}) cannot exist "
            f"as of {current_date.isoformat()} for {resolved_type} "
            f"(minimum lag: {min_months} months, typical lag: {typical_months} months; "
            f"earliest plausible release around {min_available_on.isoformat()}, "
            f"typical release around {typical_available_on.isoformat()})."
        )
    elif current_date < typical_available_on:
        existence = "may_exist"
        can_exist = True
        action = "PROCEED — preliminary or early release possible; verify data-as-of date"
        reason = (
            f"Period {period_label} (ending {period_end.isoformat()}) is past the minimum lag "
            f"({min_months} months) but within the typical lag ({typical_months} months); "
            f"data may be preliminary or partially released."
        )
    else:
        existence = "should_exist"
        can_exist = True
        action = "PROCEED — fetch and verify with recency check"
        reason = (
            f"Period {period_label} (ending {period_end.isoformat()}) is past the typical "
            f"{typical_months}-month publication lag as of {current_date.isoformat()}."
        )

    return {
        "info_type": resolved_type,
        "lag_months": typical_months,
        "min_lag_months": min_months,
        "max_lag_months": max_months,
        "current_date": current_date.isoformat(),
        "requested_period": period_end.isoformat(),
        "requested_period_label": period_label,
        "expected_latest_data_date": expected_latest.isoformat(),
        "earliest_plausible_data_date": earliest_plausible.isoformat(),
        "expected_release_date": typical_available_on.isoformat(),
        "existence": existence,
        "can_exist": can_exist,
        "reason": reason,
        "best_available_hint": (
            f"Most recent complete data is typically around {expected_latest.isoformat()} "
            f"(earliest plausible: {earliest_plausible.isoformat()})."
        ),
        "action": action,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--query", required=True)
    p.add_argument(
        "--date",
        dest="current_date",
        required=True,
        help="YYYY-MM-DD, use anchor_date.py's output",
    )
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
        help="Requested data period: YYYY, YYYY-MM, or YYYY-MM-DD (omit for 'latest')",
    )
    args = p.parse_args()
    cd = date.fromisoformat(args.current_date)
    print(json.dumps(temporal_prior(args.query, cd, args.info_type, args.period), indent=2))


if __name__ == "__main__":
    main()
