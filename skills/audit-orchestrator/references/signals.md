# Raw signals contract

The crawl emits **facts**, not narrative. Detectors decide which finding IDs fire and at what severity. The harness agent writes `evidence` / `suggested_action` from signals only.

## Digital consensus (off-origin)

After the on-origin crawl, the script probes **free** public endpoints (no paid keys):

- Wikipedia opensearch + summary
- Wikidata `wbsearchentities`
- DuckDuckGo Instant Answer
- Reddit public search JSON (best-effort)

Results land in `digital_consensus` and inform `site_scale` / FC-ENT-01 severity. LinkedIn/Quora are listed under limitations when not probeable without auth.

If `crawl_quality.crawl_incomplete` and `offsite_identity_strong`, missing on-site Organization JSON-LD is **medium** (“not visible in raw HTML”), not high “brand unknown.”

## Required honesty

- If a fetch fails: `http_status` null/0 and `fetch_error` set — never pretend the absence was confirmed.
- `name_collision_check.unrelated_entities_found` is **null** unless an off-site search was run (stdlib crawl does not invent SERP counts).
- `site_type` / `looks_placeholder` must not label a JS-thin enterprise homepage as an IANA placeholder when meta is rich or consensus echoes the brand.
- Evidence must not be a laundry list of nulls — lead with mechanism + consensus.
