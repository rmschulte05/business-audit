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


def _citability(home: HttpResult) -> "tuple":
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


def _eeat(url: str, home: HttpResult) -> "tuple":
    body = home.body or ""
    low = body.lower()
    text = visible_text(body)
    base = origin(url)
    raw: dict = {}
    signals: list[Signal] = []

    # Trustworthiness — these are largely countable. 40 total.
    has_https = home.final_url.startswith("https://")
    # Privacy / terms links
    has_privacy = bool(re.search(r"privacy[\s\-]?policy", low) or "/privacy" in low)
    has_terms = bool(re.search(r"terms[\s\-]?(of|&)?[\s\-]?(service|use|conditions)", low) or "/terms" in low)
    # Contact signals
    has_email = bool(re.search(r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}", low))
    has_phone = bool(re.search(r"(\+?\d[\d\s().\-]{7,}\d)", text))
    has_contact_page = "/contact" in low or "contact us" in low

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
    has_author = bool(re.search(r'\b(author|by\s+[A-Z][a-z]+|rel=["\']author["\'])', body))
    has_author = has_author or '"author"' in low or "byline" in low
    signals.append(measured(
        "authorship", "Author attribution detectable",
        10.0, 10.0 if has_author else 0.0, value=has_author,
        recommendation="" if has_author else
        "Add visible author bylines linking to author bio pages (strong E-E-A-T).",
    ))

    # Freshness — date presence is detectable (quality of recency is judged). 10.
    has_date = bool(DATE_RE.search(text)) or "datepublished" in low or "datemodified" in low
    signals.append(measured(
        "date_present", "Publication / update date present",
        10.0, 10.0 if has_date else 0.0, value=has_date,
        recommendation="" if has_date else
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


def collect(url: str, home: HttpResult):
    """Return ((citability_cat, raw), (eeat_cat, raw))."""
    cit_cat, cit_raw = _citability(home)
    eeat_cat, eeat_raw = _eeat(url, home)
    return (cit_cat, cit_raw), (eeat_cat, eeat_raw)
