#!/usr/bin/env python3
"""Audit any business website for AI-search (GEO) readiness — zero config.

Quickstart (from a fresh clone, nothing but Python 3 installed):

    python3 audit.py https://example.com

Optional flags:

    python3 audit.py https://example.com --type saas
    python3 audit.py https://example.com --max-pages 12 --out-dir ~/reports

What it does:
  * Fetches the homepage (and a few inner pages) with the bundled, stdlib-only
    deterministic engine — no API key, no pip install, no network library beyond
    the Python standard library.
  * Writes three files into <out-dir>/<slug>/:
      - GEO-AUDIT.json        machine-readable evidence + per-pillar scores
      - GEO-AUDIT-REPORT.md   client-facing report with a confidence band
      - GEO-AUDIT.html        polished, shareable page (email it / print to PDF)
  * Prints your GEO score, the path to the HTML, and a ready-to-paste prompt you
    can hand to Claude Code to actually fix the site.

Honesty contract: every signal is either MEASURED from real HTTP/HTML evidence
or explicitly NOT MEASURED (it never inflates the score; it lowers confidence).
Off-site pillars (Brand Authority, Platform Optimization) are not measured by
this free engine and show as "not measured" — the confidence percentage tells
you how much of the score is backed by direct measurement.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys

# --- Make the bundled engine importable from a fresh clone, no PYTHONPATH ----
_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
_ENGINE_DIR = os.path.join(_REPO_ROOT, "engine")
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

try:
    from geo_audit.run_audit import run as run_audit
    from geo_audit.report import render as render_md
    from geo_audit.http_client import fetch, normalize_url
except ImportError as exc:  # pragma: no cover - clone integrity guard
    sys.stderr.write(
        "ERROR: could not import the bundled GEO engine from "
        f"{_ENGINE_DIR!r}.\n"
        f"  {exc}\n"
        "Make sure you cloned the whole repository (the 'engine/' folder must "
        "be next to this script) and are running Python 3.\n"
    )
    raise SystemExit(2)

# report_html is being built in parallel by a teammate; depend on the frozen
# signature render_html(result: dict) -> str, but degrade gracefully if the
# module is not present yet so JSON + Markdown still always produce.
try:
    from geo_audit.report_html import render_html  # type: ignore
    _HTML_AVAILABLE = True
    _HTML_IMPORT_ERROR = ""
except Exception as exc:  # noqa: BLE001 - any import-time failure is non-fatal
    render_html = None  # type: ignore
    _HTML_AVAILABLE = False
    _HTML_IMPORT_ERROR = str(exc)


VALID_TYPES = ("local", "saas", "ecommerce", "publisher", "agency")
DEFAULT_OUT_DIR = "./audits"
DEFAULT_MAX_PAGES = 8


# ---------------------------------------------------------------------------
# Business-type auto-detection (conservative; defaults when unsure)
# ---------------------------------------------------------------------------
def _count_hits(text: str, needles: tuple[str, ...]) -> int:
    """How many distinct needles appear in the (lower-cased) text."""
    return sum(1 for n in needles if n in text)


def detect_business_type(html: str) -> tuple[str | None, str]:
    """Guess the business type from homepage HTML using honest keyword cues.

    Returns (type_or_None, human_reason). Returns (None, reason) when nothing
    scores clearly, so the caller can fall back to the engine default rather
    than guess. Heuristics are intentionally conservative.
    """
    if not html:
        return None, "no homepage HTML to inspect"

    t = html.lower()

    # E-commerce: shopping-cart language (incl. Dutch "winkelmand").
    ecommerce = (
        "add to cart", "add-to-cart", "addtocart", "winkelmand",
        "shopping cart", "in winkelwagen", "winkelwagen", "checkout",
        '"product"', "schema.org/product", "product:price", "add to bag",
    )
    # Local: physical-presence + opening-hours cues (incl. Dutch).
    local = (
        "localbusiness", "openinghours", "opening hours", "openingstijden",
        "google.com/maps", "maps.google", "address", "our location",
        "find us", "directions", "geo.position", "addresslocality",
    )
    # SaaS: pricing / signup / trial language.
    saas = (
        "pricing", "free trial", "free-trial", "start free", "sign up",
        "signup", "get started", "request a demo", "book a demo",
        "/login", "api docs", "documentation", "monthly", "per month",
        "per user", "subscription",
    )
    # Publisher: many articles + bylines.
    publisher = (
        "/article/", "/articles/", "/blog/", "/news/", "by author",
        'rel="author"', "newsletter", "subscribe", "published on",
        "read more", "latest stories", "/category/", "datePublished",
    )
    # Agency: portfolio / case-study / services language (incl. Dutch "diensten").
    agency = (
        "case study", "case studies", "our work", "portfolio", "our services",
        "diensten", "our clients", "what we do", "get a quote",
        "book a call", "let's talk", "projects", "testimonials",
    )

    scores = {
        "ecommerce": _count_hits(t, ecommerce),
        "local": _count_hits(t, local),
        "saas": _count_hits(t, saas),
        "publisher": _count_hits(t, publisher),
        "agency": _count_hits(t, agency),
    }

    # Strong structured signals override fuzzy keyword counts.
    if "schema.org/product" in t or '"@type":"product"' in t.replace(" ", ""):
        return "ecommerce", "found Product schema / cart markup"
    if "localbusiness" in t or "openingstijden" in t or "openinghours" in t:
        return "local", "found LocalBusiness / opening-hours signals"

    best_type = max(scores, key=lambda k: scores[k])
    best = scores[best_type]
    # Require a meaningful margin so a single stray keyword never decides.
    ordered = sorted(scores.values(), reverse=True)
    runner_up = ordered[1] if len(ordered) > 1 else 0
    if best >= 2 and best - runner_up >= 1:
        cues = {
            "ecommerce": "cart / product language",
            "local": "address / opening-hours language",
            "saas": "pricing / signup / trial language",
            "publisher": "article / byline / blog language",
            "agency": "portfolio / case-study / services language",
        }[best_type]
        return best_type, f"matched {best} {cues} cues"

    return None, "no clear signal — using the engine default"


def slugify_domain(url: str) -> str:
    """stripe.com -> stripe-com ; keeps it filesystem-safe and predictable."""
    from urllib.parse import urlsplit

    netloc = urlsplit(normalize_url(url)).netloc or url
    host = netloc.split("@")[-1].split(":")[0]  # strip auth + port
    host = host.lower().lstrip("www.") if host.lower().startswith("www.") else host.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", host).strip("-")
    return slug or "site"


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------
def _claude_prompt(json_path: str, md_path: str) -> str:
    """A ready-to-paste prompt that points Claude Code at the produced files."""
    json_name = os.path.basename(json_path)
    md_name = os.path.basename(md_path)
    return (
        f"Read {md_name} and {json_name} (the GEO audit of my website — scores, "
        f"per-pillar breakdown, and every measured signal with its evidence). "
        f"Work through the 'Prioritized Fixes' in {md_name}, highest-impact "
        f"first. For each one, find the relevant file in this codebase, make the "
        f"change, and show me a diff. Only act on signals the audit marked as "
        f"MEASURED; skip anything it marked 'not measured'. After your changes, "
        f"summarize what you fixed and what should improve on the next audit."
    )


def _print_success(result: dict, slug_dir: str, json_path: str,
                   md_path: str, html_path: str | None) -> None:
    comp = result.get("composite", {})
    score = comp.get("geo_score")
    rating = comp.get("rating", "")
    conf = comp.get("confidence", 0.0)
    band = comp.get("score_band")

    print("")
    print("=" * 64)
    if score is None:
        print("  GEO score: N/A (insufficient data measured)")
    else:
        band_txt = ""
        if band and len(band) == 2 and band[0] is not None:
            half = (band[1] - band[0]) / 2.0
            band_txt = f" plus/minus {half:.0f}"
        print(f"  GEO score: {score}/100{band_txt} — {rating} "
              f"(confidence {int(round(conf * 100))}%)")
    print("=" * 64)
    print("")
    print("Your three files are in:")
    print(f"  {slug_dir}")
    print(f"  - {os.path.basename(md_path)}   (the readable report)")
    print(f"  - {os.path.basename(json_path)} (the data behind it)")
    if html_path:
        print(f"  - {os.path.basename(html_path)} (the shareable page)")
        print("")
        print("SHARE IT: open this in any browser, or print it to PDF and "
              "email it to a client:")
        print(f"  {html_path}")
    else:
        print("")
        print("NOTE: the polished HTML report could not be generated yet "
              "(the report_html module is not present in this build).")
        if _HTML_IMPORT_ERROR:
            print(f"      reason: {_HTML_IMPORT_ERROR}")
        print("      The JSON and Markdown reports above were still written.")
    print("")
    print("-" * 64)
    print("FIX THE SITE WITH CLAUDE CODE")
    print("-" * 64)
    print("1. Copy this folder into your website's code repository:")
    print(f"     {slug_dir}")
    print("2. Open Claude Code in that repository.")
    print("3. Paste the prompt between the lines below:")
    print("")
    print("v" * 64)
    print(_claude_prompt(json_path, md_path))
    print("^" * 64)
    print("")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="audit.py",
        description="Audit any business website for AI-search (GEO) readiness. "
                    "No API key, no install — just Python 3.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("url", help="The website to audit, e.g. https://example.com")
    ap.add_argument("--type", dest="business_type", choices=VALID_TYPES,
                    default=None,
                    help="Business type. Omit to auto-detect from the homepage.")
    ap.add_argument("--max-pages", dest="max_pages", type=int,
                    default=DEFAULT_MAX_PAGES,
                    help=f"How many pages to crawl (default {DEFAULT_MAX_PAGES}; "
                         "1 = homepage only).")
    ap.add_argument("--out-dir", dest="out_dir", default=DEFAULT_OUT_DIR,
                    help=f"Where to write the report folder (default "
                         f"{DEFAULT_OUT_DIR!r}, relative to your current dir).")
    args = ap.parse_args(argv)

    url = normalize_url(args.url)
    if not url:
        print("ERROR: please provide a website URL, e.g. "
              "python3 audit.py https://example.com", file=sys.stderr)
        return 2

    slug = slugify_domain(url)
    out_root = os.path.abspath(os.path.expanduser(args.out_dir))
    slug_dir = os.path.join(out_root, slug)

    print(f"Auditing {url}")

    # --- Auto-detect business type (only when the user didn't specify) -------
    business_type = args.business_type
    if business_type:
        print(f"Business type: {business_type} (you set this with --type)")
    else:
        print("Detecting business type from the homepage ...")
        home = fetch(url)
        detected, reason = detect_business_type(home.body if home.ok else "")
        business_type = detected  # None -> engine default
        shown = detected if detected else "default (general)"
        print(f"Business type: {shown} — {reason}.")
        print("  (Override anytime with --type "
              "local|saas|ecommerce|publisher|agency.)")

    # --- Run the audit through the frozen engine interface -------------------
    today = datetime.date.today().isoformat()
    print("Running the audit (fetching pages, measuring signals) ...")
    try:
        result = run_audit(
            url,
            business_type=business_type,
            date=today,
            quiet=True,
            max_pages=args.max_pages,
        )
    except Exception as exc:  # noqa: BLE001 - never show a stack trace for a bad URL
        print(f"\nERROR: the audit could not run for {url}.", file=sys.stderr)
        print(f"  {exc}", file=sys.stderr)
        print("  Check the URL is correct and reachable, then try again.",
              file=sys.stderr)
        return 1

    # The engine returns meta.error (not an exception) for an unreachable site.
    meta_error = result.get("meta", {}).get("error")
    if meta_error:
        print(f"\nCould not audit {url}.", file=sys.stderr)
        print(f"  {meta_error}", file=sys.stderr)
        print("  Is the address spelled correctly? Is the site online?",
              file=sys.stderr)
        return 1

    # --- Write the three deliverables ----------------------------------------
    try:
        os.makedirs(slug_dir, exist_ok=True)
    except OSError as exc:
        print(f"\nERROR: could not create the output folder {slug_dir!r}: {exc}",
              file=sys.stderr)
        return 1

    json_path = os.path.join(slug_dir, "GEO-AUDIT.json")
    md_path = os.path.join(slug_dir, "GEO-AUDIT-REPORT.md")
    html_path = os.path.join(slug_dir, "GEO-AUDIT.html")

    with open(json_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(result, indent=2, default=str))

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_md(result))

    html_written: str | None = None
    if _HTML_AVAILABLE and render_html is not None:
        try:
            html = render_html(result)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            html_written = html_path
        except Exception as exc:  # noqa: BLE001 - HTML is a bonus, never block
            print(f"WARNING: the HTML report failed to render: {exc}",
                  file=sys.stderr)
            html_written = None

    _print_success(result, slug_dir, json_path, md_path, html_written)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
