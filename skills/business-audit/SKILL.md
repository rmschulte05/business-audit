---
name: business-audit
description: Runs a combined competitive intelligence + Generative Engine Optimization (GEO) audit on a website. Scrapes the client and top 5 competitors, scores AI-search visibility across 6 weighted categories, and writes two implementation-ready Markdown reports plus a print-ready interactive HTML dashboard. Use when the user says "business audit", "audit my business", "audit [domain]", "competitive + geo audit", "website audit", or "competitive analysis with AI visibility".
---

# Business Audit — Competitive Intelligence + GEO in One Pass

You are a senior web strategist and AI-search analyst. Your job: run a full competitive audit and a Generative Engine Optimization (GEO) audit on a website **in a single pipeline**, then write three artifacts a client can use directly.

This skill orchestrates two analyses:
- **Competitive intelligence** — extracted from `website-intelligence` patterns
- **GEO scoring** — delegated to the bundled `geo-audit` sub-skill (which itself coordinates `geo-citability`, `geo-content`, `geo-technical`, `geo-schema`, `geo-platform-optimizer`, `geo-brand-mentions`, `geo-crawlers`, `geo-llmstxt`)

Work the phases in order. Do not skip the discovery step.

---

## INPUTS

Required:
- **Client URL** — the website to audit (e.g., `https://acme.com`)
- **Niche / industry** — one sentence describing what they do (e.g., "B2B SaaS for engineering teams" or "local dental practice in Austin")

If either is missing, ask once at the start. Then proceed.

---

## DELIVERABLES

Write all three to the current working directory:

| File | Contents |
| --- | --- |
| `COMPETITIVE-ANALYSIS.md` | Top 5 competitor profiles, comparison matrix, winning patterns, prioritized findings using the [implementation-ready format](references/implementation-format.md). |
| `GEO-AUDIT.md` | Client GEO Score (0–100), 6-category breakdown, AI platform readiness, competitor benchmark, prioritized findings using the same format. |
| `dashboard.html` | Self-contained single-file HTML with two tabs (Competitive / GEO). Print-friendly (export to PDF via browser). |

Both Markdown files MUST use the finding block specified in `references/implementation-format.md` so a downstream Claude session can execute the recommendations without clarification.

---

## BEFORE YOU START: Firecrawl

Check whether Firecrawl MCP is connected (look for `mcp__firecrawl__scrape`, `mcp__firecrawl__map`, `mcp__firecrawl__search`).

- **Connected** → use it for all scraping and competitor discovery.
- **Not connected** → fall back to `WebFetch` for individual page scrapes, and use WebSearch for competitor discovery. Note this fallback at the top of both Markdown files so the user knows coverage is reduced.

If the user wants to enable Firecrawl, point them at https://firecrawl.dev (free tier) and the config snippet in `~/.claude/skills/website-intelligence/SKILL.md` lines 44–58.

---

## PHASE 1 — Discovery

1. Fetch the client homepage. From it, classify the business type: `saas | local | ecommerce | publisher | agency | hybrid`.
2. Map the site (Firecrawl `/map`, or WebFetch the sitemap + crawl internal links). Cap at 50 pages.
3. For each discovered page, record: URL, title, meta description, canonical, headings (H1–H3), word count, schema types found, response code.
4. Detect AI-relevant signals on the homepage: `robots.txt` access for AI crawlers, presence of `/llms.txt`, JSON-LD schema blocks, Open Graph + Twitter tags, author/byline patterns.

This step matches `~/.claude/skills/geo-audit/SKILL.md` Phase 1. Reuse its logic.

---

## PHASE 2 — Client Analysis (run in parallel)

### 2a. Brand & content extraction (competitive lens)

Following the pattern in `~/.claude/skills/website-intelligence/SKILL.md` Phase 1, extract from the client site:

- Logo URL(s) and favicon
- Brand colors — primary, secondary, accent, background, text (hex values from CSS)
- Typography — heading font, body font, weights (from `font-family` declarations or Google Fonts links)
- Tone of voice (formal / casual / playful / authoritative)
- Core messaging — headline, tagline, value proposition
- Site architecture (page count, nav depth, key sections)
- Conversion strategy — primary CTA, secondary CTA, lead capture mechanism, social proof placement

### 2b. GEO audit

**Delegate to the bundled `geo-audit` sub-skill.** Pass it the page set collected in Phase 1. It will run all 6 category analyses (AI Citability, Brand Authority, Content E-E-A-T, Technical GEO, Schema, Platform Optimization) and return a weighted composite GEO Score plus per-category findings.

Do NOT re-implement the scoring rubrics. The bundled `geo-audit` skill is at `../geo-audit/SKILL.md` relative to this file.

Capture from the GEO audit:
- Overall GEO Score (0–100)
- Per-category sub-scores
- AI platform readiness table (Google AI Overviews, ChatGPT, Perplexity, Gemini, Bing Copilot)
- All Critical and High findings with their suggested fixes

---

## PHASE 3 — Competitor Discovery

1. Use Firecrawl search (or WebSearch fallback) to find 10 competitor candidates in the niche.
2. Score each candidate on the 8 criteria in `references/competitor-scoring.md` (search visibility, review quality, visual design, mobile responsiveness, content depth, social proof, CTA strategy, page speed). Score 1–10 per criterion.
3. Pick the top 5 by total score for deep analysis.

---

## PHASE 4 — Competitor Deep Dive (parallel per competitor)

For each of the 5 selected competitors, in parallel:

### 4a. Brand & content extraction (lightweight)
Scrape the homepage + 2–3 key pages (about, pricing/services, contact). Extract the same fields as Phase 2a but in compact form: colors, typography, headline formula, CTA strategy, design aesthetic in one line, content depth in word count.

### 4b. GEO mini-audit
Run a lightweight version of the GEO audit on the competitor — only these metrics:
- Overall GEO Score
- Schema coverage (count of distinct schema types found)
- `llms.txt` presence (yes / no)
- AI crawler access (`GPTBot`, `ClaudeBot`, `PerplexityBot` — allowed / blocked)
- Top-page citability score

Do NOT run the full 6-category geo-audit on competitors — it's too slow. Just hit `geo-citability`, `geo-schema`, `geo-crawlers`, `geo-llmstxt`.

---

## PHASE 5 — Synthesis: write the two Markdown files

### Write `COMPETITIVE-ANALYSIS.md`

Use `templates/COMPETITIVE-ANALYSIS.md.tmpl` as the skeleton. Sections:

1. **Executive summary** — 3 sentences: who the client is, who they're up against, biggest opportunity.
2. **Client snapshot** — brand swatches, typography, tone, messaging from Phase 2a.
3. **Competitor profiles** — one card per competitor with logo URL, colors, typography, headline, score breakdown, strengths/weaknesses.
4. **Comparison matrix** — table with all 5 competitors + client across the 8 scoring criteria.
5. **Patterns of the top 10%** — 3–5 design/messaging/conversion patterns that ALL top competitors do but the client doesn't.
6. **Prioritized findings** — using the implementation-ready format from `references/implementation-format.md`. Group by Severity (Critical, High, Medium, Low).
7. **Quick wins** — 5–10 findings the client can ship this week.

### Write `GEO-AUDIT.md`

Use `templates/GEO-AUDIT.md.tmpl` as the skeleton. Sections:

1. **Executive summary** — overall GEO Score, biggest strength, biggest gap.
2. **Score breakdown** — table of 6 categories with weight × score × weighted score, plus the composite total.
3. **AI platform readiness** — table of 5 platforms (Google AI Overviews, ChatGPT, Perplexity, Gemini, Bing Copilot) with per-platform readiness score.
4. **Competitor benchmark** — table comparing client's GEO Score to each competitor's mini-audit score; flag where competitors win.
5. **Prioritized findings** — implementation-ready format, grouped by Severity. Each finding cites the category it belongs to.
6. **30-day action plan** — week-by-week themes (Week 1: Critical / Week 2: High / Week 3: Schema + llms.txt / Week 4: content & brand authority).

Both files MUST conform to `references/implementation-format.md`. Every finding gets the same block shape.

---

## PHASE 6 — Dashboard Render

Read both Markdown files you just wrote. Then read `templates/dashboard.html.tmpl` and produce `dashboard.html` in the working directory by replacing these tokens:

| Token | Value |
| --- | --- |
| `{{CLIENT_NAME}}` | Brand name extracted in Phase 2a |
| `{{CLIENT_URL}}` | Original input URL |
| `{{GEO_SCORE}}` | Integer 0–100 |
| `{{GEO_SCORE_LABEL}}` | One of: Excellent / Good / Fair / Poor / Critical |
| `{{AUDIT_DATE}}` | Today's date, ISO format |
| `{{COMPETITIVE_HTML}}` | HTML rendering of the Competitive tab — competitor cards, comparison table, patterns, findings (server-rendered into the template) |
| `{{GEO_HTML}}` | HTML rendering of the GEO tab — score gauge, category bars, platform readiness, findings, action plan |
| `{{FINDINGS_COUNT_CRITICAL}}` | Integer |
| `{{FINDINGS_COUNT_HIGH}}` | Integer |
| `{{FINDINGS_COUNT_MEDIUM}}` | Integer |
| `{{FINDINGS_COUNT_LOW}}` | Integer |

The template embeds all CSS and the vanilla-JS tab switcher inline so the result is a single self-contained file the user can email or open offline. Design tokens (terracotta `#c45d3e`, paper `#f6f4f0`, Instrument Serif + DM Sans, 4px accent left border, grain overlay) are documented in `references/design-system.md`.

---

## OUTPUT VERIFICATION

Before declaring the audit complete, verify:

1. All three files exist in the working directory: `COMPETITIVE-ANALYSIS.md`, `GEO-AUDIT.md`, `dashboard.html`.
2. Every finding in both Markdown files has all 6 fields from `references/implementation-format.md` (Severity, Category, Location, Current state, Recommended change, Why, Implementation hint).
3. The dashboard opens in a browser — no console errors, both tabs visible, tab switching works.
4. The print preview is clean A4 (no overflow, no missing styles, page breaks sensible).
5. No `{{TOKEN}}` placeholders remain unreplaced in `dashboard.html`.
6. No secrets, no `/Users/`, no API keys in any output file (use grep to confirm).

If any check fails, fix before handing off.

---

## REFERENCES

- [`references/workflow.md`](references/workflow.md) — full step-by-step pipeline with edge cases
- [`references/competitor-scoring.md`](references/competitor-scoring.md) — the 8-criteria rubric
- [`references/implementation-format.md`](references/implementation-format.md) — exact finding block spec
- [`references/design-system.md`](references/design-system.md) — design tokens for the dashboard
- [`examples/sample-audit/`](examples/sample-audit/) — realistic end-to-end example for a fictional business

## DELEGATED SUB-SKILLS (bundled in this plugin)

- `../geo-audit/` — orchestrates the 6-category GEO scoring
- `../geo-citability/`, `../geo-content/`, `../geo-technical/`, `../geo-schema/`, `../geo-platform-optimizer/`, `../geo-brand-mentions/`, `../geo-crawlers/`, `../geo-llmstxt/` — invoked by `geo-audit`

Do not duplicate logic from these skills. Delegate.

---

## IMPORTANT RULES

1. **Audit only.** This skill does not rebuild the website. Recommendations live in the Markdown files; another Claude session implements them.
2. **Implementation-ready or it doesn't ship.** Every finding must include a concrete code/copy change a Claude session can apply mechanically.
3. **Delegate, don't duplicate.** The `geo-audit` sub-skill is bundled — use it. Do not re-implement scoring rubrics inline.
4. **Two markdown files are the source of truth.** The HTML dashboard is for humans. The markdown is for AI implementation. Both must agree.
5. **Be opinionated.** Pick the 5 specific competitors, give them real scores, name the 3 winning patterns concretely. Avoid hedging.
6. **Fail visibly.** If Firecrawl is missing or a page 403s, note it in the report rather than fabricating data.
