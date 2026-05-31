# Business Audit

A Claude Code plugin that runs a **competitive intelligence audit** and an **AI-search (GEO) audit** on any website in one pass, then writes two implementation-ready Markdown reports plus a polished interactive HTML dashboard.

Made by **Lucid**.

---

## Install (60 seconds)

```bash
git clone https://github.com/rmschulte05/business-audit ~/.claude/plugins/business-audit
```

Restart Claude Code. That's the whole install — everything the plugin needs is bundled.

---

## Firecrawl MCP (required for the competitive half)

The **competitive analysis** scrapes the client site, discovers competitors, and
deep-scrapes the top 5. That half needs Firecrawl MCP. **Without it, the
competitive report cannot run.**

The **GEO audit** half is independent: it runs a bundled deterministic Python
engine (standard library only — no install) plus `WebFetch`/`WebSearch`, so it
works even without Firecrawl. If you only have Python, you still get a full,
reproducible GEO score with a confidence band. Optionally set a free
`PSI_API_KEY` ([PageSpeed Insights](https://developers.google.com/speed/docs/insights))
to include real Core Web Vitals.

### 1. Get a free API key

Sign up at [https://firecrawl.dev](https://firecrawl.dev) — the free tier covers a handful of audits per month, which is plenty for testing.

### 2. Add Firecrawl to Claude Code

Open your Claude Code settings (`~/.claude/settings.json` or the in-app config), and add:

```json
{
  "mcpServers": {
    "firecrawl": {
      "command": "npx",
      "args": ["-y", "firecrawl-mcp"],
      "env": {
        "FIRECRAWL_API_KEY": "fc-YOUR_KEY_HERE"
      }
    }
  }
}
```

Replace `fc-YOUR_KEY_HERE` with the key from step 1.

### 3. Restart Claude Code

After restart, you should see `mcp__firecrawl__scrape`, `mcp__firecrawl__map`, and `mcp__firecrawl__search` in your available tools. If you don't, the plugin will refuse to run and tell you what's missing.

---

## Usage

In any Claude Code session:

```
audit https://example.com — B2B SaaS for engineering teams
```

or just type `/business-audit` and the skill will ask for the URL and niche.

Expect 5–15 minutes per audit, depending on site size.

---

## What you get

Files dropped into your working directory:

| File | Purpose |
| --- | --- |
| `research/01-client-brand.md` | Brand snapshot — colors, fonts, tone, messaging, site architecture. |
| `research/02-competitor-analysis.md` | Top-5 deep scrape, comparison matrix, "Patterns of the top 10%". |
| `competitive-analysis.html` | Print-ready PDF-export competitive report. |
| `GEO-AUDIT.json` | Machine-readable: composite score, per-pillar scores, confidence band, and every signal with its evidence. |
| `GEO-AUDIT-REPORT.md` | Client-facing GEO report — score **with confidence band**, 6-pillar breakdown, prioritized fixes, 30-day plan. |
| `dashboard.html` | The combined view — two tabs (**Competitive** / **GEO**) rendered from the files above. |

The GEO score is **reproducible**: it's computed in code from observed HTTP/HTML
evidence, so re-running on the same site yields the same number. The report shows
a confidence band (how much of the score is measured vs. judged) so it's honest
enough to hand a paying client.

The two Markdown files in `research/` plus `GEO-AUDIT.json` are the
**implementation source of truth**. Open them in a fresh Claude Code session
inside your website's repo and paste:

```
Read research/02-competitor-analysis.md and GEO-AUDIT-REPORT.md. Implement every Critical and High finding against this codebase.
```

Claude can act on those reports directly.

## What the audit covers

**Competitive intelligence** — brand extraction (logo, colors, typography, tone, messaging), top-10 competitor discovery, top-5 deep scrape, 8-criteria scoring matrix, winning-pattern synthesis.

**Generative Engine Optimization (GEO)** — weighted score across 6 categories:

| Category | Weight |
| --- | --- |
| AI Citability | 25% |
| Brand Authority | 20% |
| Content E-E-A-T | 20% |
| Technical GEO | 15% |
| Schema & Structured Data | 10% |
| Platform Optimization | 10% |

Per-platform readiness for Google AI Overviews, ChatGPT, Perplexity, Gemini, and Bing Copilot. Competitor benchmark on key signals (schema coverage, `llms.txt`, AI crawler access, top-page citability).

---

## License

MIT. Fork it, ship it, improve it.

---

Made with care by **Lucid**.
