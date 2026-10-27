---
name: audit-orchestrator
description: Compose a brand AI-readiness audit for any website URL. Use when asked to audit AI discoverability, GEO, citation readiness, JSON-LD, robots.txt, sameAs, or produce the marketplace audit report JSON. Entrypoint of the brand-ai-readiness-audit marketplace.
license: MIT
compatibility: Python 3.10+ stdlib, network fetch. No paid APIs.
---

# Brand AI-readiness audit (entrypoint)

Recommend-only. Never modify the live site.

## What the script does

1. Crawl the site (robots-aware).
2. **Internally** cross-check the brand on Wikipedia / Wikidata / DuckDuckGo / Reddit to validate severity (e.g. do not call a well-known brand a “placeholder”). This consensus is **not** printed in the default report.
3. Emit **findings[]** only: real defects with evidence + suggested_action (no duplicate `problems[]`).

## Procedure

```bash
python3 scripts/run_audit.py "<URL>"
```

Optional: `--verbose` (debug: includes internal consensus + per-finding signals). `--skill <id>` for one skill.

## Output (default)

```json
{
  "site": "…",
  "audited_at": "…",
  "summary": { "total_findings": N, "critical": …, "high": …, "medium": … },
  "findings": [
    {
      "id": "CRA-02",
      "title": "…",
      "severity": "high",
      "evidence": "…",
      "suggested_action": { "summary": "…", "priority": "high" }
    }
  ]
}
```

## Rules for you (harness agent)

1. Present **findings** to the user — do not dump internal consensus or raw signals unless asked / `--verbose`.
2. You may rewrite `evidence` / `suggested_action.summary` in your own words, but every concrete fact must appear in that finding’s `signals` (when present under `--verbose`) or in the detector evidence. Do not invent findings.
3. Do not change `id` or `severity`.
4. **Case-write actions from signals — never paste a fixed SMB template:**
   - If `digital_consensus.offsite_identity_strong` or `tier1_profile_urls` is non-empty, do **not** suggest claiming a Google Business Profile.
   - If `scale_claim_phrases_found` is empty, do **not** say “substantiate scale claims.”
   - Prefer naming concrete sameAs targets **only when** `identity_verified` is true (disambiguation rejected + entity corroborated). Never attach a Wikipedia dab page, zodiac/crypto hit, or topical lookalike (KiviHealth ≠ Nemours; Google Gemini ≠ `/wiki/Gemini` dab or Q8923 constellation). When `identity_ambiguous` and not verified, say no confident external match — do not guess.
   - LocalBusiness / GBP / Restaurant wording is only for `site_type=local` (or `is_local_entity`). Never suggest Restaurant for SaaS.
   - Do not drop `id`. Every finding must keep its catalog id.

Finding IDs: [references/catalog.md](references/catalog.md). Anti-FP: [references/false-positives.md](references/false-positives.md).

## Sibling skills

`crawl-access-audit`, `render-quotability-audit`, `freshness-corroboration-audit`, `engagement-orientation-audit`, `nontext-surface-audit`.
