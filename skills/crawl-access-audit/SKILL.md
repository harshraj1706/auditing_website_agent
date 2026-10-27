---
name: crawl-access-audit
description: Check robots.txt, AI crawler allow/disallow, sitemap, homepage noindex, and WAF/403 blocks that stop indexing. Use when diagnosing crawlability, GPTBot, Cloudflare challenges, or why a site is missing from search/AI indexes.
license: MIT
compatibility: Python 3.10+ stdlib, network.
---

# Crawl / access audit

Index-funnel skill. Answers: can a fetcher **enter** the HTML?

## Procedure

```bash
python3 scripts/run.py "<URL>"
# equivalent:
python3 ../audit-orchestrator/scripts/run_audit.py "<URL>" --skill crawl-access-audit
```

Crawl is shared (`crawl_site.py`): robots.txt, sitemap, homepage, optional GPTBot/PerplexityBot GET `/`.

| ID | Fire when | Skip |
|---|---|---|
| NET-01 | Origin HTTP 0 / ≥500 / SSL certificate failure — **only** finding; abort DOM skills | Healthy 200 HTML |
| CRA-01 | robots 404 / sitemap 404 / homepage `noindex` / `Disallow: /` for GPTBot (etc.) | thank-you, cart, checkout, login `noindex`; **skipped when NET-01 or origin 403/429 fires** |
| CRA-03 | Origin HTTP 403/429, Cloudflare challenge, or AI-UA probe blocked — **only** finding when homepage is 403/429 | healthy 200 HTML |

Missing `llms.txt` is **not** this skill — orchestrator `FC-PROACT-01` only.

See [references/index-blockers.md](references/index-blockers.md).

## Output

Recommend-only JSON. Evidence is HTTP status, UA, and URL. Never write to the live site.
