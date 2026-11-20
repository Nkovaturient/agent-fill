#!/usr/bin/env python3
"""Step 1 — Anchor. Return the trusted current date/time.

Never trust a model's belief about "today" — always read the system
clock (or an injected override) and use that everywhere downstream.
"""
import argparse
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def anchor(now_override: str | None = None, tz_name: str | None = None) -> dict:
    if now_override:
        dt = datetime.fromisoformat(now_override.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
    else:
        dt = datetime.now(timezone.utc)

    result = {
        "current_date": dt.date().isoformat(),
        "current_datetime_utc": dt.isoformat(),
        "source": "override" if now_override else "system_clock",
    }
    if tz_name:
        local_dt = dt.astimezone(ZoneInfo(tz_name))
        result["timezone"] = tz_name
        result["local_date"] = local_dt.date().isoformat()
        result["local_datetime"] = local_dt.isoformat()
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--now",
        dest="now_override",
        default=None,
        help="ISO datetime override, e.g. 2026-11-20T00:00:00Z",
    )
    p.add_argument(
        "--tz",
        dest="tz_name",
        default=None,
        help="Optional IANA timezone name (e.g. Asia/Kolkata) to include local_date",
    )
    args = p.parse_args()
    print(json.dumps(anchor(args.now_override, args.tz_name), indent=2))


if __name__ == "__main__":
    main()
