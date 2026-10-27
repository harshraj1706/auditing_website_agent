---
name: engagement-orientation-audit
description: >-
  Audit on-site engagement from HTML only — dead booking/order CTAs, missing H1
  on inner templates, breadcrumbs, nav landmarks, and FAQ headings that promise
  answers but deliver empty accordion bodies. Use when visitors bounce after an
  AI citation, reservation links 404, or FAQ answers are JS-only. No analytics.
license: MIT
compatibility: Python 3.10+ stdlib, network fetch, no paid APIs.
---

# Engagement / orientation

Infer bounce risk from **structure**, not visitor stats. Prefer deterministic completeness checks over subjective “is this content specific enough” judgments (those are false-positive-prone and outside the runtime budget).

## Procedure

```bash
python3 scripts/run.py "<URL>"
```

| ID | Fire when |
|---|---|
| ENG-01 | Booking/order/menu CTA → 404/403/0 |
| ENG-02 | Deep pages lack H1, breadcrumbs, or home link |
| ENG-04 | ≥2 FAQ question headings with empty answer body and no FAQPage fallback |

3. **FAQ answer completeness (`ENG-04`):** see [references/faq-empty.md](references/faq-empty.md).

Do **not** flag city-pair or programmatic SEO pages merely because sections are templated — per-city facts substituted into a shared skeleton are legitimate. Empty FAQ answers on those pages are the defect (Akasa Delhi–Mumbai / Delhi–Ahmedabad).

## Output

Evidence includes HTTP status, URLs, and empty question strings. Do not invent heatmap or semantic-relevance claims.
