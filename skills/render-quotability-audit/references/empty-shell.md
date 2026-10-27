# Empty shell vs legitimate SSR

CRA-02 is **empty-shell only**:

- Skip if `__NEXT_DATA__` or JSON-LD is present, or HTML word_count ≥ 25.
- Flag only a near-empty shell (`#root`/`#app` with word_count < 25).

Do not compute a headed-browser vs raw HTML ratio. That false-positives Apple and Stripe. Do not put that caveat in user-facing evidence.

CRA-05 is one finding for crawler **and** visitor: gated route with no public description. Do not also emit ENG-03.

CRA-06: one facet pair per crawl (budget). Identical raw text on `?filter=` vs the collection URL → CSR-only facets.

CRA-07: JS Load More / infinite scroll without crawlable `rel=next`.
