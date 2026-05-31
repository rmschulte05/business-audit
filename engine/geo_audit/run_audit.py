"""CLI orchestrator for the deterministic GEO audit.

Usage:
    python3 -m geo_audit.run_audit <url> [--type saas|local|ecommerce|publisher|agency]
                                         [--llm-scores path.json]
                                         [--out-json path.json] [--out-md path.md]
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
from .collectors import content, crawlers, llmstxt, psi, schema, technical
from .http_client import fetch, normalize_url
from .report import render
from .scoring.aggregate import aggregate


def run(url: str, business_type: str | None = None, llm_scores: dict | None = None,
        date: str = "", quiet: bool = False) -> dict:
    """Run the full deterministic audit and return the result dict."""
    url = normalize_url(url)
    log = (lambda *a: None) if quiet else (lambda *a: print(*a, file=sys.stderr))

    log(f"[1/6] Fetching homepage {url} ...")
    home = fetch(url)
    if not home.ok and not home.body:
        return {
            "meta": {"url": url, "date": date, "engine_version": __version__,
                     "error": f"Could not fetch homepage: {home.error}"},
            "composite": aggregate({}, business_type).to_dict(),
            "raw": {},
        }

    robots = fetch(crawlers.origin(url) + "/robots.txt")

    log("[2/6] Crawler access ...")
    crawl_cat, crawl_raw = crawlers.collect(url, robots)
    log("[3/6] llms.txt ...")
    llms_cat, llms_raw = llmstxt.collect(url)
    log("[4/6] Technical ...")
    tech_cat, tech_raw = technical.collect(url, home, robots)
    log("[5/6] Schema + content ...")
    schema_cat, schema_raw = schema.collect(url, home)
    (cit_cat, cit_raw), (eeat_cat, eeat_raw) = content.collect(url, home)
    log("[6/6] Core Web Vitals (PSI) ...")
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
        },
        "composite": comp.to_dict(),
        "raw": {
            "crawlers": crawl_raw, "llms_txt": llms_raw, "technical": tech_raw,
            "schema": schema_raw, "citability": cit_raw, "eeat": eeat_raw,
            "core_web_vitals": cwv_raw,
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Deterministic GEO audit engine")
    ap.add_argument("url")
    ap.add_argument("--type", dest="business_type", default=None)
    ap.add_argument("--llm-scores", default=None,
                    help="Path to JSON of LLM-judged sub-scores to merge.")
    ap.add_argument("--date", default="")
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--out-md", default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    llm_scores = None
    if args.llm_scores:
        with open(args.llm_scores) as f:
            llm_scores = json.load(f)

    result = run(args.url, args.business_type, llm_scores, args.date, args.quiet)

    out_json = json.dumps(result, indent=2, default=str)
    if args.out_json:
        with open(args.out_json, "w") as f:
            f.write(out_json)
    md = render(result)
    if args.out_md:
        with open(args.out_md, "w") as f:
            f.write(md)

    # If no output files requested, print JSON to stdout.
    if not args.out_json and not args.out_md:
        print(out_json)
    else:
        c = result["composite"]
        print(f"GEO {c['geo_score']}/100 {c['rating']} "
              f"(confidence {int(c['confidence']*100)}%) -> "
              f"{args.out_md or args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
