"""CLI orchestrator for the deterministic GEO audit.

Usage:
    python3 -m geo_audit.run_audit <url> [--type saas|local|ecommerce|publisher|agency]
                                         [--llm-scores path.json]
                                         [--out-json path.json] [--out-md path.md]
                                         [--out-html path.html]
                                         [--quiet]

Runs every collector against a single shared homepage fetch, aggregates with the
business-type weight profile, and writes a JSON evidence bundle + Markdown report.
With no network, importing this module never executes anything (testable).
"""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .collectors import content, crawl, crawlers, llmstxt, psi, schema, technical
from .http_client import DEFAULT_UA, fetch, normalize_url
from .report import render
from .report_html import render_html
from .scoring.aggregate import aggregate

DEFAULT_MAX_PAGES = 8

# Browser-like UA used as a fallback when our default bot UA is blocked/empty.
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def _fetch_with_fallback(target: str):
    """Fetch a page; if the bot UA yields an empty/blocked body, retry as a browser."""
    res = fetch(target)
    if (not res.ok or not (res.body or "").strip()) and res.status not in (404, 410):
        alt = fetch(target, user_agent=BROWSER_UA)
        if alt.ok and (alt.body or "").strip():
            return alt
    return res


def run(url: str, business_type: str | None = None, llm_scores: dict | None = None,
        date: str = "", quiet: bool = False, max_pages: int = DEFAULT_MAX_PAGES) -> dict:
    """Run the full deterministic audit and return the result dict.

    max_pages controls multi-page crawl breadth. max_pages=1 reproduces the
    homepage-only audit exactly (no inner pages fetched, no inner-page evidence
    passed to collectors), preserving historical scores.
    """
    url = normalize_url(url)
    log = (lambda *a: None) if quiet else (lambda *a: print(*a, file=sys.stderr))

    log(f"[1/7] Fetching homepage {url} ...")
    home = fetch(url)
    if not home.ok and not home.body:
        # Browser-UA fallback before giving up — some hosts block the bot UA.
        alt = fetch(url, user_agent=BROWSER_UA)
        if alt.ok or alt.body:
            home = alt
    if not home.ok and not home.body:
        return {
            "meta": {"url": url, "date": date, "engine_version": __version__,
                     "error": f"Could not fetch homepage: {home.error}",
                     "pages_analyzed": []},
            "composite": aggregate({}, business_type).to_dict(),
            "raw": {},
        }

    robots = fetch(crawlers.origin(url) + "/robots.txt")

    # Discover and fetch inner pages (deterministic). At max_pages=1 this is just
    # the homepage and inner_pages stays empty -> identical to legacy behavior.
    sitemap_res = None
    if max_pages > 1:
        sitemap_res = fetch(crawlers.origin(url) + "/sitemap.xml")
    log("[2/7] Discovering pages ...")
    page_urls = crawl.discover_pages(url, home, robots, sitemap_res, max_pages=max_pages)

    inner_pages: list[dict] = []
    fetched_urls = [home.final_url or url]
    for page_url in page_urls[1:]:  # skip homepage (index 0)
        res = _fetch_with_fallback(page_url)
        if not res.ok or not (res.body or "").strip():
            continue  # skip failures gracefully
        inner_pages.append({"url": res.final_url or page_url, "body": res.body,
                            "status": res.status})
        fetched_urls.append(res.final_url or page_url)
    log(f"      analyzed {len(fetched_urls)} page(s)")

    log("[3/7] Crawler access ...")
    crawl_cat, crawl_raw = crawlers.collect(url, robots)
    log("[4/7] llms.txt ...")
    llms_cat, llms_raw = llmstxt.collect(url)
    log("[5/7] Technical ...")
    tech_cat, tech_raw = technical.collect(url, home, robots, inner_pages=inner_pages)
    log("[6/7] Schema + content ...")
    schema_cat, schema_raw = schema.collect(url, home, inner_pages=inner_pages)
    (cit_cat, cit_raw), (eeat_cat, eeat_raw) = content.collect(
        url, home, inner_pages=inner_pages)
    log("[7/7] Core Web Vitals (PSI) ...")
    cwv_cat, cwv_raw = psi.collect(url)

    collected = {
        "technical": tech_cat,
        "crawler_access": crawl_cat,
        "llms_txt": llms_cat,
        "core_web_vitals": cwv_cat,
        "schema": schema_cat,
        "citability": cit_cat,
        "eeat": eeat_cat,
    }
    comp = aggregate(collected, business_type, llm_scores)

    return {
        "meta": {
            "url": url,
            "final_url": home.final_url,
            "date": date,
            "engine_version": __version__,
            "http_status": home.status,
            "ttfb_ms": home.ttfb_ms,
            "pages_analyzed": fetched_urls,
        },
        "composite": comp.to_dict(),
        "raw": {
            "crawlers": crawl_raw, "llms_txt": llms_raw, "technical": tech_raw,
            "schema": schema_raw, "citability": cit_raw, "eeat": eeat_raw,
            "core_web_vitals": cwv_raw,
            "pages": [{"url": p["url"], "status": p.get("status")}
                      for p in inner_pages],
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Deterministic GEO audit engine")
    ap.add_argument("url")
    ap.add_argument("--type", dest="business_type", default=None)
    ap.add_argument("--llm-scores", default=None,
                    help="Path to JSON of LLM-judged sub-scores to merge.")
    ap.add_argument("--date", default="")
    ap.add_argument("--max-pages", dest="max_pages", type=int, default=DEFAULT_MAX_PAGES,
                    help=f"Max pages to crawl (default {DEFAULT_MAX_PAGES}; 1 = homepage only).")
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--out-md", default=None)
    ap.add_argument("--out-html", default=None,
                    help="Write a self-contained shareable HTML report to PATH.")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    llm_scores = None
    if args.llm_scores:
        with open(args.llm_scores) as f:
            llm_scores = json.load(f)

    result = run(args.url, args.business_type, llm_scores, args.date, args.quiet,
                 max_pages=args.max_pages)

    out_json = json.dumps(result, indent=2, default=str)
    if args.out_json:
        with open(args.out_json, "w") as f:
            f.write(out_json)
    md = render(result)
    if args.out_md:
        with open(args.out_md, "w") as f:
            f.write(md)
    if args.out_html:
        with open(args.out_html, "w") as f:
            f.write(render_html(result))

    # If no output files requested, print JSON to stdout.
    if not args.out_json and not args.out_md and not args.out_html:
        print(out_json)
    else:
        c = result["composite"]
        print(f"GEO {c['geo_score']}/100 {c['rating']} "
              f"(confidence {int(c['confidence']*100)}%) -> "
              f"{args.out_html or args.out_md or args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
