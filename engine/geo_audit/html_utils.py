"""Small stdlib HTML helpers shared by collectors.

WebFetch (used by the LLM skills) converts HTML to markdown and strips <head>,
which destroys JSON-LD, meta tags, and link rels. These helpers parse the RAW
HTML so schema/technical scoring works on real evidence.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser


class _LdJsonExtractor(HTMLParser):
    """Collect the text inside every <script type="application/ld+json">."""

    def __init__(self) -> None:
        super().__init__()
        self.blocks: list[str] = []
        self._in_ld = False
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script":
            attr = {k.lower(): (v or "").lower() for k, v in attrs}
            if attr.get("type", "") == "application/ld+json":
                self._in_ld = True
                self._buf = []

    def handle_data(self, data):
        if self._in_ld:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self._in_ld:
            self._in_ld = False
            text = "".join(self._buf).strip()
            if text:
                self.blocks.append(text)


def extract_ld_json_blocks(html: str) -> list[str]:
    """Return the raw text of each JSON-LD script block in the HTML."""
    parser = _LdJsonExtractor()
    try:
        parser.feed(html or "")
    except Exception:
        # Fall back to a regex if the parser chokes on malformed markup.
        return re.findall(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html or "",
            flags=re.DOTALL | re.IGNORECASE,
        )
    return parser.blocks


class _TagStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in ("script", "style", "noscript", "svg"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag.lower() in ("script", "style", "noscript", "svg") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip and data.strip():
            self.parts.append(data)


def visible_text(html: str) -> str:
    """Approximate the human-visible text of a page (no scripts/styles)."""
    stripper = _TagStripper()
    try:
        stripper.feed(html or "")
    except Exception:
        return re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", " ".join(stripper.parts)).strip()


def find_meta(html: str, name: str) -> str:
    """Return the content of <meta name="..."> (case-insensitive). '' if absent."""
    pat = re.compile(
        r'<meta\b[^>]*\bname=["\']%s["\'][^>]*\bcontent=["\']([^"\']*)["\']'
        % re.escape(name),
        re.IGNORECASE,
    )
    m = pat.search(html or "")
    if m:
        return m.group(1).strip()
    # attribute order can be reversed
    pat2 = re.compile(
        r'<meta\b[^>]*\bcontent=["\']([^"\']*)["\'][^>]*\bname=["\']%s["\']'
        % re.escape(name),
        re.IGNORECASE,
    )
    m2 = pat2.search(html or "")
    return m2.group(1).strip() if m2 else ""


def find_link_rel(html: str, rel: str) -> str:
    """Return href of <link rel="..."> (case-insensitive). '' if absent."""
    pat = re.compile(
        r'<link\b[^>]*\brel=["\']%s["\'][^>]*\bhref=["\']([^"\']*)["\']'
        % re.escape(rel),
        re.IGNORECASE,
    )
    m = pat.search(html or "")
    if m:
        return m.group(1).strip()
    pat2 = re.compile(
        r'<link\b[^>]*\bhref=["\']([^"\']*)["\'][^>]*\brel=["\']%s["\']'
        % re.escape(rel),
        re.IGNORECASE,
    )
    m2 = pat2.search(html or "")
    return m2.group(1).strip() if m2 else ""


def headings(html: str) -> dict[str, list[str]]:
    """Return {'h1': [...], 'h2': [...], ...} of heading text content."""
    out: dict[str, list[str]] = {f"h{i}": [] for i in range(1, 7)}
    for level in range(1, 7):
        for m in re.finditer(
            rf"<h{level}\b[^>]*>(.*?)</h{level}>", html or "", re.DOTALL | re.IGNORECASE
        ):
            txt = re.sub(r"<[^>]+>", " ", m.group(1))
            txt = re.sub(r"\s+", " ", txt).strip()
            if txt:
                out[f"h{level}"].append(txt)
    return out


def title(html: str) -> str:
    m = re.search(r"<title\b[^>]*>(.*?)</title>", html or "", re.DOTALL | re.IGNORECASE)
    if not m:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip()
