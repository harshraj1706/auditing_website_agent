---
name: freshness-corroboration-audit
description: >-
  Audit entity identity and whether JSON-LD types fit the page vertical
  (Product/Offer, ItemList on listing grids, Flight/IATA, Vehicle/Car,
  LocalBusiness NAP, Article dateModified, FAQPage, Organization.sameAs).
  Use for schema mismatch, GEO structured data, name-twins, local vs global
  disambiguation, or undated articles.
license: MIT
compatibility: Python 3.10+ stdlib, network fetch, no paid APIs.
---

# Freshness / corroboration / entity identity

Appendix D: machines trust facts that are **consistent and anchored off-site**. Name-twins (Novatech UK vs US vs India) merge leadership unless the origin publishes a hard identity graph. Single-location clinics with common names (Krishna Dental) disambiguate through **geography**, not Wikidata.

## Gold pattern (not a defect checklist)

Apple-class `Organization.sameAs` includes a **Wikidata entity** plus official social profile URLs. A lone LinkedIn URL is weak. **Do not** require `taxID` / NAICS as high severity — many healthy enterprises omit them.

## Procedure

```bash
python3 scripts/run.py "<URL>"
```

Checks (see [references/entity.md](references/entity.md) and [references/schema-by-vertical.md](references/schema-by-vertical.md)):

1. **Tier 0 (any size):** Organization/LocalBusiness + NAP consistency + at least one independently-controlled profile (Google Business, LinkedIn, Justdial, Yelp…) in `sameAs`. Wikipedia is **not** required.
2. **Local vs global disambiguation:** If LocalBusiness has complete PostalAddress + phone, that satisfies identity (FC-ENT-04). Do **not** also demand ≥2 authority `sameAs` (FC-ENT-02) — that bar is for address-less / multi-location brands.
3. **Tier 1 only if the site claims scale:** “India’s #1” / “Featured in Forbes” / “500+ retailers” without independent corroboration → high. No such claims → wiki gap is proactive only, with `confidence_note`.
4. Vertical schema fit (Product vs **ItemList on listing grids** — including homepage merch and tiny 2–3 SKU categories — vs Flight vs Vehicle vs FAQPage vs Article dates).
5. Icon-only socials; identical hours typos.
6. Blank fallback metadata (`FC-FRESH-06`) — severity by which tag is empty.

Legal IDs (`taxID`, `leiCode`) are **low / optional** on ambiguous names only, and never when local geo already disambiguates.

## Output

Suggested actions must tell the brand to **declare identity in HTML JSON-LD**, not to “run ads.”
