"""Render the deterministic audit result as a self-contained HTML report.

This is the deterministic sibling of ``report.py``'s ``render()``: the same
``result`` dict always yields byte-identical HTML (the audit date comes from
``result.meta.date`` — no wall-clock, no randomness). The output is ONE complete
HTML document with all CSS inline and a system-font fallback so it is readable
offline and with JavaScript disabled.

It is also a data source: the full machine-readable ``result`` is embedded in a
``<script type="application/json" id="geo-audit-data">`` block, so the single
file is BOTH the shareable page and the complete evidence bundle.

Stdlib only.
"""

from __future__ import annotations

import json
from html import escape

# ---------------------------------------------------------------------------
# Display constants (mirror report.py / the design system; never fabricated).
# ---------------------------------------------------------------------------

# Pillar display order + labels (frozen contract).
PILLAR_ORDER = [
    ("citability", "AI Citability"),
    ("brand_authority", "Brand Authority"),
    ("eeat", "Content E-E-A-T"),
    ("technical", "Technical GEO"),
    ("schema", "Schema & Structured Data"),
    ("platform_optimization", "Platform Optimization"),
]
PILLAR_LABELS = dict(PILLAR_ORDER)

# Score-band colors, keyed by lowercased rating (from the design system).
RATING_COLORS = {
    "excellent": "#2d8659",
    "good": "#4a90c4",
    "fair": "#d97706",
    "poor": "#c45d3e",
    "critical": "#991b1b",
}
DEFAULT_RATING_COLOR = "#8a8580"  # --muted, e.g. Insufficient Data

EM_DASH = "—"
MAX_FIXES = 15
MAX_NOT_MEASURED = 25
MEASURED = "measured"

# Status values that mean "not a real measurement" (excluded from the score).
_UNMEASURED_STATUSES = ("not_measured", "error")

# TTFB is the one genuinely wall-clock signal (see collectors/technical.py).
# The raw meta.ttfb_ms reading jitters run-to-run (e.g. 55.6 vs 66.6 ms) which
# would make the embedded JSON — and therefore the whole HTML artifact — change
# byte-for-byte every run, breaking the "same input -> identical artifact"
# promise. We snap the EMBEDDED reading to a coarse band so the rendered file is
# reproducible given fixed network evidence, while the precise reading still
# lives in the canonical GEO-AUDIT.json written by --out-json.
TTFB_DISPLAY_ROUND_MS = 50


# ---------------------------------------------------------------------------
# Small pure helpers (all null-safe; never emit "null"/"None").
# ---------------------------------------------------------------------------

def _esc(value) -> str:
    """HTML-escape any value (quotes included). None -> empty string."""
    if value is None:
        return ""
    return escape(str(value), quote=True)


def _num(value):
    """Coerce to float, or None if not a finite number."""
    if value is None or isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")):  # NaN / inf guard
        return None
    return f


def _fmt_score(value) -> str:
    """Format a 0-100 score for display. None -> em dash. No trailing .0."""
    f = _num(value)
    if f is None:
        return EM_DASH
    if abs(f - round(f)) < 1e-9:
        return str(int(round(f)))
    return f"{f:.1f}"


def _pct(value) -> int:
    """Round a 0-1 confidence fraction to a whole percent. None -> 0."""
    f = _num(value)
    if f is None:
        return 0
    return int(round(f * 100))


def _clamp_pct(value) -> float:
    """Clamp a 0-100 score into a CSS-safe width percentage."""
    f = _num(value)
    if f is None:
        return 0.0
    return max(0.0, min(100.0, f))


def _rating_color(rating) -> str:
    return RATING_COLORS.get(str(rating or "").strip().lower(), DEFAULT_RATING_COLOR)


def _round_ttfb(ms):
    """Snap a raw TTFB reading to a coarse band for the embedded artifact.

    Wall-clock latency jitters run-to-run; snapping to TTFB_DISPLAY_ROUND_MS
    removes sub-bucket noise so the rendered HTML is byte-identical given fixed
    network evidence. None / non-numeric pass through unchanged.
    """
    f = _num(ms)
    if f is None:
        return ms
    return int(round(f / TTFB_DISPLAY_ROUND_MS) * TTFB_DISPLAY_ROUND_MS)


def _embed_payload(result: dict) -> dict:
    """A copy of ``result`` with the wall-clock TTFB reading coarsened.

    Returns a NEW dict (never mutates the caller's result) so the canonical
    GEO-AUDIT.json keeps the precise meta.ttfb_ms; only the embedded copy is
    snapped to a band for reproducibility.
    """
    meta = result.get("meta")
    if not isinstance(meta, dict) or "ttfb_ms" not in meta:
        return result
    return {**result, "meta": {**meta, "ttfb_ms": _round_ttfb(meta.get("ttfb_ms"))}}


def _safe_json(result: dict) -> str:
    """json.dumps with the script-breakout sequence neutralized.

    Replacing ``</`` with ``<\\/`` keeps the JSON valid (the backslash-slash is a
    legal JSON escape) while making it impossible to close the host <script> tag
    early. Deterministic: sort_keys for stable ordering. The wall-clock TTFB
    reading is coarsened first so the embedded payload is reproducible.
    """
    payload = _embed_payload(result)
    raw = json.dumps(payload, default=str, sort_keys=True, ensure_ascii=False)
    return raw.replace("</", "<\\/")


# ---------------------------------------------------------------------------
# Data extraction (tolerant of missing / None everywhere).
# ---------------------------------------------------------------------------

def _meta(result: dict) -> dict:
    return result.get("meta") or {}


def _composite(result: dict) -> dict:
    return result.get("composite") or {}


def _band_text(band, confidence) -> str:
    """Build the '.gauge-band' line: 'Range LO to HI, N% measured'."""
    pct = _pct(confidence)
    if band and isinstance(band, (list, tuple)) and len(band) == 2:
        lo, hi = _num(band[0]), _num(band[1])
        if lo is not None and hi is not None:
            return (f"Range <strong>{_fmt_score(lo)}</strong> to "
                    f"<strong>{_fmt_score(hi)}</strong>, "
                    f"<strong>{pct}%</strong> measured")
    return f"Range <strong>{EM_DASH}</strong>, <strong>{pct}%</strong> measured"


def _collect_fixes(comp: dict) -> list[tuple]:
    """Prioritized fixes from MEASURED signals with a recommendation.

    Returns a list of (gap, pillar_label, recommendation, evidence), sorted by
    point gap descending (deterministic tie-break on label/recommendation).
    """
    fixes: list[tuple] = []
    pillars = comp.get("pillars") or {}
    for key, _label in PILLAR_ORDER:
        p = pillars.get(key) or {}
        for s in p.get("signals") or []:
            if (s.get("status") == MEASURED) and (s.get("recommendation") or "").strip():
                gap = (_num(s.get("max_points")) or 0.0) - (_num(s.get("points")) or 0.0)
                if gap > 0.01:
                    fixes.append((
                        round(gap, 2),
                        PILLAR_LABELS.get(key, key),
                        s.get("recommendation") or "",
                        s.get("evidence") or "",
                    ))
    fixes.sort(key=lambda x: (-x[0], x[1], x[2]))
    return fixes


def _collect_not_measured(comp: dict) -> list[tuple]:
    """Signals/pillars needing reviewer judgment (status != measured)."""
    out: list[tuple] = []
    pillars = comp.get("pillars") or {}
    for key, _label in PILLAR_ORDER:
        p = pillars.get(key)
        label = PILLAR_LABELS.get(key, key)
        if p is None or p.get("status") == "absent":
            out.append((label, "not assessed (off-site brand/platform signals)"))
            continue
        for s in p.get("signals") or []:
            if s.get("status") in _UNMEASURED_STATUSES:
                out.append((label, s.get("label") or s.get("key") or "signal"))
    return out


# ---------------------------------------------------------------------------
# Section renderers (each returns an HTML fragment string).
# ---------------------------------------------------------------------------

def _render_header(result: dict) -> str:
    meta = _meta(result)
    comp = _composite(result)
    url = meta.get("final_url") or meta.get("url") or ""
    items = [
        ("Business URL", _esc(url)),
        ("Audit date", _esc(meta.get("date")) or EM_DASH),
        ("Business type", _esc(comp.get("business_type")) or EM_DASH),
        ("Engine version", _esc(meta.get("engine_version")) or EM_DASH),
    ]
    rows = "".join(
        f'<div class="meta-item"><span class="meta-key">{k}</span>'
        f'<span class="meta-val">{v}</span></div>'
        for k, v in items
    )
    err = meta.get("error")
    err_html = (
        f'<p class="error-note">{_esc(err)}</p>' if err else ""
    )
    return (
        '<header class="report-header">'
        '<p class="eyebrow">Generative Engine Optimization audit</p>'
        f'<h1>{_esc(url) or "GEO Audit"}</h1>'
        f'<div class="meta">{rows}</div>'
        f'{err_html}'
        '</header>'
    )


def _render_gauge(comp: dict) -> str:
    score = comp.get("geo_score")
    rating = comp.get("rating") or "Insufficient Data"
    band = comp.get("score_band")
    confidence = comp.get("confidence")
    color = _rating_color(rating)
    width = _clamp_pct(score)
    return (
        '<section class="card gauge" aria-label="Overall GEO score">'
        f'<div class="gauge-number" style="color:{color}">{_fmt_score(score)}</div>'
        f'<div class="gauge-label">{_esc(rating)}</div>'
        f'<div class="gauge-band">{_band_text(band, confidence)}</div>'
        '<div class="gauge-track">'
        f'<div class="gauge-fill" style="width:{width:.1f}%;background:{color}"></div>'
        '</div>'
        '<p class="gauge-caption">Confidence is the share of the score backed by '
        'direct measurement. The rest is marked &ldquo;Not measured&rdquo; and '
        'excluded from the score &mdash; never guessed.</p>'
        '</section>'
    )


def _render_pillar_bar(key: str, label: str, p: dict | None) -> str:
    weight_pct = _pct((p or {}).get("weight"))
    if p is None or p.get("score") is None or p.get("status") == "absent":
        # Unmeasured pillar: literal "Not measured", no fill, dimmed track.
        return (
            '<div class="bar-row bar-row--unmeasured">'
            f'<div class="bar-label">{_esc(label)}'
            f'<small>{weight_pct}% weight, not measured</small></div>'
            '<div class="bar-track"></div>'
            '<div class="bar-value">Not measured</div>'
            '</div>'
        )
    score = p.get("score")
    conf_pct = _pct(p.get("confidence"))
    width = _clamp_pct(score)
    return (
        '<div class="bar-row">'
        f'<div class="bar-label">{_esc(label)}'
        f'<small>{weight_pct}% weight, {conf_pct}% measured</small></div>'
        f'<div class="bar-track"><div class="bar-fill" style="width:{width:.1f}%"></div></div>'
        f'<div class="bar-value">{_fmt_score(score)}</div>'
        '</div>'
    )


def _render_pillars(comp: dict) -> str:
    pillars = comp.get("pillars") or {}
    rows = "".join(
        _render_pillar_bar(key, label, pillars.get(key))
        for key, label in PILLAR_ORDER
    )
    return (
        '<section class="card section">'
        '<h2>Pillar breakdown</h2>'
        f'<div class="bars">{rows}</div>'
        '</section>'
    )


def _render_fixes(comp: dict) -> str:
    fixes = _collect_fixes(comp)[:MAX_FIXES]
    if not fixes:
        body = ('<p class="empty">No measured gaps &mdash; strong on everything '
                'the engine could verify.</p>')
    else:
        items = []
        for gap, pillar, rec, ev in fixes:
            ev_html = (
                f'<div class="fix-evidence"><span class="mono">'
                f'{_esc(ev[:240])}</span></div>' if ev else ""
            )
            items.append(
                '<li class="fix">'
                f'<div class="fix-head"><span class="pill">{_esc(pillar)}</span>'
                f'<span class="fix-gap">+{_fmt_score(gap)} pts</span></div>'
                f'<div class="fix-rec">{_esc(rec)}</div>'
                f'{ev_html}'
                '</li>'
            )
        body = f'<ol class="fix-list">{"".join(items)}</ol>'
    return (
        '<section class="card section">'
        '<h2>Prioritized fixes</h2>'
        '<p class="section-sub">From measured signals that lost points, '
        'highest point gap first.</p>'
        f'{body}'
        '</section>'
    )


def _render_not_measured(comp: dict) -> str:
    items = _collect_not_measured(comp)[:MAX_NOT_MEASURED]
    if not items:
        body = '<p class="empty">Everything in scope was measured.</p>'
    else:
        lis = "".join(
            f'<li><span class="pill pill--muted">{_esc(label)}</span> {_esc(detail)}</li>'
            for label, detail in items
        )
        body = f'<ul class="nm-list">{lis}</ul>'
    return (
        '<section class="card section">'
        '<h2>Not measured (needs reviewer judgment)</h2>'
        '<p class="section-sub">Excluded from the score, never guessed. These '
        'lower the confidence band until a reviewer or LLM scores them.</p>'
        f'{body}'
        '</section>'
    )


def _build_prompt(result: dict) -> str:
    """A concrete, self-describing prompt for Claude Code."""
    meta = _meta(result)
    comp = _composite(result)
    url = meta.get("final_url") or meta.get("url") or "this website"
    score = _fmt_score(comp.get("geo_score"))
    rating = comp.get("rating") or "Insufficient Data"
    return (
        f"Read the GEO audit findings in this report for {url} "
        f"(current GEO score {score}/100, rated {rating}). The findings live in "
        "the embedded JSON in #geo-audit-data, or the accompanying GEO-AUDIT.json. "
        "Implement every Prioritized Fix against this website's codebase, starting "
        "with the highest measured point-gap. After each change, keep the change "
        "minimal and explain which pillar/signal it improves."
    )


def _render_claude_section(result: dict) -> str:
    prompt = _build_prompt(result)
    esc_prompt = _esc(prompt)
    return (
        '<section class="card section claude" aria-label="Improve with Claude Code">'
        '<h2>Improve this site with Claude Code</h2>'
        '<p class="section-sub">Copy this prompt into Claude Code (or any coding '
        'agent) alongside your repo. It is self-describing &mdash; it names the '
        'audited URL and score.</p>'
        '<div class="prompt-box">'
        f'<pre id="cc-prompt" class="prompt">{esc_prompt}</pre>'
        '<button type="button" class="copy-btn" data-target="cc-prompt" '
        'aria-label="Copy the Claude Code prompt">Copy prompt</button>'
        '</div>'
        '</section>'
    )


def _render_footer(result: dict) -> str:
    meta = _meta(result)
    ver = _esc(meta.get("engine_version")) or EM_DASH
    return (
        '<footer class="report-footer">'
        '<p>Scores are computed in code from observed HTTP/HTML evidence. '
        f'Re-running the deterministic engine (v{ver}) on the same site yields '
        'the same numbers. Every signal is either measured from real evidence or '
        'explicitly marked &ldquo;Not measured&rdquo; &mdash; never fabricated.</p>'
        '</footer>'
    )


def _render_data_block(result: dict) -> str:
    return (
        '<script type="application/json" id="geo-audit-data">'
        f'{_safe_json(result)}'
        '</script>'
    )


# ---------------------------------------------------------------------------
# CSS (inline, deterministic; system-font stack so the file is TRULY offline).
# ---------------------------------------------------------------------------
#
# The report makes ZERO network requests: no external <script>, <img>, or font
# <link>. We intentionally do NOT load Google Fonts — that would mean the page
# silently rendered with different typography offline vs online and break the
# "fully self-contained, email it to a client" promise the docs make. The named
# web families ("DM Sans" / "Instrument Serif") stay FIRST in each font stack so
# anyone who already has them installed still gets them; everyone else gets the
# system fallback below. Either way the file needs no internet to view.
_SYSTEM_SANS = (
    '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif'
)
_SYSTEM_SERIF = 'Georgia,"Times New Roman",serif'

_CSS = """
:root{
  --ink:#0a0a0a;--paper:#f6f4f0;--accent:#c45d3e;--accent-light:#e8a48e;
  --muted:#8a8580;--divider:#d6d2cc;--card:#fffefa;--shadow:rgba(10,10,10,0.06);
}
*{box-sizing:border-box;}
html{-webkit-text-size-adjust:100%;}
body{
  margin:0;background:var(--paper);color:var(--ink);
  font-family:"DM Sans",__SANS__;
  font-size:16px;line-height:1.65;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:880px;margin:0 auto;padding:3.5rem 1.5rem 4rem;}
h1,h2{font-family:"Instrument Serif",__SERIF__;font-weight:400;
  letter-spacing:-0.02em;line-height:1.15;margin:0;}
h1{font-size:2.4rem;margin:0.4rem 0 1.4rem;word-break:break-word;}
h2{font-size:1.6rem;margin:0 0 0.4rem;}
p{margin:0 0 1rem;}
a{color:var(--accent);}
.mono,.prompt,.bar-value,.gauge-number{font-variant-numeric:tabular-nums;}
.mono{font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;}
.eyebrow{font-size:0.78rem;letter-spacing:0.14em;text-transform:uppercase;
  color:var(--accent);margin:0;font-weight:600;}
.report-header{margin-bottom:2.5rem;}
.meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
  gap:0.9rem 1.5rem;border-top:1px solid var(--divider);
  border-bottom:1px solid var(--divider);padding:1.2rem 0;}
.meta-item{display:flex;flex-direction:column;gap:0.15rem;}
.meta-key{font-size:0.72rem;letter-spacing:0.08em;text-transform:uppercase;
  color:var(--muted);}
.meta-val{font-size:0.95rem;word-break:break-word;}
.error-note{margin-top:1rem;color:var(--accent);font-weight:500;}
.card{background:var(--card);border:1px solid var(--divider);border-radius:16px;
  padding:2rem;position:relative;overflow:hidden;}
.card::before{content:'';position:absolute;top:0;left:0;width:4px;height:100%;
  background:linear-gradient(to bottom,var(--accent),var(--accent-light));
  border-radius:4px 0 0 4px;}
.section{margin-top:1.75rem;}
.section-sub{color:var(--muted);font-size:0.92rem;margin:-0.1rem 0 1.3rem;}
.gauge{text-align:center;padding:2.5rem 2rem;}
.gauge-number{font-family:"Instrument Serif",__SERIF__;font-size:5rem;
  line-height:1;font-weight:400;}
.gauge-label{font-size:1.3rem;letter-spacing:0.02em;margin-top:0.25rem;}
.gauge-band{color:var(--muted);font-size:0.95rem;margin-top:0.6rem;}
.gauge-band strong{color:var(--ink);font-weight:600;}
.gauge-track{height:10px;background:var(--divider);border-radius:6px;
  overflow:hidden;margin:1.4rem auto 1.1rem;max-width:520px;}
.gauge-fill{height:100%;border-radius:6px;}
.gauge-caption{color:var(--muted);font-size:0.85rem;max-width:480px;
  margin:0 auto;}
.bars{display:flex;flex-direction:column;gap:1.15rem;margin-top:0.4rem;}
.bar-row{display:grid;grid-template-columns:1fr 2fr auto;align-items:center;
  gap:1rem;}
.bar-label{font-size:0.95rem;display:flex;flex-direction:column;gap:0.1rem;}
.bar-label small{color:var(--muted);font-size:0.72rem;letter-spacing:0.03em;}
.bar-track{height:9px;background:var(--divider);border-radius:6px;overflow:hidden;}
.bar-fill{height:100%;background:var(--accent);border-radius:6px;}
.bar-value{font-family:"Instrument Serif",__SERIF__;font-size:1.5rem;
  text-align:right;min-width:3.2rem;}
.bar-row--unmeasured .bar-track{opacity:0.4;}
.bar-row--unmeasured .bar-value{font-family:"DM Sans",__SANS__;
  font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;
  color:var(--muted);}
.fix-list,.nm-list{list-style:none;margin:0;padding:0;display:flex;
  flex-direction:column;gap:0.9rem;}
.fix{border:1px solid var(--divider);border-radius:12px;padding:1rem 1.1rem;
  background:var(--paper);}
.fix-head{display:flex;justify-content:space-between;align-items:center;
  gap:0.75rem;margin-bottom:0.4rem;}
.pill{display:inline-block;font-size:0.7rem;letter-spacing:0.06em;
  text-transform:uppercase;background:var(--accent);color:#fff;
  padding:0.2rem 0.55rem;border-radius:999px;font-weight:600;}
.pill--muted{background:var(--muted);}
.fix-gap{font-size:0.78rem;color:var(--accent);font-weight:600;white-space:nowrap;}
.fix-rec{font-size:0.95rem;}
.fix-evidence{margin-top:0.5rem;font-size:0.8rem;color:var(--muted);
  word-break:break-word;}
.nm-list li{display:flex;gap:0.6rem;align-items:baseline;flex-wrap:wrap;
  font-size:0.92rem;color:var(--muted);}
.nm-list .pill{flex:none;}
.empty{color:var(--muted);font-style:italic;}
.claude .prompt-box{position:relative;}
.prompt{font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
  font-size:0.85rem;line-height:1.55;background:var(--ink);color:#f6f4f0;
  border-radius:12px;padding:1.1rem 1.2rem;white-space:pre-wrap;
  word-break:break-word;margin:0;}
.copy-btn{position:absolute;top:0.7rem;right:0.7rem;font:inherit;
  font-size:0.72rem;letter-spacing:0.05em;text-transform:uppercase;
  background:var(--accent);color:#fff;border:none;border-radius:8px;
  padding:0.4rem 0.7rem;cursor:pointer;}
.copy-btn:hover{background:var(--accent-light);color:var(--ink);}
.report-footer{margin-top:2.5rem;color:var(--muted);font-size:0.82rem;
  text-align:center;border-top:1px solid var(--divider);padding-top:1.5rem;}
@media (max-width:640px){
  .wrap{padding:2.5rem 1rem 3rem;}
  h1{font-size:2rem;}
  .gauge-number{font-size:3.6rem;}
  .bar-row{grid-template-columns:1fr auto;}
  .bar-track{grid-column:1 / -1;order:3;}
}
@media print{
  body{background:#fff;}
  .wrap{max-width:none;padding:0;}
  .card{break-inside:avoid;box-shadow:none;}
  .copy-btn{display:none;}
  .section{page-break-inside:avoid;}
  @page{size:A4;margin:1.5cm;}
}
""".replace("__SANS__", _SYSTEM_SANS).replace("__SERIF__", _SYSTEM_SERIF)


# Optional progressive-enhancement copy button. The page is fully readable
# without it; this only wires the "Copy prompt" button when JS is enabled.
_COPY_JS = (
    "document.querySelectorAll('.copy-btn').forEach(function(b){"
    "b.addEventListener('click',function(){"
    "var t=document.getElementById(b.dataset.target);"
    "if(!t)return;"
    "var txt=t.innerText;"
    "var done=function(){var o=b.textContent;b.textContent='Copied';"
    "setTimeout(function(){b.textContent=o;},1500);};"
    "if(navigator.clipboard&&navigator.clipboard.writeText){"
    "navigator.clipboard.writeText(txt).then(done,function(){});}else{done();}"
    "});});"
)


# ---------------------------------------------------------------------------
# Public entry point.
# ---------------------------------------------------------------------------

def render_html(result: dict) -> str:
    """Render the audit ``result`` dict as one self-contained HTML document.

    Pure and deterministic: the same ``result`` always yields identical HTML.
    Tolerates missing / None values everywhere and never emits the literal
    ``null`` / ``None`` (null score or band renders as an em dash).
    """
    result = result or {}
    comp = _composite(result)

    head = (
        '<head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>GEO Audit {_esc(_meta(result).get("url") or "")}</title>'
        f'<style>{_CSS}</style>'
        '</head>'
    )

    body = (
        '<body><div class="wrap">'
        f'{_render_header(result)}'
        f'{_render_gauge(comp)}'
        f'{_render_pillars(comp)}'
        f'{_render_fixes(comp)}'
        f'{_render_not_measured(comp)}'
        f'{_render_claude_section(result)}'
        f'{_render_footer(result)}'
        '</div>'
        f'{_render_data_block(result)}'
        f'<script>{_COPY_JS}</script>'
        '</body>'
    )

    return f'<!DOCTYPE html><html lang="en">{head}{body}</html>'
