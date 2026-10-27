# System Architecture & Technical Guide — Brand AI-Readiness Audit

Use this document as the technical specification and architecture reference for the project.

## What this engine does

A portable **Agent Skills suite** (built in accordance with the `agentskills.io` standard with root `marketplace.json`). Any AI agent or automated harness can consume these skills, point them at target websites, and evaluate:

1. Detection accuracy (evidence-grounded, low false-positive rate)
2. Suggested-action quality (mechanism-sound, prioritized, actionable verification steps)
3. Output schema conformity
4. Skill-format hygiene
5. Modular skill composition (clean domain separation)
6. Broad generalization across diverse web architectures

Recommend-only. Python 3 stdlib. Network enabled. No paid APIs, no site writes, <5 min, ≤50 MB. Provider-neutral.

## Architecture

```
URL → crawl_site.py (robots, sitemap, llms.txt, ≤12 pages, CTA HEAD, optional GPTBot probe, 1 facet pair)
    → snapshot JSON
    → detect.py (per-skill functions)
    → compose_report.py (funnel rank, cap 18, unique IDs)
    → audit JSON (standard schema + extras)
```

Entrypoint skill: `skills/audit-orchestrator` (`marketplace.json` `entrypoint: true`).

Crawl **once**. Other skills read the snapshot via `--skill <id>`.

### Visibility funnel (severity)

1. **Index** — can a fetcher enter and read HTML? (robots, noindex, WAF, empty SPA)
2. **Cite** — can it extract the right fact for the right entity? (schema-type fit, sameAs, ItemList, dates)
3. **Land** — after a citation, is the visitor oriented and able to act? (dead CTA, H1/crumbs)

Index blockers &gt; money-template citability &gt; landability &gt; proactive (`llms.txt`, Wikipedia-for-SMB).

### Two-axis site model

- **Failure mode:** small business / enterprise / SPA / ambiguous name (not 24 industry cells)
- **Template:** ecommerce, airline, automotive, local, docs, media, collection, FAQ

Industry only changes **which JSON-LD type is eligible**.

### Corroboration tiers (do not penalize smallness)

- **Tier 0 (any size):** Org/LocalBusiness, NAP consistency, ≥1 controlled profile (GBP, LinkedIn, Justdial, Yelp, Instagram) in `sameAs`. Wikipedia **not** required.
- **Tier 1:** only if the **site claims** scale (`India's #1`, `Featured in Forbes`, `500+`). Then missing independent echo is **high**.
- Small shop, no boasts, no wiki → `FC-PROACT-02` low, plus `confidence_note`.

### Hard anti-FP rules

- Do not use Playwright 0.70 raw/rendered ratio (Apple/Stripe SSR). CRA-02 = empty `#root` / tiny word count only; skip if `__NEXT_DATA__` or healthy text.
- Apple gold `sameAs` (Wikidata + socials) has **no taxID**. FC-ENT-03 is **low/conditional**, never high.
- Thank-you/cart `noindex` is not a finding.
- Missing `llms.txt` = low proactive, mainly docs/SaaS.
- CRA-05 and ENG-03 are **one** finding (`CRA-05`).
- No `F-ENT-002`.
- Do not require Product schema on a restaurant homepage.

Finding IDs: [`skills/audit-orchestrator/references/catalog.md`](skills/audit-orchestrator/references/catalog.md).

## Repo map

| Path | Role |
|---|---|
| `marketplace.json` | Manifest, one entrypoint |
| `assets/report.schema.json` | Report floor + extras |
| `README.md` | Project README |
| `skills/audit-orchestrator/SKILL.md` | Entrypoint instructions |
| `skills/audit-orchestrator/scripts/crawl_site.py` | Fetch |
| `skills/audit-orchestrator/scripts/htmlutil.py` | DOM/JSON-LD signals |
| `skills/audit-orchestrator/scripts/detect.py` | All detectors |
| `skills/audit-orchestrator/scripts/compose_report.py` | Merge/rank |
| `skills/audit-orchestrator/scripts/run_audit.py` | CLI |
| `skills/audit-orchestrator/scripts/selftest.py` | Offline SPA vs Apple-like |
| `skills/*/scripts/run.py` | Per-skill CLI (`--skill`) |
| `skills/freshness-corroboration-audit/references/` | entity + schema-by-vertical |
| `research/` | Calibration fixtures — exclude from release |

Run:

```bash
python skills/audit-orchestrator/scripts/selftest.py
python skills/audit-orchestrator/scripts/skill_tests.py
python skills/audit-orchestrator/scripts/run_audit.py "https://example.com"
```

## Known Scope Boundary

ENG-02 is **structural** (H1, breadcrumbs). It checks verifiable hierarchy and navigation links, rather than subjective NLP evaluation of landing intent.

FC-FRESH-05 uses **priced-card structure** (homepage merch + tiny categories included), not Shopify `/collections/`. FC-FRESH-06 severity scales by which meta tag is blank. FC-ENT-02 skips global sameAs bar when LocalBusiness has complete NAP (FC-ENT-04). ENG-04 is empty FAQ accordion answers with schema fallback — not subjective templating.

## Engineering Quality Standards

Lean SKILL.md; logic in scripts; details in references. Evidence is `n/m` + URLs. Actions say **what to change and why a crawler/LLM cares**. Cap ~18 findings. Broad coverage across failure modes and templates.

## Current directory (paste into the next chat)

Do not zip `research/` or `.git`. Missing vs intended: `LICENSE`, `skills/nontext-surface-audit/scripts/run.py`.

```
brand-ai-readiness-audit/
  HANDOFF.md
  README.md
  marketplace.json
  .gitignore
  assets/
    report.schema.json
  skills/
    audit-orchestrator/
      SKILL.md
      references/
        catalog.md
        composition.md
        false-positives.md
      scripts/
        crawl_site.py
        htmlutil.py
        detect.py
        compose_report.py
        run_audit.py
        selftest.py
    crawl-access-audit/
      SKILL.md
      scripts/run.py
    render-quotability-audit/
      SKILL.md
      scripts/run.py
    freshness-corroboration-audit/
      SKILL.md
      references/
        entity.md
        schema-by-vertical.md
      scripts/run.py
    engagement-orientation-audit/
      SKILL.md
      scripts/run.py
    nontext-surface-audit/
      SKILL.md
  research/          # calibration only — exclude from package zip
    DAY1.md
    field-notes.md
    fetch-checklist.md
    gold-hypotheses.md
    gold-sheet.csv
    query-packs.md
    workbook.csv
```

