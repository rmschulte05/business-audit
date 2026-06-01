"""llms.txt collector — deterministic presence + format validation.

Checks /llms.txt and /llms-full.txt. Presence and structural validity are fully
measurable. We do NOT score subjective "usefulness" here — that is left to the
LLM skill, which receives this evidence. Honest framing: llms.txt is an emerging
convention with low adoption, so it is a small bonus signal, not a core pillar.
"""

from __future__ import annotations

import re

from ..evidence import Signal, category, measured
from ..http_client import HttpResult, fetch, origin


def _validate(body: str) -> dict:
    lines = body.splitlines()
    has_h1 = bool(lines) and lines[0].lstrip().startswith("# ")
    has_quote = any(ln.lstrip().startswith(">") for ln in lines[:6])
    section_count = sum(1 for ln in lines if ln.lstrip().startswith("## "))
    # Markdown link entries: - [Title](https://...)
    entries = re.findall(r"^\s*-\s*\[[^\]]+\]\((https?://[^)]+)\)", body, re.MULTILINE)
    abs_urls = [u for u in entries if u.startswith("http")]
    return {
        "has_h1": has_h1,
        "has_description": has_quote,
        "section_count": section_count,
        "entry_count": len(entries),
        "absolute_url_ratio": (len(abs_urls) / len(entries)) if entries else 0.0,
        "line_count": len(lines),
    }


def collect(url: str, llms: HttpResult | None = None):
    base = origin(url)
    llms_url = base + "/llms.txt"
    if llms is None:
        llms = fetch(llms_url)
    full = fetch(base + "/llms-full.txt", want_body=False)

    raw: dict = {"llms_url": llms_url, "status": llms.status}
    signals: list[Signal] = []

    present = bool(llms.ok and llms.status == 200 and llms.body.strip())
    raw["present"] = present

    # Presence — 50 points. Honestly weighted: it's an early-adopter edge.
    signals.append(measured(
        "llms_present", "llms.txt file present at /llms.txt",
        50.0, 50.0 if present else 0.0,
        value=present,
        evidence=f"GET {llms_url} -> {llms.status}",
        detail="Emerging standard (<5% adoption); a low-effort differentiator.",
        recommendation="" if present else
        "Publish /llms.txt summarizing your key pages so AI systems index you faster.",
    ))

    if present:
        v = _validate(llms.body)
        raw.update(v)
        # Structural validity — 30 points across measurable format rules.
        checks = [
            (v["has_h1"], "H1 title"),
            (v["has_description"], "blockquote description"),
            (v["section_count"] >= 1, "at least one ## section"),
            (v["entry_count"] >= 5, "5+ page entries"),
            (v["absolute_url_ratio"] >= 0.9, "absolute URLs"),
        ]
        passed = sum(1 for ok, _ in checks if ok)
        signals.append(measured(
            "llms_format", "llms.txt structural validity",
            30.0, 30.0 * passed / len(checks),
            value=f"{passed}/{len(checks)} format checks",
            evidence="; ".join(f"{name}={'ok' if ok else 'missing'}" for ok, name in checks),
            recommendation="" if passed == len(checks) else
            "Fix llms.txt format: needs H1 title, > description, ## sections, 5+ "
            "[title](absolute-url) entries.",
        ))
        # Coverage depth — 20 points (entry count is countable, not judged).
        depth = min(1.0, v["entry_count"] / 15.0)
        signals.append(measured(
            "llms_depth", "llms.txt coverage depth (entry count)",
            20.0, 20.0 * depth,
            value=v["entry_count"],
            recommendation="" if v["entry_count"] >= 15 else
            "List 10-30 of your most important pages in llms.txt.",
        ))
    else:
        # Format/depth simply can't be measured if the file is absent — but the
        # absence is already fully captured by the presence signal scoring 0.
        v = {}

    raw["llms_full_present"] = bool(full.ok and full.status == 200)
    cat = category("llms_txt", "llms.txt Readiness", signals)
    return cat, raw
