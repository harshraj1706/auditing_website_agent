# Entity identity — two-tier corroboration + local vs global disambiguation

Do **not** score a two-person shop and a Fortune 500 on the same “has Wikipedia” bar. That penalizes smallness, not practice.

## Tier 0 (any size)

Fair to expect:

- Organization/LocalBusiness JSON-LD, internally consistent NAP
- At least one independently-controlled profile: Google Business, LinkedIn, Justdial, IndiaMART, Yelp, Instagram/Facebook — **not** Wikipedia
- Those URLs listed in `sameAs` (not only icon `<a>` tags)

## Tier 1 (only if the site claims scale)

Wikipedia/Wikidata/press are expected **only when** homepage/about copy boasts reach (`trusted by 500+`, `Featured in Forbes`, `India's #1`, funding, N countries) **or** you are cross-checking that specific claim.

If the site only says “we make handloom sarees, established 2015”:

- Missing Wikipedia = **proactive**, never medium/high
- Add `confidence_note` when the footprint looks small

If it claims national scale and nothing off-site echoes it → **high**, framed as an unverifiable claim (credibility risk), not “you are not famous.”

## Local vs global disambiguation (Krishna Dental vs Novatech)

Common Indian SMB names (`Krishna Dental`, deity/personal name + category) collide constantly. They do **not** need Wikidata — they disambiguate through **geography**.

| Entity shape | Sufficient disambiguation | Catalog |
|---|---|---|
| LocalBusiness / single-location with street address | Complete `PostalAddress` + phone (+ Maps/GBP in `sameAs` when available) | **FC-ENT-04** primary; **FC-ENT-02** authority-count bar does **not** apply |
| Organization with no fixed address, multi-location, or online-only | ≥2 authority `sameAs` (Wikidata/Wikipedia/Crunchbase/LinkedIn + social) | **FC-ENT-02** |

Do not raise FC-ENT-02 high on a clinic that already publishes street + city + phone in LocalBusiness JSON-LD (or a title that embeds the NAP). That is the small-business false positive wearing a Novatech costume.

## Name-twins (Novatech)

Still require on-site identity graph (Tier 0 schema + sameAs to *whatever profiles exist*). Do not require Wikidata unless they claim to be the globally known entity — and never require it of a single-location LocalBusiness with complete NAP.
