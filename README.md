# Business Audit

A Claude Code plugin that runs a **competitive intelligence audit** and an **AI-search (GEO) audit** in one pass, then writes two implementation-ready Markdown reports plus a polished interactive HTML dashboard.

Built by fusing two existing skills — `website-intelligence` (competitive scraping + design pattern extraction) and `geo-audit` (Generative Engine Optimization scoring) — into a single plugin you can hand to a friend, install with one command, and run on any website.

---

## What you get per audit

Three files dropped into the working directory:

| File | Purpose |
| --- | --- |
| `COMPETITIVE-ANALYSIS.md` | Top 5 competitor profiles, comparison matrix, winning design and messaging patterns, prioritized recommendations. |
| `GEO-AUDIT.md` | Client GEO Score (0–100), 6-category breakdown, AI platform readiness, prioritized fixes with code snippets, competitor benchmark row. |
| `dashboard.html` | Self-contained HTML with two tabs (**Competitive** / **GEO**), terracotta-and-paper design, print-friendly so you can export to PDF. |

Both Markdown files use the same **implementation-ready finding format** — a downstream Claude Code session can read either file and apply the fixes mechanically without needing clarification.

---

## Install

```bash
# Clone into your Claude Code plugins directory
git clone https://github.com/YOUR_USERNAME/business-audit ~/.claude/plugins/business-audit

# Restart Claude Code so it picks up the new plugin
```

That's it. The plugin bundles all of the geo-* sub-skills it depends on, so you don't need to install anything else.

### Optional: Firecrawl

The audit uses Firecrawl MCP for high-quality scraping when available, and falls back to `WebFetch` otherwise. To enable Firecrawl, set your API key:

```bash
export FIRECRAWL_API_KEY="fc-..."
```

Sign up at https://firecrawl.dev — the free tier is enough for a handful of audits.

---

## Usage

In any Claude Code session, just describe what you want:

```
audit https://example.com — it's a B2B SaaS in the dev-tooling niche
```

or

```
/business-audit
```

The skill will ask for the URL and niche if not provided, then run through six phases:

1. **Discovery** — detect business type, map the client's site
2. **Client analysis** — extract brand assets + run GEO scoring (parallel)
3. **Competitor discovery** — find and score the top 10 candidates in the niche
4. **Competitor deep dive** — full scrape + GEO mini-audit on the top 5
5. **Synthesis** — write `COMPETITIVE-ANALYSIS.md` and `GEO-AUDIT.md`
6. **Dashboard render** — inject the data into `dashboard.html`

Expect 5–15 minutes for a real audit, depending on site size and Firecrawl latency.

---

## What the dashboard looks like

Open `dashboard.html` in any browser. Two tabs:

- **Competitive** — competitor cards, side-by-side comparison table, winning patterns, design recommendations
- **GEO** — overall score gauge, 6-category breakdown, AI platform readiness chart, prioritized findings

Print the page (Cmd/Ctrl-P) and you get a clean A4 PDF, suitable for client delivery.

---

## Implementing the recommendations

Each finding in both Markdown files follows the same block format:

```markdown
### Finding: [short title]

- **Severity**: Critical | High | Medium | Low
- **Category**: Competitive | AI Citability | Technical | Schema | Brand Authority | Content E-E-A-T | Platform
- **Location**: `https://client.com/page` (or `index.html:42`)
- **Current state**: [quoted snippet from the site]
- **Recommended change**:
  ```html
  <!-- exact code/copy to insert or replace -->
  ```
- **Why**: [1-line rationale linking to research]
- **Implementation hint**: [where to put it / what file to edit]
```

To apply the recommendations, open the website's source repo in a new Claude Code session and paste:

```
Read COMPETITIVE-ANALYSIS.md and GEO-AUDIT.md. Implement every Critical and High finding against this codebase.
```

That's the whole point of the format — Claude can act on it without asking follow-up questions.

---

## What's inside

```
business-audit/
├── .claude-plugin/plugin.json
├── README.md
├── LICENSE                                # MIT
├── .gitignore
└── skills/
    ├── business-audit/                    # Orchestrator (entry point)
    │   ├── SKILL.md
    │   ├── references/
    │   ├── templates/
    │   └── examples/sample-audit/
    ├── geo-audit/                         # Bundled (verbatim)
    ├── geo-citability/
    ├── geo-content/
    ├── geo-technical/
    ├── geo-schema/
    ├── geo-platform-optimizer/
    ├── geo-brand-mentions/
    ├── geo-crawlers/
    └── geo-llmstxt/
```

---

## Sample output

See `skills/business-audit/examples/sample-audit/` for a complete realistic example for a fictional business — two Markdown files plus the rendered dashboard. Open `dashboard.html` in a browser to see exactly what your friends will get.

---

## License

MIT. Fork it, ship it, improve it. PRs welcome.
