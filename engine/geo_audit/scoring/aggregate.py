"""Composite GEO score aggregation — pure and reproducible.

Maps the engine's collector categories onto the six client-facing GEO pillars,
optionally merges LLM-supplied scores for the judgment-only signals/pillars,
applies a business-type weight profile, and returns a composite score WITH an
explicit confidence band derived from how much of the weight was actually
measured. Same inputs always produce the same output.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..evidence import CategoryScore, Signal, Status, category, measured
from .weights import PILLARS, resolve_profile


def _merge_categories(key: str, label: str, cats: list[tuple[CategoryScore, float]]) -> CategoryScore:
    """Merge several categories into one pillar, rescaling each to a sub-weight.

    cats is a list of (CategoryScore, sub_weight). Each category's signals are
    rescaled so its measured signals sum to sub_weight, preserving the
    measured/not-measured accounting.
    """
    merged: list[Signal] = []
    for cat, sub_weight in cats:
        total = cat.total_max or 1.0
        factor = sub_weight / total
        for s in cat.signals:
            merged.append(
                Signal(
                    key=f"{cat.key}.{s.key}",
                    label=s.label,
                    status=s.status,
                    max_points=s.max_points * factor,
                    points=s.points * factor,
                    value=s.value,
                    detail=s.detail,
                    evidence=s.evidence,
                    recommendation=s.recommendation,
                )
            )
    return category(key, label, merged)


def _apply_llm(cat: CategoryScore, llm_scores: dict | None) -> CategoryScore:
    """Replace NOT_MEASURED judgment signals with LLM-provided scores.

    llm_scores maps signal key -> {"points": float, "detail": str, "evidence": str}.
    Only signals the LLM actually scored become MEASURED; the rest stay
    NOT_MEASURED so confidence remains honest.
    """
    if not llm_scores:
        return cat
    new_signals: list[Signal] = []
    for s in cat.signals:
        if s.status != Status.MEASURED and s.key in llm_scores:
            sc = llm_scores[s.key]
            new_signals.append(measured(
                s.key, s.label, s.max_points, float(sc.get("points", 0.0)),
                value=sc.get("value"), detail=sc.get("detail", "Scored by LLM reviewer."),
                evidence=sc.get("evidence", ""), recommendation=sc.get("recommendation", ""),
            ))
        else:
            new_signals.append(s)
    return category(cat.key, cat.label, new_signals)


@dataclass(frozen=True)
class Composite:
    score: float | None
    rating: str
    confidence: float
    band: tuple[float, float] | None
    business_type: str
    pillars: dict
    weights: dict

    def to_dict(self) -> dict:
        return {
            "geo_score": self.score,
            "rating": self.rating,
            "confidence": self.confidence,
            "score_band": list(self.band) if self.band else None,
            "business_type": self.business_type,
            "weights": self.weights,
            "pillars": self.pillars,
        }


def rating_for(score: float | None) -> str:
    if score is None:
        return "Insufficient Data"
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 60:
        return "Fair"
    if score >= 40:
        return "Poor"
    return "Critical"


def build_pillars(collected: dict, llm_scores: dict | None = None) -> dict[str, CategoryScore]:
    """Turn raw collector categories into the six GEO pillars.

    `collected` keys expected (any may be missing):
      technical, crawler_access, llms_txt, core_web_vitals, schema,
      citability, eeat, brand_authority, platform_optimization
    """
    llm = llm_scores or {}
    pillars: dict[str, CategoryScore] = {}

    # Technical pillar = foundations + crawler access + llms.txt + CWV.
    tech_parts = []
    if "technical" in collected:
        tech_parts.append((collected["technical"], 55.0))
    if "crawler_access" in collected:
        tech_parts.append((collected["crawler_access"], 25.0))
    if "core_web_vitals" in collected:
        tech_parts.append((collected["core_web_vitals"], 15.0))
    if "llms_txt" in collected:
        tech_parts.append((collected["llms_txt"], 5.0))
    if tech_parts:
        pillars["technical"] = _merge_categories("technical", "Technical GEO", tech_parts)

    # Schema pillar — direct.
    if "schema" in collected:
        pillars["schema"] = collected["schema"]

    # Citability — engine structural signals + LLM judgment signals.
    if "citability" in collected:
        pillars["citability"] = _apply_llm(collected["citability"], llm.get("citability"))

    # E-E-A-T — engine trust signals + LLM judgment signals.
    if "eeat" in collected:
        pillars["eeat"] = _apply_llm(collected["eeat"], llm.get("eeat"))

    # Brand Authority — LLM-only (off-site). Engine cannot measure it.
    if "brand_authority" in collected:
        pillars["brand_authority"] = _apply_llm(collected["brand_authority"], llm.get("brand_authority"))
    elif llm.get("brand_authority_score") is not None:
        pillars["brand_authority"] = category("brand_authority", "Brand Authority", [
            measured("brand_authority", "Off-site brand authority (LLM-assessed)", 100.0,
                     float(llm["brand_authority_score"]),
                     detail=llm.get("brand_authority_detail", "Assessed by LLM from off-site presence."))
        ])

    # Platform Optimization — LLM-only.
    if llm.get("platform_optimization_score") is not None:
        pillars["platform_optimization"] = category(
            "platform_optimization", "Platform Optimization", [
                measured("platform_optimization", "Per-platform readiness (LLM-assessed)", 100.0,
                         float(llm["platform_optimization_score"]),
                         detail=llm.get("platform_optimization_detail", "Assessed by LLM."))
            ])

    return pillars


def aggregate(collected: dict, business_type: str | None = None,
              llm_scores: dict | None = None) -> Composite:
    """Compute the composite GEO score from collected categories."""
    profile_name, weights = resolve_profile(business_type)
    pillars = build_pillars(collected, llm_scores)

    # Weighted composite over pillars that have a measured score.
    weighted_sum = 0.0
    weight_used = 0.0          # weight of pillars with any measured score
    confidence_num = 0.0       # weight * pillar-confidence
    total_weight = sum(weights[p] for p in PILLARS)
    pillar_out: dict = {}

    for p in PILLARS:
        w = weights.get(p, 0.0)
        cat = pillars.get(p)
        if cat is None:
            pillar_out[p] = {"score": None, "confidence": 0.0, "weight": round(w, 3),
                             "status": "absent"}
            continue
        sc = cat.score
        conf = cat.confidence
        entry = cat.to_dict()
        entry["weight"] = round(w, 3)
        if sc is not None:
            weighted_sum += sc * w
            weight_used += w
            confidence_num += w * conf
        pillar_out[p] = entry

    if weight_used <= 0:
        return Composite(None, "Insufficient Data", 0.0, None, profile_name,
                         pillar_out, {p: round(weights[p], 3) for p in PILLARS})

    score = round(weighted_sum / weight_used, 1)
    # Confidence = measured-weight coverage * average pillar confidence.
    coverage = weight_used / total_weight
    avg_pillar_conf = confidence_num / weight_used
    confidence = round(coverage * avg_pillar_conf, 3)

    # Band widens as confidence drops: +-(1-confidence)*15 points.
    half = round((1.0 - confidence) * 15.0, 1)
    band = (max(0.0, score - half), min(100.0, score + half))

    return Composite(score, rating_for(score), confidence, band, profile_name,
                     pillar_out, {p: round(weights[p], 3) for p in PILLARS})
