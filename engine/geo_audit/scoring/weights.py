"""Business-type weight profiles for the six GEO pillars.

The old skill applied one fixed weighting to every business, then only *talked*
about adjusting for type. That penalizes the SMBs this tool is meant to serve
(a local plumber should not carry the same 20% Brand-Authority expectation as a
global SaaS). These profiles actually change the math. Each profile is
normalized at use time, so the numbers below just need to express priorities.
"""

from __future__ import annotations

PILLARS = (
    "citability",
    "brand_authority",
    "eeat",
    "technical",
    "schema",
    "platform_optimization",
)

PROFILES: dict[str, dict[str, float]] = {
    # Generic / unknown — balanced.
    "default": {
        "citability": 25, "brand_authority": 20, "eeat": 20,
        "technical": 15, "schema": 10, "platform_optimization": 10,
    },
    # Local business — entity/schema/technical matter; off-site brand expectation lower.
    "local": {
        "citability": 20, "brand_authority": 15, "eeat": 20,
        "technical": 20, "schema": 15, "platform_optimization": 10,
    },
    # SaaS — content + community (Reddit/HN) + platform presence.
    "saas": {
        "citability": 25, "brand_authority": 20, "eeat": 15,
        "technical": 15, "schema": 10, "platform_optimization": 15,
    },
    # E-commerce — Product schema and technical performance dominate.
    "ecommerce": {
        "citability": 20, "brand_authority": 15, "eeat": 15,
        "technical": 20, "schema": 20, "platform_optimization": 10,
    },
    # Publisher — citability + author E-E-A-T + Article schema.
    "publisher": {
        "citability": 25, "brand_authority": 15, "eeat": 25,
        "technical": 15, "schema": 15, "platform_optimization": 5,
    },
    # Agency / professional services — expertise + case-study citability.
    "agency": {
        "citability": 25, "brand_authority": 20, "eeat": 20,
        "technical": 15, "schema": 10, "platform_optimization": 10,
    },
}

# Accepted aliases -> canonical profile key.
ALIASES = {
    "local business": "local", "localbusiness": "local", "restaurant": "local",
    "service": "local", "services": "agency", "professional services": "agency",
    "software": "saas", "b2b saas": "saas", "saas company": "saas",
    "store": "ecommerce", "shop": "ecommerce", "e-commerce": "ecommerce",
    "ecom": "ecommerce", "blog": "publisher", "media": "publisher",
    "news": "publisher", "consultancy": "agency", "consulting": "agency",
}


def resolve_profile(business_type: str | None) -> tuple[str, dict[str, float]]:
    """Return (profile_name, normalized_weights summing to 1.0)."""
    key = (business_type or "default").strip().lower()
    key = ALIASES.get(key, key)
    if key not in PROFILES:
        key = "default"
    raw = PROFILES[key]
    total = sum(raw.values()) or 1.0
    norm = {p: raw[p] / total for p in PILLARS}
    return key, norm
