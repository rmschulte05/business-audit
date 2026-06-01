"""Offline, deterministic tests for the GEO audit engine.

No network: every test builds synthetic HttpResult objects and asserts exact
scores. This is both the regression suite and the proof that the engine is
reproducible. Run: python3 -m tests.test_engine  (from engine/).
"""

from __future__ import annotations

import json
import sys
import unittest

sys.path.insert(0, ".")

from geo_audit.evidence import Status, category, measured, not_measured  # noqa: E402
from geo_audit.http_client import HttpResult  # noqa: E402
from geo_audit.collectors import crawl, crawlers, schema, technical, content, llmstxt  # noqa: E402
from geo_audit.scoring.aggregate import aggregate, rating_for  # noqa: E402
from geo_audit.scoring.weights import resolve_profile  # noqa: E402
import geo_audit.run_audit as run_audit  # noqa: E402


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


# ---------- multi-page crawl: discover_pages ----------
class TestDiscoverPages(unittest.TestCase):
    HOME_LINKS = (
        '<html><body>'
        '<a href="/about">About</a>'
        '<a href="/pricing">Pricing</a>'
        '<a href="/blog/post-1">Post</a>'
        '<a href="/about/">About (dup w/ trailing slash)</a>'
        '<a href="https://other.com/x">offsite</a>'
        '<a href="/image.png">asset</a>'
        '<a href="https://x.com/contact">Contact</a>'
        '<a href="#frag">fragment-only</a>'
        '<a href="/secret">secret</a>'
        '</body></html>'
    )
    SITEMAP = (
        '<?xml version="1.0"?><urlset>'
        '<url><loc>https://x.com/docs/guide</loc></url>'
        '<url><loc>https://x.com/pricing</loc></url>'
        '<url><loc>https://x.com/random-page</loc></url>'
        '</urlset>'
    )

    def _inputs(self):
        home = html_result(self.HOME_LINKS, url="https://x.com",
                           final_url="https://x.com/")
        robots = html_result("User-agent: *\nDisallow: /secret\n"
                             "Sitemap: https://x.com/sitemap.xml")
        sitemap = html_result(self.SITEMAP)
        return home, robots, sitemap

    def test_homepage_always_first(self):
        home, robots, sitemap = self._inputs()
        pages = crawl.discover_pages("https://x.com", home, robots, sitemap, max_pages=6)
        self.assertEqual(pages[0], "https://x.com/")

    def test_max_pages_1_returns_homepage_only(self):
        home, robots, sitemap = self._inputs()
        pages = crawl.discover_pages("https://x.com", home, robots, sitemap, max_pages=1)
        self.assertEqual(pages, ["https://x.com/"])

    def test_dedupe_trailing_slash(self):
        home, robots, sitemap = self._inputs()
        pages = crawl.discover_pages("https://x.com", home, robots, sitemap, max_pages=10)
        about = [p for p in pages if p.endswith("/about")]
        self.assertEqual(len(about), 1)

    def test_respects_robots_disallow(self):
        home, robots, sitemap = self._inputs()
        pages = crawl.discover_pages("https://x.com", home, robots, sitemap, max_pages=10)
        self.assertTrue(all("/secret" not in p for p in pages))

    def test_excludes_offsite_and_assets(self):
        home, robots, sitemap = self._inputs()
        pages = crawl.discover_pages("https://x.com", home, robots, sitemap, max_pages=10)
        self.assertTrue(all("other.com" not in p for p in pages))
        self.assertTrue(all(not p.endswith(".png") for p in pages))

    def test_cap_respected(self):
        home, robots, sitemap = self._inputs()
        pages = crawl.discover_pages("https://x.com", home, robots, sitemap, max_pages=3)
        self.assertLessEqual(len(pages), 3)

    def test_deterministic_ordering(self):
        home, robots, sitemap = self._inputs()
        a = crawl.discover_pages("https://x.com", home, robots, sitemap, max_pages=6)
        b = crawl.discover_pages("https://x.com", home, robots, sitemap, max_pages=6)
        self.assertEqual(a, b)

    def test_high_value_paths_ranked_first(self):
        home, robots, sitemap = self._inputs()
        pages = crawl.discover_pages("https://x.com", home, robots, sitemap, max_pages=6)
        # about (rank 0) and pricing (rank 1) precede blog (rank 6) / contact (rank 8).
        idx = {p: i for i, p in enumerate(pages)}
        self.assertLess(idx["https://x.com/about"], idx["https://x.com/contact"])
        self.assertLess(idx["https://x.com/pricing"], idx["https://x.com/blog/post-1"])

    def test_sitemap_index_followed_one_level(self):
        home = html_result("<html><body></body></html>", url="https://x.com",
                           final_url="https://x.com/")
        index = html_result(
            '<?xml version="1.0"?><sitemapindex>'
            '<sitemap><loc>https://x.com/sitemap-pages.xml</loc></sitemap>'
            '</sitemapindex>')
        child = html_result(
            '<?xml version="1.0"?><urlset>'
            '<url><loc>https://x.com/docs/guide</loc></url>'
            '</urlset>')

        def fake_child(url, **kw):
            return child

        pages = crawl.discover_pages(
            "https://x.com", home, None, index, max_pages=5,
            fetch_sitemap_child=fake_child)
        self.assertIn("https://x.com/docs/guide", pages)


# ---------- multi-page crawl: schema union ----------
class TestSchemaUnion(unittest.TestCase):
    HOME = ('<html><head><script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"Organization",'
            '"name":"Acme","url":"https://x.com"}</script></head><body>hi</body></html>')
    INNER_PRODUCT = ('<html><head><script type="application/ld+json">'
                     '{"@type":"Product","name":"Widget","offers":{}}</script>'
                     '</head><body>p</body></html>')

    def test_inner_page_types_unioned(self):
        home = html_result(self.HOME)
        cat, raw = schema.collect(
            "https://x.com", home,
            inner_pages=[{"url": "https://x.com/p", "body": self.INNER_PRODUCT}])
        self.assertIn("Organization", raw["detected_types"])
        self.assertIn("Product", raw["detected_types"])  # found on inner page

    def test_union_is_superset_of_homepage(self):
        home = html_result(self.HOME)
        cat0, raw0 = schema.collect("https://x.com", home)
        cat1, raw1 = schema.collect(
            "https://x.com", home,
            inner_pages=[{"url": "https://x.com/p", "body": self.INNER_PRODUCT}])
        self.assertTrue(set(raw0["detected_types"]).issubset(set(raw1["detected_types"])))
        self.assertEqual(raw1["detected_types_homepage"], raw0["detected_types"])


# ---------- multi-page crawl: max_pages=1 PARITY ----------
class TestMaxPagesParity(unittest.TestCase):
    """Driving run() with max_pages=1 must reproduce homepage-only scores exactly."""

    HOME = ('<html lang="en"><head><title>Acme</title>'
            '<meta name="description" content="d">'
            '<meta name="viewport" content="width=device-width">'
            '<script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"Organization",'
            '"name":"Acme","url":"https://acme.test"}</script></head>'
            '<body><h1>Acme</h1><h2>What is Acme?</h2>' + ("word " * 400) +
            '50% in 2025 saved $400 privacy policy contact us</body></html>')

    def _fake_fetch(self, url, **kw):
        if url.endswith("/robots.txt"):
            return html_result("User-agent: *\nAllow: /", url=url)
        if url.endswith("/sitemap.xml"):
            return html_result(
                "<urlset><url><loc>https://acme.test/about</loc></url></urlset>",
                url=url)
        if url.endswith("/llms.txt") or url.endswith("/llms-full.txt"):
            return html_result("", url=url, status=404, ok=False)
        if url.startswith("http://"):
            return html_result("", url=url, final_url="https://acme.test/")
        if "/about" in url:
            return html_result(
                "<html><body><h1>About</h1>" + ("team " * 300) +
                " by Jane Doe 2025 author</body></html>", url=url)
        return html_result(self.HOME, url=url, final_url="https://acme.test/",
                           ttfb=120.0)

    def _patch_all(self):
        from geo_audit.collectors import (content as c, technical as t,
                                          schema as s, llmstxt as lt, psi as p,
                                          crawlers as cr, crawl as cw)
        self._orig = {}
        for mod in (run_audit, c, t, s, lt, p, cr, cw):
            if hasattr(mod, "fetch"):
                self._orig[mod] = mod.fetch
                mod.fetch = self._fake_fetch

    def _unpatch_all(self):
        for mod, fn in self._orig.items():
            mod.fetch = fn

    def test_max_pages_1_matches_homepage_only(self):
        self._patch_all()
        try:
            r1 = run_audit.run("https://acme.test", "saas", None, "2026-05-31",
                               True, max_pages=1)
        finally:
            self._unpatch_all()
        # Only the homepage is analyzed.
        self.assertEqual(r1["meta"]["pages_analyzed"], ["https://acme.test/"])
        # Composite contract preserved.
        comp = r1["composite"]
        self.assertEqual(sorted(comp.keys()),
                         sorted(["geo_score", "rating", "confidence", "score_band",
                                 "business_type", "weights", "pillars"]))
        self.assertEqual(
            sorted(comp["pillars"].keys()),
            sorted(["citability", "brand_authority", "eeat", "technical",
                    "schema", "platform_optimization"]))
        # Citability at max_pages=1 has NO multi-page coverage signal (parity).
        cit_keys = [s["key"] for s in comp["pillars"]["citability"]["signals"]]
        self.assertNotIn("citability_coverage", cit_keys)

    def test_max_pages_gt_1_finds_inner_pages_and_keeps_contract(self):
        self._patch_all()
        try:
            r1 = run_audit.run("https://acme.test", "saas", None, "2026-05-31",
                               True, max_pages=1)
            r8 = run_audit.run("https://acme.test", "saas", None, "2026-05-31",
                               True, max_pages=8)
        finally:
            self._unpatch_all()
        # Multi-page run analyzes more than the homepage.
        self.assertGreater(len(r8["meta"]["pages_analyzed"]), 1)
        analyzed = {p.rstrip("/") for p in r8["meta"]["pages_analyzed"]}
        self.assertIn("https://acme.test/about", analyzed)
        # New output fields present, composite contract unchanged.
        self.assertIn("pages", r8["raw"])
        self.assertEqual(sorted(r8["composite"].keys()), sorted(r1["composite"].keys()))
        # Site-wide schema is a superset of the homepage-only schema.
        self.assertTrue(
            set(r1["raw"]["schema"]["detected_types"]).issubset(
                set(r8["raw"]["schema"]["detected_types"])))


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


class TestInvariants(unittest.TestCase):
    """Invariants the composite must always satisfy (regression guards)."""

    def test_all_profiles_normalize_to_one(self):
        # Every business-type weight profile must normalize to 1.0 so the
        # weighted average is on a true 0-100 scale regardless of profile.
        for t in ("default", "local", "saas", "ecommerce", "publisher", "agency"):
            _, w = resolve_profile(t)
            self.assertAlmostEqual(sum(w.values()), 1.0, places=3,
                                   msg=f"profile {t} must sum to 1.0")

    def test_band_always_contains_score(self):
        # The headline confidence band must never exclude its own score —
        # including the realistic low-confidence case (an SMB whose off-site
        # pillars are unmeasured, like the rmit4you run).
        collected = {
            "citability": category("citability", "Citability",
                                   [measured("a", "A", 80, 0), not_measured("j", "J", 20)]),
            "eeat": category("eeat", "EEAT", [measured("a", "A", 100, 30)]),
            "technical": category("technical", "Technical", [measured("a", "A", 100, 50)]),
            "schema": category("schema", "Schema", [measured("a", "A", 100, 0)]),
        }
        comp = aggregate(collected, "agency")
        lo, hi = comp.band
        self.assertLessEqual(lo, comp.score)
        self.assertLessEqual(comp.score, hi)

    def test_band_narrows_at_full_confidence(self):
        # When every pillar is measured at full confidence, confidence hits 1.0
        # and the band collapses onto the score. platform_optimization is
        # LLM-only, so it is supplied via llm_scores (not `collected`).
        collected = {p: category(p, p, [measured("a", "A", 100, 70)])
                     for p in ("citability", "brand_authority", "eeat",
                               "technical", "schema")}
        comp = aggregate(collected, "saas",
                         {"platform_optimization_score": 70})
        self.assertEqual(comp.confidence, 1.0)
        self.assertEqual(comp.band[0], comp.band[1])


# ---------- standalone HTML report ----------
class TestHtmlReport(unittest.TestCase):
    """Offline tests for the deterministic, self-contained HTML renderer."""

    def _result(self):
        """A realistic result dict built from the engine (no network)."""
        collected = {
            "technical": category("technical", "Technical GEO",
                                  [measured("a", "A", 100, 80,
                                            recommendation="Add HSTS header.",
                                            evidence="missing: strict-transport-security")]),
            "schema": category("schema", "Schema", [measured("a", "A", 100, 60)]),
            "citability": category("citability", "Citability",
                                   [measured("a", "A", 80, 40,
                                             recommendation="Add a direct answer paragraph.",
                                             evidence="no <h2> question heading found"),
                                    not_measured("uniqueness", "Content uniqueness", 20)]),
            "eeat": category("eeat", "EEAT", [measured("a", "A", 100, 50)]),
        }
        return {
            "meta": {
                "url": "https://example.test",
                "final_url": "https://example.test/",
                "date": "2026-05-31",
                "engine_version": "2.0.0",
                "http_status": 200,
                "ttfb_ms": 120.0,
                "pages_analyzed": ["https://example.test/"],
            },
            "composite": aggregate(collected, "saas").to_dict(),
            "raw": {},
        }

    def _extract_embedded_json(self, html):
        import re
        m = re.search(
            r'<script type="application/json" id="geo-audit-data">(.*?)</script>',
            html, re.DOTALL)
        self.assertIsNotNone(m, "embedded JSON script block must be present")
        # Reverse the breakout-escaping done by the renderer before parsing.
        return json.loads(m.group(1).replace("<\\/", "</"))

    def _visible_part(self, html):
        """The human-readable HTML, excluding the embedded machine-readable JSON
        block (which legitimately contains JSON `null` and raw string data)."""
        marker = '<script type="application/json" id="geo-audit-data">'
        idx = html.find(marker)
        self.assertNotEqual(idx, -1, "data block must exist")
        return html[:idx]

    def test_returns_doctype_string(self):
        html = run_audit.render_html(self._result())
        self.assertIsInstance(html, str)
        self.assertTrue(html.startswith("<!"))

    def test_contains_score_and_rating(self):
        result = self._result()
        html = run_audit.render_html(result)
        comp = result["composite"]
        self.assertIn(str(int(round(comp["geo_score"]))), html)
        self.assertIn(comp["rating"], html)

    def test_embedded_json_roundtrips_to_same_score(self):
        result = self._result()
        html = run_audit.render_html(result)
        self.assertIn('<script type="application/json" id="geo-audit-data">', html)
        parsed = self._extract_embedded_json(html)
        self.assertEqual(parsed["composite"]["geo_score"],
                         result["composite"]["geo_score"])

    def test_null_score_renders_not_measured_and_never_literal_null(self):
        # Nothing measured -> composite geo_score is None and pillars are absent.
        result = {
            "meta": {"url": "https://empty.test", "date": "2026-05-31",
                     "engine_version": "2.0.0", "pages_analyzed": []},
            "composite": aggregate({}, "saas").to_dict(),
            "raw": {},
        }
        self.assertIsNone(result["composite"]["geo_score"])
        html = run_audit.render_html(result)
        visible = self._visible_part(html)
        self.assertIn("Not measured", visible)
        # The visible report never prints the literal null/None (the em dash is
        # used instead). The embedded JSON block legitimately contains JSON null.
        self.assertNotIn("null", visible)
        self.assertNotIn("None", visible)

    def test_no_template_tokens_left(self):
        html = run_audit.render_html(self._result())
        self.assertEqual(html.count("{" + "{"), 0)

    def test_deterministic(self):
        result = self._result()
        self.assertEqual(run_audit.render_html(result),
                         run_audit.render_html(result))

    def test_ttfb_jitter_does_not_change_embedded_artifact(self):
        # TTFB is the one sanctioned wall-clock signal. Two runs with the SAME
        # network evidence but a different sub-bucket TTFB reading (55.6 vs 66.6
        # ms — both in the <=800ms tier) must still render byte-identical HTML.
        r1 = self._result()
        r1["meta"]["ttfb_ms"] = 55.6
        r2 = self._result()
        r2["meta"]["ttfb_ms"] = 66.6
        self.assertEqual(run_audit.render_html(r1), run_audit.render_html(r2))
        # And rendering never leaks the raw sub-bucket reading into the artifact.
        html = run_audit.render_html(r1)
        self.assertNotIn("55.6", html)
        self.assertNotIn("66.6", html)

    def test_render_html_does_not_mutate_result(self):
        # The TTFB coarsening must produce a copy, never mutate the caller's dict
        # (the canonical GEO-AUDIT.json keeps the precise reading).
        result = self._result()
        result["meta"]["ttfb_ms"] = 66.6
        run_audit.render_html(result)
        self.assertEqual(result["meta"]["ttfb_ms"], 66.6)

    def test_report_is_fully_offline_no_external_requests(self):
        # "Fully self-contained — no internet needed to view it." The artifact
        # must make ZERO network requests: no Google Fonts at all, and no
        # resource-fetching tags (<link>/<img>/<script src>/preconnect) in the
        # rendered markup. Recommendation/evidence STRINGS may legitimately
        # contain "<link" etc. inside the embedded JSON data block (it is data,
        # not markup), so the markup checks are scoped to the visible region.
        html = run_audit.render_html(self._result())
        self.assertNotIn("fonts.googleapis.com", html)  # not even as data
        self.assertNotIn("fonts.gstatic.com", html)
        self.assertEqual(html.count("<style>"), 1)      # exactly one inline style
        markup = self._visible_part(html)               # head+body, no data block
        self.assertNotIn("<link", markup)               # no external stylesheets
        self.assertNotIn("preconnect", markup)
        self.assertNotIn("<img", markup)                # no external images
        self.assertNotIn("src=", markup)                # no <script src>/<img src>

    def test_dynamic_text_is_escaped(self):
        # Evidence/recommendation containing markup must not break out raw.
        result = self._result()
        result["composite"]["pillars"]["citability"]["signals"][0]["evidence"] = (
            '<img src=x onerror="alert(1)"> & "quoted" </script>')
        html = run_audit.render_html(result)
        # In the human-readable body the markup must be escaped, not raw.
        visible = self._visible_part(html)
        self.assertNotIn('<img src=x onerror=', visible)
        self.assertIn("&lt;img", visible)
        # The embedded JSON keeps the raw value (it is data), but the only
        # script-tag breakout risk </ is neutralized as <\/, so the </script>
        # the payload contains cannot prematurely close the data block.
        import re
        m = re.search(
            r'<script type="application/json" id="geo-audit-data">(.*?)</script>',
            html, re.DOTALL)
        self.assertIsNotNone(m)
        self.assertNotIn("</", m.group(1))   # all </ neutralized to <\/
        self.assertIn("<\\/script>", m.group(1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
