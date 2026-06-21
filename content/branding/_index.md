---
title: "Branding & Design System"
description: "Centralized design tokens for Weavers.town"
layout: "branding"
---

# Branding & Design System

This page shows the current design tokens defined in the centralized branding file.

All colors, fonts, and tokens are managed in one place:
**`layouts/partials/head/branding.html`**

---

## Typography

### Display Font
Used for large hero headlines (homepage).

<div style="font-family: var(--font-display); font-size: 3rem; line-height: 1.1; margin: 1rem 0;">
The Thread
</div>

**Variable:** `--font-display`

---

### Heading Font
Used for section and article headings.

<div style="font-family: var(--font-heading); font-size: 2rem; line-height: 1.25; margin: 1rem 0;">
A Hierarchy of Meaning
</div>

**Variable:** `--font-heading`

---

### Body Font (Serif)
Main reading font — chosen for long-form readability.

<div style="font-family: var(--font-serif); font-size: 1.15rem; line-height: 1.85; max-width: 68ch;">
This is the body text. The Thread is a practical, cross-scale framework for understanding how meaning emerges from stabilized regularities. Stable patterns become the foundation for higher levels of organization and meaning — each conferring emergent interaction capabilities that enable the weave to continue upward.
</div>

**Variable:** `--font-serif`

---

### Sans & Monospace

**Sans-serif:** Used for UI elements.

<div style="font-family: var(--font-sans); font-size: 1rem;">
This is the sans-serif font stack.
</div>

**Monospace:** Used for code, labels, and technical text.

<div style="font-family: var(--font-mono); font-size: 0.95rem;">
const meaning = stabilize(patterns);
</div>

---

## Colors

### Backgrounds

<div style="display: flex; gap: 1rem; flex-wrap: wrap; margin: 1rem 0;">
  <div style="background: var(--bg); border: 1px solid var(--rule); padding: 1rem; border-radius: 8px; width: 140px;">
    <strong>--bg</strong><br>
    <code>#f8f9f7</code>
  </div>
  <div style="background: var(--bg-alt); border: 1px solid var(--rule); padding: 1rem; border-radius: 8px; width: 140px;">
    <strong>--bg-alt</strong><br>
    <code>#f1f3f0</code>
  </div>
  <div style="background: var(--paper); border: 1px solid var(--rule); padding: 1rem; border-radius: 8px; width: 140px;">
    <strong>--paper</strong><br>
    <code>#fdfdfb</code>
  </div>
</div>

### Text Colors

<div style="display: flex; gap: 1rem; flex-wrap: wrap; margin: 1rem 0;">
  <div style="background: var(--paper); color: var(--ink); border: 1px solid var(--rule); padding: 1rem; border-radius: 8px; width: 140px;">
    <strong>--ink</strong>
  </div>
  <div style="background: var(--paper); color: var(--ink-mid); border: 1px solid var(--rule); padding: 1rem; border-radius: 8px; width: 140px;">
    <strong>--ink-mid</strong>
  </div>
  <div style="background: var(--paper); color: var(--ink-light); border: 1px solid var(--rule); padding: 1rem; border-radius: 8px; width: 140px;">
    <strong>--ink-light</strong>
  </div>
  <div style="background: var(--paper); color: var(--ink-muted); border: 1px solid var(--rule); padding: 1rem; border-radius: 8px; width: 140px;">
    <strong>--ink-muted</strong>
  </div>
</div>

### Accent Colors

<div style="display: flex; gap: 1rem; flex-wrap: wrap; margin: 1rem 0;">
  <div style="background: var(--accent); color: white; padding: 1rem; border-radius: 8px; width: 140px;">
    <strong>--accent</strong><br>
    <code>#145f58</code>
  </div>
  <div style="background: var(--accent-2); color: white; padding: 1rem; border-radius: 8px; width: 140px;">
    <strong>--accent-2</strong>
  </div>
  <div style="background: var(--accent-soft); padding: 1rem; border-radius: 8px; width: 140px;">
    <strong>--accent-soft</strong>
  </div>
</div>

### Borders & Rules

<div style="display: flex; gap: 1rem; flex-wrap: wrap; margin: 1rem 0;">
  <div style="border: 2px solid var(--rule); padding: 1rem; border-radius: 8px; width: 140px;">
    <strong>--rule</strong>
  </div>
  <div style="border: 2px solid var(--rule-light); padding: 1rem; border-radius: 8px; width: 140px;">
    <strong>--rule-light</strong>
  </div>
</div>

---

## How to Edit Branding

1. Open this file:
   ```
   layouts/partials/head/branding.html
   ```

2. Modify the values inside the `:root { ... }` block.

3. Changes will appear live when using `npm run dev`.

All pages (including the homepage and book chapters) automatically use these tokens.

---

*This page is a live view of the design system defined in the centralized branding file.*