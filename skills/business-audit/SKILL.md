---
name: business-audit
description: One-command orchestrator that runs the bundled website-intelligence skill (Phases 1-3 only — brand extraction, competitor analysis, competitive report) and the bundled geo-audit skill (full GEO scoring across 6 categories), then renders a combined interactive HTML dashboard from their Markdown outputs. Use when the user says "business audit", "audit my business", "audit [domain]", "competitive + geo audit", "website audit", or "competitive analysis with AI visibility".
---

# Business Audit — One Command, Two Source Skills, One Dashboard

This skill is a **thin orchestrator**. It does not re-implement competitive analysis or GEO scoring. It runs two existing skills back-to-back and combines their output:

- **`website-intelligence`** (bundled at `../website-intelligence/`) — produces competitor analysis
- **`geo-audit`** (bundled at `../geo-audit/`) — produces the GEO Score and findings

Then it generates a **new combined `dashboard.html`** from the Markdown those two skills produced.

You MUST use the bundled source skills exactly as they are. Do not paraphrase, do not extract their prompts, do not reinvent their scoring rubrics. Run them as written.

---

## Required: Firecrawl MCP

Both source skills require Firecrawl MCP. Before doing anything else, verify it's available — look for `mcp__firecrawl__scrape`, `mcp__firecrawl__map`, `mcp__firecrawl__search` in your tool list. If missing, stop and tell the user to set up Firecrawl (see README).

---

## INPUTS

- **Client URL** (required) — e.g., `https://acme.com`
- **Niche / industry** (required) — e.g., "B2B SaaS for engineering teams"

If either is missing, ask once. Do not start scraping without both.

---

## STEP 1 — Run `website-intelligence` (Phases 1–3 ONLY)

Read and execute `../website-intelligence/SKILL.md` against the client URL.

**You MUST stop after Phase 3 (Competitive Analysis Report).** Do NOT continue to:
- Phase 4 (Build Brief & Approval)
- Phase 5 (Build the Website)
- Phase 6 (Quality Audit)

This skill is audit-only. The user does not want a rebuilt website.

After Phase 3 completes, the working directory will contain:

```
research/01-client-brand.md           # Brand snapshot (colors, fonts, tone, messaging, site map)
research/02-competitor-analysis.md    # Top-5 deep scrape, comparison table, patterns
competitive-analysis.html             # The original PDF-ready HTML report from website-intelligence
```

Keep all three files. They are the source of truth for the competitive half of the audit.

---

## STEP 2 — Run `geo-audit` (full)

Read and execute `../geo-audit/SKILL.md` against the same client URL.

Run all three phases of `geo-audit`:
1. Discovery & Reconnaissance
2. Parallel Subagent Delegation (all 6 categories)
3. Score Aggregation & Report Generation

It will produce:

```
GEO-AUDIT-REPORT.md    # Full audit: overall score, 6-category breakdown, prioritized issues, 30-day plan
```

This file is the source of truth for the AI-visibility half of the audit.

---

## STEP 3 — Render the combined `dashboard.html`

Now read the three Markdown files produced by the source skills and render `dashboard.html` from `templates/dashboard.html.tmpl`.

### Extract from `research/01-client-brand.md`
- `client_name` (from `## Brand Snapshot` → Company)
- `client_url` (the URL input by the user)
- `business_type` (saas / local / ecommerce / publisher / agency / hybrid — from the snapshot or inferred)
- `brand_colors`: primary + secondary + accent hex values
- `fonts`: heading and body
- `tone`, `headline`, `primary_cta`

### Extract from `research/02-competitor-analysis.md`
- Top 5 competitor names + URLs
- Each competitor's brand colors (hex)
- Each competitor's headline (verbatim)
- The comparison-table scores
- The "Patterns of the Top 10%" section (3–5 patterns)

### Extract from `GEO-AUDIT-REPORT.md`
- `geo_score` (integer 0–100, from `Overall GEO Score: X/100`)
- `geo_rating` (the rating word — Excellent / Good / Fair / Poor / Critical)
- The 6-category Score Breakdown table: `citability`, `brand_authority`, `eeat`, `technical`, `schema`, `platform_optimization` each as integer 0–100
- All Critical / High / Medium / Low issues with their text and any recommended fixes
- Quick Wins list
- 30-Day Action Plan (weekly themes)

### Token replacement
Open `templates/dashboard.html.tmpl` and replace these tokens:

| Token | Source |
| --- | --- |
| `{{CLIENT_NAME}}` | `01-client-brand.md` Company |
| `{{CLIENT_URL}}` | user input |
| `{{AUDIT_DATE}}` | today's date in ISO format (YYYY-MM-DD) |
| `{{GEO_SCORE}}` | integer from `GEO-AUDIT-REPORT.md` |
| `{{GEO_SCORE_LABEL}}` | rating word |
| `{{FINDINGS_COUNT_CRITICAL}}` | count of Critical issues in GEO report + count of competitive gaps you flag as Critical (cap at 5) |
| `{{FINDINGS_COUNT_HIGH}}` | same for High |
| `{{FINDINGS_COUNT_MEDIUM}}` | same for Medium |
| `{{FINDINGS_COUNT_LOW}}` | same for Low |
| `{{COMPETITIVE_HTML}}` | server-render the Competitive tab from `01-client-brand.md` + `02-competitor-analysis.md` (see "Tab content" below) |
| `{{GEO_HTML}}` | server-render the GEO tab from `GEO-AUDIT-REPORT.md` (see "Tab content" below) |

### Tab content shape

**Competitive tab (`{{COMPETITIVE_HTML}}`):**
- `<h2>Client snapshot</h2>` — one card with company name, brand color swatches, fonts, headline, primary CTA
- `<h2>Top 5 competitors</h2>` — 5 cards, one per competitor, each showing name, URL, colors, headline, strengths/weaknesses
- `<h2>Comparison matrix</h2>` — the table from `02-competitor-analysis.md`, plus a row for the client
- `<h2>Patterns of the top 10%</h2>` — 3–5 cards summarizing the patterns section

**GEO tab (`{{GEO_HTML}}`):**
- Score gauge: `<div class="gauge">` with `gauge-number` `gauge-label` `gauge-track` `gauge-fill` (width = `{{GEO_SCORE}}%`)
- `<h2>Score breakdown</h2>` — 6 `bar-row` rows, one per category
- `<h2>Critical issues</h2>` / `High` / `Medium` / `Low` — each issue rendered as `<details class="finding" data-severity="...">` collapsible block
- `<h2>30-day action plan</h2>` — table from the GEO report

Use the class names defined in `templates/dashboard.html.tmpl` so the embedded CSS picks them up. See `references/design-system.md` if you need to add new components.

### Verification

After write:
- `grep '{{' dashboard.html` must return nothing.
- Open in a browser; both tabs must render; tab switching must work.
- Print preview must be clean A4.

---

## OUTPUT

When done, the working directory contains:

```
research/
  01-client-brand.md           ← from website-intelligence
  02-competitor-analysis.md    ← from website-intelligence
competitive-analysis.html      ← from website-intelligence
GEO-AUDIT-REPORT.md            ← from geo-audit
dashboard.html                 ← from this skill (NEW combined view)
```

The two source skills' Markdown files are the source of truth for implementation. `dashboard.html` is the human-readable view.

---

## RULES

1. **Use the bundled source skills exactly.** Do not paraphrase or re-implement their logic.
2. **Stop website-intelligence at Phase 3.** Phases 4–6 (build brief, website build, quality audit) are not part of this skill.
3. **Run geo-audit fully.** All 6 categories, all phases.
4. **Generate ONE new artifact only.** `dashboard.html`. Everything else is what the source skills wrote.
5. **No fabrication.** If a source skill couldn't extract a value, leave it blank in the dashboard rather than inventing one.
6. **Fail visibly.** If Firecrawl is missing or a page 403s, tell the user — don't push past the error.

---

## REFERENCES

- [`references/workflow.md`](references/workflow.md) — the orchestration in detail, with edge cases
- [`references/design-system.md`](references/design-system.md) — dashboard design tokens
- [`examples/sample-audit/`](examples/sample-audit/) — realistic end-to-end example output

## BUNDLED SOURCE SKILLS

- `../website-intelligence/` — competitor analysis (run Phases 1–3 only)
- `../geo-audit/` — GEO scoring (run fully); orchestrates `../geo-citability/`, `../geo-content/`, `../geo-technical/`, `../geo-schema/`, `../geo-platform-optimizer/`, `../geo-brand-mentions/`, `../geo-crawlers/`, `../geo-llmstxt/`
