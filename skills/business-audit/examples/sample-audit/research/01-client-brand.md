# Client Brand Snapshot — Tideline

> Sample output from `website-intelligence` Phase 1.
> Produced verbatim by the bundled source skill — this plugin does not modify it.

## Brand Snapshot

- **Company:** Tideline
- **URL:** https://tideline.example
- **Primary Color:** `#0a1f3f` (deep navy)
- **Secondary Color:** `#3aafa9` (teal)
- **Accent Color:** `#f4f4f4` (paper)
- **Fonts:** Inter (heading) / Inter (body)
- **Tone:** Technical
- **Core Message:** "Analytics workspace for revenue teams who want answers."

## Logo

- **Type:** Wordmark
- **Format:** SVG
- **URL:** `https://tideline.example/logo.svg`

## Typography

| Role | Family | Weights | Source |
| --- | --- | --- | --- |
| Heading | Inter | 600, 700 | Google Fonts |
| Body | Inter | 400, 500 | Google Fonts |

Letter-spacing: `-0.01em` on headings, default on body. Line-height 1.5 body, 1.2 headings.

## Tone of Voice Analysis

The site reads as written by and for engineers: short sentences, specific verbs, no marketing fluff. There's no use of "we", no superlatives ("amazing", "best-in-class"), no exclamation points. The closest comparable tone is Stripe's developer docs or Linear's product pages.

This is a strength for credibility with technical buyers and a weakness for broader audiences that expect warmth or social proof.

## Key Messaging

- **Headline (verbatim):** "Analytics for revenue teams who want answers."
- **Subheading:** "Connect a database, build dashboards in 30 minutes."
- **Primary CTA:** "Get started" → `/signup`
- **Secondary CTA:** (none on the homepage)
- **Value proposition structure:** Outcome-focused but unquantified. No customers named, no metrics, no time/money comparison to alternatives.

## Site Architecture

Discovered via Firecrawl `/map`. 23 pages total.

```
/
├── /pricing
├── /security
├── /integrations
├── /docs/
│   ├── /docs/getting-started
│   ├── /docs/semantic-layer
│   ├── /docs/embedded
│   └── [11 more docs pages]
├── /blog/
│   └── [14 posts]
├── /about
├── /signup
└── /login
```

Navigation depth: 2 levels. No mega-menu. Footer has 14 unsorted links in a single column.

## Existing Content (sampled)

- **Homepage:** 312 words. Hero (28 words), feature grid with 3 cards (60 words total), FAQ section with 6 Q&A pairs (180 words), footer.
- **About:** 187 words. Three founder bios (no photos linked, no LinkedIn).
- **Pricing:** 95 words plus a three-tier price grid ($0 / $25 / Contact).
- **Blog (avg post):** ~1100 words. No author bylines.

## Conversion Strategy (observed)

Single CTA cluster funneling all visitors to `/signup`. No demo request path. No lead-gen content (no whitepapers, no email gates). Footer testimonials are unnamed ("Game changer for our team — Eng leader at a Series B fintech").

## Trust Signals (present / absent)

| Signal | Present? |
| --- | --- |
| Customer logos | ✗ |
| Named case studies | ✗ |
| Quantified social proof ("X customers", "Y queries / day") | ✗ |
| Reviews (G2, Capterra, Trustpilot) badge | ✗ |
| SOC 2 / security certs | ✓ (on /security) |
| Founder LinkedIn links | ✗ |
| Press mentions | ✗ |
