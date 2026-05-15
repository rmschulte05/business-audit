# Business Audit — Orchestration in Detail

This file expands the 3 steps in `SKILL.md` with edge cases and exact file expectations. Read this if anything in the main SKILL.md is ambiguous.

The plugin **never re-implements** anything from `website-intelligence` or `geo-audit`. It runs them as written, then composes a new HTML view from what they wrote.

---

## Step 1 — `website-intelligence` Phases 1–3

### Why we stop at Phase 3

`website-intelligence` is a full-stack skill: Phases 1–3 produce the research deliverables (brand snapshot, competitor analysis, PDF-ready report), Phases 4–6 build a new website. This plugin is **audit-only** — Phase 4's "Build Brief & Approval" is the hard stop. Skip it and everything below.

### Invoking the skill

Read `../website-intelligence/SKILL.md` and execute the phases as written. When prompted by that skill for the client URL and niche, use the inputs the user gave this orchestrator.

### Files it must produce

After Phase 3 finishes, these must exist in the working directory:

| Path | Producer | Used by dashboard tab |
| --- | --- | --- |
| `research/01-client-brand.md` | `website-intelligence` Phase 1 | Competitive |
| `research/02-competitor-analysis.md` | `website-intelligence` Phase 2 | Competitive |
| `competitive-analysis.html` | `website-intelligence` Phase 3 | (kept as the source skill's original deliverable; not consumed by the dashboard) |

If any of these is missing after Phase 3, the source skill failed — stop and report the error.

### Edge cases

- **Phase 2 finds fewer than 5 competitors** → that's the source skill's problem to handle. Use whatever count it returned. The dashboard renders 1–5 competitor cards based on what's in `02-competitor-analysis.md`.
- **`website-intelligence` asks for approval at Phase 4** → answer "stop here, the user only wants the audit". Do not continue.

---

## Step 2 — `geo-audit` (full)

### Invoking the skill

Read `../geo-audit/SKILL.md` and execute all three phases:

1. Discovery & Reconnaissance — homepage fetch, business-type classification, 50-page crawl
2. Parallel Subagent Delegation — `geo-citability`, `geo-content`, `geo-technical`, `geo-schema`, `geo-platform-optimizer`, `geo-brand-mentions`, `geo-crawlers`, `geo-llmstxt` (all bundled in this plugin at `../geo-*`)
3. Score Aggregation & Report Generation

### File it must produce

| Path | Producer | Used by dashboard tab |
| --- | --- | --- |
| `GEO-AUDIT-REPORT.md` | `geo-audit` Phase 3 | GEO |

### Edge cases

- **Site is JavaScript-rendered and crawlers can't see content** → `geo-audit` will write that finding into the report itself. Pass it through to the dashboard.
- **Site is unreachable** → `geo-audit` will error out. Don't proceed to Step 3; surface the error.

---

## Step 3 — Render `dashboard.html`

### Data extraction

Read the three Markdown files and extract the values listed in `SKILL.md`'s "Token replacement" section.

Useful patterns:
- The GEO Score is on a line like `**Overall GEO Score: 47/100 (Poor)**` — extract integer 47 and word "Poor".
- The Score Breakdown table is a standard Markdown table. Parse it row-by-row.
- Issues are under `## Critical Issues`, `## High Priority Issues`, etc. Count entries per section.
- Competitor data in `02-competitor-analysis.md` follows the table format from `website-intelligence`'s `references/competitor-scoring.md` — header row, one row per competitor, total column.

### Server-side render

This plugin produces a **static HTML file**. You do not embed a Markdown parser. You read the source Markdown, structure the data, and emit HTML directly into the template tokens. See `examples/sample-audit/dashboard.html` for the exact shape.

For each finding in the GEO report, emit:

```html
<details class="finding" data-severity="critical">
  <summary>
    <span class="severity-tag" data-severity="critical">Critical</span>
    [title from the issue]
  </summary>
  <div class="finding-body">
    [body content — pages affected, recommended fix]
  </div>
</details>
```

### Verification

After writing `dashboard.html`:

```bash
grep -n '{{' dashboard.html        # must return nothing
```

Open in a browser:
- Both tabs render
- Tab switcher works (click "GEO" → competitive panel hides, GEO panel shows)
- Print preview is clean A4 (margins, no overflow)
- File size < 500 KB

If any check fails, fix before declaring the audit complete.

---

## Final working-directory state

```
research/
  01-client-brand.md           ← website-intelligence
  02-competitor-analysis.md    ← website-intelligence
competitive-analysis.html      ← website-intelligence
GEO-AUDIT-REPORT.md            ← geo-audit
dashboard.html                 ← this plugin (the new combined view)
```

The two `.md` files in `research/` plus `GEO-AUDIT-REPORT.md` are the **implementation source of truth**. They are what a downstream Claude session reads to apply changes. The dashboard is for humans.
