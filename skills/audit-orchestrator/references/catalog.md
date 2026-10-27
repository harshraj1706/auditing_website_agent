# Master check catalog (IDs in report JSON)

Consolidated from Novatech, Pine Villa, dainyjose, Uniswap, Apple, Suta.in, Akasa (Delhi–Mumbai), Krishna Dental.

No `F-ENT-002`. No `F-FRESH-*` / `F-ENG-*` aliases. CRA-05 and ENG-03 are **one** finding (`CRA-05`).

CRA-02 does **not** use a 0.70 rendered/raw ratio (Apple/Stripe SSR false positive). Empty raw shell only.

FC-FRESH-05 is gated by a **structural** listing signal (priced cards; homepage merch + tiny 2–3 SKU categories included), not Shopify `/collections/`. FC-FRESH-06 lives only in freshness; severity scales by which meta tag is blank. Twitter-only empty is low.

FC-ENT-02 (global sameAs) does **not** apply its ≥2 authority bar when a LocalBusiness already has complete PostalAddress + phone (FC-ENT-04 is the primary local disambiguator).

ENG-04: FAQ question headings with empty answer bodies — high only when FAQPage `acceptedAnswer` also absent. Short answers like `2h 15m` are **not** empty. Do not flag legitimate city-pair templating.

| ID | Skill | Notes |
|---|---|---|
| NET-01 | crawl-access / orchestrator | Origin unreachable (status 0), TLS/SSL failure, or HTTP ≥500. Fail-fast: do **not** run DOM/schema detectors. |
| CRA-03 | crawl-access | Origin HTTP 403/429 (WAF/rate-limit) **or** AI-UA probe blocked. Fail-fast when **homepage** is 403/429: emit CRA-03 only; do not invent FC-ENT/FC-FRESH from a challenge page. |
| CRA-01 | crawl-access | robots / sitemap / homepage noindex |
| CRA-02 | render | empty JS shell; third-party menu as CRA-02-MENU |
| CRA-04 | nontext | missing alt on load-bearing images only (width/height &gt; 100px); skip icon/logo/spacer |
| CRA-04-PDF | nontext | PDF-only thin HTML |
| CRA-04-CANVAS | nontext | canvas + low text |
| CRA-05 | render | state-gated, crawler **and** visitor fallback (includes ENG-03) |
| CRA-06 | render | CSR-only query facets |
| CRA-07 | render | Load More without rel=next |
| FC-ENT-01 | freshness | missing homepage Organization (or LocalBusiness when site_type=local). Never attach a Wikipedia/Wikidata sameAs unless the item's label overlaps the brand name. |
| FC-ENT-01-PRODUCT | freshness | Product/Offer on product templates |
| FC-ENT-01-FLIGHT | freshness | Flight/Airport/IATA on route pages |
| FC-ENT-01-VEHICLE | freshness | Car/Vehicle on inventory pages |
| FC-ENT-01-LOCAL | freshness | LocalBusiness + PostalAddress/hours — only when site_type=local **and** some identity schema already exists (do not double-count with FC-ENT-01) |
| FC-ENT-01-ARTICLE | freshness | Article/NewsArticle on editorial URLs |
| FC-ENT-01-FAQ | freshness | FAQPage on help/FAQ templates |
| FC-ENT-02 | freshness | sameAs triangulation for address-less / multi-location brands |
| FC-ENT-03 | freshness | taxID low/proactive, ambiguous + weak sameAs only |
| FC-ENT-04 | freshness | LocalBusiness PostalAddress + phone (primary local disambiguation) |
| FC-ENT-05 | freshness | unlabeled social |
| FC-FRESH-01 | freshness | no dateModified / last updated |
| FC-FRESH-02 | freshness | on-site vs 3rd-party prices |
| FC-FRESH-03 | freshness | 11pm–11pm |
| FC-FRESH-04 | freshness | Tier 0 profile vs Tier 1 unverifiable claims |
| FC-FRESH-05 | freshness | ItemList on **listing grids** (not PDP Product schema) |
| FC-FRESH-06 | freshness | blank meta `content=""`; severity by which tag |
| FC-PROACT-01 | orchestrator | llms.txt |
| FC-PROACT-02 | orchestrator | Wikipedia/Wikidata optional reach guidance |
| FC-PROACT-03 | orchestrator | schema.org speakable specification for voice/audio agents |
| ENG-01 | engagement | dead CTA |
| ENG-02 | engagement | H1 / breadcrumb / home link |
| ENG-04 | engagement | FAQ heading with empty answer body (schema fallback) |

**Known limitation (not coded):** subjective “is templated city-pair copy specific enough” — structural ENG-04 is the engagement check; do not score semantic relevance to visitor intent.
