#!/usr/bin/env python3
"""Step 3 — Fetch & extract. Real HTTP fetch with SSRF/redirect guards,
content-type filtering, and a 2 MB streaming cap.

Pulls page text and distinct dates (published, modified, data-as-of,
accessed). Does not decide staleness — that's staleness_score.py.
"""
import argparse
import ipaddress
import json
import socket
import sys
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from extract_dates import extract_dates

HEADERS = {
    "User-Agent": "agent-fill/0.2 (Temporal Grounding Verifier; +https://modelcontextprotocol.io)",
    "Accept": "text/html,application/xhtml+xml,application/json,text/plain;q=0.9,*/*;q=0.5",
}
TIMEOUT = 15
MAX_BYTES = 2 * 1024 * 1024  # 2 MB
MAX_REDIRECTS = 5
ALLOWED_CONTENT_TYPES = (
    "text/html",
    "application/xhtml+xml",
    "text/plain",
    "application/json",
    "application/ld+json",
)


def _check_safe_url(url: str) -> tuple[bool, str | None]:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False, f"Disallowed URL scheme '{parsed.scheme}'; only http/https are permitted."
    host = parsed.hostname
    if not host:
        return False, "URL has no valid hostname."
    if host.lower() in ("localhost", "localhost.localdomain"):
        return False, f"Blocked loopback host '{host}'."

    try:
        addr_infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as e:
        return False, f"DNS resolution failed for '{host}': {e}"

    for info in addr_infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False, f"Invalid resolved IP '{ip_str}'."
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False, f"Blocked non-public IP address {ip} for host '{host}'."
    return True, None


def fetch_and_verify(url: str) -> dict:
    current_url = url
    session = requests.Session()

    for _hop in range(MAX_REDIRECTS + 1):
        safe, reason = _check_safe_url(current_url)
        if not safe:
            return {"url": url, "final_url": current_url, "error": reason, "fetched": False}

        try:
            resp = session.get(
                current_url,
                headers=HEADERS,
                timeout=TIMEOUT,
                allow_redirects=False,
                stream=True,
            )
        except requests.RequestException as e:
            return {"url": url, "final_url": current_url, "error": str(e), "fetched": False}

        if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
            location = resp.headers.get("Location")
            resp.close()
            if not location:
                return {
                    "url": url,
                    "final_url": current_url,
                    "error": f"Redirect ({resp.status_code}) missing Location header.",
                    "fetched": False,
                }
            current_url = urljoin(current_url, location)
            continue

        try:
            resp.raise_for_status()
        except requests.RequestException as e:
            resp.close()
            return {"url": url, "final_url": current_url, "error": str(e), "fetched": False}

        raw_ct = resp.headers.get("Content-Type", "")
        mime = raw_ct.split(";")[0].strip().lower()
        if mime and not any(mime.startswith(allowed) for allowed in ALLOWED_CONTENT_TYPES):
            resp.close()
            return {
                "url": url,
                "final_url": current_url,
                "error": f"Unsupported Content-Type '{mime}'.",
                "fetched": False,
            }

        chunks: list[bytes] = []
        total = 0
        truncated = False
        try:
            for chunk in resp.iter_content(chunk_size=16384):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_BYTES:
                    chunks.append(chunk[: MAX_BYTES - (total - len(chunk))])
                    truncated = True
                    break
                chunks.append(chunk)
        finally:
            resp.close()

        encoding = resp.encoding or "utf-8"
        body = b"".join(chunks).decode(encoding, errors="replace")
        dates = extract_dates(body, headers=dict(resp.headers))

        if mime == "application/json" or mime.endswith("+json"):
            title = None
            text = body[:2000]
            try:
                payload = json.loads(body)
                if isinstance(payload, dict):
                    info = payload.get("info") if isinstance(payload.get("info"), dict) else payload
                    title = info.get("name") or info.get("title")
            except ValueError:
                pass
        else:
            soup = BeautifulSoup(body, "html.parser")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            text = " ".join(soup.get_text(separator=" ").split())
            title = soup.title.string.strip() if soup.title and soup.title.string else None

        return {
            "url": url,
            "final_url": current_url,
            "fetched": True,
            "status_code": resp.status_code,
            "content_type": mime or "text/html",
            "truncated": truncated,
            "title": title,
            "text_excerpt": text[:2000],
            **dates,
        }

    return {
        "url": url,
        "final_url": current_url,
        "error": f"Exceeded maximum redirects ({MAX_REDIRECTS}).",
        "fetched": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    args = p.parse_args()
    result = fetch_and_verify(args.url)
    print(json.dumps(result, indent=2))
    if not result.get("fetched"):
        sys.exit(1)


if __name__ == "__main__":
    main()
