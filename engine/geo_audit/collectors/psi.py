"""PageSpeed Insights collector — the honest Core Web Vitals path.

The old skill told the model to "estimate CWV from page characteristics" — i.e.
guess. That is exactly the fabrication we are removing. Real CWV requires field
(CrUX) or lab (Lighthouse) data. This collector calls Google's free PageSpeed
Insights API when PSI_API_KEY is set, and otherwise returns NOT_MEASURED so the
score is honest about what it could and could not observe.

Get a free key: https://developers.google.com/speed/docs/insights/v5/get-started
Set it as the PSI_API_KEY environment variable.
"""

from __future__ import annotations

import json
import os
from urllib.parse import urlencode

from ..evidence import Signal, category, errored, measured, not_measured
from ..http_client import fetch

PSI_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

# Good thresholds (2026): LCP <=2.5s, INP <=200ms, CLS <=0.1.
THRESHOLDS = {
    "LARGEST_CONTENTFUL_PAINT_MS": (2500, 4000),
    "INTERACTION_TO_NEXT_PAINT": (200, 500),
    "CUMULATIVE_LAYOUT_SHIFT_SCORE": (0.1, 0.25),
}


def _band_points(metric: str, value: float, max_pts: float) -> float:
    good, poor = THRESHOLDS[metric]
    if value <= good:
        return max_pts
    if value <= poor:
        return max_pts * 0.5
    return 0.0


def collect(url: str, api_key: str | None = None):
    key = api_key or os.environ.get("PSI_API_KEY", "").strip()
    raw: dict = {"source": "PageSpeed Insights"}

    if not key:
        signals = [
            not_measured("cwv_lcp", "Largest Contentful Paint (CWV)", 6.0,
                         detail="Needs PSI_API_KEY (free) to measure real CWV.",
                         recommendation="Set PSI_API_KEY to include Core Web Vitals in the score."),
            not_measured("cwv_inp", "Interaction to Next Paint (CWV)", 6.0,
                         detail="Needs PSI_API_KEY to measure."),
            not_measured("cwv_cls", "Cumulative Layout Shift (CWV)", 3.0,
                         detail="Needs PSI_API_KEY to measure."),
        ]
        raw["measured"] = False
        return category("core_web_vitals", "Core Web Vitals", signals), raw

    qs = urlencode({"url": url, "key": key, "category": "PERFORMANCE", "strategy": "MOBILE"})
    res = fetch(f"{PSI_ENDPOINT}?{qs}", timeout=60.0)
    raw["measured"] = res.ok
    if not res.ok:
        return category("core_web_vitals", "Core Web Vitals",
                        [errored("cwv", "Core Web Vitals", 15.0,
                                 detail=f"PSI API error: {res.error or res.status}")]), raw

    try:
        data = json.loads(res.body)
    except Exception as e:
        return category("core_web_vitals", "Core Web Vitals",
                        [errored("cwv", "Core Web Vitals", 15.0,
                                 detail=f"PSI parse error: {e}")]), raw

    # Prefer field data (loadingExperience); fall back to lab (lighthouse audits).
    field = data.get("loadingExperience", {}).get("metrics", {})
    raw["field_metrics"] = {k: v.get("percentile") for k, v in field.items()}
    signals: list[Signal] = []

    def add(metric_key, label, max_pts, divide=1.0):
        m = field.get(metric_key)
        if not m or m.get("percentile") is None:
            signals.append(not_measured(metric_key, label, max_pts,
                                        detail="No field data for this URL in CrUX."))
            return
        val = m["percentile"] / divide
        pts = _band_points(metric_key, m["percentile"], max_pts)
        signals.append(measured(metric_key, label, max_pts, pts,
                                value=val, evidence=f"p75={m['percentile']}",
                                recommendation="" if pts == max_pts else
                                f"Improve {label}: p75 is {val}."))

    add("LARGEST_CONTENTFUL_PAINT_MS", "Largest Contentful Paint (CWV)", 6.0, 1000.0)
    add("INTERACTION_TO_NEXT_PAINT", "Interaction to Next Paint (CWV)", 6.0, 1.0)
    add("CUMULATIVE_LAYOUT_SHIFT_SCORE", "Cumulative Layout Shift (CWV)", 3.0, 1.0)

    return category("core_web_vitals", "Core Web Vitals", signals), raw
