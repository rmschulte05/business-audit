# Business Audit — Detailed Workflow

This file expands the 6-phase pipeline in `SKILL.md` with edge cases and concrete steps. Read this if anything in the main SKILL.md is ambiguous.

---

## Phase 1 — Discovery

### Goals
- Classify the business type (drives prompt selection in later phases)
- Build a page inventory (capped at 50)
- Surface AI-relevant signals visible on the homepage

### Business type classification

Detect from homepage signals:

| Type | Signals |
| --- | --- |
| `saas` | Pricing page with tiers, "Start free trial", G2/Capterra links, login link in nav, `software/SoftwareApplication` schema |
| `local` | Physical address in footer, phone number prominent, hours of operation, "Book appointment" CTA, `LocalBusiness` schema |
| `ecommerce` | Product cards on home, "Add to cart", `Product` schema, shop nav item |
| `publisher` | Article cards, "Latest posts", author bylines, dates, `Article` / `BlogPosting` schema |
| `agency` | "Our work" / case studies, "Get a quote" CTA, services list, no pricing |
| `hybrid` | Multiple of the above (e.g., SaaS + agency hybrid) |

### Page inventory

Prefer in this order:
1. Firecrawl `/map` — returns full URL list
2. `sitemap.xml` — fetch and parse
3. Internal-link crawl from homepage (BFS, depth 2, dedup)

Cap at 50 unique pages. Always include: home, about, pricing/services, contact, blog index (if exists), one representative article.

### Homepage signal extraction

Record for the report header:
- `robots.txt` lines mentioning `GPTBot`, `ClaudeBot`, `PerplexityBot`, `Google-Extended`, `Bytespider`
- Presence of `https://{domain}/llms.txt`
- JSON-LD blocks (count, types)
- `<meta name="robots">` value
- `X-Robots-Tag` header value

---

## Phase 2 — Client Analysis (parallel)

Run 2a and 2b concurrently. They don't depend on each other.

### 2a. Brand & content extraction

Follow `~/.claude/skills/website-intelligence/SKILL.md` lines 78–106 for the exact extraction prompt. Output goes into the `COMPETITIVE-ANALYSIS.md` under "Client snapshot".

Minimum captured fields:
- `company_name`
- `logo_url`
- `colors`: { primary, secondary, accent, background, text } as hex
- `fonts`: { heading, body } with weights
- `tone`: one-word descriptor
- `headline`, `subhead`, `primary_cta_label`, `primary_cta_destination`
- `nav_items`: array of strings
- `social_proof`: { testimonials_count, customer_logos_count, case_studies_count, review_aggregator_links }
- `conversion_strategy`: one-paragraph summary

### 2b. GEO audit

Invoke the bundled `geo-audit` skill. Pass it the page inventory from Phase 1. It will run all 6 sub-audits and return:
- `overall_score` (0–100)
- `category_scores`: { citability, brand_authority, eeat, technical, schema, platform_optimization }
- `platform_readiness`: { google_aio, chatgpt, perplexity, gemini, bing_copilot } each 0–100
- `findings`: array of finding objects with all 6 implementation-ready fields

---

## Phase 3 — Competitor Discovery

### Search strategies (try in order)

1. **Direct competitor query** — Firecrawl search for `"{niche} alternatives to {client_name}"` and `"best {niche} companies 2026"`.
2. **Category query** — Search `"top {niche} {business_type}"` (e.g., "top dev tooling SaaS").
3. **Local query** (if `business_type == local`) — Search `"{niche} {city}"`.

Aim for 10 unique candidates. Skip:
- The client itself
- Aggregator/directory sites (G2, Capterra, Yelp) unless they are the niche
- Domain parkers and 404s

### Scoring

Score each candidate 1–10 across the 8 criteria in `competitor-scoring.md`. Total possible: 80.

Pick the top 5 by total score. If there's a tie at position 5, prefer the one with the higher "Search visibility" sub-score (they're the loudest competitor).

---

## Phase 4 — Competitor Deep Dive (parallel)

Run all 5 competitors in parallel (separate Agent calls if you want, or interleaved scrapes).

### Per competitor

**Brand & content (lightweight):**
- Scrape homepage + 2 key pages
- Extract: colors (hex), fonts, headline (verbatim), primary CTA, design aesthetic in one line, total word count across the 3 pages

**GEO mini-audit:**
- Call only these 4 sub-skills: `geo-citability` (top page), `geo-schema`, `geo-crawlers`, `geo-llmstxt`
- Compute a synthetic "competitor GEO score" = average of the 4 sub-scores. Note this is approximate — flag it as such in the report.

---

## Phase 5 — Synthesis

### Implementation-ready findings

Every finding in both files MUST conform to `implementation-format.md`. Use the template's pre-formatted Markdown block.

### COMPETITIVE-ANALYSIS.md generation

Order: executive summary → client snapshot → 5 competitor profiles → comparison matrix → patterns → findings (sorted by severity desc) → quick wins.

Aim for 40–80 findings total across both files combined. Quality > quantity — if you have 200 nitpicks, cluster them.

### GEO-AUDIT.md generation

Order: executive summary → score breakdown table → platform readiness table → competitor benchmark table → findings (sorted by severity desc) → 30-day action plan.

Always include the competitor benchmark — that's the killer comparison the user actually wants.

---

## Phase 6 — Dashboard Render

### Token replacement

The template has `{{TOKEN}}` placeholders. Use a simple string-replace pass — no fancy templating engine. After replacement, grep for `{{` to confirm none remain.

### `{{COMPETITIVE_HTML}}` and `{{GEO_HTML}}`

These are the largest tokens. They contain server-rendered HTML for each tab's content. Construct them by:

1. Build competitor cards as `<div class="card"><h3>{name}</h3>...</div>`.
2. Build the comparison matrix as a `<table>`.
3. Render findings as `<details>` blocks (collapsed by default, severity color in summary).
4. Concatenate into the appropriate `{{*_HTML}}` token.

Keep it semantic — the dashboard should be readable even with CSS disabled.

### Verification

After write:
- `grep -n '{{' dashboard.html` → must return nothing
- Open in browser, click both tabs, scroll through both
- File > Print → verify A4 preview is clean
- File size < 500 KB (no external assets)

---

## Edge cases

### Client site is unreachable
- 5xx / timeout → retry once with 30s timeout
- Still failing → ask user to confirm URL; if confirmed bad, abort with a friendly error
- Cloudflare bot wall → fall back to WebFetch; note in report header

### Niche is too vague
- E.g., user says "tech company" → ask for a more specific niche before proceeding
- Examples of good niches: "B2B SaaS for engineering teams", "DTC skincare for men", "local dental practice in Austin", "Substack for science writers"

### Fewer than 10 competitor candidates found
- Run a broader search with the next-level-up category (e.g., "dev tooling" → "developer tools")
- If still <5 candidates, audit what you have and flag the small sample size in the report

### GEO audit returns score 0 / errors
- Likely a JavaScript-rendered SPA — note "JS-rendered site, AI crawlers cannot index" as a Critical finding
- Still produce the report with whatever signals are extractable
