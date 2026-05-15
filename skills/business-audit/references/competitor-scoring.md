# Competitor Scoring Rubric

Score each competitor candidate 1–10 across these 8 criteria. Total possible: 80.

Adapted from `website-intelligence` Phase 2 with GEO-relevant additions in the rationale column.

---

| # | Criterion | What to look for | Why it matters |
| --- | --- | --- | --- |
| 1 | **Search visibility** | Do they rank on page 1 for key industry terms? | Strong search presence is a direct AI-citation precursor — 92% of Google AI Overviews cite top 10 organic results. |
| 2 | **Review quality** | Google reviews, Trustpilot, G2 — 4.5+ stars with depth? | Social proof signal that ChatGPT/Perplexity weight when surfacing recommendations. |
| 3 | **Visual design** | Modern, professional, not template-looking? Custom illustrations, considered typography, intentional spacing? | Trust signal that affects conversion AND credibility ranking in AI summaries. |
| 4 | **Mobile responsive** | Clean on mobile, not just "it works" — designed for touch, no layout shift? | Google mobile-first indexing affects both classical and AI search visibility. |
| 5 | **Content depth** | Real copy or placeholder garbage? Articles >1500 words, substantive product pages? | Thin content is invisible to AI; depth correlates strongly with citation rate. |
| 6 | **Social proof** | Testimonials, customer logos, case studies, named quotes, video? | Authority/Trust E-E-A-T signals. AI models heavily favor pages with named experts. |
| 7 | **CTA strategy** | Clear next step? Primary + secondary CTAs? Lead capture mechanism beyond contact form? | Indicates competitor sophistication — a baseline for what "great" looks like in this niche. |
| 8 | **Page speed** | Fast load (<2s LCP), no layout shift (CLS <0.1), responsive interactions (INP <200ms)? | Core Web Vitals are a direct GEO factor; Bing Copilot explicitly weights speed <2s. |

---

## How to score

- **1–3**: Below baseline — clearly weaker than the median in this niche
- **4–6**: At baseline — what an average competitor does
- **7–8**: Above baseline — visibly invested in this dimension
- **9–10**: Best-in-class — sets the standard

Be ruthless. If you score everyone 8+, the ranking is useless.

---

## Tie-breaking

If two competitors tie on total score and you have to pick one for the top 5, prefer the one with the higher **Search visibility** sub-score. They're the loudest competitor and the client will encounter them most often.

---

## Output format

When you write competitor scores into `COMPETITIVE-ANALYSIS.md`, use this exact table shape so the dashboard renderer can parse it consistently:

```markdown
| Competitor | Search | Reviews | Design | Mobile | Content | Social Proof | CTA | Speed | **Total** |
|---|---|---|---|---|---|---|---|---|---|
| Competitor A | 9 | 8 | 9 | 8 | 8 | 7 | 8 | 9 | **66** |
| Competitor B | 8 | 7 | 8 | 9 | 9 | 8 | 7 | 8 | **64** |
| ... | | | | | | | | | |
| **Client** | 5 | 6 | 6 | 7 | 4 | 3 | 5 | 6 | **42** |
```

Always include the client as the last row for direct comparison.
