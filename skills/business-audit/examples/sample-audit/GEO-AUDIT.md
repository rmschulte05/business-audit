# GEO Audit — Tideline

> Audit date: 2026-05-15 · Source: business-audit Claude Code plugin
>
> This file is the **source of truth for AI-search visibility recommendations**. Every finding follows the [implementation-ready format](../../references/implementation-format.md) — a downstream Claude Code session can read this and apply the changes mechanically.
>
> _This is a sample audit for a fictional company. Use it as a reference for shape and density._

---

## Executive summary

**GEO Score: 47/100 — Poor**

Tideline's strongest signal is technical (SSR Next.js, fast LCP, clean URL structure). The biggest gap is structured data and brand-authority signals: zero Organization schema, no `sameAs` array, no `/llms.txt`, and essentially no presence on the platforms AI models train on (YouTube, Reddit, Wikipedia). At this score, AI systems are unlikely to surface Tideline in response to category queries — closing 4 of the 6 Critical findings below should lift the score by 18–25 points within 30 days.

---

## Score breakdown

| Category | Weight | Score (0–100) | Weighted |
|---|---:|---:|---:|
| AI Citability | 25% | 52 | 13.0 |
| Brand Authority | 20% | 22 | 4.4 |
| Content E-E-A-T | 20% | 41 | 8.2 |
| Technical GEO | 15% | 78 | 11.7 |
| Schema & Structured Data | 10% | 15 | 1.5 |
| Platform Optimization | 10% | 38 | 3.8 |
| **Composite** | **100%** | — | **47** |

Score bands: 90–100 Excellent · 75–89 Good · 60–74 Fair · 40–59 Poor · 0–39 Critical

---

## AI platform readiness

| Platform | Readiness (0–100) | Top gap |
|---|---:|---|
| Google AI Overviews | 51 | Page-1 Google ranking missing for category terms |
| ChatGPT (web search) | 38 | No Wikipedia entry; Bing index thin |
| Perplexity | 34 | No Reddit presence; no original research content |
| Google Gemini | 44 | No Knowledge Panel; no YouTube channel |
| Bing Copilot | 42 | Bing index has 12 pages indexed; needs IndexNow setup |

---

## Competitor benchmark

How Tideline stacks up against the 5 competitors on key GEO signals:

| Site | GEO Score | Schema types | llms.txt | AI crawlers allowed | Top-page citability |
|---|---:|---:|---|---|---:|
| **Tideline** | **47** | 1 | no | yes | 48 |
| Mode | 78 | 6 | yes | yes | 81 |
| Hex | 74 | 5 | no | yes | 79 |
| Lightdash | 71 | 4 | yes | yes | 76 |
| Metabase | 73 | 7 | no | yes | 74 |
| Preset | 65 | 4 | no | yes | 68 |

Note: competitor GEO scores are approximate (4-sub-skill mini-audit, not the full 6-category run).

**Read:** All 5 competitors beat Tideline by ≥18 points. Mode, Lightdash, and Metabase all publish `llms.txt` (a 2025-emerging signal). Tideline only has a single `WebSite` schema block — every competitor has at least 4 schema types.

---

## Prioritized findings

Every finding below uses the [implementation-ready format](../../references/implementation-format.md). Apply them in severity order.

### Critical

### Finding: Add Organization schema with full sameAs array

- **Severity**: Critical
- **Category**: Schema
- **Location**: Site-wide (`<head>` of every page)
- **Current state**: Only a `WebSite` JSON-LD block on the homepage. No `Organization`, no `sameAs` array anywhere.
- **Recommended change**:
  ```html
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "Tideline",
    "url": "https://tideline.example",
    "logo": "https://tideline.example/logo.svg",
    "description": "Analytics workspace for revenue teams.",
    "sameAs": [
      "https://www.linkedin.com/company/tideline",
      "https://twitter.com/tidelineHQ",
      "https://github.com/tideline",
      "https://www.youtube.com/@tidelineHQ"
    ]
  }
  </script>
  ```
- **Why**: `sameAs` links to LinkedIn/YouTube/Wikipedia are the strongest predictor of AI entity recognition — Ahrefs Dec 2025 study shows 3x lift on AI visibility vs. backlinks alone.
- **Implementation hint**: Add to `app/layout.tsx` `<head>` so it appears on every page. Verify with `https://validator.schema.org/`.

### Finding: Ship /llms.txt at site root

- **Severity**: Critical
- **Category**: Platform
- **Location**: `https://tideline.example/llms.txt` (currently 404)
- **Current state**: No `llms.txt` file. Mode, Lightdash both publish one.
- **Recommended change**: Create `public/llms.txt`:
  ```txt
  # Tideline

  > Tideline is an analytics workspace where revenue teams ship dashboards in an afternoon instead of a quarter. We're built for SQL-fluent analysts who want to skip the BI-tool setup.

  ## Docs

  - [Getting started](https://tideline.example/docs/getting-started): Connect a database, build your first dashboard in 30 minutes
  - [Semantic layer](https://tideline.example/docs/semantic-layer): Define metrics once, reuse everywhere
  - [Embedded analytics](https://tideline.example/docs/embedded): Drop dashboards into your own app via iframe or React SDK

  ## Product

  - [Pricing](https://tideline.example/pricing): Per-seat, transparent, $25/user/month
  - [Security](https://tideline.example/security): SOC 2 Type II, HIPAA-ready, data residency options
  - [Integrations](https://tideline.example/integrations): Postgres, Snowflake, BigQuery, Redshift, MySQL, MotherDuck

  ## About

  - [Customers](https://tideline.example/customers): Named case studies from 40+ revenue teams
  - [Blog](https://tideline.example/blog): Engineering and analytics writing from the team
  ```
- **Why**: <5% of websites have llms.txt as of early 2026 — first-mover advantage on a signal AI assistants are already indexing. Mode reports ChatGPT/Perplexity citation rate doubled within 6 weeks of publishing theirs.
- **Implementation hint**: Save as `public/llms.txt`. Next.js will serve it at root automatically. Also create `public/llms-full.txt` with the full markdown content of key docs concatenated.

### Finding: Unblock all Tier 1 AI crawlers in robots.txt

- **Severity**: Critical
- **Category**: Technical
- **Location**: `https://tideline.example/robots.txt`
- **Current state**:
  ```txt
  User-agent: *
  Disallow:

  User-agent: GPTBot
  Disallow: /
  ```
  GPTBot is blocked; ChatGPT cannot index any page.
- **Recommended change**:
  ```txt
  User-agent: *
  Disallow: /admin/
  Disallow: /api/

  # Tier 1 AI crawlers — explicitly allowed
  User-agent: GPTBot
  Allow: /

  User-agent: ClaudeBot
  Allow: /

  User-agent: PerplexityBot
  Allow: /

  User-agent: Google-Extended
  Allow: /

  User-agent: OAI-SearchBot
  Allow: /

  Sitemap: https://tideline.example/sitemap.xml
  ```
- **Why**: Blocking GPTBot makes the site invisible to ChatGPT web search, which has 200M+ weekly users (OpenAI Feb 2026). The previous block was likely added defensively in 2023 — that thinking is obsolete.
- **Implementation hint**: Replace `public/robots.txt`. Verify with `curl https://tideline.example/robots.txt`. Confirm GPTBot is no longer blocked at https://gptbot-checker.com/.

### Finding: Add an author byline + bio to every blog post

- **Severity**: Critical
- **Category**: Content E-E-A-T
- **Location**: `https://tideline.example/blog/*` (all 14 posts)
- **Current state**: Posts have a date but no author name, no photo, no bio. The "About" page lists three founders but doesn't link to their content.
- **Recommended change**: Add an author block to every post template:
  ```html
  <div class="author-block">
    <img src="/team/jane-doe.jpg" alt="Jane Doe">
    <div>
      <p class="author-name">Jane Doe</p>
      <p class="author-title">Co-founder · Engineer · ex-Stripe data</p>
      <a href="/team/jane-doe">All posts by Jane</a>
    </div>
  </div>
  ```
  Plus JSON-LD Article schema with author:
  ```html
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "[Post title]",
    "datePublished": "2026-04-12",
    "author": {
      "@type": "Person",
      "name": "Jane Doe",
      "url": "https://tideline.example/team/jane-doe"
    }
  }
  </script>
  ```
- **Why**: AI systems weight Author E-E-A-T heavily — content without a named expert author is 4–7x less likely to be cited (Princeton GEO study 2024). Author bio pages also create new indexable entities.
- **Implementation hint**: Add to the blog post layout (`app/blog/[slug]/page.tsx`). Create author profile pages at `app/team/[slug]/page.tsx`.

---

### High

### Finding: Add FAQPage schema to the homepage FAQ section

- **Severity**: High
- **Category**: Schema
- **Location**: `https://tideline.example/` (FAQ section, near footer)
- **Current state**: 6 Q&A pairs in plain HTML, no schema.
- **Recommended change**:
  ```html
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [
      {
        "@type": "Question",
        "name": "How does Tideline differ from Looker?",
        "acceptedAnswer": {
          "@type": "Answer",
          "text": "Tideline ships in 30 minutes vs Looker's 2-week LookML setup. Both have semantic layers, but Tideline is per-seat and transparent in pricing."
        }
      }
    ]
  }
  </script>
  ```
- **Why**: FAQPage schema is a direct Google AI Overviews citation source — pages with valid FAQPage markup are cited 1.8x more often than those without (Schema App 2025 study).
- **Implementation hint**: `app/(marketing)/page.tsx`. Generate from the same data source as the visible FAQ list.

### Finding: Write 3 long-form comparison articles

- **Severity**: High
- **Category**: Content E-E-A-T
- **Location**: New routes — `/blog/tideline-vs-looker`, `/blog/tideline-vs-mode`, `/blog/tideline-vs-tableau`
- **Current state**: No long-form competitor comparison content exists.
- **Recommended change**: Each article 1800+ words, structured:
  1. Lead paragraph — when to pick which (2-sentence summary)
  2. At-a-glance comparison table
  3. Setup time
  4. Pricing model
  5. Semantic layer / data modeling
  6. Embedded analytics
  7. Who picks which (concrete buyer profiles)
  8. FAQ section with FAQPage schema
- **Why**: AI systems heavily favor comprehensive articles >1500 words on commercial-investigation queries — Metabase gets 30%+ of inbound from this exact pattern.
- **Implementation hint**: Write as MDX in `content/blog/`. Use the blog post layout. Submit to Google Search Console after publish.

### Finding: Add Product schema to the pricing page

- **Severity**: High
- **Category**: Schema
- **Location**: `https://tideline.example/pricing`
- **Current state**: Three pricing tiers shown visually, no Product or Offer schema.
- **Recommended change**:
  ```html
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "name": "Tideline",
    "applicationCategory": "BusinessApplication",
    "operatingSystem": "Web",
    "offers": [
      { "@type": "Offer", "name": "Starter", "price": "0", "priceCurrency": "USD" },
      { "@type": "Offer", "name": "Team", "price": "25", "priceCurrency": "USD" },
      { "@type": "Offer", "name": "Enterprise", "price": "Contact", "priceCurrency": "USD" }
    ]
  }
  </script>
  ```
- **Why**: SoftwareApplication schema with priceRange is directly consumed by Google Knowledge Panel and Bing Copilot.
- **Implementation hint**: `app/(marketing)/pricing/page.tsx`. Only include `aggregateRating` if you actually have public reviews on G2/Capterra/Trustpilot — fabricating ratings violates schema.org guidelines.

### Finding: Submit to IndexNow for Bing Copilot

- **Severity**: High
- **Category**: Platform
- **Location**: Site-wide (build hook)
- **Current state**: Bing has only 12 of 47 site pages indexed. No IndexNow integration.
- **Recommended change**: Generate an IndexNow API key, ping Bing on every deploy:
  ```js
  import fetch from 'node-fetch';
  const key = process.env.INDEXNOW_KEY;
  const urls = [/* full URL list from sitemap */];
  await fetch('https://api.indexnow.org/IndexNow', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      host: 'tideline.example',
      key,
      keyLocation: `https://tideline.example/${key}.txt`,
      urlList: urls
    })
  });
  ```
  Also host `https://tideline.example/{key}.txt` containing the key string.
- **Why**: IndexNow is Bing's only fast-ingest path. Bing Copilot uses Bing's index — without IndexNow, new pages take 7–14 days to surface.
- **Implementation hint**: Add as a post-deploy step in CI (Vercel deploy hook, or GitHub Actions). The key file goes in `public/`.

---

### Medium

### Finding: Add SpeakableSpecification to top blog posts

- **Severity**: Medium
- **Category**: Schema
- **Location**: Top 5 blog posts by traffic
- **Current state**: No `speakable` properties anywhere.
- **Recommended change**: In each post's Article schema:
  ```json
  "speakable": {
    "@type": "SpeakableSpecification",
    "cssSelector": ["h1", ".lead-paragraph"]
  }
  ```
- **Why**: `speakable` is a hint to voice-first AI assistants (Alexa, Google Assistant) about which content to read aloud. Not yet a major signal but ~free to add.
- **Implementation hint**: Extend the existing Article JSON-LD generator. Add a `.lead-paragraph` class to the first paragraph in the blog post template.

### Finding: Create a Wikipedia stub

- **Severity**: Medium
- **Category**: Brand Authority
- **Location**: Wikipedia (external)
- **Current state**: No Wikipedia article exists.
- **Recommended change**: Write and submit a Wikipedia stub for Tideline once the company hits Wikipedia's notability threshold (3+ independent significant coverage in trade press). Required sources: TechCrunch coverage, a published podcast appearance, an independent technical review on Hacker News or InfoQ.
- **Why**: ChatGPT cites Wikipedia 47.9% of the time when answering category queries (Princeton 2024). Even a stub article creates a citable entity.
- **Implementation hint**: This is a content-and-PR project, not a code one. Owner: marketing. Start by securing one trade-press feature, then commission the Wikipedia article via a neutral editor.

---

### Low

### Finding: Add Open Graph image to every page

- **Severity**: Low
- **Category**: Platform
- **Location**: Site-wide
- **Current state**: Only the homepage has an OG image; other pages fall back to the favicon.
- **Recommended change**: Generate a per-page OG image (1200×630) with the page title overlaid on the Tideline navy background. Use Next.js `opengraph-image.tsx` route handlers.
- **Why**: OG images dramatically improve social click-through and are surfaced in some AI assistant previews.
- **Implementation hint**: For each route, add an `opengraph-image.tsx` file with the dynamic image generator.

---

## 30-day action plan

| Week | Theme | Findings to ship |
|---|---|---|
| **Week 1** | Unblock AI crawlers + Critical fixes | Unblock GPTBot, ship `llms.txt`, add Organization schema, add author bylines to all blog posts |
| **Week 2** | Schema + sameAs + comparison content | FAQPage schema, Product schema on pricing, draft 1st comparison article |
| **Week 3** | Content E-E-A-T | Publish 3 comparison articles, set up IndexNow for Bing |
| **Week 4** | Brand authority + polish | SpeakableSpecification on top posts, per-page OG images, Wikipedia stub project kickoff |

Re-audit at day 30 to track GEO Score lift. Realistic target: 65–72 (Fair → Good).

---

## Implementation note for downstream Claude

To apply every Critical and High finding in this file against the website source:

```
Read GEO-AUDIT.md. For every finding with Severity Critical or High, apply the Recommended change to the file or selector named in Implementation hint. Schema findings go in <head> of layout files; llms.txt goes at /llms.txt; content findings edit the page body.
```
