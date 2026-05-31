"""Render the deterministic audit result as a client-facing Markdown report.

The report is explicit about what was MEASURED vs left to judgment, and stamps a
confidence band on the headline number — the honesty that makes the score
defensible to a paying client.
"""

from __future__ import annotations

from .evidence import Status


def _bar(score, width=20):
    if score is None:
        return "—"
    filled = int(round(score / 100 * width))
    return "█" * filled + "░" * (width - filled)


def render(result: dict) -> str:
    comp = result["composite"]
    meta = result["meta"]
    L = []
    L.append(f"# GEO Audit — {meta['url']}")
    L.append("")
    L.append(f"**Audit date:** {meta['date']}  ")
    L.append(f"**Business type:** {comp['business_type']}  ")
    L.append(f"**Engine version:** {meta['engine_version']} (deterministic)")
    L.append("")
    score = comp["geo_score"]
    band = comp["score_band"]
    conf = comp["confidence"]
    L.append("## Overall GEO Score")
    L.append("")
    if score is None:
        L.append("**Insufficient data to compute a score.**")
        L.append("")
        # Canonical machine-parseable line (kept even on failure).
        L.append("**Overall GEO Score: N/A (Insufficient Data)**")
    else:
        band_txt = f" (range {band[0]:.0f}–{band[1]:.0f})" if band else ""
        L.append(f"# {score}/100 — {comp['rating']}{band_txt}")
        L.append("")
        # Canonical machine-parseable line (downstream dashboards grep this).
        L.append(f"**Overall GEO Score: {score}/100 ({comp['rating']})**")
        L.append("")
        L.append(f"**Confidence: {int(conf*100)}%** — share of the weighted score "
                 f"backed by direct measurement. The rest is judgment or not yet measured.")
    L.append("")

    L.append("## Score Breakdown")
    L.append("")
    L.append("| Pillar | Key | Score | Confidence | Weight |")
    L.append("|---|---|---|---|---|")
    labels = {
        "citability": "AI Citability", "brand_authority": "Brand Authority",
        "eeat": "Content E-E-A-T", "technical": "Technical GEO",
        "schema": "Schema & Structured Data", "platform_optimization": "Platform Optimization",
    }
    for key, label in labels.items():
        p = comp["pillars"].get(key, {})
        sc = p.get("score")
        sc_txt = f"{sc}/100" if sc is not None else "not measured"
        cf = p.get("confidence", 0.0)
        w = p.get("weight", 0.0)
        # Include the snake_case key so downstream tooling can map rows reliably.
        L.append(f"| {label} | `{key}` | {sc_txt} | {int(cf*100)}% | {int(round(w*100))}% |")
    L.append("")

    # Prioritized fixes from measured signals that lost points.
    L.append("## Prioritized Fixes (from measured evidence)")
    L.append("")
    fixes = []
    for key, p in comp["pillars"].items():
        for s in p.get("signals", []):
            if s.get("status") == Status.MEASURED.value and s.get("recommendation"):
                gap = s.get("max_points", 0) - s.get("points", 0)
                if gap > 0.01:
                    fixes.append((gap, labels.get(key, key), s["recommendation"], s.get("evidence", "")))
    fixes.sort(key=lambda x: -x[0])
    if not fixes:
        L.append("_No measured gaps — strong on everything the engine could verify._")
    for gap, pillar, rec, ev in fixes[:15]:
        L.append(f"- **[{pillar}]** {rec}")
        if ev:
            L.append(f"  - evidence: `{ev[:160]}`")
    L.append("")

    # What still needs human/LLM judgment.
    L.append("## Not Measured by the Engine (needs reviewer judgment)")
    L.append("")
    nm = []
    for key, p in comp["pillars"].items():
        if p.get("score") is None and p.get("status") == "absent":
            nm.append(f"- **{labels.get(key, key)}** — not assessed (e.g. off-site brand/platform signals).")
            continue
        for s in p.get("signals", []):
            if s.get("status") != Status.MEASURED.value:
                nm.append(f"- **{labels.get(key, key)}** — {s['label']}")
    if not nm:
        L.append("_Everything in scope was measured._")
    for line in nm[:20]:
        L.append(line)
    L.append("")
    L.append("---")
    L.append("_Scores are computed in code from observed HTTP/HTML evidence. "
             "Re-running on the same site yields the same numbers._")
    return "\n".join(L)
