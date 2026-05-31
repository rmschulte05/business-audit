"""AI crawler access collector — fully deterministic.

Fetches robots.txt and computes, per AI crawler, whether the site allows it.
This is the most reproducible GEO signal there is: the same robots.txt always
yields the same access map. Replaces the LLM "assess crawler access" guesswork.

Crawler reference is kept current with the geo-crawlers skill (early 2026).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..evidence import Signal, category, errored, measured
from ..http_client import HttpResult, fetch, origin

# (user_agent_token, operator, tier) — tier 1 = critical AI-search surfaces.
AI_CRAWLERS: list[tuple[str, str, int]] = [
    ("GPTBot", "OpenAI", 1),
    ("OAI-SearchBot", "OpenAI", 1),
    ("ChatGPT-User", "OpenAI", 1),
    ("ClaudeBot", "Anthropic", 1),
    ("PerplexityBot", "Perplexity", 1),
    ("Google-Extended", "Google", 2),
    ("GoogleOther", "Google", 2),
    ("Applebot-Extended", "Apple", 2),
    ("Amazonbot", "Amazon", 2),
    ("FacebookBot", "Meta", 2),
]

# Crawlers many sites intentionally block; not counted as a penalty.
OPTIONAL_BLOCK = {"Bytespider", "CCBot", "anthropic-ai", "cohere-ai"}


@dataclass(frozen=True)
class _Group:
    agents: list[str]
    disallows: list[str]
    allows: list[str]


def _parse_robots(text: str) -> list[_Group]:
    """Parse robots.txt into User-agent groups with their rules."""
    groups: list[_Group] = []
    cur_agents: list[str] = []
    cur_dis: list[str] = []
    cur_allow: list[str] = []
    expecting_agent = False

    def flush():
        nonlocal cur_agents, cur_dis, cur_allow
        if cur_agents:
            groups.append(_Group(cur_agents[:], cur_dis[:], cur_allow[:]))
        cur_agents, cur_dis, cur_allow = [], [], []

    for raw in (text or "").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, _, value = line.partition(":")
        field = field.strip().lower()
        value = value.strip()
        if field == "user-agent":
            if not expecting_agent and (cur_dis or cur_allow):
                flush()
            cur_agents.append(value)
            expecting_agent = True
        elif field == "disallow":
            cur_dis.append(value)
            expecting_agent = False
        elif field == "allow":
            cur_allow.append(value)
            expecting_agent = False
    flush()
    return groups


def _group_for(agent: str, groups: list[_Group]) -> _Group | None:
    """Return the most specific matching group for an agent token, or wildcard."""
    agent_low = agent.lower()
    specific = None
    wildcard = None
    for g in groups:
        for a in g.agents:
            al = a.strip().lower()
            if al == "*":
                wildcard = g
            elif al and al in agent_low:
                specific = g
    return specific or wildcard


def _access(agent: str, groups: list[_Group]) -> str:
    """'allowed', 'blocked', or 'not_mentioned' for the site root."""
    g = _group_for(agent, groups)
    if g is None:
        return "not_mentioned"
    # Site-wide block is "Disallow: /" with no overriding root Allow.
    blocks_root = any(d.strip() == "/" for d in g.disallows)
    allows_root = any(a.strip() in ("/", "") for a in g.allows)
    if blocks_root and not allows_root:
        return "blocked"
    # A bare "Disallow:" (empty) means allow-all.
    return "allowed"


def collect(url: str, robots: HttpResult | None = None):
    """Return (CategoryScore, raw_dict). robots may be pre-fetched."""
    robots_url = origin(url) + "/robots.txt"
    if robots is None:
        robots = fetch(robots_url)

    signals: list[Signal] = []
    raw: dict = {"robots_url": robots_url}

    if robots is None or (not robots.ok and robots.status not in (401, 403)):
        # No robots.txt (404/unreachable) means NOTHING is blocked → max access.
        if robots is not None and robots.status == 404:
            access_map = {a: "not_mentioned" for a, _, _ in AI_CRAWLERS}
            raw["robots_status"] = 404
            raw["note"] = "No robots.txt (404): all crawlers implicitly allowed."
        else:
            err = robots.error if robots else "no result"
            raw["robots_status"] = robots.status if robots else None
            raw["error"] = err
            cat = category(
                "crawler_access",
                "AI Crawler Access",
                [errored("robots_fetch", "Fetch robots.txt", 100.0,
                         detail=f"Could not fetch robots.txt: {err}")],
            )
            return cat, raw
    else:
        groups = _parse_robots(robots.body)
        access_map = {a: _access(a, groups) for a, _, _ in AI_CRAWLERS}
        raw["robots_status"] = robots.status
        raw["robots_bytes"] = len(robots.body)

    raw["access_map"] = access_map

    tier1 = [a for a, _, t in AI_CRAWLERS if t == 1]
    tier2 = [a for a, _, t in AI_CRAWLERS if t == 2]
    t1_ok = [a for a in tier1 if access_map.get(a) != "blocked"]
    t2_ok = [a for a in tier2 if access_map.get(a) != "blocked"]

    # Tier 1 access — 50 points, proportional to allowed crawlers.
    signals.append(measured(
        "tier1_access", "Tier-1 AI crawlers allowed (ChatGPT/Claude/Perplexity)",
        50.0, 50.0 * len(t1_ok) / len(tier1),
        value=f"{len(t1_ok)}/{len(tier1)}",
        detail=f"Allowed: {', '.join(t1_ok) or 'none'}",
        evidence="; ".join(f"{a}={access_map[a]}" for a in tier1),
        recommendation=(
            "" if len(t1_ok) == len(tier1)
            else "Allow all Tier-1 AI crawlers in robots.txt — blocking them removes "
                 "you from ChatGPT/Claude/Perplexity answers."
        ),
    ))
    # Tier 2 access — 25 points.
    signals.append(measured(
        "tier2_access", "Tier-2 AI crawlers allowed (Google-Extended/Apple/Meta/Amazon)",
        25.0, 25.0 * len(t2_ok) / len(tier2),
        value=f"{len(t2_ok)}/{len(tier2)}",
        evidence="; ".join(f"{a}={access_map[a]}" for a in tier2),
        recommendation=(
            "" if len(t2_ok) == len(tier2)
            else "Allow Tier-2 AI crawlers to appear in Gemini/Apple Intelligence/Meta AI."
        ),
    ))
    # No blanket block of all bots — 15 points.
    groups2 = _parse_robots(robots.body) if robots and robots.ok else []
    wildcard = _group_for("*", groups2)
    blanket = bool(wildcard and any(d.strip() == "/" for d in wildcard.disallows)
                   and not any(a.strip() in ("/", "") for a in wildcard.allows))
    signals.append(measured(
        "no_blanket_block", "No blanket 'Disallow: /' for all user-agents",
        15.0, 0.0 if blanket else 15.0,
        value=not blanket,
        detail="A site-wide Disallow blocks every crawler including AI search.",
        recommendation="Remove 'User-agent: * / Disallow: /'." if blanket else "",
    ))
    # Sitemap referenced — 10 points (helps AI discovery).
    has_sitemap = bool(re.search(r"(?im)^\s*sitemap:\s*\S+", robots.body or "")) if robots else False
    signals.append(measured(
        "sitemap_in_robots", "Sitemap referenced in robots.txt",
        10.0, 10.0 if has_sitemap else 0.0,
        value=has_sitemap,
        recommendation="Add 'Sitemap: https://<domain>/sitemap.xml' to robots.txt." if not has_sitemap else "",
    ))

    cat = category("crawler_access", "AI Crawler Access", signals)
    return cat, raw
