"""Schema.org / JSON-LD collector — deterministic.

This fixes two real bugs in the old skill: (1) the referenced fetch_page.py did
not exist, and (2) WebFetch strips <head>, hiding JSON-LD entirely. We parse the
RAW HTML, so detected schema types, required-property completeness, and sameAs
links are measured facts, not guesses.
"""

from __future__ import annotations

import json

from ..evidence import Signal, category, measured
from ..html_utils import extract_ld_json_blocks
from ..http_client import HttpResult

# Required properties per GEO-critical type (subset of schema.org requirements).
REQUIRED = {
    "Organization": ["name", "url"],
    "LocalBusiness": ["name", "address"],
    "Article": ["headline", "author", "datePublished"],
    "BlogPosting": ["headline", "author", "datePublished"],
    "Product": ["name", "offers"],
    "SoftwareApplication": ["name", "applicationCategory"],
    "WebSite": ["name", "url"],
    "Person": ["name"],
    "FAQPage": ["mainEntity"],
    "BreadcrumbList": ["itemListElement"],
}


def _iter_types(node, found: dict):
    """Recursively collect @type nodes and their property keys."""
    if isinstance(node, dict):
        t = node.get("@type")
        types = t if isinstance(t, list) else ([t] if t else [])
        for ty in types:
            if isinstance(ty, str):
                found.setdefault(ty, []).append(node)
        for v in node.values():
            _iter_types(v, found)
    elif isinstance(node, list):
        for v in node:
            _iter_types(v, found)


def collect(url: str, home: HttpResult):
    """home is the already-fetched homepage HttpResult (raw HTML)."""
    raw: dict = {}
    signals: list[Signal] = []

    blocks = extract_ld_json_blocks(home.body or "")
    parsed = []
    parse_errors = 0
    for b in blocks:
        try:
            parsed.append(json.loads(b))
        except Exception:
            parse_errors += 1

    found: dict[str, list] = {}
    for p in parsed:
        # handle @graph wrappers
        if isinstance(p, dict) and "@graph" in p:
            _iter_types(p["@graph"], found)
        _iter_types(p, found)

    detected = sorted(found.keys())
    raw["ld_json_blocks"] = len(blocks)
    raw["parse_errors"] = parse_errors
    raw["detected_types"] = detected

    # 1) Any JSON-LD present at all — 20 points.
    has_any = len(parsed) > 0
    signals.append(measured(
        "json_ld_present", "JSON-LD structured data present",
        20.0, 20.0 if has_any else 0.0,
        value=has_any,
        evidence=f"{len(blocks)} ld+json block(s); types: {', '.join(detected) or 'none'}",
        recommendation="" if has_any else
        "Add JSON-LD structured data — it is how AI systems identify your entity.",
    ))

    # 2) Organization or LocalBusiness identity — 25 points.
    org_node = None
    for t in ("Organization", "LocalBusiness", "Corporation"):
        if t in found:
            org_node = found[t][0]
            break
    if org_node is not None:
        req = REQUIRED.get("Organization", [])
        present = [k for k in req if org_node.get(k)]
        signals.append(measured(
            "org_schema", "Organization/LocalBusiness schema with required props",
            25.0, 25.0 * (len(present) / len(req)) if req else 25.0,
            value=f"{len(present)}/{len(req)} required",
            evidence=f"keys: {', '.join(sorted(org_node.keys()))[:200]}",
            recommendation="" if len(present) == len(req) else
            f"Add missing Organization properties: {', '.join(k for k in req if k not in present)}.",
        ))
    else:
        signals.append(measured(
            "org_schema", "Organization/LocalBusiness schema present",
            25.0, 0.0, value=False,
            recommendation="Add an Organization (or LocalBusiness) JSON-LD block on the homepage.",
        ))

    # 3) sameAs entity links — 15 points (3 per link, capped). Countable.
    sameas = []
    for nodes in found.values():
        for n in nodes:
            sa = n.get("sameAs")
            if isinstance(sa, str):
                sameas.append(sa)
            elif isinstance(sa, list):
                sameas.extend(x for x in sa if isinstance(x, str))
    sameas = sorted(set(sameas))
    raw["sameas"] = sameas
    signals.append(measured(
        "sameas_links", "sameAs entity links (Wikipedia/LinkedIn/socials)",
        15.0, min(15.0, 3.0 * len(sameas)),
        value=len(sameas),
        evidence="; ".join(sameas[:6]),
        recommendation="" if len(sameas) >= 5 else
        "Add 5+ sameAs links (Wikipedia, Wikidata, LinkedIn, YouTube, X) to your "
        "Organization schema to strengthen entity recognition.",
    ))

    # 4) WebSite schema — 10 points.
    has_website = "WebSite" in found
    signals.append(measured(
        "website_schema", "WebSite schema present",
        10.0, 10.0 if has_website else 0.0,
        value=has_website,
        recommendation="" if has_website else "Add a WebSite JSON-LD block (enables SearchAction).",
    ))

    # 5) Server-rendered (in raw HTML, not JS-injected) — 15 points.
    # If we found it in the static body at all, it is server-rendered by definition.
    signals.append(measured(
        "schema_server_rendered", "JSON-LD is in server-rendered HTML",
        15.0, 15.0 if has_any else 0.0,
        value=has_any,
        detail="Parsed from raw HTML (no JS execution); AI crawlers can read it.",
        recommendation="" if has_any else
        "Render JSON-LD server-side — JS-injected schema is missed by AI crawlers.",
    ))

    # 6) Valid JSON (no parse errors) — 15 points.
    valid_ratio = 1.0 if not blocks else (len(parsed) / len(blocks))
    signals.append(measured(
        "schema_valid_json", "JSON-LD blocks parse as valid JSON",
        15.0, 15.0 * valid_ratio if blocks else 0.0,
        value=f"{len(parsed)}/{len(blocks)} valid" if blocks else "no blocks",
        recommendation="Fix malformed JSON-LD (trailing commas / unquoted keys)."
        if parse_errors else "",
    ))

    cat = category("schema", "Schema & Structured Data", signals)
    return cat, raw
