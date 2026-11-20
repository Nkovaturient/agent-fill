#!/usr/bin/env python3
"""Shared helper — extract published / modified / data-as-of / accessed
dates from HTML, HTTP headers, or raw text. Never conflates published_date
with data_as_of_date.
"""
import json
import re
from datetime import datetime, timezone
from typing import Mapping

from bs4 import BeautifulSoup
from dateutil import parser as dateparser

_PUBLISHED_META_KEYS = (
    "article:published_time",
    "og:published_time",
    "publication_date",
    "publishdate",
    "dc.date.issued",
    "dc.date",
    "date",
    "dcterms.issued",
)

_MODIFIED_META_KEYS = (
    "article:modified_time",
    "og:updated_time",
    "last-modified",
    "dc.date.modified",
    "dcterms.modified",
    "updated_time",
)

_DATA_AS_OF_RE = re.compile(
    r"\b(?:data\s+as\s+of|figures\s+as\s+of|statistics\s+as\s+of|as\s+of|"
    r"reference\s+period|reporting\s+period|for\s+the\s+period\s+ended)\s*[:\-]?\s*"
    r"([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}|"
    r"[A-Za-z]{3,9}\s+\d{4}|Q[1-4]\s+\d{4}|FY\s*\d{4})",
    re.IGNORECASE,
)


def _try_parse_iso_date(raw: str | None) -> str | None:
    if not raw or not isinstance(raw, str):
        return None
    cleaned = raw.strip()
    if not cleaned:
        return None
    m_q = re.fullmatch(r"Q([1-4])\s+(\d{4})", cleaned, re.IGNORECASE)
    if m_q:
        q, yr = int(m_q.group(1)), int(m_q.group(2))
        end_month = q * 3
        end_day = 31 if end_month in (3, 12) else 30
        return f"{yr:04d}-{end_month:02d}-{end_day:02d}"
    m_fy = re.fullmatch(r"FY\s*(\d{4})", cleaned, re.IGNORECASE)
    if m_fy:
        yr = int(m_fy.group(1))
        return f"{yr:04d}-12-31"
    try:
        dt = dateparser.parse(cleaned, fuzzy=False)
        if dt:
            return dt.date().isoformat()
    except (ValueError, OverflowError, TypeError):
        pass
    return None


def _iter_jsonld_objects(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _iter_jsonld_objects(v)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_jsonld_objects(item)


def extract_dates(
    html_or_text: str,
    headers: Mapping[str, str] | None = None,
    now_utc: datetime | None = None,
) -> dict:
    """Return distinct {published_date, modified_date, data_as_of_date,
    accessed_date, accessed_datetime_utc, date_sources}. Never falls back
    from data_as_of_date to published_date.
    """
    published_date: str | None = None
    modified_date: str | None = None
    data_as_of_date: str | None = None
    date_sources: dict[str, str] = {}

    soup = BeautifulSoup(html_or_text or "", "html.parser")

    # 1. Meta tags (attribute-order independent)
    for meta in soup.find_all("meta"):
        content = meta.get("content")
        if not content:
            continue
        key = (
            meta.get("property")
            or meta.get("name")
            or meta.get("itemprop")
            or meta.get("http-equiv")
            or ""
        ).strip().lower()
        if not key:
            continue
        if published_date is None and key in _PUBLISHED_META_KEYS:
            parsed = _try_parse_iso_date(content)
            if parsed:
                published_date = parsed
                date_sources["published_date"] = f"meta:{key}"
        if modified_date is None and key in _MODIFIED_META_KEYS:
            parsed = _try_parse_iso_date(content)
            if parsed:
                modified_date = parsed
                date_sources["modified_date"] = f"meta:{key}"

    # 2. JSON-LD blocks (datePublished, dateCreated, dateModified, temporalCoverage)
    for script in soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)}):
        raw_json = script.string or script.get_text()
        if not raw_json:
            continue
        try:
            payload = json.loads(raw_json)
        except (ValueError, TypeError):
            continue
        for obj in _iter_jsonld_objects(payload):
            if published_date is None:
                for k in ("datePublished", "dateCreated", "dateIssued"):
                    parsed = _try_parse_iso_date(obj.get(k))
                    if parsed:
                        published_date = parsed
                        date_sources["published_date"] = f"jsonld:{k}"
                        break
            if modified_date is None:
                parsed = _try_parse_iso_date(obj.get("dateModified"))
                if parsed:
                    modified_date = parsed
                    date_sources["modified_date"] = "jsonld:dateModified"
            if data_as_of_date is None and isinstance(obj.get("temporalCoverage"), str):
                cov = obj["temporalCoverage"].split("/")[-1]
                parsed = _try_parse_iso_date(cov)
                if parsed:
                    data_as_of_date = parsed
                    date_sources["data_as_of_date"] = "jsonld:temporalCoverage"

    # 3. <time datetime="...">
    if published_date is None:
        for time_tag in soup.find_all("time"):
            dt_attr = time_tag.get("datetime") or time_tag.get_text(strip=True)
            parsed = _try_parse_iso_date(dt_attr)
            if parsed:
                published_date = parsed
                date_sources["published_date"] = "html:time"
                break

    # 4. HTTP Last-Modified header
    if headers and modified_date is None:
        for hk, hv in headers.items():
            if hk.lower() == "last-modified" and hv:
                parsed = _try_parse_iso_date(hv)
                if parsed:
                    modified_date = parsed
                    date_sources["modified_date"] = "header:last-modified"
                break

    # 5. Visible text scan for explicit data-as-of phrases only
    visible_text = " ".join(soup.get_text(separator=" ").split())
    if data_as_of_date is None:
        m = _DATA_AS_OF_RE.search(visible_text)
        if m:
            parsed = _try_parse_iso_date(m.group(1))
            if parsed:
                data_as_of_date = parsed
                date_sources["data_as_of_date"] = "text:as_of_phrase"

    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    date_sources["accessed_date"] = "system_clock"

    return {
        "published_date": published_date,
        "modified_date": modified_date,
        "data_as_of_date": data_as_of_date,
        "accessed_date": now.date().isoformat(),
        "accessed_datetime_utc": now.isoformat(),
        "date_sources": date_sources,
    }
