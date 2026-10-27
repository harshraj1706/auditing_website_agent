---
name: render-quotability-audit
description: Detect JS-empty shells, SPA #root with no HTML text, third-party client-rendered menus, auth/wallet-gated routes without a public fallback, CSR-only facets, and Load More without crawlable pagination. Use when AI says the page is empty, Petpooja/Toast menus fail, or Uniswap-style state walls appear.
license: MIT
compatibility: Python 3.10+ stdlib. Do not require Playwright; raw HTML is the source of truth.
---

# Render / quotability

AI fetchers see **curl HTML**, not a headed browser.

## Procedure

```bash
python3 scripts/run.py "<URL>"
```

| ID | Fire when | Skip |
|---|---|---|
| CRA-02 | Empty `#root`/`#app` and word_count < 25 | `__NEXT_DATA__`, JSON-LD, word_count ≥ 25 (Apple/Stripe) |
| CRA-02-MENU | Local/marketing site, menu/order hrefs on Petpooja/Toast/Zomato/Swiggy | Brand-origin HTML menu |
| CRA-05 | Thin auth-path routes (`/login`, `/account`, …; includes ENG-03) | About/home with Log in only in the nav |
| CRA-06 | Facet/filter URL raw HTML identical to the unfiltered listing | Distinct server HTML per facet |
| CRA-07 | Collection/product “Load More” / infinite scroll without `rel=next` or `page=` | Real href pagination |

**Do not** apply a Playwright 0.70 raw/rendered ratio. See [references/empty-shell.md](references/empty-shell.md).

## Output

Evidence: word counts, URLs, facet pair comparison. Suggest SSR/SSG or in-domain Menu JSON-LD, not “enable JavaScript.”
