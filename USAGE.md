# Audit any business in 60 seconds

This guide is for anyone who wants to audit a website's **AI-search readiness**
(GEO — Generative Engine Optimization) with nothing but Python installed. No API
key, no account, no paid tools.

---

## What you need

- **Python 3** (3.10+). Check with `python3 --version`.
- **git** (to clone this repo).

That's it. The audit engine is bundled and uses only the Python standard
library — there is nothing to `pip install`.

---

## Quickstart (one command)

```bash
git clone https://github.com/rmschulte05/business-audit
cd business-audit
python3 audit.py https://example.com
```

Replace `https://example.com` with the site you want to audit. In under a
minute you get a GEO score, a confidence band, and three files you can share or
act on.

### Options

```bash
# Tell it the business type instead of auto-detecting:
python3 audit.py https://example.com --type saas
#   choices: local | saas | ecommerce | publisher | agency

# Crawl more (or fewer) pages — default is 8, use 1 for homepage-only:
python3 audit.py https://example.com --max-pages 12

# Put the report somewhere else (default is ./audits):
python3 audit.py https://example.com --out-dir ~/reports
```

If you omit `--type`, the launcher reads the homepage and makes a conservative
guess (e.g. pricing/sign-up language → SaaS; address/opening-hours → local
business; cart/product → e-commerce). It prints what it detected and reminds you
that you can override it.

---

## The three files you get

Everything lands in `audits/<your-domain>/` (e.g. `audits/example-com/`):

| File | What it is | Use it to… |
| --- | --- | --- |
| **GEO-AUDIT.html** | A polished, self-contained web page. | **Share it.** Open in a browser, or print to PDF and email a client. |
| **GEO-AUDIT-REPORT.md** | The same report in plain Markdown. | Read it, paste it into a doc, or hand it to Claude Code. |
| **GEO-AUDIT.json** | The raw data: composite score, per-pillar scores, confidence band, and every signal with its evidence. | Feed it to Claude Code, a dashboard, or your own scripts. |

---

## Share the report with a client

1. Open `audits/<your-domain>/GEO-AUDIT.html` in any browser (double-click it,
   or `open` it on macOS).
2. To send it as a PDF: in the browser, choose **Print → Save as PDF**.
3. Email the HTML file or the PDF directly. It's fully self-contained — no
   internet needed to view it. Everything (styles and data) is inlined in the
   single file, and it loads no web fonts, so it looks the same online or off.

---

## Feed it into Claude Code to fix the site

The audit doesn't just grade the site — it tells Claude Code exactly what to fix.

1. **Copy the report folder into your website's code repository.** For example:

   ```bash
   cp -r audits/example-com /path/to/your-website-repo/
   ```

2. **Open Claude Code in that repository.**

3. **Paste the prompt the launcher printed** (it references your
   `GEO-AUDIT-REPORT.md` and `GEO-AUDIT.json`). It looks like this:

   > Read GEO-AUDIT-REPORT.md and GEO-AUDIT.json (the GEO audit of my website —
   > scores, per-pillar breakdown, and every measured signal with its evidence).
   > Work through the 'Prioritized Fixes' in GEO-AUDIT-REPORT.md, highest-impact
   > first. For each one, find the relevant file in this codebase, make the
   > change, and show me a diff. Only act on signals the audit marked as
   > MEASURED; skip anything it marked 'not measured'. After your changes,
   > summarize what you fixed and what should improve on the next audit.

Claude Code reads the evidence and works through the fixes against your actual
code. Re-run `python3 audit.py <url>` afterward to see the score move.

---

## How to read the score (and why it's honest)

The headline looks like:

```
GEO score: 88/100 plus/minus 7 — Good (confidence 52%)
```

- **Score** — the weighted GEO score from the pillars the engine could measure.
- **plus/minus band** — the uncertainty range around that score.
- **Confidence** — the share of the score backed by *direct measurement*. The
  rest is either not yet measured or needs human judgment.

### Measured vs. not measured

Every signal is one of two things:

- **Measured** — observed from the real HTTP response and HTML (headers,
  robots.txt, JSON-LD schema, `llms.txt`, page content, etc.). These move the
  score.
- **Not measured** — the engine couldn't observe it. It is **never** guessed or
  faked. It simply lowers the confidence percentage.

Two pillars are **not measured** by this free engine because they live off-site:

- **Brand Authority** — third-party mentions, backlinks, reputation across the
  web.
- **Platform Optimization** — per-platform presence on AI surfaces.

You'll see these marked "not measured" in the report. That's deliberate: the
score you get is everything the engine could actually verify, and the confidence
number tells you how complete that picture is. Nothing is fabricated.

> The score is **reproducible** — run it on the same site twice and you get the
> same number, because it's computed in code from observed evidence.

---

## Troubleshooting

- **"Could not audit … Is the site online?"** — the site was unreachable. Check
  the spelling and that the URL loads in a browser.
- **Detected the wrong business type** — pass `--type` explicitly.
- **Want real Core Web Vitals** — set a free
  [PageSpeed Insights](https://developers.google.com/speed/docs/insights) key as
  `PSI_API_KEY` in your environment before running.
- **No HTML file appeared** — the JSON and Markdown reports are always written;
  the polished HTML is a bonus layer. Re-run after updating the repo if it's
  missing.
