# Page-class gate (`classify_page`)

Vertical specialists (flight, product, product_catalog, faq, local_business, vehicle, article) **must not run** unless `classify_page(url, signals)` returns their class.

## Rules

1. **Default is `general`.** If proof is weak or mixed, return `general` and skip every vertical check.
2. **Strong proof only** — path + hard tokens / schema / priced grids. Search forms, dropdowns, bare “departure/arrival date”, or site_type alone do **not** qualify.
3. **Skip means skip** — do not run the detector and suppress the finding; do not enter the eligible list.
4. Legal/compliance paths (`/terms`, `/privacy`, `/accessibility`, `/vpat`, `/wcag`) are always `general`.
5. Non-HTML (`text/plain`, markdown, JSON) is always `general` for HTML-structural and schema verticals.

## Verbose log

`compose(..., verbose=True)` prints and embeds `page_classifications`: `{url, page_class, role}` for every crawled page. Use this to tell “fixed” from “never visited that page.”

## Permanent fixtures (in `selftest.py`)

| Specialist | Should fire | Lookalike silent | Unrelated silent |
|---|---|---|---|
| flight | Akasa-style `/flights/delhi-mumbai` | VPAT / accessibility checkout | Shopify homepage |
| product_catalog | Priced card grid | Terms with currency + city list | Shopify homepage |
| faq | `/faq` with 3 Q&A pairs | — | Shopify homepage |
| local_business | Dentist home with NAP JSON-LD | — | Shopify homepage (saas) |
