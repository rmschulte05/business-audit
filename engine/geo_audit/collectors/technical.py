"""Technical GEO collector — deterministic.

Measures the technical-SEO/GEO foundations that are objectively observable from
HTTP + raw HTML: HTTPS enforcement, security headers, canonical, mobile viewport,
server-side rendering, sitemap, TTFB, compression, title/description, lang.

Core Web Vitals (LCP/INP/CLS) are intentionally NOT guessed here — they require
field/lab data and are handled by the optional PageSpeed collector, which emits
NOT_MEASURED when no API key is configured.
"""

from __future__ import annotations

from ..evidence import Signal, category, measured
from ..html_utils import find_link_rel, find_meta, headings, title, visible_text
from ..http_client import HttpResult, fetch, normalize_url, origin

SECURITY_HEADERS = [
    ("strict-transport-security", "HSTS"),
    ("content-security-policy", "CSP"),
    ("x-content-type-options", "X-Content-Type-Options"),
    ("x-frame-options", "X-Frame-Options"),
    ("referrer-policy", "Referrer-Policy"),
]


def _page_body(page) -> str:
    if isinstance(page, dict):
        return page.get("body", "") or ""
    return getattr(page, "body", "") or ""


def _ssr_points(body: str) -> float:
    """SSR points (0-20) for one page: 12 for >=250 words (6 for >=80) + 8 for an H1."""
    text = visible_text(body)
    words = len(text.split())
    h1s = headings(body)["h1"]
    pts = 0.0
    if words >= 250:
        pts += 12.0
    elif words >= 80:
        pts += 6.0
    if h1s:
        pts += 8.0
    return pts


def collect(url: str, home: HttpResult, robots: HttpResult | None = None,
            inner_pages: list | None = None):
    base = origin(url)
    raw: dict = {}
    signals: list[Signal] = []

    # 1) HTTPS enforced — 15. Final URL https + http→https redirect.
    https_final = home.final_url.startswith("https://")
    http_probe = fetch("http://" + base.split("://", 1)[1], want_body=False)
    redirects_to_https = http_probe.final_url.startswith("https://") or (
        http_probe.status in (301, 308, 302, 307)
        and http_probe.header("location", "").startswith("https://")
    )
    https_pts = (10.0 if https_final else 0.0) + (5.0 if redirects_to_https else 0.0)
    raw["https_final"] = https_final
    raw["http_redirects_https"] = redirects_to_https
    signals.append(measured(
        "https", "HTTPS enforced (secure + HTTP redirects to HTTPS)",
        15.0, https_pts, value=https_final,
        evidence=f"final={home.final_url}; http_probe->{http_probe.final_url}",
        recommendation="" if https_pts == 15 else
        "Serve over HTTPS and 301-redirect all HTTP traffic to HTTPS.",
    ))

    # 2) Security headers — 10 (2 each).
    present = [(h, lbl) for h, lbl in SECURITY_HEADERS if home.header(h)]
    raw["security_headers"] = [lbl for _, lbl in present]
    signals.append(measured(
        "security_headers", "Security headers present",
        10.0, 2.0 * len(present), value=f"{len(present)}/{len(SECURITY_HEADERS)}",
        evidence=", ".join(lbl for _, lbl in present) or "none",
        recommendation="" if len(present) == len(SECURITY_HEADERS) else
        "Add missing security headers: " + ", ".join(
            lbl for h, lbl in SECURITY_HEADERS if not home.header(h)) + ".",
    ))

    # 3) Canonical tag — 8.
    canonical = find_link_rel(home.body, "canonical")
    signals.append(measured(
        "canonical", "Canonical link present on homepage",
        8.0, 8.0 if canonical else 0.0, value=canonical or False,
        evidence=canonical, recommendation="" if canonical else
        "Add <link rel='canonical'> to prevent duplicate-content dilution.",
    ))

    # 4) Mobile viewport — 10.
    viewport = find_meta(home.body, "viewport")
    signals.append(measured(
        "viewport", "Mobile viewport meta tag",
        10.0, 10.0 if "width=device-width" in viewport else 0.0,
        value=viewport or False, evidence=viewport,
        recommendation="" if "width=device-width" in viewport else
        "Add <meta name='viewport' content='width=device-width, initial-scale=1'>.",
    ))

    # 5) Server-side rendering — 20. Real text + an H1 present in RAW HTML.
    # Sampled across pages: the homepage always counts; inner pages (if crawled)
    # are averaged in so SSR reflects the whole site (fraction server-rendered).
    # With no inner pages this is exactly the homepage-only score.
    text = visible_text(home.body)
    words = len(text.split())
    h1s = headings(home.body)["h1"]
    raw["raw_word_count"] = words
    raw["h1_count"] = len(h1s)
    home_ssr_pts = _ssr_points(home.body or "")
    pages = inner_pages or []
    if pages:
        per_page_ssr = [home_ssr_pts] + [_ssr_points(_page_body(p)) for p in pages]
        ssr_pts = round(sum(per_page_ssr) / len(per_page_ssr), 2)
        rendered = sum(1 for p in per_page_ssr if p >= 20.0)
        raw["ssr_pages_full"] = f"{rendered}/{len(per_page_ssr)}"
        ssr_value = f"avg {ssr_pts}/20 across {len(per_page_ssr)} pages"
        ssr_evidence = f"per-page SSR points: {per_page_ssr}"
    else:
        ssr_pts = home_ssr_pts
        ssr_value = f"{words} words, {len(h1s)} H1"
        ssr_evidence = f"raw visible words={words}; h1={h1s[:1]}"
    signals.append(measured(
        "ssr", "Content server-rendered (visible in raw HTML)",
        20.0, ssr_pts, value=ssr_value,
        detail="AI crawlers do not run JavaScript; content must be in the HTML source.",
        evidence=ssr_evidence,
        recommendation="" if ssr_pts == 20 else
        "Server-render main content — little/no text in raw HTML means AI crawlers "
        "see an empty page. Use SSR/SSG (Next.js, Nuxt, etc.).",
    ))

    # 6) robots.txt present — 5.
    if robots is None:
        robots = fetch(base + "/robots.txt", want_body=False)
    robots_ok = bool(robots.ok and robots.status == 200)
    signals.append(measured(
        "robots_present", "robots.txt present",
        5.0, 5.0 if robots_ok else 0.0, value=robots_ok,
        recommendation="" if robots_ok else "Add a robots.txt with a Sitemap directive.",
    ))

    # 7) XML sitemap reachable — 7.
    sitemap = fetch(base + "/sitemap.xml", want_body=False)
    sitemap_ok = bool(sitemap.ok and sitemap.status == 200)
    raw["sitemap_status"] = sitemap.status
    signals.append(measured(
        "sitemap", "XML sitemap reachable at /sitemap.xml",
        7.0, 7.0 if sitemap_ok else 0.0, value=sitemap_ok,
        recommendation="" if sitemap_ok else
        "Publish an XML sitemap and reference it in robots.txt.",
    ))

    # 8) TTFB — 10. Measured wall-clock to full homepage response.
    ttfb = home.ttfb_ms
    if ttfb is None:
        ttfb_pts = 0.0
    elif ttfb <= 800:
        ttfb_pts = 10.0
    elif ttfb <= 1800:
        ttfb_pts = 6.0
    elif ttfb <= 3000:
        ttfb_pts = 3.0
    else:
        ttfb_pts = 0.0
    signals.append(measured(
        "ttfb", "Server response time (TTFB)",
        10.0, ttfb_pts, value=f"{ttfb} ms",
        detail="Measured server response latency for the homepage.",
        recommendation="" if ttfb_pts >= 10 else
        "Reduce TTFB below 800ms via caching/CDN/faster origin.",
    ))

    # 9) Title + meta description — 8.
    t = title(home.body)
    desc = find_meta(home.body, "description")
    meta_pts = (4.0 if t else 0.0) + (4.0 if desc else 0.0)
    signals.append(measured(
        "title_description", "Title and meta description present",
        8.0, meta_pts, value={"title": bool(t), "description": bool(desc)},
        evidence=f"title='{t[:60]}'; desc='{desc[:60]}'",
        recommendation="" if meta_pts == 8 else
        "Add a unique <title> and <meta name='description'> to the homepage.",
    ))

    # 10) Compression — 5.
    enc = home.header("content-encoding", "")
    compressed = any(x in enc for x in ("gzip", "br", "deflate"))
    signals.append(measured(
        "compression", "HTTP compression enabled",
        5.0, 5.0 if compressed else 0.0, value=enc or False,
        recommendation="" if compressed else "Enable gzip or brotli compression.",
    ))

    # 11) HTML lang attribute — 2.
    import re
    has_lang = bool(re.search(r"<html[^>]*\blang=", home.body or "", re.IGNORECASE))
    signals.append(measured(
        "html_lang", "HTML lang attribute set",
        2.0, 2.0 if has_lang else 0.0, value=has_lang,
        recommendation="" if has_lang else "Set <html lang='en'> (or appropriate locale).",
    ))

    cat = category("technical", "Technical GEO", signals)
    return cat, raw
