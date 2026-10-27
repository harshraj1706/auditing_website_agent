# Composition

Crawl **once** (`crawl_site.py`) → detectors in `detect.py` → `compose_report.py`.

Sibling skills do not recrawl. They call `run_audit.py --skill <id>` and filter detectors via `SKILL_MAP`.

| Skill id | Detectors |
|---|---|
| `audit-orchestrator` | all + proactive |
| `crawl-access-audit` | NET-01 (fail-fast), CRA-01, CRA-03 |
| `render-quotability-audit` | CRA-02, CRA-02-MENU, CRA-05, CRA-06, CRA-07 |
| `freshness-corroboration-audit` | FC-ENT-*, FC-FRESH-*, plus proactive |
| `engagement-orientation-audit` | ENG-01, ENG-02, ENG-04 |
| `nontext-surface-audit` | CRA-04, CRA-04-PDF, CRA-04-CANVAS |

Funnel rank: **NET-01 (origin dead / SSL)** > **CRA-03 (origin 403/429 WAF)** > WAF-on-probes/noindex/robots > empty SPA / missing org schema / empty FAQ > dead CTA > sameAs/hours/nav > `llms.txt` (low/proactive).

When the origin fetch is status 0, ≥500, or SSL-invalid, emit **only** NET-01 and skip every DOM detector.

When the origin fetch is HTTP **403** or **429**, emit **only** CRA-03 and skip every DOM detector (challenge HTML is not the site).

Cap 18 findings. Unique IDs. Evidence is countable (status codes, n/m pages). Recommend-only.
