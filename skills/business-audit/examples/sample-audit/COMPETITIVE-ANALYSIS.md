# Competitive Analysis — Tideline

> Audit date: 2026-05-15 · Source: business-audit Claude Code plugin
>
> This file is the **source of truth for competitive recommendations**. Every finding follows the [implementation-ready format](../../references/implementation-format.md) — a downstream Claude Code session can read this and apply the changes mechanically.
>
> _This is a sample audit for a fictional company. Use it as a reference for shape and density — real audits will have real URLs and verbatim quotes._

---

## Executive summary

Tideline is a B2B SaaS for revenue analytics dashboards, competing in a mature category dominated by Mode, Hex, and Lightdash. The site reads as an engineering prototype — sparse copy, no social proof, no pricing — while every top competitor leads with a quantified value prop, named customer logos, and an interactive product demo above the fold. The single biggest opportunity is shipping a homepage that earns its first 10 seconds: add a quantified outcome in the headline, three customer logos with named quotes below it, and a 30-second product loop video before the H2.

---

## Client snapshot

**Company:** Tideline
**URL:** https://tideline.example
**Business type:** saas

**Brand colors:** `#0a1f3f` (primary navy) · `#3aafa9` (secondary teal) · `#f4f4f4` (neutral background)
**Typography:** Inter (headings + body, all weights)
**Tone:** Technical
**Headline:** "Analytics for revenue teams who want answers."
**Primary CTA:** "Get started" → `/signup`
**Conversion strategy:** Single CTA leading to self-serve signup. No demo request, no pricing tier comparison, no lead-gen content. Two thin testimonials on the homepage, no logos, no case studies.

---

## Top 5 competitors

### 1. Mode — https://mode.com
- **Colors:** `#0d1117`, `#ff5722`, `#fafafa`
- **Typography:** Söhne (heading) / Inter (body)
- **Headline:** "The collaborative data platform for high-performance teams."
- **Primary CTA:** "Book a demo" + secondary "Try free"
- **Strengths:**
  - Quantified social proof: "Trusted by 60% of the Fortune 100 data teams"
  - 6 customer logos above the fold with named case studies linked
  - Interactive notebook embed in hero — visitor can actually click and explore
- **Weaknesses:**
  - Pricing hidden behind sales call
  - Heavy gated content for whitepapers

### 2. Hex — https://hex.tech
- **Colors:** `#1c1c1c`, `#fff700`, `#fafafa`
- **Typography:** GT America (heading) / GT America Mono (code) / Inter (body)
- **Headline:** "The data workspace where teams ship insights."
- **Primary CTA:** "Get started free" + "Talk to sales"
- **Strengths:**
  - Strong visual identity — chartreuse-on-black is unforgettable
  - Documentation depth: 200+ articles, indexed and AI-citable
  - Video product demo plays inline on scroll
- **Weaknesses:**
  - High visual noise — three animated elements competing in hero
  - Heavy reliance on jargon ("notebooks", "magic cells") without first-mention definitions

### 3. Lightdash — https://lightdash.com
- **Colors:** `#7c3aed`, `#fbbf24`, `#ffffff`
- **Typography:** Inter (everything)
- **Headline:** "The open source alternative to Looker."
- **Primary CTA:** "Start free" + GitHub star count visible
- **Strengths:**
  - Killer positioning: defines self against a known incumbent in 8 words
  - Open source repo prominently linked, GitHub star count = social proof
  - Comprehensive `/docs` with anchor links — chunkable for AI
- **Weaknesses:**
  - Dependent on Looker brand recognition (loses force outside that audience)
  - Hero video is 8MB, blocks LCP

### 4. Metabase — https://metabase.com
- **Colors:** `#509ee3`, `#88bf4d`, `#ffffff`
- **Typography:** Lato (heading) / Inter (body)
- **Headline:** "The easy, open source way for everyone in your company to ask questions."
- **Primary CTA:** "Get started" → cloud trial, plus self-host download
- **Strengths:**
  - Two distinct paths above the fold (cloud trial + self-host) handle different intents
  - 50,000+ companies citation with specific named logos
  - Comprehensive comparison pages vs. Tableau, Looker, Power BI — caught in AI Overview citations
- **Weaknesses:**
  - Dated visual design (rounded illustrations from 2018)
  - Slow homepage LCP (3.4s)

### 5. Preset — https://preset.io
- **Colors:** `#20a7c9`, `#1e3a8a`, `#f0f9ff`
- **Typography:** Söhne (heading) / Inter (body)
- **Headline:** "The complete Apache Superset cloud platform."
- **Primary CTA:** "Try free for 14 days"
- **Strengths:**
  - Clear sub-tagline below headline: "From the creators of Superset" — borrowed authority
  - Side-by-side comparison vs Tableau/Looker on dedicated `/compare` pages
  - Customer story videos with named CTOs speaking
- **Weaknesses:**
  - Pricing page requires email gate
  - Documentation lives on a subdomain — fragments AI crawling

---

## Comparison matrix

| Competitor | Search | Reviews | Design | Mobile | Content | Social Proof | CTA | Speed | **Total** |
|---|---|---|---|---|---|---|---|---|---|
| Mode | 9 | 9 | 9 | 8 | 9 | 10 | 8 | 8 | **70** |
| Hex | 8 | 8 | 10 | 9 | 9 | 8 | 9 | 9 | **70** |
| Lightdash | 8 | 8 | 8 | 9 | 8 | 8 | 9 | 7 | **65** |
| Metabase | 9 | 9 | 6 | 8 | 9 | 9 | 8 | 6 | **64** |
| Preset | 7 | 8 | 8 | 9 | 8 | 9 | 8 | 8 | **65** |
| **Tideline** | 3 | 2 | 7 | 8 | 4 | 2 | 5 | 8 | **39** |

---

## Patterns of the top 10%

What ALL top competitors do that Tideline doesn't yet:

1. **Quantified social proof above the fold** — Mode ("60% of Fortune 100"), Metabase ("50,000+ companies"), Hex (named logos), Lightdash (GitHub stars). Tideline shows nothing.
2. **Two-path CTA strategy** — every competitor offers both a high-intent CTA ("Book a demo") and a low-intent CTA ("Try free" / "View pricing"). Tideline funnels everyone to signup.
3. **Comparison pages vs. incumbents** — Metabase has `/looker-alternative`, Preset has `/tableau-vs`, Lightdash leads with "alternative to Looker". These pages dominate AI Overview citations for "X alternatives" queries.

---

## Prioritized findings

Every finding below uses the [implementation-ready format](../../references/implementation-format.md). Apply them in severity order.

### Critical

### Finding: Rewrite homepage headline with quantified outcome

- **Severity**: Critical
- **Category**: Competitive
- **Location**: `https://tideline.example/` (hero H1)
- **Current state**: "Analytics for revenue teams who want answers."
- **Recommended change**:
  ```html
  <h1>Cut your revenue reporting cycle from 3 days to 30 minutes.</h1>
  <p class="subhead">Tideline is the analytics workspace 40+ revenue teams use to ship dashboards in a single afternoon — not a quarter.</p>
  ```
- **Why**: Every top competitor leads with a quantified outcome; vague headlines lose 50%+ of below-the-fold engagement in B2B SaaS A/B tests (Wynter 2024).
- **Implementation hint**: `app/(marketing)/page.tsx` — replace the first `<h1>` and the following `<p>`. Keep the existing CTA buttons below.

### Finding: Add 3 named customer logos with quotes above the fold

- **Severity**: Critical
- **Category**: Competitive
- **Location**: `https://tideline.example/` (between hero and feature grid)
- **Current state**: No customer logos anywhere on the homepage. Two unnamed testimonials in the footer.
- **Recommended change**:
  ```html
  <section class="social-proof">
    <p class="eyebrow">Trusted by revenue teams at</p>
    <div class="logo-row">
      <img src="/logos/customer-1.svg" alt="[Customer 1 name]">
      <img src="/logos/customer-2.svg" alt="[Customer 2 name]">
      <img src="/logos/customer-3.svg" alt="[Customer 3 name]">
    </div>
    <blockquote>
      "[Verbatim quote from a real named customer — get their permission first.]"
      <cite>— [Name], [Title], [Company]</cite>
    </blockquote>
  </section>
  ```
- **Why**: Named social proof is the strongest known precursor to enterprise inquiry — Nielsen/Norman data shows logo + named quote lifts demo-request rate 2.4x in B2B SaaS.
- **Implementation hint**: Insert after the hero section in `app/(marketing)/page.tsx`. Get permission from 3 current customers before launching; SVG logos under `/public/logos/`.

---

### High

### Finding: Add comparison page targeting "Looker alternatives"

- **Severity**: High
- **Category**: Competitive
- **Location**: `https://tideline.example/compare/looker` (new route)
- **Current state**: No `/compare/*` routes exist. Searching "tideline vs looker" returns nothing on Tideline's site.
- **Recommended change**:
  ```md
  # Tideline vs Looker

  A side-by-side comparison for revenue teams considering both platforms.

  ## At a glance

  | | Tideline | Looker |
  |---|---|---|
  | Time to first dashboard | 30 minutes | 2 weeks |
  | Pricing model | Per seat, transparent | Quote-based, opaque |
  | SQL semantic layer | Yes | Yes (LookML) |
  | Embedded analytics | Yes | Yes |
  | Open source option | No | No |

  [Continue with sections: Pricing, Setup, Integrations, Security, FAQ, "Who picks which"]
  ```
- **Why**: Comparison pages own AI Overview citations for "X alternatives" queries — Metabase and Lightdash get 30%+ of their inbound from this pattern (Ahrefs Mar 2026).
- **Implementation hint**: Add as `app/(marketing)/compare/looker/page.tsx`. Also add `app/(marketing)/compare/tableau/page.tsx` and `app/(marketing)/compare/mode/page.tsx`. Link from the footer.

### Finding: Add 30-second product loop video to hero

- **Severity**: High
- **Category**: Competitive
- **Location**: `https://tideline.example/` (hero, right column)
- **Current state**: Static gradient block with the word "Dashboard" in serif type. No actual product visible.
- **Recommended change**:
  ```html
  <video autoplay muted loop playsinline
         poster="/hero-poster.jpg"
         class="hero-video"
         width="640" height="480">
    <source src="/hero-loop.webm" type="video/webm">
    <source src="/hero-loop.mp4" type="video/mp4">
  </video>
  ```
  Record a 30-second screen capture of the actual product: a user dragging a metric onto a chart, the chart re-rendering, exporting to Slack. Encode at <2MB.
- **Why**: Hex, Mode, and Preset all use looping product video in the hero — visitors form trust judgments within 50ms, and seeing real UI beats any prose description.
- **Implementation hint**: `app/(marketing)/page.tsx` hero section. Put the video files in `/public/`. Add `prefers-reduced-motion` fallback to the poster image only.

### Finding: Add a "Talk to sales" CTA next to "Get started"

- **Severity**: High
- **Category**: Competitive
- **Location**: `https://tideline.example/` (hero CTA cluster) and site nav
- **Current state**: Single "Get started" button. No alternative for high-intent enterprise visitors who want a demo conversation.
- **Recommended change**:
  ```html
  <div class="cta-cluster">
    <a href="/signup" class="btn btn-primary">Start free</a>
    <a href="/demo" class="btn btn-secondary">Talk to sales</a>
  </div>
  ```
  Build `/demo` as a Calendly-style scheduler with 3 fields: name, work email, team size. Route to a real human.
- **Why**: A single CTA funnels both self-serve and enterprise intent into the wrong bucket — enterprise visitors abandon when they can't talk to a person, and self-serve users feel sales-pressured. Mode reports 2-CTA hero lifts qualified demo bookings 3.1x.
- **Implementation hint**: Update `components/Hero.tsx` CTA cluster and `components/Nav.tsx`. New route at `app/(marketing)/demo/page.tsx`.

---

### Medium

### Finding: Add customer count to nav or footer

- **Severity**: Medium
- **Category**: Competitive
- **Location**: `https://tideline.example/` (footer or below-nav banner)
- **Current state**: No mention of customer count anywhere on the site.
- **Recommended change**:
  ```html
  <p class="customer-count">Used by 40+ revenue teams shipping dashboards every week.</p>
  ```
  Update the number monthly from your actual customer count.
- **Why**: Concrete numbers ground claims; "thousands" sounds vague, "40+" sounds honest.
- **Implementation hint**: Add to `components/Footer.tsx`. Pull the number from a CMS or env var so non-engineers can update it.

### Finding: Replace stock illustrations with screenshots in the features section

- **Severity**: Medium
- **Category**: Competitive
- **Location**: `https://tideline.example/` (features grid, three cards)
- **Current state**: Each feature card uses an abstract gradient + emoji icon.
- **Recommended change**: Replace each card's visual with a 480×320 product screenshot showing the actual feature in use. Add an alt text describing what's shown.
- **Why**: Hex and Preset use real product screenshots; abstract visuals reduce credibility and add zero information.
- **Implementation hint**: `components/FeatureGrid.tsx`. Export PNGs from Figma if no real product yet, but eventually replace with real screenshots.

---

### Low

### Finding: Tighten the footer link structure

- **Severity**: Low
- **Category**: Competitive
- **Location**: `https://tideline.example/` (footer)
- **Current state**: Single column with 14 unsorted links.
- **Recommended change**: Group into 4 columns: Product, Resources, Company, Legal. Match the Mode/Metabase footer pattern.
- **Why**: Scannable footers reduce bounce on long pages by ~8% (Baymard 2024).
- **Implementation hint**: `components/Footer.tsx`. Use a CSS grid with `grid-template-columns: repeat(4, 1fr)` on desktop, single column on mobile.

---

## Quick wins (this week)

5 findings the team can ship in under a day each:

- [ ] Rewrite homepage headline with quantified outcome (Critical)
- [ ] Add 3 customer logos to homepage (Critical — needs permission)
- [ ] Add "Talk to sales" CTA (High)
- [ ] Add customer count to footer (Medium)
- [ ] Tighten footer link structure (Low)

---

## Implementation note for downstream Claude

To apply every Critical and High finding in this file against the website source:

```
Read COMPETITIVE-ANALYSIS.md. For every finding with Severity Critical or High, apply the Recommended change to the file or selector named in Implementation hint. Skip Medium and Low for now.
```
