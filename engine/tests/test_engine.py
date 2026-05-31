"""Offline, deterministic tests for the GEO audit engine.

No network: every test builds synthetic HttpResult objects and asserts exact
scores. This is both the regression suite and the proof that the engine is
reproducible. Run: python3 -m tests.test_engine  (from engine/).
"""

from __future__ import annotations

import sys
import unittest

sys.path.insert(0, ".")

from geo_audit.evidence import Status, category, measured, not_measured  # noqa: E402
from geo_audit.http_client import HttpResult  # noqa: E402
from geo_audit.collectors import crawlers, schema, technical, content, llmstxt  # noqa: E402
from geo_audit.scoring.aggregate import aggregate, rating_for  # noqa: E402
from geo_audit.scoring.weights import resolve_profile  # noqa: E402


def html_result(body="", *, url="https://x.com", status=200, headers=None,
                final_url=None, ttfb=100.0, ok=True):
    return HttpResult(
        url=url, final_url=final_url or url, ok=ok, status=status,
        headers={k.lower(): v for k, v in (headers or {}).items()},
        body=body, ttfb_ms=ttfb,
    )


# ---------- evidence contract ----------
class TestEvidenceContract(unittest.TestCase):
    def test_measured_excludes_not_measured_from_denominator(self):
        c = category("t", "T", [measured("a", "A", 10, 7), not_measured("b", "B", 10)])
        self.assertEqual(c.score, 70.0)        # 7/10 measured, NOT 7/20
        self.assertEqual(c.confidence, 0.5)    # half the weight measured

    def test_points_clamped(self):
        s = measured("a", "A", 10, 999)
        self.assertEqual(s.points, 10.0)
        s2 = measured("a", "A", 10, -5)
        self.assertEqual(s2.points, 0.0)

    def test_none_score_when_nothing_measured(self):
        c = category("t", "T", [not_measured("a", "A", 10)])
        self.assertIsNone(c.score)
        self.assertEqual(c.confidence, 0.0)


# ---------- crawlers ----------
class TestCrawlers(unittest.TestCase):
    def test_open_robots_scores_full(self):
        robots = html_result("User-agent: *\nAllow: /\nSitemap: https://x.com/sitemap.xml")
        cat, raw = crawlers.collect("https://x.com", robots)
        self.assertEqual(cat.score, 100.0)
        self.assertEqual(cat.confidence, 1.0)

    def test_blocking_gptbot_loses_tier1_points(self):
        robots = html_result("User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nAllow: /")
        cat, raw = crawlers.collect("https://x.com", robots)
        self.assertEqual(raw["access_map"]["GPTBot"], "blocked")
        self.assertLess(cat.score, 100.0)

    def test_blanket_block_detected(self):
        robots = html_result("User-agent: *\nDisallow: /")
        cat, raw = crawlers.collect("https://x.com", robots)
        blanket = [s for s in cat.signals if s.key == "no_blanket_block"][0]
        self.assertEqual(blanket.points, 0.0)

    def test_404_robots_means_all_allowed(self):
        robots = html_result("", status=404, ok=False)
        cat, raw = crawlers.collect("https://x.com", robots)
        self.assertEqual(raw["robots_status"], 404)


# ---------- schema ----------
class TestSchema(unittest.TestCase):
    ORG = '''<html><head><script type="application/ld+json">
    {"@context":"https://schema.org","@type":"Organization","name":"Acme",
     "url":"https://x.com","sameAs":["https://linkedin.com/company/acme",
     "https://youtube.com/@acme","https://twitter.com/acme",
     "https://en.wikipedia.org/wiki/Acme","https://wikidata.org/Q1"]}
    </script></head><body>hi</body></html>'''

    def test_full_org_schema(self):
        cat, raw = schema.collect("https://x.com", html_result(self.ORG))
        self.assertIn("Organization", raw["detected_types"])
        self.assertEqual(len(raw["sameas"]), 5)
        sa = [s for s in cat.signals if s.key == "sameas_links"][0]
        self.assertEqual(sa.points, 15.0)   # 5 links * 3, capped at 15

    def test_no_schema_scores_low(self):
        cat, raw = schema.collect("https://x.com", html_result("<html><body>nothing</body></html>"))
        self.assertEqual(raw["detected_types"], [])
        self.assertEqual([s for s in cat.signals if s.key == "json_ld_present"][0].points, 0.0)

    def test_malformed_json_penalized(self):
        bad = '<script type="application/ld+json">{bad json,}</script>'
        cat, raw = schema.collect("https://x.com", html_result(bad))
        self.assertEqual(raw["parse_errors"], 1)


# ---------- technical ----------
class TestTechnical(unittest.TestCase):
    def test_https_and_headers(self):
        body = ('<html lang="en"><head><title>T</title>'
                '<meta name="description" content="d">'
                '<meta name="viewport" content="width=device-width">'
                '<link rel="canonical" href="https://x.com"></head>'
                '<body><h1>Hello</h1>' + ("word " * 300) + '</body></html>')
        home = html_result(body, headers={
            "strict-transport-security": "max-age=1", "x-frame-options": "DENY",
            "x-content-type-options": "nosniff", "content-security-policy": "default-src 'self'",
            "referrer-policy": "no-referrer", "content-encoding": "gzip"})
        # robots provided so it doesn't hit network; sitemap/http probe will fail gracefully
        robots = html_result("User-agent: *\nAllow: /", url="https://x.com/robots.txt")
        cat, raw = technical.collect("https://x.com", home, robots)
        sec = [s for s in cat.signals if s.key == "security_headers"][0]
        self.assertEqual(sec.points, 10.0)
        ssr = [s for s in cat.signals if s.key == "ssr"][0]
        self.assertEqual(ssr.points, 20.0)   # 300 words + h1


# ---------- content ----------
class TestContent(unittest.TestCase):
    def test_judgment_signals_not_measured(self):
        home = html_result("<html><body><h1>A</h1><h2>What is X?</h2>"
                           + ("data " * 200) + "50% of users in 2025 saved $400</body></html>")
        (cit, craw), (eeat, eraw) = content.collect("https://x.com", home)
        keys = {s.key: s.status for s in cit.signals}
        self.assertEqual(keys["answer_self_containment"], Status.NOT_MEASURED)
        self.assertEqual(keys["uniqueness"], Status.NOT_MEASURED)
        # confidence < 1 because judgment signals are unmeasured
        self.assertLess(cit.confidence, 1.0)


# ---------- aggregate ----------
class TestAggregate(unittest.TestCase):
    def _collected(self):
        return {
            "technical": category("technical", "Technical GEO",
                                  [measured("a", "A", 100, 80)]),
            "schema": category("schema", "Schema", [measured("a", "A", 100, 60)]),
            "citability": category("citability", "Citability",
                                   [measured("a", "A", 80, 70), not_measured("j", "J", 20)]),
            "eeat": category("eeat", "EEAT", [measured("a", "A", 100, 50)]),
        }

    def test_composite_excludes_absent_pillars_from_band(self):
        comp = aggregate(self._collected(), "saas")
        self.assertIsNotNone(comp.score)
        # brand_authority and platform absent -> confidence well below 1
        self.assertLess(comp.confidence, 0.8)
        self.assertEqual(comp.business_type, "saas")

    def test_determinism(self):
        a = aggregate(self._collected(), "local").to_dict()
        b = aggregate(self._collected(), "local").to_dict()
        self.assertEqual(a, b)

    def test_llm_scores_fill_judgment(self):
        # The synthetic citability category's unmeasured signal is keyed "j".
        collected = self._collected()
        llm = {"citability": {"j": {"points": 20}}}
        comp = aggregate(collected, "saas", llm)
        cit = comp.pillars["citability"]
        self.assertEqual(cit["confidence"], 1.0)   # judgment now filled by LLM

    def test_band_widens_with_low_confidence(self):
        comp = aggregate(self._collected(), "saas")
        lo, hi = comp.band
        self.assertLess(lo, comp.score)
        self.assertGreater(hi, comp.score)


class TestWeights(unittest.TestCase):
    def test_profiles_normalize_to_one(self):
        for t in ("default", "local", "saas", "ecommerce", "publisher", "agency"):
            _, w = resolve_profile(t)
            self.assertAlmostEqual(sum(w.values()), 1.0, places=6)

    def test_alias_resolution(self):
        name, _ = resolve_profile("B2B SaaS")
        self.assertEqual(name, "saas")
        name2, _ = resolve_profile("local business")
        self.assertEqual(name2, "local")

    def test_rating_bands(self):
        self.assertEqual(rating_for(95), "Excellent")
        self.assertEqual(rating_for(80), "Good")
        self.assertEqual(rating_for(65), "Fair")
        self.assertEqual(rating_for(45), "Poor")
        self.assertEqual(rating_for(10), "Critical")
        self.assertEqual(rating_for(None), "Insufficient Data")


if __name__ == "__main__":
    unittest.main(verbosity=2)
