---
name: nontext-surface-audit
description: Find facts locked in images without alt, PDF-only pages, or canvas-only UI that AI text fetchers cannot quote. Use when menus are photos, reports are PDF-only, or the page is a canvas app.
license: MIT
compatibility: Python 3.10+ stdlib.
---

# Non-text surfaces

Standard AI text fetchers cannot OCR images or parse canvas pixels without dedicated multimodal pipelines.

## Procedure

```bash
python3 scripts/run.py "<URL>"
```

| ID | Fire when |
|---|---|
| CRA-04 | `<img>` with empty/missing `alt` |
| CRA-04-PDF | PDF links on a page with little HTML text |
| CRA-04-CANVAS | `<canvas>` plus low word count |

Recommend HTML/JSON-LD equivalents of the locked facts. See [references/locked-surfaces.md](references/locked-surfaces.md).

## Output

Do not OCR. Suggest `alt` that contains the fact (hours, dish, product name), HTML summary of PDFs, or a DOM text fallback for canvas.
