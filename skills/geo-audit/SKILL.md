---
name: geo-audit
description: Full website GEO+SEO audit. Runs a deterministic measurement engine for everything objectively observable (AI crawler access, schema, technical, countable content) and adds LLM judgment only for what truly needs it (semantic quality, off-site brand/platform presence). Produces a reproducible composite GEO Score (0-100) with an explicit confidence band and a prioritized action plan.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - WebFetch
  - Write
---

# GEO Audit Orchestration Skill

## Purpose

This skill performs a comprehensive Generative Engine Optimization (GEO) audit of
any website. GEO is the practice of optimizing content so AI systems (ChatGPT,
Claude, Perplexity, Gemini, Copilot) can discover, understand, cite, and recommend
it. The audit produces a **reproducible** GEO Score: run it twice on the same site
and the measured portion of the score is identical.

## The core principle: measure first, judge second, never fabricate

The score has two layers:

1. **Measured layer (deterministic engine).** A bundled Python engine collects
   objectively observable evidence — robots.txt AI-crawler rules, JSON-LD parsed
   from raw HTML, HTTPS/headers/SSR/sitemap/TTFB, countable content signals
   (heading hierarchy, statistic density), llms.txt, and Core Web Vitals (when a
   PageSpeed key is set). These scores are exact and repeatable.
2. **Judged layer (you, the LLM).** Only the signals that genuinely require
   judgment — semantic answer quality, originality, expertise depth, and
   **off-site brand/platform presence** — are scored by you, each backed by
   evidence. The engine marks these `not_measured` until you fill them.

Every claim must be backed by evidence. If something cannot be measured or
verified, it stays `not_measured` and **lowers the confidence band** — it is never
guessed. A fabricated metric in a paid audit is a liability; this design removes
the temptation structurally.

---

## Locate the engine

The engine ships with this plugin at `<plugin-root>/engine/`. This skill lives at
`<plugin-root>/skills/geo-audit/`, so the engine is two directories up. Locate it
robustly:

```bash
ENGINE_DIR="$(python3 - <<'PY'
import os, glob
roots = [os.getcwd(), os.path.expanduser("~/.claude/plugins"), os.path.expanduser("~/.claude")]
cands = []
for r in roots:
    cands += glob.glob(os.path.join(r, "**", "engine", "geo_audit", "run_audit.py"), recursive=True)
print(os.path.dirname(os.path.dirname(cands[0])) if cands else "")
PY
)"
echo "Engine: ${ENGINE_DIR:-NOT FOUND}"
```

If `ENGINE_DIR` is empty, tell the user the plugin is not fully installed and stop.
All engine commands below run with `PYTHONPATH="$ENGINE_DIR"`.

---

## Phase 1 — Run the deterministic engine

Detect the business type first (see the classification table at the end), then run:

```bash
PYTHONPATH="$ENGINE_DIR" python3 -m geo_audit.run_audit "<URL>" \
    --type <local|saas|ecommerce|publisher|agency> \
    --date "$(date +%F)" \
    --max-pages 8 \
    --out-json geo-engine.json
```

`--max-pages N` (default `8`) controls the deterministic multi-page crawl. The
engine discovers same-domain pages in a fixed order — homepage first, then
`sitemap.xml` (following a sitemap index one level), then high-value homepage
links (about, pricing, services, products, blog, docs, contact) — while
respecting `robots.txt`. Across the fetched pages it then:
- UNIONs schema `@types` and `sameAs` (so Product/Article/FAQ schema living on
  inner pages is detected and credited, not just the homepage);
- reports a site-wide `citability_coverage` signal (fraction of pages with strong
  answer-style content) alongside the homepage citability signals;
- turns E-E-A-T `authorship` and `date_present` into the fraction of pages
  exhibiting them, and treats trust signals (privacy/terms/contact) as present if
  found on ANY page;
- samples server-side rendering across pages (reported as the fraction
  server-rendered, homepage always counted).

Use `--max-pages 1` for a fast, homepage-only run that reproduces the legacy
single-page scores exactly. Re-running with the same `--max-pages` on the same
site yields byte-identical output (no randomness).

Optional but recommended — real Core Web Vitals (free Google key):

```bash
export PSI_API_KEY=...   # https://developers.google.com/speed/docs/insights
```

`geo-engine.json` now contains:
- `composite` — the measured GEO score, per-pillar scores, confidence band, and
  every signal with `status` (`measured` / `not_measured`), points, evidence, and
  recommendation.
- `raw` — the underlying data (parsed schema types, robots access map, captured
  homepage word counts/headings, etc.) you will read for the judgment phase.
- `meta.pages_analyzed` — the list of page URLs actually fetched, and `raw.pages`
  — compact per-page detail (only populated when `--max-pages > 1`). The
  `composite` contract is unchanged regardless of `--max-pages`.

If `meta.error` is present (site unreachable or blocks all crawlers), report that
honestly and stop — do not invent a score.

---

## Phase 2 — Add LLM judgment (only the `not_measured` signals)

Read `geo-engine.json`. For each signal with `"status": "not_measured"`, supply a
score **backed by evidence**, following `engine/LLM_SCORES.md`. There are exactly
two kinds:

### 2a. On-page judgment signals (read the captured page text)

Using the homepage text and headings in `geo-engine.json` `raw` (and WebFetch for
key inner pages — articles, service/product, about), score:

| Signal | Max | What you are judging |
|---|---|---|
| `citability.answer_self_containment` | 20 | Do top sections open with a 1-2 sentence direct answer that stands alone? |
| `citability.uniqueness` | 10 | Original data/insight vs. derivative restatement? |
| `eeat.expertise_depth` | 20 | Genuine technical depth, correct terminology, explained methodology? |
| `eeat.experience` | 5 | First-hand accounts, case studies with specifics? |

Use the rubrics in the bundled reference skills for consistent banding:
`../geo-citability/SKILL.md` (answer/uniqueness) and `../geo-content/SKILL.md`
(E-E-A-T). These are **reference rubrics for your judgment**, not separate scorers.

### 2b. Off-site research signals (verify with WebSearch/WebFetch)

The engine cannot see off-site presence. Research it and score two whole pillars,
each 0-100, **with verified URLs** (per the Evidence Standard below):

| Field | What to assess | Reference rubric |
|---|---|---|
| `brand_authority_score` | YouTube / Reddit / Wikipedia / Wikidata / LinkedIn presence for entity recognition | `../geo-brand-mentions/SKILL.md` |
| `platform_optimization_score` | Per-platform readiness: AI Overviews, ChatGPT, Perplexity, Gemini, Copilot | `../geo-platform-optimizer/SKILL.md` |

For Wikipedia/Wikidata, verify via the API (do not rely on web search alone):

```bash
python3 - <<'PY'
import urllib.request, urllib.parse, json
brand = "BRAND NAME"
u = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
    {"action":"query","list":"search","srsearch":brand,"format":"json"})
req = urllib.request.Request(u, headers={"User-Agent":"GEO-Audit/2.0"})
print(json.load(urllib.request.urlopen(req, timeout=15))["query"]["search"][:1])
PY
```

If a platform cannot be verified, write "not found" and score it 0 — **do not
guess a follower count or mention volume.**

Write your judgments to `llm-scores.json` exactly as specified in
`engine/LLM_SCORES.md`. Every judged signal needs an `evidence` string.

---

## Phase 3 — Merge and generate the report

Re-run the engine with your judgments merged in:

```bash
PYTHONPATH="$ENGINE_DIR" python3 -m geo_audit.run_audit "<URL>" \
    --type <type> --date "$(date +%F)" \
    --llm-scores llm-scores.json \
    --out-json GEO-AUDIT.json \
    --out-md GEO-AUDIT-REPORT.md
```

`GEO-AUDIT-REPORT.md` is the client-facing report: headline score + confidence
band, pillar table, prioritized fixes (drawn from measured gaps), and an explicit
"Not Measured" section. The composite is computed in code, so it is identical on
re-run given the same inputs.

Read `GEO-AUDIT-REPORT.md` back and, if useful, expand the deep-dive prose using
the category rubrics — but **never change the numbers**; they come from the engine.

---

## Composite GEO Score

The engine computes the composite as a business-type-weighted average over the six
pillars, **using only the measured weight of each pillar** (so unmeasured signals
lower confidence rather than silently zeroing a category):

| Pillar | What it measures | Default weight |
|---|---|---|
| AI Citability | Quotable/extractable content (engine: structure, stats; LLM: answer quality, originality) | 25% |
| Brand Authority | Off-site entity signals (LLM-judged, evidence-linked) | 20% |
| Content E-E-A-T | Trust signals (engine) + expertise/experience (LLM) | 20% |
| Technical GEO | Crawler access, SSR, HTTPS, sitemap, TTFB, CWV (engine) | 15% |
| Schema & Structured Data | JSON-LD from raw HTML, Organization/sameAs (engine) | 10% |
| Platform Optimization | Per-platform readiness (LLM-judged) | 10% |

Weights shift by business type (`local`, `saas`, `ecommerce`, `publisher`,
`agency`) — see `engine/geo_audit/scoring/weights.py`. A local business is not
penalized for lacking a global YouTube presence.

### Score interpretation

| Score | Rating | Interpretation |
|---|---|---|
| 90-100 | Excellent | Highly likely to be cited by AI systems |
| 75-89 | Good | Strong foundation, clear improvements remain |
| 60-74 | Fair | Moderate; significant opportunities |
| 40-59 | Poor | Weak signals; AI may struggle to cite |
| 0-39 | Critical | Largely invisible to AI systems |

The report always shows `score ± band (confidence N%)`. Low confidence means more
of the score depends on judgment or could not be measured — say so plainly.

---

## Issue severity classification

- **Critical:** All AI crawlers blocked; no server-rendered content; domain-level
  noindex; complete absence of structured data; brand unrecognized as an entity.
- **High:** Key AI crawlers (GPTBot/ClaudeBot/PerplexityBot) blocked; no llms.txt;
  missing Organization schema; no author attribution.
- **Medium:** Partial crawler blocking; thin citability; missing FAQ schema; weak
  author bios.
- **Low:** Minor schema validation issues; missing alt text; missing OG tags.

The engine's per-signal recommendations feed the prioritized fix list
automatically; layer these severity labels on top when writing the report.

---

## Evidence & Competitor Standard

**MANDATORY:** every claim that references a competitor or an off-site fact must
include a verifiable URL to the specific page. Never write "Competitor X has
1,200-word service pages" without linking the page. Verify with WebFetch before
citing. Each audit making competitive claims must include at least 3 verified
competitor URLs; if competitors cannot be verified, say so rather than guessing.

This applies especially to the Phase 2b off-site research: brand-authority and
platform-optimization scores must be grounded in real, fetched URLs.

---

## Business-type detection

Fetch the homepage and classify (this sets `--type`):

| Type | Signals |
|---|---|
| `saas` | Pricing page, "Sign up"/"Free trial", app subdomain, feature/integration pages |
| `local` | Physical address, Google Maps embed, LocalBusiness schema, service-area pages |
| `ecommerce` | Product listings, cart, Product schema, category pages, "Add to cart" |
| `publisher` | Blog-heavy nav, Article schema, author pages, date archives, high content volume |
| `agency` | Case studies, portfolio, "Our Work", team page, client logos |

Pass the dominant pattern. If ambiguous, use the closest match (the engine falls
back to a balanced default for unknown types).

---

## Output files

```
geo-engine.json         # Phase 1: measured-only evidence + scores
llm-scores.json         # Phase 2: your evidence-backed judgments
GEO-AUDIT.json          # Phase 3: full merged result (machine-readable)
GEO-AUDIT-REPORT.md     # Phase 3: client-facing report (the deliverable)
```

`GEO-AUDIT.json` is the source of truth for the AI-visibility half of a business
audit and is consumed by the `business-audit` dashboard.

---

## Reference rubrics (bundled in this plugin)

These provide the detailed banding for your Phase 2 judgments and the background
knowledge for the deep-dive prose. They are **rubrics you apply**, not separate
scorers — the single composite comes from the engine:

- `../geo-citability/` — answer quality, self-containment, statistical density
- `../geo-content/` — E-E-A-T dimensions and content quality
- `../geo-technical/` — technical checks the engine automates (use for deep-dive)
- `../geo-schema/` — schema types and sameAs strategy
- `../geo-brand-mentions/` — off-site platform weighting for brand authority
- `../geo-platform-optimizer/` — per-platform readiness for platform optimization
- `../geo-crawlers/` — AI crawler reference (engine automates the access map)
- `../geo-llmstxt/` — llms.txt spec (engine automates presence/format)
