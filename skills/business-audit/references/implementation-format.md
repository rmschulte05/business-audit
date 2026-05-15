# Implementation-Ready Finding Format

Every actionable finding in `COMPETITIVE-ANALYSIS.md` and `GEO-AUDIT.md` MUST use this exact block format. The format exists so a downstream Claude Code session can read either Markdown file and execute the recommendations mechanically — no clarifying questions, no guessing.

---

## The block

```markdown
### Finding: [short imperative title]

- **Severity**: Critical | High | Medium | Low
- **Category**: Competitive | AI Citability | Technical | Schema | Brand Authority | Content E-E-A-T | Platform
- **Location**: `https://client.com/path` (or `index.html:42`)
- **Current state**: [quoted snippet of what's there now]
- **Recommended change**:
  ```html
  <!-- exact code, copy, or markup to insert or replace -->
  ```
- **Why**: [one sentence linking the change to a measurable outcome or cited research]
- **Implementation hint**: [where to put it, which file, which selector]
```

---

## Field rules

### Severity
- **Critical** — fix this week or AI systems will materially mis-represent or skip the site. Examples: AI crawlers blocked, no Organization schema, page returns 500.
- **High** — fix this month. Material visibility or conversion impact. Examples: missing FAQPage schema on FAQ pages, thin homepage content (<300 words), no llms.txt.
- **Medium** — fix this quarter. Real impact but not load-bearing. Examples: missing sameAs links, slow LCP on secondary pages.
- **Low** — nice-to-have polish. Examples: shorter meta description, alt-text tightening.

Cap **Critical** at 5 findings total across both files combined. If you have more, you're crying wolf — re-grade them.

### Category
Pick exactly one of the seven values. If a finding spans two (e.g., schema affects citability), pick the more actionable one — usually the more technical of the two.

### Location
- Use the full URL when the finding applies to a specific page: `https://acme.com/pricing`
- Use a file path with line number when it's a file in a known source repo: `src/app/layout.tsx:14`
- Use a CSS selector for repeated DOM patterns: `header > nav a[href]`
- "Site-wide" is acceptable only if the finding truly applies to every page

### Current state
- Quote verbatim what's on the site today
- Use a fenced code block if it's HTML/JSON/CSS
- Use a `> blockquote` if it's prose
- Keep it under ~6 lines. If the snippet is enormous, summarize and link to the page.

### Recommended change
- Provide the literal code, copy, or markup to ship
- Use the correct language fence (`html`, `json`, `css`, `md`, `txt`)
- Don't write "consider X" or "you might want to Y" — write the X or Y
- If a finding requires content the writer can't generate (e.g., "write an author bio"), provide a precise template the user fills in

### Why
- One sentence
- Tie to a measurable outcome: citation rate, GEO Score delta, conversion lift, traffic lift
- When citing research, name the source briefly (e.g., "Georgia Tech 2024 GEO study: definition patterns 2.1x citation rate")

### Implementation hint
- Tell the implementer WHERE to put it
- For Next.js apps: name the file (`app/layout.tsx`, `app/page.tsx`, `app/[slug]/page.tsx`)
- For static sites: name the file or the selector
- For CMS content: name the field (e.g., "Article body in Sanity, before the first H2")
- Include any prerequisite: "Add `<script type='application/ld+json'>` to `<head>` if not already present."

---

## Example — a well-formed finding

```markdown
### Finding: Add Organization schema with full sameAs array to site root

- **Severity**: Critical
- **Category**: Schema
- **Location**: Site-wide (homepage `<head>`)
- **Current state**: No JSON-LD `Organization` schema present on any page. Only a single `WebSite` block on the homepage.
- **Recommended change**:
  ```html
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "Acme Corp",
    "url": "https://acme.com",
    "logo": "https://acme.com/logo.png",
    "sameAs": [
      "https://www.linkedin.com/company/acme-corp",
      "https://twitter.com/acmecorp",
      "https://github.com/acmecorp",
      "https://www.youtube.com/@acmecorp",
      "https://en.wikipedia.org/wiki/Acme_Corp"
    ]
  }
  </script>
  ```
- **Why**: `sameAs` links to Wikipedia/LinkedIn/YouTube are the strongest known signal for AI entity recognition — Ahrefs Dec 2025 study shows 3x predictive lift on AI visibility vs. backlinks alone.
- **Implementation hint**: Add to the global `<head>` (in Next.js: `app/layout.tsx` `<head>` block; in static HTML: `index.html` `<head>`). Make sure exactly one Organization block exists site-wide.
```

---

## Anti-examples — what NOT to do

**Vague:**
> "Improve content depth."

Bad — no location, no current state, no change.

**Non-actionable:**
> "Consider adding more structured data."

Bad — "consider" makes it un-implementable.

**No why:**
> Finding with everything filled in EXCEPT a rationale.

Bad — the implementer can't prioritize without knowing impact.

If a finding can't fit this format, it's not implementation-ready — leave it out or convert it into a "Strategic recommendation" in a separate section.
