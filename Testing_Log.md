# Testing & Hardening Log

This log documents the adversarial testing process used to harden this
marketplace — real bugs found against real live sites, root-caused, fixed,
and in most cases independently re-verified against a *different* site than
the one that first exposed them. Status tags are honest, not aspirational:
**Verified** means confirmed fixed on a second, independent case;
**Fixed, pending re-verification** means the fix is implemented but hasn't
yet been re-tested against the original failing case; **Open** means
identified but not yet resolved.

---

## 1. Entity identity & disambiguation

| Issue | Evidence | Fix | Status |
|---|---|---|---|
| False entity match — a corroboration search matched "healthcare" keyword overlap and suggested attaching an unrelated real charity (Nemours Foundation) to a client's `sameAs` | Live run on kivihealth.com | Require real name-string/domain corroboration before accepting a `sameAs` candidate, not topical keyword similarity | **Verified** — re-tested on KiviHealth, cppsmuz.org (honest empty result), and Gemini (below) |
| Ambiguous-name match — "Gemini" resolved to a Wikipedia disambiguation page and a Wikidata ID for the zodiac constellation, not Google's AI product | Live run on gemini.google.com; both URLs independently verified wrong | Reject disambiguation-page hits outright; require corroborating context beyond bare name match | **Verified** — re-run returned the correct Wikidata entity (Q116698014, confirmed via independent lookup) with no Wikipedia link offered at all |
| Flat disambiguation threshold wrongly penalized local businesses | Stress test: "Krishna Dental" collides with 7+ unrelated clinics nationally, yet resolves fine via street-address in its own title tag | Branch disambiguation logic: `LocalBusiness` with a complete `PostalAddress` satisfies via geography; `Organization` with no fixed address requires global authority-domain links (Wikidata/Wikipedia/Crunchbase) | **Verified** via the Krishna Dental / Novatech contrast |
| Hard legal identifiers (taxID/DUNS/LEI) flagged High severity | Apple's own real, correct schema has no taxID/DUNS/LEI and would have failed this check | Downgraded to low/proactive, only surfaced when an ambiguity signal is already present | **Fixed** |
| Corroboration check missed real, plainly-linked social profiles already in a site's own footer, before falling back to external search | KiviHealth's real footer has working Facebook/X/LinkedIn/Instagram links; report still said "no profile found" and suggested creating new ones | Parse on-page footer/header links for known social domains *before* running external search | **Verified** — re-run correctly cited the existing on-origin profiles and suggested adding them to `sameAs`, not creating new ones |
| Domain-anchored short brands (e.g. BBC) over-rejected by the Gemini/Nemours disambiguation guard — bare Wikipedia title treated as dab without site context | Live suspicion on bbc.com FC-FRESH-04 "zero corroboration" for one of the most-documented brands online | Treat registrable-label brands (`bbc.com` → BBC) as domain-anchored; pass site snap into dab checks; accept primary Wikipedia/Wikidata when title matches | **Verified** — offline BBC fixture (selftest): FC-FRESH-04 absent; only FC-ENT-02 (sameAs hygiene, medium) fires |

## 2. Fetch reliability & data integrity

| Issue | Evidence | Fix | Status |
|---|---|---|---|
| Total connection failure (expired SSL cert) reported as a confirmed content absence ("crawled homepage; 0 JSON-LD nodes found") | pinevillecafe.com — `limitations.fetch_errors` showed a total SSL failure while `findings[]` asserted a successful, empty crawl | Gate: on total fetch failure, suppress all content-dependent checks for that URL, emit one dedicated critical "unreachable" finding using the real error, in `findings[]` not just `limitations` | **Verified** — generalized correctly to a plain network timeout on a different KiviHealth page in a later run |
| Same bug recurred in a third form: robots.txt `Disallow: /` prevented crawler from fetching homepage, but engine treated it as "crawled, 0 JSON-LD nodes found" (`Crawled homepage None`), omitting `affected_urls` and leaving `CRA-01` in limitations | wsj.com — crawler obeyed robots.txt and blocked 30 URLs, but emitted FC-ENT-01 asserting missing schema from a page never seen | Add `origin_robots_blocked` gate in `detect_network_failure`; inherit `User-agent: *` disallow for bots in `_ai_bot_rules`; emit critical `CRA-01` and fail-fast before content checks; guarantee `affected_urls` and fallback `url` in `home()` | **Verified** — live wsj.com run: exactly 1 finding (`CRA-01`, critical), `affected_urls: ["https://www.wsj.com"]`, zero content findings, site_type "media", selftest fixture passing |
| `site_scale` fields (`page_count`, `has_careers`, `has_press`, etc.) returned byte-identical stub output across unrelated real sites | Confirmed via example.com / flipkart.com / apple.com all returning identical values including for Apple, which obviously has careers/press pages | Compute from actual crawled content; if crawl depth is intentionally limited, say so explicitly rather than defaulting to `false` | **Fixed, pending re-verification** — later runs (e.g. Gemini's `looks_small: false`) show differentiation, but no isolated confirmation pass has been run |

## 3. Vertical / page-type classification

| Issue | Evidence | Fix | Status |
|---|---|---|---|
| Collection/catalog schema check fired on a Terms & Conditions page | KiviHealth `/terms` — real repeated `<li>` link lists + one incidental currency mention elsewhere on the page, treated as a product grid | Require price-shaped text on the *same* repeated elements, not independent page-wide signals; exclude `/terms`, `/privacy`, `/legal` as `role=legal` | **Verified** via fixture (23 city links + "25 paise" → no false fire) |
| Flight/route schema check fired on an unrelated accessibility document | shopify.com/accessibility/vpat-checkout — zero relation to travel | Same root cause as above: loose structural proxy instead of a hard, category-specific token | **Fixed** — niche FLIGHT/VEHICLE schema emitters disabled; VPAT/Shopify fixtures assert silence |
| Same check fired on Shopify's own homepage — which already had *correct*, real `Corporation`/`ContactPoint` schema | shopify.com/in — evidence field itself proved real schema was present and still flagged "missing Flight schema" | Shared `classify_page()` gate; niche flight/vehicle checks disabled entirely after BBC Business/Technology false positives | **Fixed, pending re-verification** — flight check stopped on fixtures and later Shopify-like runs; live Shopify URL with crawl scope held constant still recommended |
| Vehicle schema check fired on BBC Technology / news pages | bbc.com technology coverage treated as dealership inventory | Disabled `FC-ENT-01-VEHICLE` niche emitter alongside flight | **Fixed, pending re-verification** |
| FAQ-completeness check fired on ordinary news headlines phrased as questions | bbc.com — "Can Europe recharge its battery industry?" independently confirmed as a real, currently-published feature headline, not an FAQ | Require real accordion/FAQ chrome (`<details>`/`<summary>`, `aria-expanded`, accordion/faq class, or explicit FAQ section heading) before ENG-04 runs; bare `?` headlines are not candidates | **Fixed, pending re-verification** — offline BBC-style fixture stays silent; live bbc.com re-run recommended |
| Same root cause affecting FAQPage-schema check on BBC Sport/Health section pages | bbc.com/sport, /health | Same FAQ-chrome gate for `hard_faq_signal` / `FC-ENT-01-FAQ` — no FAQ class without path, FAQPage schema, or real FAQ chrome + Q&A pairs | **Fixed, pending re-verification** |
| FAQ-completeness threshold itself was flawed — a short real answer ("2h 15m") would have false-positived against a character-count minimum | Design review, corrected before shipping | Changed to a presence check (any real text vs. genuinely empty), not a length threshold | **Fixed** |

## 4. Report hygiene

| Issue | Evidence | Fix | Status |
|---|---|---|---|
| Duplicate `problems[]` and `findings[]` arrays carrying the same content under different field names | Gemini run | Removed `problems[]` entirely | **Verified** — absent from all subsequent runs |
| Internal dev/calibration notes leaking into user-facing `how`/`evidence` fields (research site names, appendix references, "do not attach..." guard notes) | Recurred across at least 4 separate rounds (KiviHealth, cppsmuz, Shopify) before fully resolved | `_public_prose()` filter applied to `evidence`, `action`, and `how`; test suite fails build if leaked patterns detected | **Verified** — confirmed clean via direct text grep on a full report; note this took multiple passes to actually close |
| Non-HTML resource (a real `SKILL.md` file on shopify.com, served as `text/plain`) ran through HTML-structural checks (H1/breadcrumbs) | Fetched directly and confirmed real | Gate structural engagement checks on `Content-Type: text/html`; skip non-HTML resources | **Open** |
| Minor evidence/`affected_urls` count mismatches (e.g. "2 pages" but 1 URL listed) | Shopify, early KiviHealth runs | Fixed in later runs | **Verified** on most recent runs checked |
| FC-FRESH-01 wording used e-commerce framing ("near prices/specs") on a news publisher | bbc.com freshness finding | Adapt copy by site type: publishers get publish/update timestamp language; commerce keeps prices/hours/policies | **Fixed, pending re-verification** |

## 5. Process & packaging verification

| Item | Status |
|---|---|
| README.md — required deliverable, describes skills + composition | **Verified** — real content reviewed |
| `marketplace.json` — single entrypoint, correct shape | **Verified** — real content reviewed |
| `skills-ref validate` on all 6 skill folders | **Verified** — real CLI output pasted (`Exit code 0`, all 6 valid) |
| Zip size / no pretrained weights | Asserted (~0.2MB), not independently re-confirmed at time of writing |
| Full entrypoint composition (orchestrator = correct superset of sibling-skill outputs on the same URL) | **Open** — recommended, not yet run |
| Determinism (identical URL run twice → identical facts/severities) | **Verified** — finding IDs and severities are deterministic (only `audited_at` timestamp changes between runs) |

## 6. Deliberate scope decisions

| Decision | Architectural Basis |
|---|---|
| No arbitrary `priority = severity_weight × confidence` formula | Pure mechanism: severity derives strictly from the AI indexing/citation funnel rank (Index blockers > Citability > Landability), not artificial numeric weights |
| Intelligent bounded crawl budget | Fixed 12-page sample budget with strict 5-minute timeout and standard robots.txt compliance to prevent origin bombardment |
| Content-inferred engagement signals | Infer engagement and landability barriers strictly from verifiable DOM structures and response codes, avoiding unreliable external traffic guesswork |
| Core engine focus | Maintain a provider-neutral, modular Agent Skills architecture adhering to agentskills.io standard with zero bloat |

## 7. Comparative design decisions & differentiation

- **Actionable verification steps**: Added a `verification_steps` field per finding, giving the site owner concrete commands (curl, schema validators) to independently confirm their fix worked. Confirmed present across all detectors via selftest.
- **Architectural site classification**: Exposed `site_type` in the report built from DOM signals and role inference, ensuring detectors apply template-appropriate rules.
- **Voice / Conversational AI readiness (`FC-PROACT-03`)**: Added schema.org `SpeakableSpecification` inspection for article/news publishers to support Siri/Google Assistant/Gemini speech synthesis. Strictly gated on real `Article`/`NewsArticle`/`BlogPosting` schema.
- **Single source of truth**: Consolidated findings into a unified `findings[]` array without duplicate `recommendations[]` or `problems[]` arrays.

---

## Highest-priority open items at time of writing

1. **Live re-verify** the FAQ/accordion gate on bbc.com (Business/Sport/Health) — offline BBC-style fixture is silent; confirm the live case no longer fires ENG-04 / FC-ENT-01-FAQ at high severity.
2. Widen the fetch-failure gate to cover blocked-but-responded pages (Section 2), and re-verify on a WAF-blocked site (Meesho or equivalent).
3. Confirm the vertical-classifier gate is a single shared function, not a narrow per-site patch — re-test explicitly against the original failing Shopify URL with crawl scope held constant.
4. Run the determinism and full-composition checks (Section 5) at least once before release.
5. Live re-verify BBC consensus / FC-FRESH-04 after the domain-anchored identity fix.
