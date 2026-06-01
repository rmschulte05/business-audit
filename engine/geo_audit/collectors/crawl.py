"""Deterministic page-discovery for the multi-page crawl.

Given the homepage, its robots.txt, and a fetched sitemap, produce a stable,
deduped, priority-ordered list of same-registrable-domain page URLs to audit.

The whole module is pure given its inputs (the only I/O is the optional sitemap
fetch the caller passes in). There is NO randomness: pages are ordered by a fixed
priority rank, then by URL, so re-running on the same site yields the SAME list.

Sources, in priority order:
  1. the homepage itself (always first),
  2. URLs from sitemap.xml (following a sitemap index ONE level deep),
  3. internal <a href> links discovered on the homepage.

High-value paths (about, pricing, services, products, blog, docs, contact, ...)
are ranked ahead of generic inner pages so that, under a small max_pages cap, we
sample the pages most likely to carry Product/Article/FAQ schema and rich content.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin, urlsplit

from ..http_client import HttpResult, fetch, normalize_url

# High-value path keywords -> lower rank number = higher priority. The homepage
# is always rank -1 (kept strictly first). Everything unmatched falls to GENERIC.
PRIORITY_KEYWORDS: tuple[tuple[int, tuple[str, ...]], ...] = (
    (0, ("about", "about-us", "team", "company")),
    (1, ("pricing", "plans", "price")),
    (2, ("services", "solutions", "service")),
    (3, ("products", "product", "shop", "store")),
    (4, ("features",)),
    (5, ("docs", "documentation", "guide", "guides", "help", "support")),
    (6, ("blog", "articles", "article", "news", "resources", "insights")),
    (7, ("faq", "faqs", "questions")),
    (8, ("contact", "contact-us")),
    (9, ("case-studies", "case-study", "customers", "portfolio", "work")),
)
GENERIC_RANK = 50

# File extensions that are never HTML pages worth auditing.
SKIP_EXTENSIONS = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
    ".css", ".js", ".json", ".xml", ".zip", ".gz", ".mp4", ".mp3", ".mov",
    ".woff", ".woff2", ".ttf", ".eot", ".rss", ".atom", ".txt", ".csv",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
)


def registrable_domain(host: str) -> str:
    """Approximate the registrable domain (eTLD+1) without external deps.

    Stdlib has no public-suffix list, so we use a pragmatic heuristic: take the
    last two labels, but for common two-level public suffixes (co.uk, com.au,
    ...) take the last three. Good enough to keep a crawl on one site and reject
    third-party links. Deterministic.
    """
    host = (host or "").lower().strip().rstrip(".")
    if not host:
        return ""
    # Strip port if present.
    host = host.split(":", 1)[0]
    labels = host.split(".")
    if len(labels) <= 2:
        return host
    two_level = {
        "co", "com", "org", "net", "gov", "edu", "ac", "or", "ne", "go",
    }
    cctlds_with_second = {"uk", "au", "nz", "za", "jp", "br", "in", "il", "tr"}
    if labels[-1] in cctlds_with_second and labels[-2] in two_level:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def _same_site(url: str, home_domain: str) -> bool:
    try:
        host = urlsplit(url).netloc
    except Exception:
        return False
    return bool(host) and registrable_domain(host) == home_domain


def _is_http(url: str) -> bool:
    return url.startswith("http://") or url.startswith("https://")


def _has_skip_ext(path: str) -> bool:
    p = path.lower()
    return any(p.endswith(ext) for ext in SKIP_EXTENSIONS)


def _canonicalize(url: str) -> str:
    """Normalize a URL for dedupe: drop fragment, strip trailing slash on path."""
    url, _frag = urldefrag(url)
    parts = urlsplit(url)
    path = parts.path or "/"
    # Treat "/x/" and "/x" as the same page (but keep root "/").
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    rebuilt = f"{parts.scheme}://{parts.netloc}{path}"
    if parts.query:
        rebuilt += f"?{parts.query}"
    return rebuilt


def _priority_rank(url: str) -> int:
    """Lower = higher priority. Matches the first high-value keyword in the path."""
    path = urlsplit(url).path.lower()
    segments = [s for s in path.split("/") if s]
    for rank, keywords in PRIORITY_KEYWORDS:
        for kw in keywords:
            if any(seg == kw or seg.startswith(kw) for seg in segments):
                return rank
    return GENERIC_RANK


class _LinkExtractor(HTMLParser):
    """Collect raw href values from <a> tags (stdlib only)."""

    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        for k, v in attrs:
            if k.lower() == "href" and v:
                self.hrefs.append(v.strip())


def extract_links(html: str, base_url: str) -> list[str]:
    """Return absolute http(s) hrefs found in <a> tags, in document order."""
    parser = _LinkExtractor()
    try:
        parser.feed(html or "")
    except Exception:
        parser.hrefs = re.findall(
            r'<a\b[^>]*\bhref=["\']([^"\']+)["\']', html or "", re.IGNORECASE
        )
    out: list[str] = []
    for href in parser.hrefs:
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
            continue
        absolute = urljoin(base_url, href)
        if _is_http(absolute):
            out.append(absolute)
    return out


def _parse_sitemap(xml: str) -> tuple[list[str], list[str]]:
    """Return (page_urls, nested_sitemap_urls) from a sitemap or sitemap index."""
    if not xml:
        return [], []
    locs = re.findall(r"<loc>\s*(.*?)\s*</loc>", xml, re.IGNORECASE | re.DOTALL)
    locs = [re.sub(r"\s+", "", l) for l in locs if l.strip()]
    is_index = "<sitemapindex" in xml.lower()
    if is_index:
        return [], locs
    return locs, []


def _robots_disallows(robots: HttpResult | None, ua_tokens: tuple[str, ...]) -> list[str]:
    """Extract Disallow paths that apply to our user-agent (or '*')."""
    if robots is None or not robots.body:
        return []
    disallows: list[str] = []
    cur_agents: list[str] = []
    applies = False

    def agent_applies(agents: list[str]) -> bool:
        for a in agents:
            al = a.strip().lower()
            if al == "*":
                return True
            if al and any(tok in al for tok in ua_tokens):
                return True
        return False

    started_rules = False
    for raw in robots.body.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, _, value = line.partition(":")
        field = field.strip().lower()
        value = value.strip()
        if field == "user-agent":
            if started_rules:
                cur_agents = []
                started_rules = False
            cur_agents.append(value)
            applies = agent_applies(cur_agents)
        elif field == "disallow":
            started_rules = True
            if applies and value:
                disallows.append(value)
        elif field == "allow":
            started_rules = True
    return disallows


def _is_disallowed(url: str, disallows: list[str]) -> bool:
    path = urlsplit(url).path or "/"
    for rule in disallows:
        if rule == "/":
            return True
        if path.startswith(rule):
            return True
    return False


def discover_pages(
    url: str,
    home: HttpResult,
    robots: HttpResult | None = None,
    sitemap: HttpResult | None = None,
    max_pages: int = 8,
    ua_tokens: tuple[str, ...] = ("businessaudit", "*"),
    fetch_sitemap_child=fetch,
) -> list[str]:
    """Return a deterministic, deduped, ordered list of page URLs to audit.

    The homepage (home.final_url, falling back to the requested url) is ALWAYS
    first. Remaining slots are filled by sitemap entries then homepage links,
    ranked by high-value path priority then URL, capped at max_pages.

    `sitemap` is an optional pre-fetched /sitemap.xml HttpResult. If it is a
    sitemap index, ONE level of child sitemaps is followed via fetch_sitemap_child
    (injectable for tests).
    """
    url = normalize_url(url)
    home_url = _canonicalize(home.final_url or url)
    home_domain = registrable_domain(urlsplit(home_url).netloc)

    if max_pages <= 1 or not home_domain:
        return [home_url]

    disallows = _robots_disallows(robots, ua_tokens)

    # --- Gather candidate URLs from sitemap (source priority 1). ---
    sitemap_urls: list[str] = []
    if sitemap is not None and sitemap.ok and sitemap.body:
        pages, nested = _parse_sitemap(sitemap.body)
        sitemap_urls.extend(pages)
        # Follow a sitemap index ONE level deep, deterministically (sorted).
        for child in sorted(set(nested))[:5]:
            if not _same_site(child, home_domain):
                continue
            child_res = fetch_sitemap_child(child, want_body=True)
            if child_res.ok and child_res.body:
                child_pages, _ = _parse_sitemap(child_res.body)
                sitemap_urls.extend(child_pages)

    # --- Gather candidate URLs from homepage links (source priority 2). ---
    link_urls = extract_links(home.body or "", home_url)

    # --- Merge candidates, recording the source order for tie-breaking. ---
    # source_rank: sitemap=0, links=1 (homepage always handled separately).
    candidates: dict[str, int] = {}
    for u in sitemap_urls:
        cu = _canonicalize(u)
        candidates.setdefault(cu, 0)
    for u in link_urls:
        cu = _canonicalize(u)
        candidates.setdefault(cu, 1)

    # --- Filter: same-site, http(s), not the homepage, not disallowed, no asset. ---
    filtered: list[str] = []
    for cu in candidates:
        if cu == home_url:
            continue
        if not _is_http(cu) or not _same_site(cu, home_domain):
            continue
        if _has_skip_ext(urlsplit(cu).path):
            continue
        if _is_disallowed(cu, disallows):
            continue
        filtered.append(cu)

    # --- Deterministic ordering: (priority rank, source rank, URL). ---
    filtered.sort(key=lambda u: (_priority_rank(u), candidates[u], u))

    ordered = [home_url] + filtered
    return ordered[:max_pages]
