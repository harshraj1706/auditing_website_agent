# Index blockers

Funnel rank: cannot fetch HTML → nothing else matters.

- **NET-01**: origin GET returns status 0, TLS/`CERTIFICATE_VERIFY_FAILED` / hostname mismatch, or HTTP ≥500. Emit this alone; do not invent CRA-01/FC-ENT findings from an empty DOM.
- **CRA-03 fail-fast**: origin GET returns 403 or 429. Emit CRA-03 alone; a WAF/rate-limit body is not evidence of missing JSON-LD or meta tags.
- `GET /robots.txt` and `/sitemap.xml` status codes are evidence, not guesses — but only after the origin HTML is reachable.
- `User-agent: GPTBot` / `Google-Extended` / `PerplexityBot` / `ClaudeBot` with `Disallow: /` is an index block.
- Homepage `meta robots noindex` is critical. Path hints `thank`, `cart`, `checkout`, `login`, `search?` are excluded.
- WAF: status 403, `cf-mitigated`, or “just a moment” + Cloudflare body on `/` or AI UA probes (CRA-03 — not NET-01).
- If robots disallows a path, record `limitations.robots_blocked` instead of inventing page findings.
