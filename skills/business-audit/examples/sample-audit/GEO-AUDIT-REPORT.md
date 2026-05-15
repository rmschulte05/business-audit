# GEO Audit Report: Tideline

> Sample output from `geo-audit`.
> Produced verbatim by the bundled source skill — this plugin does not modify it.

**Audit Date:** 2026-05-15
**URL:** https://tideline.example
**Business Type:** SaaS
**Pages Analyzed:** 23

---

## Executive Summary

**Overall GEO Score: 47/100 (Poor)**

Tideline's technical foundation is solid (SSR Next.js, fast LCP, clean URL structure) but its AI-search visibility is severely limited by missing structured data and zero brand-authority signals. Closing 4 of the 6 Critical issues below should lift the composite score by 18–25 points within 30 days.

### Score Breakdown

| Category | Score | Weight | Weighted Score |
|---|---|---|---|
| AI Citability | 52/100 | 25% | 13.0 |
| Brand Authority | 22/100 | 20% | 4.4 |
| Content E-E-A-T | 41/100 | 20% | 8.2 |
| Technical GEO | 78/100 | 15% | 11.7 |
| Schema & Structured Data | 15/100 | 10% | 1.5 |
| Platform Optimization | 38/100 | 10% | 3.8 |
| **Overall GEO Score** | | | **47/100** |

---

## Critical Issues (Fix Immediately)

### 1. GPTBot blocked in robots.txt

**Pages affected:** Site-wide
**Detail:** `robots.txt` contains `User-agent: GPTBot \n Disallow: /`. ChatGPT (web search, 200M+ weekly users per OpenAI Feb 2026) cannot index any page on the site.
**Recommended fix:** Remove the GPTBot block. Explicitly allow GPTBot, ClaudeBot, PerplexityBot, Google-Extended, OAI-SearchBot. Keep `Disallow: /admin/` and `/api/`.

### 2. No `Organization` schema with `sameAs`

**Pages affected:** Site-wide
**Detail:** Homepage has a single `WebSite` JSON-LD block. No `Organization`, no `sameAs` linking the brand to LinkedIn, YouTube, GitHub, or Wikipedia.
**Recommended fix:** Add an `Organization` JSON-LD block to the global layout `<head>` with a full `sameAs` array (LinkedIn, X/Twitter, GitHub, YouTube — and Wikipedia once the entry exists).

### 3. No `/llms.txt`

**Pages affected:** Site root
**Detail:** `https://tideline.example/llms.txt` returns 404. Three of the five competitors (Mode, Lightdash, Metabase) publish one.
**Recommended fix:** Ship `public/llms.txt` with H1, blockquote description, and H2 sections for Docs, Product, About.

### 4. No author bylines on blog posts

**Pages affected:** All 14 posts under `/blog/*`
**Detail:** Posts have a date but no author name, photo, or bio. The `/about` page lists three founders but doesn't link to their writing. Princeton 2024 GEO study: content without a named expert author is cited 4–7x less by AI systems.
**Recommended fix:** Add an author block to the blog post template. Create `/team/[slug]` author profile pages. Emit JSON-LD `Article` schema with `author.@type: Person`.

---

## High Priority Issues

### 5. No `FAQPage` schema on the homepage FAQ

**Pages affected:** `/`
**Detail:** Six visible Q&A pairs in HTML, zero structured data wrapping them.
**Recommended fix:** Emit `FAQPage` JSON-LD generated from the same data source as the visible FAQ.

### 6. No `SoftwareApplication` schema on `/pricing`

**Pages affected:** `/pricing`
**Detail:** Three tiers shown visually; no `Product` or `SoftwareApplication` JSON-LD; no `Offer` markup.
**Recommended fix:** Add `SoftwareApplication` schema with an `offers` array per tier. Include `aggregateRating` ONLY if real public reviews exist (G2/Capterra/Trustpilot).

### 7. Bing index only covers 12 of 47 pages

**Pages affected:** Site-wide
**Detail:** Bing Webmaster Tools shows 12 indexed pages. No IndexNow setup.
**Recommended fix:** Add IndexNow integration as a post-deploy step. Generate an API key, host the key file at `/{key}.txt`, ping `api.indexnow.org/IndexNow` with the updated URL list on every deploy.

### 8. No long-form comparison content

**Pages affected:** Missing routes — `/blog/tideline-vs-looker`, `/blog/tideline-vs-mode`, `/blog/tideline-vs-tableau`
**Detail:** Top competitors (Metabase, Lightdash, Preset) each have multiple long-form comparison pages that dominate AI Overview citations for "X alternatives" queries.
**Recommended fix:** Write 3 articles, 1800+ words each, structured with at-a-glance table → pricing → setup → semantic layer → embedded → "who picks which" → FAQ with `FAQPage` schema.

---

## Medium Priority Issues

### 9. No `SpeakableSpecification` on top blog posts

**Pages affected:** Top 5 blog posts by traffic
**Detail:** No `speakable` property in `Article` schema.
**Recommended fix:** Add `"speakable": { "@type": "SpeakableSpecification", "cssSelector": ["h1", ".lead-paragraph"] }` to each post's JSON-LD. Mark the first paragraph with `class="lead-paragraph"`.

### 10. No Wikipedia entity

**Pages affected:** External
**Detail:** Tideline has no Wikipedia article. ChatGPT cites Wikipedia 47.9% of the time on category queries (Princeton 2024).
**Recommended fix:** This is a PR project, not code. Secure 3+ independent significant trade-press coverage first (TechCrunch, podcast appearance, independent technical review). Then commission a Wikipedia stub via a neutral editor.

---

## Low Priority Issues

### 11. Per-page Open Graph images missing

**Pages affected:** All pages except homepage
**Detail:** Only the homepage has an OG image; other pages fall back to the favicon.
**Recommended fix:** Add `opengraph-image.tsx` route handlers per top-level route. 1200×630 with the page title overlaid on the Tideline navy.

---

## Category Deep Dives

### AI Citability (52/100)

The site has citable content but it's not packaged for extraction. Definitions are buried inside long paragraphs rather than offered as standalone answer blocks. Statistics are scarce. Authority quotes (named experts, customer voices) are absent. Best citable passage: the SOC 2 disclosure on `/security`, which is fact-rich and answer-first. Worst: the homepage hero, which is 28 words with no extractable answer.

### Brand Authority (22/100)

Almost no presence on the platforms AI models train on. No YouTube channel. No Reddit threads from the founders. No Wikipedia entry. LinkedIn company page exists but has 14 followers. The strongest brand-authority signal is the GitHub org (47 stars across a couple of public packages).

### Content E-E-A-T (41/100)

Experience and Expertise are evident in the writing — the founders clearly know the domain. But the site doesn't surface that expertise: no author bylines, no founder bios on the about page, no LinkedIn links, no podcast appearances or conference talks listed.

### Technical GEO (78/100)

Strongest category. Next.js with SSR; LCP 1.4 s on the homepage; clean URL structure; mobile-first; valid HTML; correct canonical tags. The only deduction is the GPTBot block in `robots.txt` (Critical issue #1).

### Schema & Structured Data (15/100)

Weakest category. Only a single `WebSite` JSON-LD block on the homepage. Missing: `Organization`, `sameAs`, `Article`, `FAQPage`, `SoftwareApplication`, `BreadcrumbList`. No `speakable`. The pricing page should be the easiest win — it already has the data, just needs the markup.

### Platform Optimization (38/100)

Google AI Overviews readiness: 51 — page-1 organic ranking missing on category terms is the blocker.
ChatGPT (Bing index + Wikipedia): 38 — no Wikipedia entry; Bing index thin (only 12 pages).
Perplexity: 34 — heavy weight on Reddit/forums; Tideline has zero presence.
Gemini: 44 — no Knowledge Panel; no YouTube channel.
Bing Copilot: 42 — no IndexNow integration.

---

## Quick Wins (Implement This Week)

1. Remove the GPTBot block in `robots.txt` (5 minutes).
2. Ship `Organization` schema with `sameAs` in `app/layout.tsx` `<head>` (30 minutes).
3. Write and publish `public/llms.txt` (1 hour).
4. Add `FAQPage` schema to the homepage FAQ (30 minutes).
5. Add author byline + bio block to the blog post template (2 hours).

---

## 30-Day Action Plan

### Week 1: Unblock AI crawlers and ship Critical fixes
- [ ] Remove GPTBot block in robots.txt
- [ ] Add Organization schema with full sameAs array site-wide
- [ ] Ship /llms.txt
- [ ] Add author bylines + bio pages for all blog posts

### Week 2: Schema and comparison content
- [ ] Add FAQPage schema to homepage
- [ ] Add SoftwareApplication schema to /pricing
- [ ] Draft the first long-form comparison article

### Week 3: Content E-E-A-T and Bing
- [ ] Publish 3 comparison articles
- [ ] Set up IndexNow for Bing Copilot

### Week 4: Brand authority and polish
- [ ] Add SpeakableSpecification to top blog posts
- [ ] Add per-page Open Graph images
- [ ] Kick off Wikipedia stub project (PR-side, not engineering)

Re-audit at day 30 to track GEO Score lift. Realistic target: 65–72 (Fair → Good).

---

## Appendix: Pages Analyzed

| URL | Title | GEO Issues |
| --- | --- | --- |
| / | Tideline — Analytics for revenue teams | 6 |
| /pricing | Pricing — Tideline | 3 |
| /security | Security — Tideline | 1 |
| /integrations | Integrations — Tideline | 2 |
| /docs/getting-started | Getting started | 2 |
| /docs/semantic-layer | Semantic layer | 2 |
| /docs/embedded | Embedded analytics | 2 |
| /about | About Tideline | 3 |
| /blog/[14 posts] | (various) | 14 × 3 |
