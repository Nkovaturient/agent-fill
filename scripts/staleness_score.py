#!/usr/bin/env python3
"""Step 4 — Score staleness.

Compares a source's date against the info_type's lag thresholds in
references/lag_matrix.json and returns a verdict: fresh, aging, stale,
or unverifiable.
"""
import argparse
import json
from datetime import datetime, timezone

from lag_prior import LAG_MATRIX, VALID_INFO_TYPES

VALID_DATE_BASES = ("data_as_of", "published", "modified")


def _parse_dt(value: str) -> tuple[datetime, bool]:
    """Return (UTC datetime, has_time_component)."""
    raw = value.strip()
    has_time = "T" in raw or " " in raw or ":" in raw
    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt, has_time


def staleness_score(
    data_date: str | None,
    current_datetime: str,
    info_type: str,
    date_basis: str = "data_as_of",
) -> dict:
    norm_type = info_type.strip().lower()
    if norm_type not in LAG_MATRIX:
        raise ValueError(
            f"Unknown info_type '{info_type}'. Valid types: {', '.join(VALID_INFO_TYPES)}"
        )
    if date_basis not in VALID_DATE_BASES:
        raise ValueError(
            f"Invalid date_basis '{date_basis}'. Valid values: {', '.join(VALID_DATE_BASES)}"
        )

    spec = LAG_MATRIX[norm_type]
    typical_months = int(spec["typical_months"])
    max_months = int(spec["max_months"])
    fresh_window_seconds = spec.get("fresh_window_seconds")

    if not data_date:
        return {
            "verdict": "unverifiable",
            "info_type": norm_type,
            "date_basis": date_basis,
            "data_date": None,
            "current_datetime": current_datetime,
            "age_months": None,
            "age_seconds": None,
            "expected_lag_months": typical_months,
            "is_upper_bound": False,
            "note": "No extractable data-as-of or publication date; do not treat as current.",
        }

    d_dt, d_has_time = _parse_dt(data_date)
    c_dt, c_has_time = _parse_dt(current_datetime)
    delta_seconds = (c_dt - d_dt).total_seconds()

    # Future date check (allow up to 60s clock skew only when timestamps are used)
    if (d_has_time and c_has_time and delta_seconds < -60) or (
        not (d_has_time and c_has_time) and d_dt.date() > c_dt.date()
    ):
        return {
            "verdict": "unverifiable",
            "info_type": norm_type,
            "date_basis": date_basis,
            "data_date": data_date,
            "current_datetime": current_datetime,
            "age_months": round(delta_seconds / (86400.0 * 30.4375), 2),
            "age_seconds": round(delta_seconds, 1),
            "expected_lag_months": typical_months,
            "is_upper_bound": date_basis != "data_as_of",
            "note": (
                f"Source date ({data_date}) is in the future relative to "
                f"current_datetime ({current_datetime}); treating as unverifiable."
            ),
        }

    age_days = max(0.0, delta_seconds / 86400.0)
    age_months = age_days / 30.4375

    if typical_months == 0 and fresh_window_seconds is not None:
        window = float(fresh_window_seconds)
        if not d_has_time and window < 86400:
            # Date-only stamp cannot prove sub-day freshness (e.g. 60s market/on-chain window)
            if d_dt.date() == c_dt.date():
                verdict = "aging"
            else:
                verdict = "stale"
        else:
            if delta_seconds <= window:
                verdict = "fresh"
            elif delta_seconds <= window * 5:
                verdict = "aging"
            else:
                verdict = "stale"
    else:
        fresh_limit = float(max(typical_months, 1))
        aging_limit = float(max(max_months, typical_months * 2, 2))
        if age_months <= fresh_limit:
            verdict = "fresh"
        elif age_months <= aging_limit:
            verdict = "aging"
        else:
            verdict = "stale"

    is_upper_bound = date_basis != "data_as_of"
    result = {
        "verdict": verdict,
        "info_type": norm_type,
        "date_basis": date_basis,
        "is_upper_bound": is_upper_bound,
        "data_date": data_date,
        "current_datetime": current_datetime,
        "age_months": round(age_months, 2),
        "age_seconds": round(max(0.0, delta_seconds), 1),
        "expected_lag_months": typical_months,
        "fresh_window_seconds": fresh_window_seconds,
    }
    if is_upper_bound:
        result["note"] = (
            f"Scored using {date_basis} date because no explicit data_as_of date was "
            "present; freshness verdict is an upper bound (underlying data may be older)."
        )
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data-date", dest="data_date", default=None)
    p.add_argument(
        "--current-date",
        "--current-datetime",
        dest="current_datetime",
        required=True,
        help="ISO date or datetime from anchor_date.py",
    )
    p.add_argument(
        "--info-type",
        dest="info_type",
        required=True,
        help=f"Information type ({', '.join(VALID_INFO_TYPES)})",
    )
    p.add_argument(
        "--date-basis",
        dest="date_basis",
        default="data_as_of",
        choices=VALID_DATE_BASES,
        help="Which extracted date is being scored (data_as_of, published, modified)",
    )
    args = p.parse_args()
    print(
        json.dumps(
            staleness_score(
                args.data_date,
                args.current_datetime,
                args.info_type,
                args.date_basis,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
