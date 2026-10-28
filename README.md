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

## REST API (Phase 1 Integration)

The engine includes a lightweight, asynchronous REST API built with FastAPI to support future web interfaces (e.g. React frontend) without altering the underlying skill-based audit architecture.

### 1. Installation

Install the additional API and testing dependencies:

```bash
pip install -r requirements.txt
```

### 2. Start the API Server (Windows PowerShell)

```powershell
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

The interactive OpenAPI documentation will be accessible at `http://127.0.0.1:8000/docs`.

### 3. API Endpoints

| Method | Endpoint | Description | Status Code |
|---|---|---|---|
| `GET` | `/api/health` | Health check & engine readiness check | `200 OK` |
| `POST` | `/api/audits` | Submit a website URL for an asynchronous audit | `202 Accepted` |
| `GET` | `/api/audits/{audit_id}` | Poll the current status (`queued`, `running`, `completed`, `failed`) | `200 OK` / `404` |
| `GET` | `/api/audits/{audit_id}/report` | Retrieve the completed JSON report | `200 OK` / `409` / `422` |

### 4. Example Usage (PowerShell)

**Submit an audit:**
```powershell
$body = @{ url = "https://example.com" } | ConvertTo-Json
$res = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/audits" -Method Post -Body $body -ContentType "application/json"
$auditId = $res.audit_id
Write-Host "Audit queued with ID: $auditId"
```

**Check status:**
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/audits/$auditId"
```
*Response while running:*
```json
{
  "audit_id": "65805e1b02ec49549c4c4a94ca61ea2b",
  "status": "running",
  "url": "https://example.com/",
  "created_at": "2026-10-28T11:45:11.055976Z",
  "started_at": "2026-10-28T11:45:11.056300Z",
  "completed_at": null,
  "error": null
}
```

**Retrieve the report once completed:**
```powershell
$report = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/audits/$auditId/report"
$report | ConvertTo-Json -Depth 5
```

### 5. Running the API Test Suite

```bash
# Run unit & mock integration tests
python -m pytest tests/test_api.py -v

# Run existing engine offline tests
python skills/audit-orchestrator/scripts/selftest.py
```

### 6. Configuration & Architecture Notes

- **In-Process Job Store**: Audit jobs and status are tracked in memory for development efficiency. Jobs are reset if the server restarts. Persistent storage (database/Supabase) can be integrated in later phases.
- **Concurrency & Throttling**: Limits concurrent crawls via `MAX_CONCURRENT_AUDITS` (default `2`) and enforces execution timeouts via `AUDIT_TIMEOUT_SECONDS` (default `240s`).
- **SSRF Protections**: Request validation rejects loopback (`127.0.0.0/8`, `::1`), private networks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local addresses, and cloud metadata (`169.254.169.254`, `metadata.google.internal`).
- **Crawler Isolation**: The existing crawler operates strictly on-origin and obeys robots.txt. Unsafe redirect destinations beyond initial preflight are bounded by crawler fetch timeouts and network limits.

## React Frontend (Phase 2 Integration)

A modern, responsive React frontend built with TypeScript, Vite, Tailwind CSS, and React Router. The frontend implements the finalized Google Stitch design system (dark navy theme, cyan/teal accents, technical SaaS typography, evidence-focused finding cards, and status polling).

### 1. Installation

```bash
cd frontend
npm install
```

### 2. Development Server (Windows PowerShell)

In terminal 1 (start FastAPI backend):
```powershell
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

In terminal 2 (start React frontend):
```powershell
cd frontend
npm run dev
```

Open your browser to `http://localhost:5173`.

### 3. Production Build

```powershell
cd frontend
npm run build
```

Production assets are emitted to `frontend/dist/`.

### 4. Available Frontend Routes

* `/` — **Public Landing Page**: Hero headline, prominent URL search input, capability badges, and interactive example report preview.
* `/audit/new` — **New Audit Dispatcher**: Target URL submission with validation, quick suggestions, and execution scope details.
* `/audit/:auditId` — **Live Audit Dashboard**: Real-time polling indicator (`queued`, `running`), summary metrics, severity filters, search, and expandable finding cards.
* `/dashboard` — **Active / Recent Dashboard**: View active audit or latest inspected site.
* `/findings` — **Detailed Findings Explorer**: Deep inspection across all rule families (`CRA-*`, `FC-ENT-*`, `FC-FRESH-*`, `ENG-*`, `FC-PROACT-*`), category filters, and verification commands.
* `/history` — **Recent Audits**: In-browser session audit log with quick links to previous reports.
* `/settings` — **System & Engine Info**: Live FastAPI health diagnostic, stdlib verification, and crawl safeguards.

## Known limitation

Engagement checks are **structural** (dead CTAs, H1, breadcrumbs, empty FAQ bodies). They do not score subjective “is this templated city-pair copy specific enough?”

## License

MIT — see [LICENSE](LICENSE).


