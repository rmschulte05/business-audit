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

## Firecrawl MCP (required)

The audit scrapes the client site, discovers competitors, and deep-scrapes the top 5. It needs Firecrawl MCP to do that. **The plugin will not run without it.**

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

Five files dropped into your working directory:

| File | Producer | Purpose |
| --- | --- | --- |
| `research/01-client-brand.md` | `website-intelligence` | Brand snapshot — colors, fonts, tone, messaging, site architecture. |
| `research/02-competitor-analysis.md` | `website-intelligence` | Top-5 deep scrape, comparison matrix, "Patterns of the top 10%". |
| `competitive-analysis.html` | `website-intelligence` | Print-ready PDF-export competitive report. |
| `GEO-AUDIT-REPORT.md` | `geo-audit` | Overall GEO Score, 6-category breakdown, prioritized issues, 30-day plan. |
| `dashboard.html` | this plugin | The new combined view — two tabs (**Competitive** / **GEO**) rendered from the markdowns above. |

The two Markdown files in `research/` plus `GEO-AUDIT-REPORT.md` are the **implementation source of truth**. Open them in a fresh Claude Code session inside your website's repo and paste:

```
Read research/02-competitor-analysis.md and GEO-AUDIT-REPORT.md. Implement every Critical and High finding against this codebase.
```

Claude can act on those reports directly.

---

## Preview the output

See `skills/business-audit/examples/sample-audit/` for a complete realistic audit on a fictional brand. Open `dashboard.html` in a browser to see the dashboard format. Read the two `.md` files to see the finding-block shape.

---

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
