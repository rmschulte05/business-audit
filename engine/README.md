# GEO Audit Engine — deterministic scoring core

This is the measurement layer that turns the GEO score from "an LLM's opinion"
into a **reproducible, evidence-based number**. Run it on the same site twice and
you get the same score. It is pure Python 3, **standard library only** — no pip
install, no API key required (one optional key unlocks Core Web Vitals).

## Why it exists

The audit skills used to ask the model to *assess*, *estimate*, and *assign*
0–100 scores from qualitative bands. Two runs on the same site could differ by
10–20 points, and some inputs (subscriber counts, Core Web Vitals, "does the
brand appear in ChatGPT") were guessed. You cannot sell a number a client can't
reproduce. This engine fixes that by measuring everything that is objectively
observable and being explicit about everything that is not.

## The core idea: MEASURED vs NOT_MEASURED

Every signal is either:

- **MEASURED** — real evidence was captured (a header value, a parsed JSON-LD
  block, a counted statistic). Its points are trustworthy.
- **NOT_MEASURED** — the engine could not observe it (off-site brand presence,
  semantic quality judgments). It is **excluded from the score** (never fabricated,
  never a false penalty) and instead **lowers the confidence band**.

So the headline is always `score ± band  (confidence N%)`. Confidence is the
share of the weighted score backed by direct measurement.

## What it measures (deterministic)

| Pillar | Measured by the engine | Left to reviewer judgment |
|---|---|---|
| Technical GEO | HTTPS, security headers, canonical, viewport, **SSR (raw-HTML)**, robots.txt, sitemap, TTFB, compression, lang, **AI-crawler access**, llms.txt, **CWV via PSI*** | — |
| Schema | JSON-LD detection (from **raw HTML**, not WebFetch), Organization/WebSite completeness, **sameAs** count, valid-JSON, server-rendered | schema.org semantic correctness |
| AI Citability | heading hierarchy, question headings, **statistic density**, content volume | answer self-containment, originality |
| Content E-E-A-T | trust signals (HTTPS/privacy/terms/contact/phone), author byline, dates, About page | expertise depth, first-hand experience |
| Brand Authority | — | all (off-site: YouTube/Reddit/Wikipedia/LinkedIn) |
| Platform Optimization | — | all (Knowledge Panel, GBP, Bing index, etc.) |

\* Core Web Vitals are only measured when `PSI_API_KEY` is set (free Google
PageSpeed Insights key). Without it they are `NOT_MEASURED` — **never guessed**.

## Usage

```bash
cd engine
python3 -m geo_audit.run_audit https://example.com --type saas \
    --out-json audit.json --out-md audit.md
```

`--type` is one of `local`, `saas`, `ecommerce`, `publisher`, `agency`
(default: balanced). It selects a **business-type weight profile** so a local
plumber isn't scored as if it should have a global YouTube presence.

Optional Core Web Vitals:

```bash
export PSI_API_KEY=your_free_key   # https://developers.google.com/speed/docs/insights
```

### Merging LLM judgment (hybrid flow)

The judgment signals (`NOT_MEASURED`) can be filled by an LLM reviewer that reads
the page text and scores them, then passes a JSON file:

```bash
python3 -m geo_audit.run_audit https://example.com --type saas \
    --llm-scores llm.json --out-json audit.json
```

`llm.json` shape (see `LLM_SCORES.md`):

```json
{
  "citability": { "answer_self_containment": {"points": 16, "evidence": "..."} },
  "eeat": { "expertise_depth": {"points": 15, "evidence": "..."} },
  "brand_authority_score": 42,
  "platform_optimization_score": 55
}
```

Filling a judgment signal turns it MEASURED (by the reviewer) and **raises
confidence**. The arithmetic stays in code, so the score is still reproducible
given the same LLM inputs.

## Output

- `audit.json` — full evidence bundle: composite, per-pillar scores, every
  signal with its points/max/status/evidence/recommendation, and the raw
  collector data.
- `audit.md` — client-facing report: headline score + confidence band, pillar
  table, prioritized fixes (from measured gaps), and an explicit "Not Measured"
  section.

## Tests

```bash
cd engine
python3 -m unittest tests.test_engine
```

20 offline tests (no network) assert exact scores and prove determinism.

## Layout

```
engine/geo_audit/
  evidence.py        # MEASURED/NOT_MEASURED data contract + category math
  http_client.py     # stdlib HTTP (redirects, gzip, TTFB)
  html_utils.py      # raw-HTML JSON-LD/meta/heading extraction
  collectors/        # crawlers, llmstxt, schema, technical, content, psi
  scoring/           # weights (business-type profiles), aggregate (composite)
  report.py          # Markdown renderer
  run_audit.py       # CLI orchestrator
tests/test_engine.py
```
