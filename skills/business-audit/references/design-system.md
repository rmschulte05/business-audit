# Dashboard Design System

The dashboard inherits the visual language from `website-intelligence`'s `process-overview.html` reference: warm paper tones, terracotta accent, serif-and-sans pairing, subtle grain texture, accent-bordered cards.

---

## Tokens

```css
:root {
  --ink: #0a0a0a;
  --paper: #f6f4f0;
  --accent: #c45d3e;
  --accent-light: #e8a48e;
  --muted: #8a8580;
  --divider: #d6d2cc;
  --card: #fffefa;
  --shadow: rgba(10, 10, 10, 0.06);

  /* Severity colors — used in finding blocks and score gauge */
  --severity-critical: #c45d3e;
  --severity-high: #d97706;
  --severity-medium: #ca8a04;
  --severity-low: #6b7280;

  /* Score-band colors — used in GEO gauge */
  --score-excellent: #2d8659;
  --score-good: #4a90c4;
  --score-fair: #d97706;
  --score-poor: #c45d3e;
  --score-critical: #991b1b;
}
```

## Typography

- **Headings**: `Instrument Serif`, 400 weight, `-0.02em` letter-spacing, line-height 1.1–1.2
- **Body**: `DM Sans`, 400 weight, line-height 1.6–1.75
- **Numerals in score gauge**: Instrument Serif, large (3–5rem)
- **Code / data**: `ui-monospace, "SF Mono", monospace`

Load via Google Fonts:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&display=swap" rel="stylesheet">
```

## Card

```css
.card {
  background: var(--card);
  border: 1px solid var(--divider);
  border-radius: 16px;
  padding: 2rem;
  position: relative;
  overflow: hidden;
  transition: box-shadow 0.3s ease;
}
.card:hover { box-shadow: 0 12px 40px var(--shadow); }
.card::before {
  content: '';
  position: absolute;
  top: 0; left: 0;
  width: 4px;
  height: 100%;
  background: linear-gradient(to bottom, var(--accent), var(--accent-light));
  border-radius: 4px 0 0 4px;
}
```

## Grain overlay

```css
body::after {
  content: '';
  position: fixed;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");
  pointer-events: none;
  z-index: 9999;
}
```

## Tabs

Two tabs only: **Competitive** and **GEO**. Minimal switcher — text labels with an accent underline on the active tab.

```css
.tabs { display: flex; gap: 2rem; border-bottom: 1px solid var(--divider); margin-bottom: 3rem; }
.tab { font-family: 'DM Sans', sans-serif; font-size: 0.95rem; letter-spacing: 0.05em; text-transform: uppercase; padding: 1rem 0; cursor: pointer; color: var(--muted); border-bottom: 2px solid transparent; transition: color 0.2s, border-color 0.2s; }
.tab[aria-selected="true"] { color: var(--ink); border-bottom-color: var(--accent); }
```

JS:
```js
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    const target = tab.dataset.tab;
    document.querySelectorAll('.tab').forEach(t => t.setAttribute('aria-selected', t === tab));
    document.querySelectorAll('.panel').forEach(p => p.hidden = p.dataset.panel !== target);
  });
});
```

## Print rules

The dashboard must print clean on A4. Required `@media print`:

```css
@media print {
  body::after { display: none; } /* drop grain — saves toner */
  .tabs { display: none; }
  .panel { display: block !important; page-break-before: always; }
  .panel:first-of-type { page-break-before: avoid; }
  @page { size: A4; margin: 1.5cm; }
}
```

## Score gauge

A simple horizontal bar with the numeric score above it, color-banded by `--score-*` tokens.

```html
<div class="gauge">
  <div class="gauge-number">{{GEO_SCORE}}</div>
  <div class="gauge-label">{{GEO_SCORE_LABEL}}</div>
  <div class="gauge-track">
    <div class="gauge-fill" style="width: {{GEO_SCORE}}%"></div>
  </div>
</div>
```

## Responsive

Mobile breakpoint at 640px. Tabs stack vertically below that; cards go full-width.

---

## Don't use

- Drop shadows beyond the one on `.card:hover`
- Gradients beyond the 4px accent border
- More than 2 fonts
- Pure black (`#000`) — always `--ink` (`#0a0a0a`)
- Decorative emoji as section icons (the tone is editorial, not playful)
