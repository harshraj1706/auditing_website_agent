# brand-ai-readiness-audit

Autonomous Brand AI-Readiness Audit Engine & Agent Skills Suite. Given any public website URL, crawl once and emit a **recommend-only JSON audit** explaining why the brand is hard for AI assistants to **index, cite, and land on**.

Provider-neutral. **Python 3.10+ stdlib only.** Network fetch allowed. No live-site writes, no paid APIs, no Playwright, no pretrained weights. Typical run: ≤12 HTML pages + consensus probes + a few CTA HEAD checks — well under **5 minutes** and **50 MB**.

## Marketplace layout

```
brand-ai-readiness-audit/
  marketplace.json          # manifest — entrypoint: audit-orchestrator
  assets/report.schema.json # report JSON floor
  README.md
  LICENSE
  skills/
    audit-orchestrator/     # entrypoint skill (crawl + all detectors + compose)
    crawl-access-audit/
    render-quotability-audit/
    freshness-corroboration-audit/
    engagement-orientation-audit/
    nontext-surface-audit/
```

Each skill folder follows the [Agent Skills](https://agentskills.io) layout: `SKILL.md` (instructions), `references/` (deep docs), `scripts/run.py` (CLI wrapper). The orchestrator holds the shared crawl and detector code under `skills/audit-orchestrator/scripts/`.

## What each skill does

| Skill | Responsibility | Finding families |
|---|---|---|
| **audit-orchestrator** | **Entrypoint.** One robots-aware crawl, digital consensus (Wikipedia/Wikidata/DDG/Reddit), all detectors, funnel rank, JSON report. | All `CRA-*`, `FC-*`, `ENG-*`, `FC-PROACT-*` |
| **crawl-access-audit** | Can fetchers enter? robots.txt, sitemap, homepage noindex, WAF / AI-UA blocks. | `CRA-01`, `CRA-03` |
| **render-quotability-audit** | Is raw HTML quotable? Empty JS shells, third-party SPA menus, auth-gated thin routes, CSR-only facets, infinite scroll. | `CRA-02`, `CRA-02-MENU`, `CRA-05`, `CRA-06`, `CRA-07` |
| **freshness-corroboration-audit** | Is identity anchored and schema typed correctly? Organization/`sameAs`, vertical JSON-LD (Product, ItemList, Flight, Vehicle, LocalBusiness, Article, FAQPage), dates, blank meta. | `FC-ENT-*`, `FC-FRESH-*`, proactive |
| **engagement-orientation-audit** | After citation, can a visitor act? Dead CTAs, missing H1/nav/breadcrumbs, empty FAQ accordion bodies. | `ENG-01`, `ENG-02`, `ENG-04` |
| **nontext-surface-audit** | Are non-text surfaces blocking facts? Hero images without alt, PDF-only pages, canvas-only UI. | `CRA-04`, `CRA-04-PDF`, `CRA-04-CANVAS` |

## Standout Differentiators (Beyond Basic SEO)

Most audit tools stop at standard search-engine checklists (robots.txt, H1, meta tags). This engine goes further:

1. **Multimodal & Voice AI Readiness (`FC-PROACT-03`)**: Inspects content and news pages for schema.org `SpeakableSpecification`. Conversational agents (Google Assistant, Gemini Live, Siri audio briefings) require structured speakable selectors to cite and read articles aloud. Gated strictly on real `Article`/`NewsArticle` schema (zero heuristic guessing).
2. **Actionable `verification_steps` on Every Finding**: Site owners are given exact verification commands (`curl`, Rich Results Test, robots validator) to independently confirm their fixes worked.
3. **Adversarial Anti-False-Positive Hardening**: Documented in [`Testing_Log.md`](Testing_Log.md) across 12+ real-world verticals (WSJ, Apple, BBC, Meesho, Shopify, KiviHealth). Includes RFC 9309 robots wildcard inheritance, domain-anchored entity resolution, and WAF challenge-page suppression.

## How the entrypoint composes them

The entrypoint does **not** re-crawl per skill. One pipeline:

```
URL
  → crawl_site.py        # robots, sitemap, ≤12 pages, CTA probes, facet pair
  → consensus.py         # Wikipedia / Wikidata / DuckDuckGo / Reddit (internal severity only)
  → detect.py            # all detector functions (grouped by skill id in SKILL_MAP)
  → compose_report.py    # signal grounding, dedupe, cap 18, findings[] JSON
  → stdout
```

1. **`run_audit.py`** (no `--skill`) calls `crawl()` then `compose()` with **all** detectors via `run_all()`.
2. **Sibling skills** are thin wrappers: `skills/<id>/scripts/run.py` → `run_audit.py <url> --skill <id>`, which runs the **same crawl** but filters detectors through `SKILL_MAP` in `detect.py`.
3. **`compose_report.py`** merges findings, applies identity guard on consensus, resynthesizes prose from signals, ranks by severity funnel, and emits schema-shaped `findings[]` (no duplicate `problems[]`).

See `skills/audit-orchestrator/references/composition.md` for the detector → skill mapping table.

## Quick start

```bash
# Full audit (entrypoint — all skills composed)
python skills/audit-orchestrator/scripts/run_audit.py "https://example.com"

# Offline smoke tests (no network)
python skills/audit-orchestrator/scripts/selftest.py

# All six skills + schema validation (network)
python skills/audit-orchestrator/scripts/skill_tests.py

# Single-skill slice (same crawl, filtered detectors)
python skills/crawl-access-audit/scripts/run.py "https://example.com"
```

Attach the skills package to an AI agent, or point any Agent Skills host at `marketplace.json` (`entrypoint: audit-orchestrator`).

## Output

JSON matches `assets/report.schema.json`. Required: `site`, `audited_at`, `summary`, `findings[]` with `id`, `title`, `severity`, `evidence`, `suggested_action.{summary,priority}`.

Finding IDs: `skills/audit-orchestrator/references/catalog.md`. Digital consensus is used **internally** to calibrate severity and identity guard; it is not dumped in the default report (`--verbose` for debug).

## Validation & Packaging checklist

```bash
# 1. skills-ref validate (per skill folder)
npx skills-ref validate skills/audit-orchestrator
npx skills-ref validate skills/crawl-access-audit
# … repeat for all six skills/

# 2. Integration + schema
python skills/audit-orchestrator/scripts/skill_tests.py

# 3. Full entrypoint timing (should stay well under 300s)
python skills/audit-orchestrator/scripts/run_audit.py "https://www.kivihealth.com"

# 4. Package zip ≤50 MB — exclude .git/, venv/
# PowerShell example from repo parent:
Compress-Archive -Path brand-ai-readiness-audit\marketplace.json,brand-ai-readiness-audit\README.md,brand-ai-readiness-audit\LICENSE,brand-ai-readiness-audit\assets,brand-ai-readiness-audit\skills -DestinationPath brand-ai-readiness-audit.zip
```

Measured on a typical dev machine: `example.com` ~5s, `kivihealth.com` (12 pages + consensus) ~8s. Package zip ~0.2 MB with no weights or venv.

## Design notes (calibration)

- **Signal extraction → agent synthesis** — Python emits signals + fixed finding ID/severity; the harness agent may rewrite prose per `SKILL.md`. No paid LLM API in the script.
- **Recommend-only** — never patch HTML on the live site.
- **Respects robots.txt** — no login, POST, or cart flows.
- **Identity guard** — Wikipedia/Wikidata `sameAs` only when disambiguation is rejected and the candidate corroborates the audited entity (domain/parent company). Wrong link > no link.
- **CRA-02** — empty-shell only (`word_count` < 25, no `__NEXT_DATA__`/JSON-LD); no Playwright ratio.
- **FC-FRESH-05** — structural priced-card grids, not Shopify `/collections/` URLs.
- **ENG-04** — empty FAQ accordion bodies only; short factual answers are not empty.

## Known limitation

Engagement checks are **structural** (dead CTAs, H1, breadcrumbs, empty FAQ bodies). They do not score subjective “is this templated city-pair copy specific enough?”

## License

MIT — see [LICENSE](LICENSE).
