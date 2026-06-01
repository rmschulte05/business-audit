"""Stdlib-only HTTP client for the audit engine.

No third-party dependencies (no requests) so the plugin runs anywhere Python 3
runs. Captures everything the collectors need from a single fetch: final URL
after redirects, status, headers, decoded body, and TTFB.
"""

from __future__ import annotations

import gzip
import io
import socket
import ssl
import time
import urllib.error
import urllib.request
import zlib
from dataclasses import dataclass

DEFAULT_UA = (
    "Mozilla/5.0 (compatible; BusinessAuditBot/2.0; "
    "+https://github.com/rmschulte05/business-audit)"
)
DEFAULT_TIMEOUT = 20.0
MAX_BYTES = 5_000_000  # 5 MB cap so a giant page can't hang the audit


@dataclass(frozen=True)
class HttpResult:
    """Outcome of a single HTTP fetch."""

    url: str                 # the URL requested
    final_url: str           # URL after following redirects
    ok: bool
    status: int | None
    headers: dict            # lower-cased header names -> value
    body: str                # decoded text body ("" on failure)
    ttfb_ms: float | None    # time to first byte / full response, milliseconds
    error: str = ""

    def header(self, name: str, default: str = "") -> str:
        return self.headers.get(name.lower(), default)


def _decode_body(raw: bytes, headers: dict) -> str:
    encoding = headers.get("content-encoding", "").lower()
    try:
        if "gzip" in encoding:
            raw = gzip.decompress(raw)
        elif "deflate" in encoding:
            try:
                raw = zlib.decompress(raw)
            except zlib.error:
                raw = zlib.decompress(raw, -zlib.MAX_WBITS)
        elif "br" in encoding:
            try:
                import brotli  # type: ignore

                raw = brotli.decompress(raw)
            except Exception:
                pass  # brotli rarely available; fall back to raw bytes
    except Exception:
        pass

    charset = "utf-8"
    ctype = headers.get("content-type", "")
    if "charset=" in ctype:
        charset = ctype.split("charset=", 1)[1].split(";")[0].strip() or "utf-8"
    try:
        return raw.decode(charset, errors="replace")
    except (LookupError, UnicodeDecodeError):
        return raw.decode("utf-8", errors="replace")


def fetch(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    user_agent: str = DEFAULT_UA,
    method: str = "GET",
    want_body: bool = True,
) -> HttpResult:
    """Fetch a URL, following redirects. Never raises — failures return ok=False."""
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-US,en;q=0.9",
    }
    req = urllib.request.Request(url, headers=headers, method=method)
    ctx = ssl.create_default_context()

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            raw = b""
            if want_body:
                raw = resp.read(MAX_BYTES)
            ttfb = (time.perf_counter() - start) * 1000.0
            body = _decode_body(raw, resp_headers) if want_body else ""
            return HttpResult(
                url=url,
                final_url=resp.geturl(),
                ok=True,
                status=resp.status,
                headers=resp_headers,
                body=body,
                ttfb_ms=round(ttfb, 1),
            )
    except urllib.error.HTTPError as e:
        # HTTP errors (4xx/5xx) still carry useful headers/status.
        resp_headers = {k.lower(): v for k, v in (e.headers or {}).items()}
        ttfb = (time.perf_counter() - start) * 1000.0
        body = ""
        if want_body:
            try:
                body = _decode_body(e.read(MAX_BYTES), resp_headers)
            except Exception:
                body = ""
        return HttpResult(
            url=url,
            final_url=getattr(e, "url", url) or url,
            ok=False,
            status=e.code,
            headers=resp_headers,
            body=body,
            ttfb_ms=round(ttfb, 1),
            error=f"HTTP {e.code} {e.reason}",
        )
    except (urllib.error.URLError, socket.timeout, ssl.SSLError, ValueError, OSError) as e:
        return HttpResult(
            url=url,
            final_url=url,
            ok=False,
            status=None,
            headers={},
            body="",
            ttfb_ms=None,
            error=str(getattr(e, "reason", e)),
        )


def normalize_url(raw: str) -> str:
    """Add https:// if no scheme is present; strip surrounding whitespace."""
    raw = (raw or "").strip()
    if not raw:
        return raw
    if not raw.startswith(("http://", "https://")):
        return "https://" + raw
    return raw


def origin(url: str) -> str:
    """Return scheme://host[:port] for building robots.txt / llms.txt URLs."""
    from urllib.parse import urlsplit

    parts = urlsplit(normalize_url(url))
    return f"{parts.scheme}://{parts.netloc}"
