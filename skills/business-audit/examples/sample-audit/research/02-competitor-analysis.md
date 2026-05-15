# Competitive Analysis — Tideline (B2B SaaS, analytics workspace)

> Sample output from `website-intelligence` Phase 2.
> Produced verbatim by the bundled source skill — this plugin does not modify it.

## Top 10 Candidates (initial screen)

Found via Firecrawl search for "analytics workspace alternatives" + "BI tools 2026" + "data exploration platform for SQL teams".

| Rank | Name | URL |
| --- | --- | --- |
| 1 | Mode | mode.com |
| 2 | Hex | hex.tech |
| 3 | Metabase | metabase.com |
| 4 | Lightdash | lightdash.com |
| 5 | Preset | preset.io |
| 6 | Sigma | sigmacomputing.com |
| 7 | Count | count.co |
| 8 | Omni | omni.co |
| 9 | Holistics | holistics.io |
| 10 | Lumi | lumi.example |

## Scoring Matrix (top 5)

| Competitor | Search | Reviews | Design | Mobile | Content | Social Proof | CTA | Speed | **Total** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mode | 9 | 9 | 9 | 8 | 9 | 10 | 8 | 8 | **70** |
| Hex | 8 | 8 | 10 | 9 | 9 | 8 | 9 | 9 | **70** |
| Lightdash | 8 | 8 | 8 | 9 | 8 | 8 | 9 | 7 | **65** |
| Preset | 7 | 8 | 8 | 9 | 8 | 9 | 8 | 8 | **65** |
| Metabase | 9 | 9 | 6 | 8 | 9 | 9 | 8 | 6 | **64** |
| **Tideline** (client) | 3 | 2 | 7 | 8 | 4 | 2 | 5 | 8 | **39** |

## Deep Scrape — Mode (https://mode.com)

- **Visual identity:** Ink `#0d1117`, accent `#ff5722` (orange), background `#fafafa`. Söhne (heading) / Inter (body). Photography is studio shots of real people at laptops.
- **Headline:** "The collaborative data platform for high-performance teams."
- **Primary CTA:** "Book a demo" · Secondary: "Try free"
- **Architecture:** 4-level nav (Product / Solutions / Resources / Customers). 80+ pages indexed.
- **Conversion:** 6 customer logos above the fold; "Trusted by 60% of the Fortune 100 data teams" quantified claim; case-study links to named companies.
- **Strengths:** Quantified social proof, interactive notebook embed in hero, two-CTA strategy.
- **Weaknesses:** Pricing hidden behind sales call; heavy gated content for whitepapers.

## Deep Scrape — Hex (https://hex.tech)

- **Visual identity:** Black `#1c1c1c`, chartreuse `#fff700`, off-white `#fafafa`. GT America (heading), GT America Mono (code), Inter (body).
- **Headline:** "The data workspace where teams ship insights."
- **Primary CTA:** "Get started free" · Secondary: "Talk to sales"
- **Architecture:** 5-level nav. Heavy docs presence (200+ articles).
- **Conversion:** Hero plays an inline product video on scroll. Customer logos below the fold. "Loved by data teams at" copy.
- **Strengths:** Strongest visual identity in the category; comprehensive docs structure for AI citation; inline video.
- **Weaknesses:** Visual noise — three animated elements competing in hero; heavy jargon ("notebooks", "magic cells") without first-mention definitions.

## Deep Scrape — Lightdash (https://lightdash.com)

- **Visual identity:** Purple `#7c3aed`, amber `#fbbf24`, white. Inter everywhere.
- **Headline:** "The open source alternative to Looker."
- **Primary CTA:** "Start free" · GitHub star count visible in nav
- **Architecture:** 3-level nav. `/docs` heavily linked.
- **Conversion:** GitHub stars as social proof. "Built by ex-Looker engineers" borrowed authority.
- **Strengths:** Eight-word positioning against a known incumbent; open-source as a trust signal; chunkable docs.
- **Weaknesses:** Depends on Looker brand recognition (loses force outside that audience); hero video is 8 MB and blocks LCP.

## Deep Scrape — Preset (https://preset.io)

- **Visual identity:** Cyan `#20a7c9`, navy `#1e3a8a`, pale blue `#f0f9ff`. Söhne / Inter.
- **Headline:** "The complete Apache Superset cloud platform."
- **Primary CTA:** "Try free for 14 days"
- **Architecture:** Standard 4-level nav. `/compare` pages for Tableau, Looker, Mode.
- **Conversion:** Customer story videos with named CTOs on camera. "From the creators of Superset" sub-tagline borrows authority.
- **Strengths:** Borrowed-authority tagline; dedicated `/compare/*` pages catch AI Overview citations.
- **Weaknesses:** Pricing page email-gated; docs live on a subdomain — fragments AI crawling.

## Deep Scrape — Metabase (https://metabase.com)

- **Visual identity:** Blue `#509ee3`, green `#88bf4d`, white. Lato (heading) / Inter (body). Rounded illustrations from 2018.
- **Headline:** "The easy, open source way for everyone in your company to ask questions."
- **Primary CTA:** "Get started" → cloud trial, alongside "Download" → self-host
- **Architecture:** 4-level nav. 100+ pages indexed. Strong `/blog` and `/learn` sections.
- **Conversion:** Two distinct paths above the fold (cloud + self-host). "50,000+ companies" claim with named logos.
- **Strengths:** Two-path CTA strategy handles different buyer intents; comprehensive comparison pages catch AI Overviews.
- **Weaknesses:** Dated visual design; slow homepage LCP (3.4 s).

## Patterns of the Top 10%

What ALL five top competitors do that **Tideline doesn't yet**:

### 1. Quantified social proof above the fold

Mode says "60% of Fortune 100". Metabase says "50,000+ companies". Hex shows named logos. Lightdash shows GitHub star count. Preset shows customer-story videos with named CTOs.

Tideline shows nothing.

### 2. Two-path CTA strategy

Every top competitor offers a high-intent CTA ("Book a demo" / "Talk to sales") AND a low-intent CTA ("Try free" / "Start free" / "Download"). This handles enterprise and self-serve buyers in the same hero.

Tideline funnels everyone to a single signup form.

### 3. Comparison pages vs. incumbents

Metabase has `/looker-alternative`, Preset has `/tableau-vs-superset`, Lightdash leads with "alternative to Looker". These pages are the highest-converting traffic in the category — they dominate Google AI Overview citations for "X alternatives" queries.

Tideline has no `/compare/*` routes.

### 4. Real product UI in the hero

Hex plays a 30-second product loop. Mode embeds an interactive notebook. Preset shows customer-story video. The "show, don't tell" pattern dominates this category.

Tideline shows a static gradient block.

### 5. Named expert authors on blog content

All five competitors have author bylines on blog posts, with photos, LinkedIn links, and `/team/[slug]` pages. The blog posts also include JSON-LD `Article` schema with `author.@type: Person`.

Tideline's blog posts have dates but no author names.

## Comparison Table (concise, for the dashboard)

This is the table the dashboard's Competitive tab renders verbatim:

| Competitor | Search | Reviews | Design | Mobile | Content | Social Proof | CTA | Speed | **Total** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mode | 9 | 9 | 9 | 8 | 9 | 10 | 8 | 8 | **70** |
| Hex | 8 | 8 | 10 | 9 | 9 | 8 | 9 | 9 | **70** |
| Lightdash | 8 | 8 | 8 | 9 | 8 | 8 | 9 | 7 | **65** |
| Preset | 7 | 8 | 8 | 9 | 8 | 9 | 8 | 8 | **65** |
| Metabase | 9 | 9 | 6 | 8 | 9 | 9 | 8 | 6 | **64** |
| **Tideline** | 3 | 2 | 7 | 8 | 4 | 2 | 5 | 8 | **39** |

## SEO / Keyword Landscape

Top competitors rank for: "analytics workspace", "open source BI tool", "Looker alternative", "modern data stack", "embedded analytics SaaS".

Tideline does not rank in the top 50 for any of these as of audit date.

## Recommended Design Direction (from this analysis)

- Keep Tideline's navy + teal palette but add a single accent color for CTAs (Mode's orange and Hex's chartreuse both work to draw the eye to a single button).
- Replace the static hero gradient with a 30-second product loop video.
- Add 3 customer logos and one named quote above the fold.
- Add a second "Talk to sales" CTA alongside the existing "Get started".
- Build `/compare/looker`, `/compare/tableau`, `/compare/mode` pages.
- Add author bylines, photos, and bio pages to the blog.
