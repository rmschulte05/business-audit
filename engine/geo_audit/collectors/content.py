"""Content collector — measures the COUNTABLE parts of Citability and E-E-A-T.

This is the honest boundary of the engine. Some content signals are objectively
measurable (word count, heading hierarchy, statistic density, question headings,
publication dates, trust-page presence). Others are genuine judgments (depth of
expertise, originality, first-hand experience) — those are emitted as
NOT_MEASURED so the LLM skill supplies them WITH this evidence, and confidence
honestly reflects how much was machine-measured.

Returns two CategoryScores: 'citability' and 'eeat'.
"""

from __future__ import annotations

import re

from ..evidence import Signal, category, measured, not_measured
from ..html_utils import headings, visible_text
from ..http_client import HttpResult, fetch, origin

# A statistic: percentage, money, explicit count, year, or multiplier.
STAT_RE = re.compile(
    r"(\b\d{1,3}(?:,\d{3})+\b|\b\d+(?:\.\d+)?\s?%|\$\s?\d|\b\d{4}\b|\b\d+(?:\.\d+)?x\b|\b\d+(?:\.\d+)?\s?(?:million|billion|k\b))",
    re.IGNORECASE,
)
DEFINITION_RE = re.compile(r"\b(is|are|refers to|means)\b", re.IGNORECASE)
DATE_RE = re.compile(
    r"\b(20\d{2}|19\d{2})\b|\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}",
    re.IGNORECASE,
)


def _page_body(page) -> str:
    if isinstance(page, dict):
        return page.get("body", "") or ""
    return getattr(page, "body", "") or ""


def _page_url(page) -> str:
    if isinstance(page, dict):
        return page.get("url", "") or page.get("final_url", "") or ""
    return getattr(page, "final_url", "") or getattr(page, "url", "") or ""


def _citability_page_metrics(body: str) -> dict:
    """Compute the countable citability metrics for one page's HTML body."""
    text = visible_text(body)
    words = text.split()
    wc = len(words)
    hs = headings(body)
    all_headings = [h for lvl in hs.values() for h in lvl]
    q_headings = [h for h in all_headings if "?" in h]
    stats = STAT_RE.findall(text)
    return {
        "word_count": wc,
        "headings": hs,
        "all_headings": all_headings,
        "q_headings": q_headings,
        "stats": stats,
    }


def _citability_page_score(m: dict) -> float:
    """Deterministic 0-100 score for one page over the measured citability rules.

    Mirrors the homepage signal math (structure 25 + question_headings 15 +
    stat_density 20 + content_volume 10 = 70 measured max, scaled to 100).
    """
    hs = m["headings"]
    wc = m["word_count"]
    h1 = len(hs["h1"])
    struct_pts = 0.0
    if h1 == 1:
        struct_pts += 10.0
    elif h1 >= 1:
        struct_pts += 5.0
    if len(hs["h2"]) >= 2:
        struct_pts += 10.0
    elif len(hs["h2"]) >= 1:
        struct_pts += 5.0
    if m["all_headings"]:
        struct_pts += 5.0
    q_pts = min(15.0, 5.0 * len(m["q_headings"]))
    density = (len(m["stats"]) / (wc / 500.0)) if wc > 0 else 0.0
    if density >= 5:
        stat_pts = 20.0
    elif density >= 3:
        stat_pts = 15.0
    elif density >= 1:
        stat_pts = 10.0
    elif density > 0:
        stat_pts = 5.0
    else:
        stat_pts = 0.0
    if wc >= 500:
        suff = 10.0
    elif wc >= 250:
        suff = 6.0
    elif wc >= 100:
        suff = 3.0
    else:
        suff = 0.0
    earned = struct_pts + q_pts + stat_pts + suff
    return round(earned / 70.0 * 100.0, 1)


def _median(values: list[float]) -> float:
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0


# A page is "well-cited" if its deterministic citability score clears this bar.
CITABILITY_COVERAGE_THRESHOLD = 60.0


def _citability(home: HttpResult, inner_pages: list | None = None) -> "tuple":
    text = visible_text(home.body)
    words = text.split()
    wc = len(words)
    hs = headings(home.body)
    all_headings = [h for lvl in hs.values() for h in lvl]
    q_headings = [h for h in all_headings if "?" in h]
    stats = STAT_RE.findall(text)
    raw = {
        "word_count": wc,
        "heading_count": len(all_headings),
        "question_headings": len(q_headings),
        "stat_count": len(stats),
    }
    signals: list[Signal] = []

    # Structural readability (countable) — heading hierarchy. 25 of citability.
    h1 = len(hs["h1"])
    has_hierarchy = h1 >= 1 and len(hs["h2"]) >= 1
    struct_pts = 0.0
    if h1 == 1:
        struct_pts += 10.0
    elif h1 >= 1:
        struct_pts += 5.0
    if len(hs["h2"]) >= 2:
        struct_pts += 10.0
    elif len(hs["h2"]) >= 1:
        struct_pts += 5.0
    if all_headings:
        struct_pts += 5.0
    signals.append(measured(
        "structure", "Heading hierarchy (H1/H2 structure)",
        25.0, struct_pts, value=f"{h1} H1, {len(hs['h2'])} H2",
        evidence=f"headings: {all_headings[:5]}",
        recommendation="" if struct_pts >= 25 else
        "Use exactly one H1 and multiple descriptive H2s so AI can segment content.",
    ))

    # Question-based headings — map directly to AI queries. 15.
    q_pts = min(15.0, 5.0 * len(q_headings))
    signals.append(measured(
        "question_headings", "Question-style headings (match AI queries)",
        15.0, q_pts, value=len(q_headings),
        evidence=f"{q_headings[:3]}",
        recommendation="" if q_pts >= 15 else
        "Add question-form headings ('What is X?', 'How does Y work?').",
    ))

    # Statistical density — 20. Countable per 500 words.
    if wc > 0:
        density = len(stats) / (wc / 500.0)
    else:
        density = 0.0
    raw["stat_density_per_500w"] = round(density, 2)
    if density >= 5:
        stat_pts = 20.0
    elif density >= 3:
        stat_pts = 15.0
    elif density >= 1:
        stat_pts = 10.0
    elif density > 0:
        stat_pts = 5.0
    else:
        stat_pts = 0.0
    signals.append(measured(
        "stat_density", "Statistical density (specific numbers/data)",
        20.0, stat_pts, value=f"{round(density,1)}/500 words",
        evidence=f"examples: {stats[:5]}",
        recommendation="" if stat_pts >= 15 else
        "Add specific statistics, dollar amounts, and dates — AI cites fact-rich passages.",
    ))

    # Content sufficiency — 10. Homepages need enough extractable text.
    if wc >= 500:
        suff = 10.0
    elif wc >= 250:
        suff = 6.0
    elif wc >= 100:
        suff = 3.0
    else:
        suff = 0.0
    signals.append(measured(
        "content_volume", "Sufficient extractable text on the page",
        10.0, suff, value=wc,
        recommendation="" if suff >= 10 else
        "Add substantive copy (500+ words of real content AI can extract).",
    ))

    # Multi-page coverage — fraction of crawled content pages that are well-cited.
    # Only emitted when inner pages were actually crawled, so the homepage-only
    # signal set (and thus the score/confidence) is byte-identical at max_pages=1.
    pages_for_coverage = inner_pages or []
    if pages_for_coverage:
        home_metrics = _citability_page_metrics(home.body or "")
        page_scores = [_citability_page_score(home_metrics)]
        per_page = [{"url": _page_url(home) or home.final_url,
                     "score": page_scores[0]}]
        for page in pages_for_coverage:
            m = _citability_page_metrics(_page_body(page))
            sc = _citability_page_score(m)
            page_scores.append(sc)
            per_page.append({"url": _page_url(page), "score": sc})
        raw["page_scores"] = per_page
        raw["median_page_score"] = _median(page_scores)
        above = sum(1 for s in page_scores if s >= CITABILITY_COVERAGE_THRESHOLD)
        coverage_frac = above / len(page_scores)
        signals.append(measured(
            "citability_coverage",
            "Site-wide citability coverage (pages with strong answer content)",
            10.0, round(10.0 * coverage_frac, 2),
            value=f"{above}/{len(page_scores)} pages >= {int(CITABILITY_COVERAGE_THRESHOLD)}",
            detail=f"Median page citability score: {raw['median_page_score']}.",
            evidence="; ".join(f"{p['url']}={p['score']}" for p in per_page[:6]),
            recommendation="" if coverage_frac >= 0.6 else
            "Raise citability across more pages (headings, stats, answer-first copy), "
            "not just the homepage — AI cites deep pages.",
        ))

    # JUDGMENT signals — left to the LLM, marked NOT_MEASURED (lower confidence).
    signals.append(not_measured(
        "answer_self_containment", "Answer-first / self-contained passages (judged)",
        20.0,
        detail="Requires semantic judgment of whether passages stand alone as answers.",
        recommendation="LLM reviewer scores this from the page text supplied as evidence.",
    ))
    signals.append(not_measured(
        "uniqueness", "Original data / unique insight (judged)",
        10.0,
        detail="Requires judging originality vs. derivative content.",
        recommendation="LLM reviewer scores this from the page text.",
    ))
    return category("citability", "AI Citability", signals), raw


def _has_author_in(body: str) -> bool:
    low = body.lower()
    has_author = bool(re.search(r'\b(author|by\s+[A-Z][a-z]+|rel=["\']author["\'])', body))
    return has_author or '"author"' in low or "byline" in low


def _has_date_in(body: str) -> bool:
    low = body.lower()
    text = visible_text(body)
    return bool(DATE_RE.search(text)) or "datepublished" in low or "datemodified" in low


def _eeat(url: str, home: HttpResult, inner_pages: list | None = None) -> "tuple":
    body = home.body or ""
    low = body.lower()
    text = visible_text(body)
    base = origin(url)
    raw: dict = {}
    signals: list[Signal] = []

    # Trust signals are site-wide: a privacy/terms/contact link found on ANY
    # crawled page counts. The homepage low/text are the baseline; inner-page
    # bodies are folded in via OR. With no inner pages this equals today's math.
    pages = inner_pages or []
    low_all = low
    text_all = text
    for page in pages:
        pb = _page_body(page)
        low_all += "\n" + pb.lower()
        text_all += "\n" + visible_text(pb)

    # Trustworthiness — these are largely countable. 40 total.
    has_https = home.final_url.startswith("https://")
    # Privacy / terms links
    has_privacy = bool(re.search(r"privacy[\s\-]?policy", low_all) or "/privacy" in low_all)
    has_terms = bool(re.search(r"terms[\s\-]?(of|&)?[\s\-]?(service|use|conditions)", low_all) or "/terms" in low_all)
    # Contact signals
    has_email = bool(re.search(r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}", low_all))
    has_phone = bool(re.search(r"(\+?\d[\d\s().\-]{7,}\d)", text_all))
    has_contact_page = "/contact" in low_all or "contact us" in low_all

    trust_items = [
        (has_https, 8, "HTTPS"),
        (has_privacy, 8, "Privacy policy link"),
        (has_terms, 6, "Terms link"),
        (has_email or has_contact_page, 10, "Contact method"),
        (has_phone, 8, "Phone number"),
    ]
    trust_pts = sum(pts for ok, pts, _ in trust_items if ok)
    raw["trust"] = {name: ok for ok, _, name in trust_items}
    signals.append(measured(
        "trust_signals", "Trust signals (HTTPS, privacy, terms, contact)",
        40.0, trust_pts,
        value=f"{sum(1 for ok,_,_ in trust_items if ok)}/{len(trust_items)}",
        evidence=", ".join(name for ok, _, name in trust_items if ok) or "none",
        recommendation="" if trust_pts == 40 else
        "Add missing trust signals: " + ", ".join(
            name for ok, _, name in trust_items if not ok) + ".",
    ))

    # Author / byline presence — detectable. 10.
    # Multi-page: fraction of crawled pages with an author byline (homepage + inner).
    # Single-page: reduces to the original homepage-only binary (1/1 -> 10 or 0).
    author_flags = [_has_author_in(body)] + [_has_author_in(_page_body(p)) for p in pages]
    author_frac = sum(1 for f in author_flags if f) / len(author_flags)
    has_author = author_flags[0]
    author_pts = round(10.0 * author_frac, 2)
    raw["author_pages"] = f"{sum(1 for f in author_flags if f)}/{len(author_flags)}"
    signals.append(measured(
        "authorship", "Author attribution detectable",
        10.0, author_pts,
        value=has_author if len(author_flags) == 1 else raw["author_pages"],
        recommendation="" if author_frac >= 1.0 else
        "Add visible author bylines linking to author bio pages (strong E-E-A-T).",
    ))

    # Freshness — date presence is detectable (quality of recency is judged). 10.
    # Multi-page: fraction of crawled pages exhibiting a publish/update date.
    date_flags = [_has_date_in(body)] + [_has_date_in(_page_body(p)) for p in pages]
    date_frac = sum(1 for f in date_flags if f) / len(date_flags)
    has_date = date_flags[0]
    date_pts = round(10.0 * date_frac, 2)
    raw["date_pages"] = f"{sum(1 for f in date_flags if f)}/{len(date_flags)}"
    signals.append(measured(
        "date_present", "Publication / update date present",
        10.0, date_pts,
        value=has_date if len(date_flags) == 1 else raw["date_pages"],
        recommendation="" if date_frac >= 1.0 else
        "Show visible publish/updated dates and datePublished/dateModified in schema.",
    ))

    # About page — detectable. 5.
    about = fetch(base + "/about", want_body=False)
    has_about = bool(about.ok and about.status == 200) or "/about" in low
    signals.append(measured(
        "about_page", "About page present",
        5.0, 5.0 if has_about else 0.0, value=has_about,
        recommendation="" if has_about else "Add an About page with team credentials.",
    ))

    # JUDGMENT signals — left to the LLM.
    signals.append(not_measured(
        "expertise_depth", "Expertise & technical depth (judged)", 20.0,
        detail="Requires judging accuracy and depth of subject-matter treatment.",
        recommendation="LLM reviewer scores from page text + author credentials.",
    ))
    signals.append(not_measured(
        "experience", "First-hand experience signals (judged)", 5.0,
        detail="Requires judging case studies / first-person accounts.",
    ))
    return category("eeat", "Content E-E-A-T", signals), raw


def collect(url: str, home: HttpResult, inner_pages: list | None = None):
    """Return ((citability_cat, raw), (eeat_cat, raw)).

    inner_pages: optional list of additional fetched pages (dicts with
    {"url","body"} or HttpResult-like objects). When empty (max_pages=1) the
    output is byte-identical to the homepage-only behavior.
    """
    cit_cat, cit_raw = _citability(home, inner_pages)
    eeat_cat, eeat_raw = _eeat(url, home, inner_pages)
    return (cit_cat, cit_raw), (eeat_cat, eeat_raw)
