"""Evidence-backed findings. Calibrated against field notes (Novatech, Pine Villa, SPA, Apple)."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from consensus import crawl_quality, JS_SHELL_NOTE
from htmlutil import (
    annotate_page_classes,
    brand_token_ambiguous,
    collect_profile_urls,
    hard_travel_signal,
    infer_site_scale,
    is_html_content_type,
    local_geo_disambiguated,
    looks_like_collection,
    merge_consensus_profiles,
    pages_of_class,
    schema_covers_question,
)

SKIP_NOINDEX_HINTS = ("thank", "cart", "checkout", "login", "signin", "search?")
AUTH_PATH_RE = re.compile(
    r"/(?:[a-z0-9_-]+/)*(?:log-?in|sign-?in|sign-?up|account|dashboard|wallet|positions|checkout|billing|auth)(?:/|$)",
    re.I,
)
GATED_SKIP_ROLES = {"home", "about", "blog", "faq", "contact", "pricing"}


def _uniq_urls(urls: list[str | None]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in urls or []:
        if not raw:
            continue
        key = raw.rstrip("/") or raw
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _identity_schema_want(site_type: str, sig: dict[str, Any]) -> str:
    text = ((sig.get("text") or "") + " " + (sig.get("title") or "")).lower()
    if site_type == "local":
        if re.search(r"\b(dentist|dental)\b", text):
            return "LocalBusiness/Dentist"
        if re.search(r"\b(restaurant|cafe|menu|hotel)\b", text):
            return "LocalBusiness/Restaurant"
        return "LocalBusiness"
    if site_type == "saas":
        return "Organization"
    return "Organization (or Person on a portfolio)"


def _verified_sameas_urls(cons: dict[str, Any]) -> list[str]:
    if not cons.get("identity_verified"):
        return []
    wiki = cons.get("wikipedia") or {}
    wd = cons.get("wikidata") or {}
    urls = []
    if wiki.get("name_match") and wiki.get("page_url"):
        urls.append(wiki["page_url"])
    if wd.get("name_match") and wd.get("top_id"):
        urls.append(f"https://www.wikidata.org/wiki/{wd['top_id']}")
    return urls


def finding(
    fid: str,
    title: str,
    severity: str,
    evidence: str,
    action: str,
    *,
    category: str,
    failure_mode: str,
    how: str,
    urls: list[str] | None = None,
    confidence: float = 0.9,
    priority: str | None = None,
    confidence_note: str | None = None,
) -> dict[str, Any]:
    rec = {
        "id": fid,
        "title": title,
        "severity": severity,
        "evidence": evidence,
        "category": category,
        "failure_mode": failure_mode,
        "confidence": confidence,
        "affected_urls": _uniq_urls(urls or []),
        "suggested_action": {
            "summary": action,
            "priority": priority or severity,
            "how": how,
        },
    }
    if confidence_note:
        rec["confidence_note"] = confidence_note
    return rec


def home(snap: dict[str, Any]) -> dict[str, Any]:
    pages = snap.get("pages") or []
    for p in pages:
        if p.get("role") == "home":
            return p
    if pages:
        return pages[0]
    origin = snap.get("origin") or snap.get("start") or ""
    home_url = (origin.rstrip("/") + "/") if origin else ""
    return {"url": home_url, "signals": {}, "role": "home"}


def _transport_dead(status: Any, error: str | None) -> bool:
    """True when the origin document was not retrieved (TLS/connect/5xx)."""
    if isinstance(status, int) and status >= 500:
        return True
    if status == 0:
        return True
    if status in (None, "") and error:
        err = (error or "").lower()
        return any(x in err for x in ("certificate", "ssl", "name mismatch", "hostname mismatch"))
    return False


def _origin_refused(status: Any) -> bool:
    """WAF/rate-limit: origin answered, but the HTML is a challenge/empty block page."""
    return status in (403, 429)


_CHALLENGE_BODY_RE = re.compile(
    r"(just a moment|checking your browser|challenge-platform|cf-chl-widget|"
    r"cf-turnstile|enable javascript and cookies|attention required|"
    r"please wait while we verify|captcha-delivery|ddos-guard)",
    re.I,
)


def _page_is_challenge(page: dict[str, Any]) -> bool:
    """True when the HTML body looks like a WAF challenge, regardless of status code.

    Catches HTTP 200 Cloudflare challenge pages (Meesho-class false positive).
    """
    sig = page.get("signals") or {}
    wc = int(sig.get("word_count") or 0)
    text = (sig.get("text") or "")[:3000].lower()
    # waf_hint is already set by crawl_site._waf_hint (checks CF headers + body keywords).
    if page.get("waf_hint") and wc < 60:
        return True
    # Even without waf_hint, detect challenge pages by body content patterns.
    if wc < 60 and _CHALLENGE_BODY_RE.search(text):
        return True
    return False


def _home_fetch_info(snap: dict[str, Any]) -> dict[str, Any]:
    h = home(snap)
    errs = (snap.get("limitations") or {}).get("fetch_errors") or []
    url = h.get("url") or snap.get("start") or snap.get("origin") or ""
    status = h.get("status") if h else None
    err = None
    if h:
        err = next(
            (e.get("error") for e in errs if (e.get("url") or "") in (url, url.rstrip("/"), url + "/")),
            None,
        )
        if err is None and errs:
            err = errs[0].get("error")
        return {"url": url, "status": status, "error": err, "page": h}
    if errs:
        e0 = errs[0]
        return {
            "url": e0.get("url") or url,
            "status": e0.get("status"),
            "error": e0.get("error"),
            "page": {},
        }
    return {"url": url, "status": None, "error": None, "page": {}}


def origin_unreachable(snap: dict[str, Any]) -> dict[str, Any] | None:
    """True when the origin HTML was never retrieved — do not run DOM detectors."""
    info = _home_fetch_info(snap)
    status, err, url = info.get("status"), info.get("error"), info.get("url") or ""
    if info.get("page") or status is not None:
        if _transport_dead(status, err):
            return {"url": url, "status": status, "error": err or "fetch_failed"}
    if not info.get("page") and err is not None:
        if _transport_dead(status, err):
            return {"url": url, "status": status, "error": err}
    pages = snap.get("pages") or []
    if pages and all(_transport_dead(p.get("status"), None) for p in pages):
        return {
            "url": url,
            "status": pages[0].get("status"),
            "error": err or "no_html_retrieved",
        }
    return None


def origin_waf_blocked(snap: dict[str, Any]) -> dict[str, Any] | None:
    """Origin blocked: HTTP 403/429 OR an HTTP 200 challenge/interstitial page.

    Widened beyond status-code-only to catch WAF challenge pages that respond with
    HTTP 200 (Cloudflare 'Just a moment', Akamai, DDoS-Guard). A challenge page is
    not the brand's real HTML — do not run schema/meta detectors against it.
    """
    info = _home_fetch_info(snap)
    status = info.get("status")
    if _origin_refused(status):
        return {
            "url": info.get("url"),
            "status": status,
            "error": info.get("error") or f"HTTP {status}",
        }
    h = info.get("page") or {}
    # Non-200 with WAF hint (401, 407, etc.)
    if h.get("waf_hint") and h.get("status") not in (200, 304):
        st = h.get("status")
        if _origin_refused(st) or st in (401, 407):
            return {"url": h.get("url") or info.get("url"), "status": st, "error": "waf_challenge"}
    # HTTP 200 challenge page: looks like a WAF interstitial despite 200 status.
    if h.get("status") == 200 and _page_is_challenge(h):
        return {
            "url": h.get("url") or info.get("url"),
            "status": 200,
            "error": "waf_challenge_200",
        }
    return None


def origin_robots_blocked(snap: dict[str, Any]) -> dict[str, Any] | None:
    """Origin blocked by robots.txt: crawlers disallowed from fetching the homepage.

    Compliance fail-fast: when robots.txt disallows the homepage, we respect robots.txt
    and do not crawl it. We must NOT run schema/meta/DOM checks asserting '0 nodes found'
    against HTML our own crawler was forbidden to fetch.
    """
    limitations = snap.get("limitations") or {}
    origin = snap.get("origin") or snap.get("start") or ""
    home_url = (origin.rstrip("/") + "/") if origin else ""
    blocked = limitations.get("robots_blocked") or []
    is_home_blocked = (
        limitations.get("home_robots_blocked")
        or home_url in blocked
        or (origin and origin in blocked)
        or snap.get("robots", {}).get("home_disallowed")
    )
    if is_home_blocked:
        return {
            "url": home_url or origin,
            "blocked_count": len(blocked) or 1,
            "blocked_samples": blocked[:5],
        }
    robots = snap.get("robots") or {}
    if robots.get("ai_bots", {}).get("*") == "disallow_root" and not snap.get("pages"):
        return {
            "url": home_url or origin,
            "blocked_count": len(blocked) or 1,
            "blocked_samples": blocked[:5],
        }
    return None


def origin_fetch_aborted(snap: dict[str, Any]) -> dict[str, Any] | None:
    """Fail-fast: no trustworthy HTML (network/SSL/5xx, WAF 403/429, or robots.txt disallow)."""
    return origin_unreachable(snap) or origin_waf_blocked(snap) or origin_robots_blocked(snap)


def detect_network_failure(snap: dict[str, Any]) -> list[dict[str, Any]]:
    """Fail-fast: no trustworthy HTML means no schema/meta conclusions."""
    net = origin_unreachable(snap)
    if net:
        err = (net.get("error") or "").strip()
        status = net.get("status")
        low = err.lower()
        sslish = any(x in low for x in ("certificate", "ssl", "hostname mismatch", "name mismatch"))
        if sslish:
            mismatch = "mismatch" in low or "doesn't match" in low or "does not match" in low
            evidence = (
                "Crawler aborted. SSL certificate verify failed"
                + (" (Hostname mismatch). " if mismatch else ". ")
                + "AI agents cannot securely ingest data from this domain."
            )
            if err and err.lower() not in evidence.lower():
                evidence = evidence.rstrip(".") + f" Detail: {err}."
        elif isinstance(status, int) and status >= 500:
            evidence = (
                f"Crawler aborted. Origin HTTP {status}. "
                "AI agents cannot securely ingest data from this domain."
            )
            if err:
                evidence = evidence.rstrip(".") + f" Detail: {err}."
        else:
            evidence = (
                f"Crawler aborted. Origin HTTP status {status}. "
                "AI agents cannot securely ingest data from this domain."
            )
            if err:
                evidence = evidence.rstrip(".") + f" Detail: {err}."
        return [
            finding(
                "NET-01",
                "Site Unreachable or SSL Invalid",
                "critical",
                evidence,
                "Install a valid HTTPS certificate that matches this hostname and confirm the homepage loads over HTTPS.",
                category="discoverability",
                failure_mode="net.origin_unreachable",
                how=(
                    "In your DNS/hosting panel, issue or renew a TLS certificate for this exact hostname "
                    "(include www and apex if both are used), wait for propagation, then verify "
                    "https:// loads without browser certificate warnings."
                ),
                urls=[net.get("url")] if net.get("url") else None,
                confidence=0.95,
            )
        ]

    waf = origin_waf_blocked(snap)
    if waf:
        status = waf.get("status")
        err_type = waf.get("error") or ""
        if status == 429:
            label = "rate limited"
        elif "challenge_200" in err_type:
            label = "WAF challenge page returned as HTTP 200"
        else:
            label = "WAF/forbidden"
        return [
            finding(
                "CRA-03",
                "WAF / bot-block for AI crawlers",
                "critical",
                (
                    f"Crawler aborted. Origin HTTP {status} ({label}). "
                    "The response is a challenge or empty block page, not the public site. "
                    "AI agents cannot ingest live HTML from this domain until the block is lifted."
                ),
                "Allow verified AI crawler user-agents on public HTML in your WAF, and raise or "
                "exempt rate limits for those bots.",
                category="discoverability",
                failure_mode="index.waf_block",
                how=(
                    "In Cloudflare/AWS WAF (or equivalent), allowlist GPTBot, PerplexityBot, and ClaudeBot "
                    "on marketing HTML, or serve a 200 HTML snapshot instead of a JS challenge. "
                    "If you rate-limit, return 200 for known AI crawlers rather than 429 on the homepage."
                ),
                urls=[waf.get("url")] if waf.get("url") else None,
                confidence=0.95,
            )
        ]

    rob = origin_robots_blocked(snap)
    if rob:
        url = rob.get("url") or snap.get("origin") or ""
        count = rob.get("blocked_count", 1)
        more = f" and {count - 1} other public section URLs" if count > 1 else ""
        evidence = (
            f"Crawler aborted. robots.txt Disallow: / blocks crawlers from accessing the homepage ({url}){more}. "
            "AI agents and search bots cannot ingest live HTML or schema from this domain while robots.txt disallows access."
        )
        return [
            finding(
                "CRA-01",
                "robots.txt Disallow: / blocks homepage and site crawling",
                "critical",
                evidence,
                "Update robots.txt to allow AI and search crawlers access to public marketing and canonical pages.",
                category="discoverability",
                failure_mode="index.robots_disallow_all",
                how=(
                    "In /robots.txt, ensure User-agent: * does not Disallow: / for public pages. "
                    "If specific bots are restricted, whitelist AI discovery crawlers (e.g. GPTBot, PerplexityBot) on public HTML."
                ),
                urls=[url],
                confidence=0.98,
            )
        ]

    return []


def detect_crawl_access(snap: dict[str, Any]) -> list[dict[str, Any]]:
    """CRA-01, CRA-03."""
    out: list[dict[str, Any]] = []
    h = home(snap)
    origin = snap.get("origin") or ""
    robots = snap.get("robots") or {}
    ai = robots.get("ai_bots") or {}
    blocked = [k for k, v in ai.items() if v == "disallow_root"]
    sig = h.get("signals") or {}
    noindex_home = sig.get("noindex") and not any(
        x in (h.get("url") or "").lower() for x in SKIP_NOINDEX_HINTS
    )
    bits = []
    sev = "medium"
    if noindex_home:
        bits.append(f"homepage meta robots noindex on {h.get('url')}")
        sev = "critical"
    if blocked:
        if "*" in blocked:
            bits.append("robots.txt Disallow:/ for all User-agents (*)")
        ai_only = [b for b in blocked if b != "*"]
        if ai_only:
            bits.append(f"robots.txt Disallow:/ for {', '.join(ai_only)}")
        sev = "critical" if ("*" in blocked or "GPTBot" in blocked or len(blocked) >= 2) else "high"
    r_blocked = (snap.get("limitations") or {}).get("robots_blocked") or []
    if r_blocked and not any("robots.txt" in b for b in bits):
        bits.append(f"robots.txt disallowed {len(r_blocked)} URLs during crawl")
    if robots.get("status") not in (200,):
        bits.append(f"GET /robots.txt HTTP {robots.get('status')}")
    sm = (snap.get("sitemap") or {}).get("status")
    if sm not in (200,):
        bits.append(f"GET /sitemap.xml HTTP {sm}")
    if bits:
        out.append(
            finding(
                "CRA-01",
                "robots.txt / sitemap / noindex blocks or weakens crawlers",
                sev,
                "; ".join(bits) + ".",
                "Fix robots/sitemap/noindex so public pages are fetchable; keep noindex only on thank-you/cart.",
                category="discoverability",
                failure_mode="index.robots_sitemap_noindex",
                how="Allow public HTML. Sitemap of canonical URLs. Never noindex the marketing homepage.",
                urls=[h.get("url") or origin],
            )
        )
    waf_bits = []
    if h.get("waf_hint") or h.get("status") == 403:
        waf_bits.append(f"default UA GET / HTTP {h.get('status')} cf={bool(h.get('cf'))}")
    for probe in snap.get("ai_ua_probes") or []:
        if probe.get("waf") or probe.get("status") == 403 or probe.get("cf-mitigated"):
            waf_bits.append(f"{probe.get('ua')} HTTP {probe.get('status')}")
    if waf_bits:
        out.append(
            finding(
                "CRA-03",
                "WAF / bot-block for AI crawlers",
                "critical",
                " ".join(waf_bits) + ". Challenge pages are invisible to GPTBot/Perplexity-class fetchers.",
                "Allow verified AI crawler UAs in WAF while keeping abusive-bot rules.",
                category="discoverability",
                failure_mode="index.waf_block",
                how="Skip JS challenges for GPTBot, PerplexityBot, ClaudeBot on public HTML.",
                urls=[h.get("url") or origin],
            )
        )
    return out


def detect_render(snap: dict[str, Any]) -> list[dict[str, Any]]:
    """CRA-02, CRA-05/ENG-03, CRA-06, CRA-07, third-party menus."""
    out: list[dict[str, Any]] = []
    pages = snap.get("pages") or []
    cons = snap.get("digital_consensus") or {}
    cq = cons.get("crawl_quality") or {}
    # CRA-02: empty shell only. Do not use a rendered/raw ratio (Apple/Stripe SSR).
    spa_hits = []
    for p in pages:
        sig = p.get("signals") or {}
        wc = int(sig.get("word_count") or 0)
        if sig.get("next_data") or sig.get("json_ld") or wc >= 25:
            continue
        if sig.get("spa_shell") or ((sig.get("script_count") or 0) >= 3):
            spa_hits.append(p)
    if spa_hits:
        urls = [p.get("url") for p in spa_hits[:6]]
        wc = (spa_hits[0].get("signals") or {}).get("word_count")
        critical = any(int((p.get("signals") or {}).get("word_count") or 0) < 15 for p in spa_hits)
        out.append(
            finding(
                "CRA-02",
                "JS-render gap / empty application shell",
                "critical" if critical else "high",
                f"{len(spa_hits)}/{len(pages)} pages have near-empty raw HTML "
                f"(word_count={wc} on {urls[0]}).",
                "Serve SSG/SSR HTML for public routes, not a blank #root.",
                category="discoverability",
                failure_mode="index.js_empty_html",
                how="curl of the URL must contain the facts a user sees.",
                urls=urls,
            )
        )
    elif (
        cq.get("crawl_incomplete")
        and cq.get("rich_meta_thin_body")
        and not (home(snap).get("signals") or {}).get("next_data")
        and not (home(snap).get("signals") or {}).get("json_ld")
    ):
        h = home(snap)
        sig = h.get("signals") or {}
        out.append(
            finding(
                "CRA-02",
                "Public homepage HTML is thin relative to marketing meta (likely JS-minimized)",
                "high",
                f"{h.get('url')}: word_count={sig.get('word_count')}, script_count={sig.get('script_count')}, "
                f"meta_description length={len((sig.get('meta_description') or ''))}, "
                f"ld_json_blocks={len(sig.get('json_ld') or [])}. "
                f"Consensus: platforms_with_echo={cons.get('platforms_with_echo')}. "
                "A lightweight fetcher cannot quote the page body even though the brand is well-known off-site.",
                "SSR the hero copy and Organization/Product JSON-LD into the first HTML byte stream.",
                category="discoverability",
                failure_mode="index.thin_shell_rich_meta",
                how="This is the real discoverability defect on JS-heavy enterprises — not 'missing Wikipedia'.",
                urls=[h.get("url") or ""],
                confidence=0.7,
                confidence_note=cq.get("note"),
            )
        )
    localish = snap.get("site_type") in {"local", "marketing"}
    third = []
    for p in pages:
        third.extend((p.get("signals") or {}).get("third_party_menu") or [])
    if localish and third:
        out.append(
            finding(
                "CRA-02-MENU",
                "Primary facts live on a client-rendered third-party host",
                "medium",
                f"Menu/order URLs point off-origin ({third[:3]}).",
                "Expose a crawlable menu (HTML or Menu JSON-LD) on the primary domain.",
                category="discoverability",
                failure_mode="cite.third_party_spa_menu",
                how="Do not rely on Petpooja/Toast SPAs for quotable items.",
                urls=third[:4],
            )
        )
    gated = [
        p
        for p in pages
        if p.get("role") not in GATED_SKIP_ROLES
        and AUTH_PATH_RE.search(urlparse(p.get("url") or "").path or "")
    ]
    thin_gated = [p for p in gated if (p.get("signals") or {}).get("word_count", 0) < 60]
    if thin_gated:
        p0 = thin_gated[0]
        sig0 = p0.get("signals") or {}
        desc = (sig0.get("meta_description") or sig0.get("og_description") or "").strip()
        out.append(
            finding(
                "CRA-05",
                "State-gated route with no public explanation for visitors",
                "high",
                f"{len(thin_gated)} URLs look auth/wallet gated and thin (e.g. {p0.get('url')}, "
                f"word_count={sig0.get('word_count')}, meta_description={desc!r}). "
                "Discoverability: crawler sees no facts. Engagement: a human without a session "
                "gets no explanation of the feature. "
                "Single finding covers CRA-05 + ENG-03 to avoid double-counting.",
                "Render public OG/description and short copy of what the route does when unauthenticated.",
                category="discoverability",
                failure_mode="index.state_gated_no_fallback",
                how="Add a meta description and short public explanation of what the page does for signed-out visitors.",
                urls=[p.get("url") for p in thin_gated[:4]],
                confidence=0.7,
            )
        )
    for pair in snap.get("facet_pairs") or []:
        if pair.get("identical_raw"):
            out.append(
                finding(
                    "CRA-06",
                    "Faceted/query-parameter content invisible to server fetch",
                    "high",
                    f"Base {pair.get('base')} words={pair.get('base_words')} vs filtered "
                    f"{pair.get('filtered')} words={pair.get('filtered_words')} — raw HTML is "
                    "near-identical, so the filter state is client-side only.",
                    "Render filter/collection variants as crawlable URLs (or sitemap those states) with distinct HTML.",
                    category="discoverability",
                    failure_mode="index.csr_only_facets",
                    how="Each facet URL must change the server HTML, not only a JS state.",
                    urls=[pair.get("base"), pair.get("filtered")],
                )
            )
    for p in pages:
        sig = p.get("signals") or {}
        if p.get("role") not in {"collection", "product"} and not sig.get("load_more_js"):
            continue
        if sig.get("load_more_js") and not (sig.get("rel_next") or sig.get("page_links")):
            out.append(
                finding(
                    "CRA-07",
                    "Pagination / infinite-scroll truncation trap",
                    "medium",
                    f"{p.get('url')} has JS Load More / infinite scroll and no crawlable "
                    "<a rel=next> or page= links. Crawlers only see the first slice of items.",
                    "Add rel=next (or sitemap) for page 2+ of collections.",
                    category="discoverability",
                    failure_mode="index.infinite_scroll_trap",
                    how="Real href pagination, not a button with no URL.",
                    urls=[p.get("url")],
                )
            )
            break
    return out


def detect_freshness(snap: dict[str, Any]) -> list[dict[str, Any]]:
    """Tier 0 identity (any size) vs Tier 1 reach (only if the site claims scale)."""
    out: list[dict[str, Any]] = []
    h = home(snap)
    sig = h.get("signals") or {}
    org = sig.get("org") or {}
    types = set(sig.get("schema_types") or [])
    site_type = snap.get("site_type") or "marketing"
    pages = snap.get("pages") or []
    scale = infer_site_scale(pages, consensus=snap.get("digital_consensus"))
    snap["site_scale"] = scale
    profiles = collect_profile_urls(pages)
    onpage_t0 = list(profiles.get("tier0") or [])
    ambiguous = brand_token_ambiguous(sig.get("title") or "", sig.get("h1") or "", sig.get("og_site_name"))
    cons = snap.get("digital_consensus") or {}
    cq = cons.get("crawl_quality") or {}
    has_org = bool(
        types
        & {
            "Organization",
            "Corporation",
            "LocalBusiness",
            "Restaurant",
            "Dentist",
            "Hotel",
            "Brand",
            "Person",
        }
    )
    if not has_org and org.get("count", 0) == 0:
        want = _identity_schema_want(site_type, sig)
        verified = _verified_sameas_urls(cons)
        # Thin JS shell + strong off-site identity: do NOT high-severity "missing org" as if the brand is unknown.
        if cq.get("crawl_incomplete") and cons.get("offsite_identity_strong") and verified:
            same_bit = f"sameAs links ({', '.join(verified[:2])})"
            out.append(
                finding(
                    "FC-ENT-01",
                    "Organization JSON-LD not visible in the raw HTML this crawler received",
                    "medium",
                    f"Raw homepage fetch word_count={sig.get('word_count')} with 0 JSON-LD Organization nodes, "
                    f"but digital consensus echoes brand on {cons.get('platforms_with_echo')}. "
                    "Off-site identity is strong; the defect is on-site schema not present in the first HTML response "
                    "(or bot-minimized HTML), not that the brand is unknown.",
                    f"Embed schema.org {want} JSON-LD in the first HTML response (SSR), including {same_bit} "
                    "— do not rely on client-only injection.",
                    category="discoverability",
                    failure_mode="cite.schema_invisible_in_raw_html",
                    how="Assistants that curl HTML never see JS-injected JSON-LD. SSR the identity graph.",
                    urls=[h.get("url") or snap.get("origin") or ""],
                    confidence=0.55,
                    confidence_note=cq.get("note"),
                )
            )
        elif cq.get("crawl_incomplete"):
            out.append(
                finding(
                    "FC-ENT-01",
                    "Homepage identity schema missing from a thin/incomplete HTML fetch",
                    "medium",
                    f"Crawled homepage {h.get('url')}; word_count={sig.get('word_count')}; 0 Organization/LocalBusiness JSON-LD. "
                    f"Crawl marked incomplete (rich meta or scripts with thin body). Treat as low-confidence until SSR HTML is verified.",
                    f"Add schema.org {want} in the first HTML response; re-check with curl after deploy.",
                    category="discoverability",
                    failure_mode="cite.missing_org_schema_incomplete_crawl",
                    how="SSR identity markup into the first HTML response and re-check with curl.",
                    urls=[h.get("url") or snap.get("origin") or ""],
                    confidence=0.45,
                    confidence_note=cq.get("note"),
                )
            )
        else:
            if verified:
                same_bit = f"sameAs links ({', '.join(verified[:2])})"
                how = "Mirror verified public identity URLs into the first HTML response."
            elif onpage_t0:
                same_bit = f"sameAs links ({', '.join(onpage_t0[:4])})"
                how = "Those profile URLs are already linked on-origin; copy them into Organization.sameAs."
            elif site_type == "local" or org.get("is_local_entity"):
                same_bit = "sameAs to your Google Business / Maps / Justdial listing"
                how = "Local businesses disambiguate via Google Business or Maps listings plus NAP."
            else:
                same_bit = "sameAs to a LinkedIn company page or official social you already control"
                how = "Put Organization JSON-LD in the first HTML response with name, url, and sameAs you control."
            echo = cons.get("platforms_with_echo") or []
            onpage_note = (
                f"On-origin profile hrefs already present: {onpage_t0[:4]}. "
                if onpage_t0
                else ""
            )
            out.append(
                finding(
                    "FC-ENT-01",
                    "Missing Organization JSON-LD on the homepage",
                    "high",
                    f"Crawled homepage {h.get('url')}; 0 JSON-LD nodes with @type Organization/LocalBusiness/Person. "
                    f"{onpage_note}"
                    f"External consensus platforms_with_echo={echo}.",
                    f"Add schema.org {want} JSON-LD in the first HTML response with name, url, and {same_bit}.",
                    category="discoverability",
                    failure_mode="cite.missing_org_schema",
                    how=how,
                    urls=[h.get("url") or snap.get("origin") or ""],
                )
            )

    same = org.get("sameAs") or []
    profiles = merge_consensus_profiles(profiles, cons)
    t0 = profiles.get("tier0") or []
    t1 = profiles.get("tier1") or []
    claims = scale.get("scale_claims") or []
    auth_n = len(org.get("authority_sameAs") or [])
    # Persist merged profiles for signal synthesis / agent.
    snap["_merged_profiles"] = profiles

    if claims and not t1 and not cons.get("offsite_identity_strong"):
        out.append(
            finding(
                "FC-FRESH-04",
                "Claimed reach is not independently corroborated",
                "high",
                f"Homepage/about copy includes scale claims {claims}. "
                f"0 Wikidata/Wikipedia/press hosts in sameAs, outbound links, or consensus probes. "
                "Unverifiable boasts risk being ignored when an assistant fact-checks before citing.",
                "Substantiate those specific claims with independent coverage in sameAs, or moderate the wording.",
                category="discoverability",
                failure_mode="cite.uncorroborated_scale_claim",
                how="Tier 1 only because the site claimed scale — not because Wikipedia is universally required.",
                urls=[h.get("url") or snap.get("origin") or ""],
                confidence=0.72,
            )
        )
    elif (
        not t0
        and not t1
        and not scale.get("looks_placeholder")
        and not cons.get("offsite_identity_strong")
        and not scale.get("looks_scaled")
        and not scale.get("crawl_incomplete")
    ):
        # True SMB gap only — never fire this on brands consensus already found on Wikipedia/Wikidata.
        if site_type == "local" or org.get("is_local_entity"):
            action = (
                "Add a Google Business Profile, Justdial, or Yelp URL to LocalBusiness.sameAs "
                "(and keep NAP consistent)."
            )
            how = "Local businesses disambiguate via listings + address, not Wikidata."
        else:
            action = (
                "Add at least one controlled profile you already own (LinkedIn company page or official social) "
                "to Organization.sameAs."
            )
            how = "Tier 0 listing only — no scale claims were found, so do not require press/Wikipedia."
        out.append(
            finding(
                "FC-FRESH-04",
                "No independently-controlled profile echoing business identity",
                "medium",
                f"No Tier-0/Tier-1 profile URLs in sameAs or crawlable links; "
                f"consensus platforms_with_echo={cons.get('platforms_with_echo') or []}; "
                f"scale_claim_phrases_found={claims or []}.",
                action,
                category="discoverability",
                failure_mode="cite.tier0_no_profile",
                how=how,
                urls=[h.get("url") or ""],
                confidence=0.55 if scale.get("looks_small") else 0.7,
                confidence_note=(
                    "Limited independent web footprint; may reflect actual scale rather than a defect."
                    if scale.get("looks_small")
                    else None
                ),
            )
        )
    elif (has_org or org.get("count")) and not same and (t1 or cons.get("offsite_identity_strong")):
        # On-site schema exists (or will) but sameAs empty while off-site anchors are known.
        wd = (cons.get("wikidata") or {}).get("top_id")
        wiki = (cons.get("wikipedia") or {}).get("page_url")
        targets = _verified_sameas_urls(cons) or [
            u for u in (wiki, f"https://www.wikidata.org/wiki/{wd}" if wd else None) if u
        ]
        if not cons.get("identity_verified"):
            targets = []
        if targets:
            out.append(
                finding(
                    "FC-ENT-02",
                    "Off-site identity exists but Organization.sameAs is empty on-origin",
                    "medium",
                    f"Consensus found {cons.get('platforms_with_echo')}; "
                    f"suggested sameAs anchors={targets[:3]}. On-page sameAs count=0.",
                    f"Add Organization.sameAs listing {', '.join(targets[:2]) or 'your Wikipedia/Wikidata URLs'}.",
                    category="discoverability",
                    failure_mode="cite.sameAs_omits_known_offsite",
                    how="Mirror known public identity into the HTML JSON-LD graph.",
                    urls=[h.get("url") or ""],
                    confidence=0.65,
                )
            )

    # FC-ENT-02: global sameAs triangulation — skip when local geo already disambiguates
    # (Krishna Dental: street + phone beats Wikidata for a single-location clinic).
    geo_ok = local_geo_disambiguated(org, profiles, scale.get("phones") or sig.get("phones") or [])
    if has_org or org.get("count"):
        if geo_ok:
            if t0 and not same and not org.get("has_maps_sameAs"):
                out.append(
                    finding(
                        "FC-ENT-02",
                        "Local profiles exist in HTML but are missing from sameAs",
                        "low",
                        f"Local NAP/geo already disambiguates; Tier-0 URLs in DOM ({t0[:3]}) "
                        "are still worth listing in LocalBusiness.sameAs for crawlers.",
                        "Copy Google Business / Maps / Justdial URLs into sameAs.",
                        category="discoverability",
                        failure_mode="cite.sameAs_omits_existing_profiles",
                        how="Geography satisfied FC-ENT-02's global bar; this is hygiene, not a Novatech-class miss.",
                        urls=[h.get("url") or ""],
                        confidence=0.55,
                    )
                )
        elif auth_n >= 2:
            pass
        elif auth_n == 1:
            out.append(
                finding(
                    "FC-ENT-02",
                    "Weak sameAs triangulation",
                    "medium",
                    f"Organization.sameAs has {len(same)} URL(s), {auth_n} authority host(s) "
                    f"{(org.get('authority_sameAs') or [])[:3]}. Need ≥2 (Wikidata/Wikipedia/Crunchbase/LinkedIn + social) "
                    "because this entity has no complete local PostalAddress+phone disambiguator.",
                    "Add a second authority sameAs (Wikidata preferred, else LinkedIn + official social).",
                    category="discoverability",
                    failure_mode="cite.weak_sameAs",
                    how="Clean bar is ≥2 curated hosts for address-less / multi-location brands. "
                    "Single-location LocalBusiness with street NAP uses FC-ENT-04 instead.",
                    urls=[h.get("url") or ""],
                )
            )
        elif not scale.get("looks_small") and (t0 or same):
            out.append(
                finding(
                    "FC-ENT-02",
                    "sameAs identity graph missing on a scaled site",
                    "high",
                    f"Site does not look small (scale_claims={claims}, careers/press signals) but "
                    f"authority sameAs count is 0 and local geo disambiguation is incomplete.",
                    "Publish Organization.sameAs with ≥2 authority profiles.",
                    category="discoverability",
                    failure_mode="cite.missing_sameAs_scaled",
                    how="Do not apply this high tier to a handloom shop with no scale claims.",
                    urls=[h.get("url") or ""],
                )
            )
        elif t0 and not same:
            out.append(
                finding(
                    "FC-ENT-02",
                    "Profiles exist in HTML but are missing from sameAs",
                    "medium",
                    f"Found Tier-0 profile URLs in the DOM ({t0[:3]}) but Organization.sameAs does not list them.",
                    "Copy those profile URLs into Organization.sameAs.",
                    category="discoverability",
                    failure_mode="cite.sameAs_omits_existing_profiles",
                    how="Icon hrefs are not a substitute for JSON-LD sameAs.",
                    urls=[h.get("url") or ""],
                )
            )

    # FC-ENT-04 is the primary disambiguation path for LocalBusiness (not a sameAs add-on).
    if (site_type == "local" or org.get("is_local_entity")) and (has_org or org.get("count")):
        if not org.get("has_address"):
            out.append(
                finding(
                    "FC-ENT-04",
                    "Local entity missing PostalAddress in JSON-LD",
                    "high",
                    "LocalBusiness-class site has no street/locality address in schema. "
                    "Common personal+category names (e.g. Krishna Dental) collide city-to-city; "
                    "geography is the disambiguator, not Wikidata.",
                    "Add PostalAddress (streetAddress, addressLocality, addressRegion, addressCountry) "
                    "and telephone so geo queries bind to this clinic, not a name twin.",
                    category="discoverability",
                    failure_mode="cite.missing_geo",
                    how="Nested address on LocalBusiness; keep it consistent with title/NAP text.",
                    urls=[h.get("url") or ""],
                )
            )
        elif not org.get("has_complete_postal_address"):
            out.append(
                finding(
                    "FC-ENT-04",
                    "Local PostalAddress is incomplete for disambiguation",
                    "medium",
                    "Schema has a partial address but not streetAddress + locality/region together.",
                    "Complete PostalAddress with street and city so assistants can separate name twins.",
                    category="discoverability",
                    failure_mode="cite.incomplete_geo",
                    how="Partial country-only addresses do not disambiguate 'Krishna Dental' across cities.",
                    urls=[h.get("url") or ""],
                )
            )
        elif not (org.get("has_telephone") or (scale.get("phones") or sig.get("phones"))):
            out.append(
                finding(
                    "FC-ENT-04",
                    "Local entity has address but no telephone in schema or crawl",
                    "medium",
                    "Complete PostalAddress found, but no telephone on LocalBusiness or visible NAP.",
                    "Add LocalBusiness.telephone matching the number in the footer/title.",
                    category="discoverability",
                    failure_mode="cite.missing_phone",
                    how="Phone + street is the Tier-0 local identity pair.",
                    urls=[h.get("url") or ""],
                )
            )

    phones = scale.get("phones") or []
    if scale.get("looks_small") and len(phones) >= 2:
        out.append(
            finding(
                "F-ENT-NAP",
                "Inconsistent phone numbers across crawled pages",
                "medium",
                f"Distinct phone digit-strings on a small crawl: {phones[:4]}. Assistants may merge the wrong NAP.",
                "Pick one canonical phone and repeat it in LocalBusiness.telephone and footer text.",
                category="discoverability",
                failure_mode="cite.nap_inconsistent",
                how="Use one primary phone number consistently in schema and on-page contact blocks.",
                urls=[h.get("url") or ""],
                confidence=0.6,
                confidence_note="Country-code formatting can make one phone look like two distinct numbers.",
            )
        )

    unlabeled = 0
    for p in pages:
        unlabeled += int((p.get("signals") or {}).get("unlabeled_social_count") or 0)
    if unlabeled >= 2 and not same:
        out.append(
            finding(
                "FC-ENT-05",
                "Social profiles are icon-only (empty link text)",
                "medium",
                f"Found {unlabeled} social <a> tags without visible text or aria-label. Parsers extract href but cannot type the channel.",
                "Add aria-label on icon links and repeat those URLs in Organization.sameAs.",
                category="discoverability",
                failure_mode="cite.unlabeled_social",
                how="<a href='https://instagram.com/…' aria-label='Instagram'> plus JSON-LD sameAs.",
            )
        )

    hours = []
    for p in pages:
        ih = (p.get("signals") or {}).get("identical_hours")
        if ih:
            hours.append((p.get("url"), ih))
    if hours:
        out.append(
            finding(
                "FC-FRESH-03",
                "Opening hours text is syntactically ambiguous",
                "medium",
                f"Identical start/end clock on {hours[0][0]}: '{hours[0][1]}' (e.g. 11pm–11pm). Assistants guess AM/PM.",
                "Publish openingHoursSpecification in JSON-LD with explicit opens/closes, and fix visible copy.",
                category="discoverability",
                failure_mode="cite.ambiguous_hours",
                how="Use schema.org OpeningHoursSpecification; never '11pm – 11:00pm' as the only representation.",
                urls=[hours[0][0]],
            )
        )

    if (
        has_org
        and not org.get("has_legal_id")
        and ambiguous
        and not scale.get("looks_small")
        and auth_n < 2
        and not geo_ok
    ):
        out.append(
            finding(
                "FC-ENT-03",
                "Proactive: hard legal identifiers absent on an ambiguous scaled name",
                "low",
                "No taxID/duns/leiCode. Apple-class sites often omit these; only suggested because the name is collision-class AND sameAs triangulation is already weak (FC-ENT-02).",
                "If the colloquial name collides globally, consider leiCode/taxID — never a blanket high.",
                category="discoverability",
                failure_mode="cite.optional_legal_id",
                how="Would fail the Apple baseline if this were high. Conditional proactive only.",
                urls=[h.get("url") or ""],
                confidence=0.45,
            )
        )

    load_bearing = [
        p
        for p in pages
        if p.get("role") in {"product", "pricing", "blog", "faq", "collection", "article"}
        or (p.get("page_class") or "") in {"article", "product", "product_catalog", "faq"}
        or (p.get("signals") or {}).get("productish_text")
    ]
    undated = [
        p
        for p in load_bearing
        if not ((p.get("signals") or {}).get("schema_caps") or {}).get("has_date_modified")
        and not (p.get("signals") or {}).get("visible_updated")
    ]
    if undated and len(undated) >= max(1, len(load_bearing) // 2):
        site_type = snap.get("site_type") or ""
        if site_type in {"media", "publisher", "news"} or any(
            (p.get("page_class") or "") == "article" for p in undated
        ):
            evidence = (
                f"{len(undated)}/{len(load_bearing)} article/section pages have neither "
                "dateModified/datePublished nor a visible publish or last-updated timestamp."
            )
            action = (
                "Add datePublished/dateModified (or a visible Published/Updated line) on articles "
                "and section pages so assistants can judge whether a story is current."
            )
            how = (
                "Put publish and last-updated timestamps in the first HTML response next to the "
                "headline — news freshness is judged by dates, not product prices or specs."
            )
        else:
            evidence = (
                f"{len(undated)}/{len(load_bearing)} product/policy/article-like pages have neither "
                "dateModified nor visible last-updated text near prices, hours, or policies."
            )
            action = "Add dateModified (or visible Updated on) next to prices, hours, and policies."
            how = "Put dateModified or a visible last-updated line next to prices, hours, and policies."
        out.append(
            finding(
                "FC-FRESH-01",
                "No freshness signal on load-bearing facts",
                "medium",
                evidence,
                action,
                category="discoverability",
                failure_mode="cite.no_freshness_signal",
                how=how,
                urls=[p.get("url") for p in undated[:5]],
            )
        )

    site_prices = []
    for p in pages:
        site_prices.extend((p.get("signals") or {}).get("prices") or [])
    tp = []
    for row in snap.get("third_party_prices") or []:
        tp.extend(row.get("prices") or [])
    if site_prices and tp:
        a, b = set(site_prices[:12]), set(tp[:12])
        if a and b and a.isdisjoint(b):
            out.append(
                finding(
                    "FC-FRESH-02",
                    "Cross-platform price/fact inconsistency",
                    "high",
                    f"On-site prices {sorted(a)[:6]} vs third-party menu {sorted(b)[:6]} (e.g. Pine Villa ₹260 vs ₹393). Assistants guess.",
                    "Align prices/hours across the brand origin and ordering platforms, or mark which source is canonical in schema.",
                    category="discoverability",
                    failure_mode="cite.cross_surface_mismatch",
                    how="Same fact, two surfaces, two values — citation-level trust failure.",
                    urls=[(snap.get("third_party_prices") or [{}])[0].get("url")],
                )
            )

    meta_hits: list[tuple[str, str, str]] = []  # url, severity, evidence
    key_roles = {"home", "product", "collection", "faq", "blog"}
    for p in pages:
        if (p.get("role") or "home") not in key_roles:
            continue
        scored = _blank_meta_score(p.get("signals") or {})
        if scored:
            meta_hits.append((p.get("url") or "", scored[0], scored[1]))
    if meta_hits:
        rank = {"low": 0, "medium": 1, "high": 2}
        meta_hits.sort(key=lambda row: rank.get(row[1], 0), reverse=True)
        sev = meta_hits[0][1]
        bits = "; ".join(f"{u}: {ev}" for u, _, ev in meta_hits[:3])
        out.append(
            finding(
                "FC-FRESH-06",
                "Empty/blank meta description tags",
                sev,
                bits + ". Owned here only (not an engagement check). "
                "Standard meta description is what most AI crawlers read first; "
                "twitter:description-only blanks are low.",
                "Fill name=description first; then og:description. Empty content=\"\" is worse than an absent Twitter card.",
                category="discoverability",
                failure_mode="cite.blank_meta",
                how="Ensure a standard <meta name='description'> tag is populated in the initial HTML response. "
                "Fallback OpenGraph or Twitter descriptions are not sufficient for primary AI crawlers.",
                urls=[u for u, _, _ in meta_hits[:4]],
            )
        )
    return out


def _blank_meta_score(sig: dict[str, Any]) -> tuple[str, str] | None:
    """Scale by which tag is blank. Twitter-only empty is not a medium finding."""
    blank = set(sig.get("blank_meta") or [])
    desc = (sig.get("meta_description") or "").strip()
    desc_missing = bool(sig.get("meta_description_missing"))
    desc_blank = "description" in blank
    og_blank = "og:description" in blank
    tw_blank = "twitter:description" in blank
    if desc_blank and og_blank and tw_blank:
        return (
            "high",
            'description, og:description, and twitter:description are all content=""',
        )
    if desc_blank:
        extras = [t for t in ("og:description", "twitter:description") if t in blank]
        extra = f" (also empty: {extras})" if extras else ""
        return "medium", f'name=description is content=""{extra}'
    if desc_missing and not desc:
        return "medium", "no name=description tag on a key template"
    if desc and (og_blank or tw_blank):
        empty = [t for t in ("og:description", "twitter:description") if t in blank]
        return "low", f"name=description is populated; empty {empty}"
    if og_blank or tw_blank:
        empty = [t for t in ("og:description", "twitter:description") if t in blank]
        return "low", f"empty {empty} (no populated description to fall back to)"
    return None


def detect_schema_vertical(snap: dict[str, Any]) -> list[dict[str, Any]]:
    """Require the schema type that matches the page class — never invent a vertical.

    Every specialist asks classify_page first (via pages_of_class). If the page is
    \"general\", the specialist does not run at all.
    """
    out: list[dict[str, Any]] = []
    annotate_page_classes(snap)
    pages = snap.get("pages") or []
    site_type = snap.get("site_type") or ""

    def caps(p: dict[str, Any]) -> dict[str, Any]:
        return (p.get("signals") or {}).get("schema_caps") or {}

    def miss(eligible: list, ok, title, fid, mode, action, how, severity="high", allow_single_high=False):
        bad = [p for p in eligible if not ok(p)]
        if not eligible or not bad:
            return
        sev = severity
        if len(eligible) < 2 and severity == "high" and not allow_single_high:
            sev = "medium"
        types_seen = []
        for p in bad[:4]:
            types_seen.extend((caps(p).get("types") or [])[:6])
        boiler = " boilerplate-only JSON-LD" if any(caps(p).get("boilerplate_only") for p in bad) else ""
        out.append(
            finding(
                fid,
                title,
                sev,
                f"{len(bad)}/{len(eligible)} {mode.split('.')[-1]} pages lack the fitting type{boiler}. "
                f"Types seen: {sorted(set(types_seen))[:8] or ['(none)']}. "
                f"URLs: {', '.join(p.get('url') or '' for p in bad[:4])}.",
                action,
                category="discoverability",
                failure_mode=mode,
                how=how,
                urls=[p.get("url") for p in bad[:6]],
            )
        )

    # Gate: only pages classify_page marked as this vertical.
    products = pages_of_class(snap, "product")
    miss(
        products,
        lambda p: caps(p).get("has_product_offer"),
        "Product pages lack Product/Offer JSON-LD",
        "FC-ENT-01-PRODUCT",
        "cite.schema_mismatch_product",
        "Add Product + Offer (price, priceCurrency, availability) on every product template — not only sitewide Organization/WebPage.",
        "A generic WebPage/Organization block does not let a crawler bind SKU, price, or stock. Nest Brand and Offer on the product URL.",
    )

    collections = pages_of_class(snap, "product_catalog")
    # Tiny 2–3 card category pages stay medium; 4+ grids (incl. homepage merch) stay high.
    tiny = all(
        int((p.get("signals") or {}).get("priced_card_count") or 0) < 4
        for p in collections
    ) if collections else False
    miss(
        collections,
        lambda p: caps(p).get("has_itemlist") and caps(p).get("has_itemlist_elements"),
        "Collection pages lack ItemList listing schema",
        "FC-FRESH-05",
        "cite.missing_itemlist",
        "Add ItemList with itemListElement[].item.offers.price on the listing URL. "
        "Product JSON-LD on individual PDPs does not substitute — assistants still cannot "
        "compare items on the collection page.",
        "Each visible card on a listing URL needs its own price in ItemList. "
        "Unpriced nav lists and a stray currency mention on a legal page are not a catalog.",
        severity="medium" if tiny else "high",
        allow_single_high=not tiny,
    )

    # Niche verticals disabled: FLIGHT / VEHICLE classifiers are too loose on news and
    # marketing pages (BBC Business → flights, BBC Technology → cars). Keep universal
    # schemas only: Organization, Article, FAQPage, Product (+ ItemList collections).
    # flights = pages_of_class(snap, "flight")
    # miss(... FC-ENT-01-FLIGHT / cite.schema_mismatch_flight ...)
    # vehicles = pages_of_class(snap, "vehicle")
    # miss(... FC-ENT-01-VEHICLE / cite.schema_mismatch_vehicle ...)

    if site_type == "local":
        h = home(snap)
        home_types = set((h.get("signals") or {}).get("schema_types") or [])
        has_identity = bool(
            home_types
            & {
                "Organization",
                "Corporation",
                "LocalBusiness",
                "Restaurant",
                "Dentist",
                "Hotel",
                "Brand",
                "Person",
            }
        )
        # Missing identity entirely is FC-ENT-01 — do not double-count as LOCAL.
        if has_identity:
            locals_p = pages_of_class(snap, "local_business")
            if locals_p:
                want_local = _identity_schema_want("local", h.get("signals") or {})
                miss(
                    [p for p in locals_p if p],
                    lambda p: caps(p).get("has_local")
                    and (caps(p).get("has_postal_address") or caps(p).get("has_opening_hours_spec")),
                    "Local pages lack LocalBusiness + address/hours specification",
                    "FC-ENT-01-LOCAL",
                    "cite.schema_mismatch_local",
                    f"Use {want_local} with PostalAddress and OpeningHoursSpecification — not free-text hours only.",
                    "Assistants quote structured opens/closes and locality; '11pm–11pm' in a paragraph is not a substitute.",
                    severity="high",
                )

    articles = pages_of_class(snap, "article")
    miss(
        articles,
        lambda p: caps(p).get("has_article"),
        "Editorial URLs lack Article/NewsArticle JSON-LD",
        "FC-ENT-01-ARTICLE",
        "cite.schema_mismatch_article",
        "Add Article (or NewsArticle/BlogPosting) with headline, author, datePublished, and dateModified.",
        "Organization-only JSON-LD on a blog post does not date or attribute the claim.",
        severity="medium",
    )
    faqs = pages_of_class(snap, "faq")
    miss(
        faqs,
        lambda p: caps(p).get("has_faq"),
        "Help/FAQ content is prose-only (no FAQPage)",
        "FC-ENT-01-FAQ",
        "cite.schema_mismatch_faq",
        "Wrap each visible question and answer in FAQPage schema so assistants can quote exact pairs.",
        "FAQPage is high-yield for citation: the Q/A shape matches how models quote.",
        severity="medium",
    )
    return out


def detect_engagement(snap: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    # 403 on account/order/cart is usually an auth wall, not a dead public CTA.
    AUTH_WALL_HINTS = ("/order", "/account", "/sign-in", "/signin", "/login", "/cart", "/checkout", "/bag")
    dead = []
    for a in snap.get("action_status") or []:
        st = a.get("status")
        u = (a.get("url") or "").lower()
        if st in {404, 410, 0}:
            dead.append(a)
        elif st == 403 and not any(h in u for h in AUTH_WALL_HINTS):
            dead.append(a)
    if dead:
        sev = "critical" if any("book" in (d.get("url") or "").lower() or "reserv" in (d.get("url") or "").lower() for d in dead) else "high"
        out.append(
            finding(
                "ENG-01",
                "Action/booking URL is not fetchable",
                sev,
                f"{len(dead)} CTA probes failed, e.g. {dead[0].get('url')} → HTTP {dead[0].get('status')}.",
                "Fix the broken link, or point visitors to a working booking page or phone number.",
                category="engagement",
                failure_mode="land.dead_cta",
                how="Repair reservation and order links so they resolve for visitors. Auth-walled account pages are excluded.",
                urls=[d.get("url") for d in dead[:5]],
            )
        )
    pages = snap.get("pages") or []
    html_pages = [
        p
        for p in pages
        if is_html_content_type(
            p.get("content_type") or (p.get("signals") or {}).get("content_type"),
            p.get("url") or "",
            (p.get("signals") or {}).get("text") or "",
        )
        and not (p.get("signals") or {}).get("non_html")
    ]
    deep = [p for p in html_pages if p.get("role") not in {"home", "legal", "non_html", "agent_resource"}]
    no_h1 = [p for p in deep if not (p.get("signals") or {}).get("h1")]
    no_crumb = [
        p
        for p in deep
        if p.get("role") in {"product", "docs", "blog", "collection"}
        and not (p.get("signals") or {}).get("has_breadcrumb")
    ]
    no_home = [p for p in deep if not (p.get("signals") or {}).get("has_home_href")]
    if len(no_h1) >= 2 or len(no_crumb) >= 2:
        out.append(
            finding(
                "ENG-02",
                "Deep-link landing context missing",
                "medium",
                f"Non-home HTML pages: {len(no_h1)}/{len(deep)} lack H1; {len(no_crumb)} lack breadcrumbs; "
                f"{len(no_home)} lack a home link. A cited visitor is not oriented.",
                "One H1 stating page purpose, breadcrumbs, and a crawlable link to / on inner templates.",
                category="engagement",
                failure_mode="land.weak_orientation",
                how="Inner templates need an H1, breadcrumbs, and a crawlable home link so a cited visitor can orient.",
                urls=[p.get("url") for p in (no_h1 or no_crumb)[:5]],
            )
        )
    h = home(snap)
    if is_html_content_type(
        h.get("content_type") or (h.get("signals") or {}).get("content_type"),
        h.get("url") or "",
        (h.get("signals") or {}).get("text") or "",
    ) and not (h.get("signals") or {}).get("non_html"):
        sig = h.get("signals") or {}
        if not sig.get("has_nav") and (sig.get("word_count") or 0) > 40:
            if out and out[-1].get("id") == "ENG-02":
                out[-1]["evidence"] += f" Homepage also lacks <nav>/<header> ({h.get('url')})."
            else:
                out.append(
                    finding(
                        "ENG-02",
                        "Deep-link landing context missing",
                        "medium",
                        f"{h.get('url')} has no <nav>/<header> landmark in the HTML parse.",
                        "Expose crawlable primary navigation in the initial HTML.",
                        category="engagement",
                        failure_mode="land.no_nav",
                        how="Real <nav> links, not only JS-injected menus.",
                        urls=[h.get("url") or ""],
                    )
                )

    # ENG-04: empty FAQ accordion answers — only when real FAQ/accordion chrome was detected.
    # Question-mark news headlines (BBC, Yahoo Finance explainers) are not FAQ candidates.
    empty_faq_pages: list[tuple[str, list[str]]] = []
    for p in pages:
        s = p.get("signals") or {}
        if not (
            s.get("has_faq_ui")
            or s.get("has_faq_section")
            or (p.get("page_class") or "") == "faq"
            or (p.get("role") or "") == "faq"
        ):
            continue
        pairs = s.get("faq_pairs") or []
        schema_ans = s.get("faq_schema_answers") or []
        empties = []
        for pair in pairs:
            if not pair.get("empty"):
                continue
            q = pair.get("question") or ""
            if schema_covers_question(q, schema_ans):
                continue
            empties.append(q)
        if len(empties) >= 2:
            empty_faq_pages.append((p.get("url") or "", empties))
    if empty_faq_pages:
        url0, qs = empty_faq_pages[0]
        n_empty = sum(len(q) for _, q in empty_faq_pages)
        out.append(
            finding(
                "ENG-04",
                "FAQ headings promise answers that static HTML does not deliver",
                "high",
                f"{len(empty_faq_pages)} page(s) have {n_empty} question heading(s) with empty "
                f"answers in the initial HTML (e.g. {url0}: {qs[:3]}). Click-to-expand "
                "accordion content that never appears in the first HTML response is "
                "invisible to AI fetchers.",
                "Render answer text in the first HTML response, or add FAQPage schema "
                "covering each visible question.",
                category="engagement",
                failure_mode="land.empty_faq_answers",
                how="Ensure all FAQ headings have their answers visible in the initial HTML load, "
                "or implement FAQPage schema so AI agents can extract the answers without clicking.",
                urls=[u for u, _ in empty_faq_pages[:4]],
                confidence=0.85,
            )
        )
    return out


def detect_nontext(snap: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    pages = snap.get("pages") or []
    pdf_only = []
    img_bad = []
    canvas = []
    for p in pages:
        sig = p.get("signals") or {}
        if (sig.get("pdf_links") or []) and (sig.get("word_count") or 0) < 80:
            pdf_only.append(p)
        if (sig.get("img_no_alt_large") or 0) >= 1:
            img_bad.append(p)
        if (sig.get("canvas") or 0) and (sig.get("word_count") or 0) < 100:
            canvas.append(p)
    if img_bad:
        # Dedupe by URL so evidence page-count matches affected_urls after _uniq_urls.
        by_url: dict[str, dict[str, Any]] = {}
        img_counts: dict[str, int] = {}
        for p in img_bad:
            u = p.get("url") or ""
            key = u.rstrip("/") or u
            n_img = int((p.get("signals") or {}).get("img_no_alt_large") or 0)
            img_counts[key] = max(img_counts.get(key, 0), n_img)
            by_url[key] = p
        uniq_pages = list(by_url.values())
        n = sum(img_counts.values())
        out.append(
            finding(
                "CRA-04",
                "Images missing descriptive alt text",
                "medium",
                f"{n} images or UI elements without alt text across {len(uniq_pages)} pages. Facts in photos are invisible to text fetchers.",
                "Add descriptive alt (and, for menus, also put items in HTML/JSON-LD).",
                category="discoverability",
                failure_mode="cite.facts_in_images",
                how="Ensure all informational images use descriptive alt text to allow AI agents to extract visual facts.",
                urls=[p.get("url") for p in uniq_pages[:5]],
            )
        )
    if pdf_only:
        out.append(
            finding(
                "CRA-04-PDF",
                "Thin HTML with PDF as the fact carrier",
                "high",
                f"{len(pdf_only)} pages have PDF links and little HTML text.",
                "Summarize the PDF facts as HTML (and Article/Dataset schema) on the same URL.",
                category="discoverability",
                failure_mode="cite.pdf_only",
                how="Do not rely on PDF extraction for core NAP, pricing, or leadership facts.",
                urls=[p.get("url") for p in pdf_only[:4]],
            )
        )
    if canvas:
        out.append(
            finding(
                "CRA-04-CANVAS",
                "Primary content may be canvas-only",
                "medium",
                f"{len(canvas)} pages include <canvas> with low text word counts.",
                "Provide a text equivalent for canvas-rendered facts so AI agents can read them.",
                category="discoverability",
                failure_mode="cite.canvas",
                how="Duplicate titles/values in DOM text nodes.",
                urls=[p.get("url") for p in canvas[:4]],
                confidence=0.6,
            )
        )
    return out


def proactive(snap: dict[str, Any]) -> list[dict[str, Any]]:
    recs = []
    st = (snap.get("llms_txt") or {}).get("status")
    site_type = snap.get("site_type")
    if st not in (200,):
        sev = "low"
        recs.append(
            finding(
                "FC-PROACT-01",
                "Proactive: add llms.txt for curated AI ingestion",
                sev,
                f"GET /llms.txt returned HTTP {st}. Not a crawl defect; docs/SaaS sites benefit most.",
                "Publish a short Markdown index of canonical, LLM-readable URLs at /llms.txt.",
                category="discoverability",
                failure_mode="proactive.llms_txt",
                how="Follow llmstxt.org: title, summary, and links to markdown or docs URLs.",
            )
        )
        if site_type not in {"docs", "saas"}:
            recs[-1]["suggested_action"]["summary"] = (
                "Optional: add llms.txt only if you have a documentation or knowledge surface."
            )
    scale = snap.get("site_scale") or infer_site_scale(
        snap.get("pages") or [], consensus=snap.get("digital_consensus")
    )
    profiles = merge_consensus_profiles(
        collect_profile_urls(snap.get("pages") or []), snap.get("digital_consensus")
    )
    claims = scale.get("scale_claims") or []
    if (
        scale.get("looks_small")
        and not scale.get("looks_placeholder")
        and not profiles.get("tier1")
        and not claims
    ):
        recs.append(
            finding(
                "FC-PROACT-02",
                "Proactive: Wikipedia/Wikidata only if you later pursue reach",
                "low",
                "No Wikipedia/Wikidata URL found. Not a defect: the site does not claim national scale.",
                "If you later pursue press coverage or a Wikidata item, add it to sameAs.",
                category="discoverability",
                failure_mode="proactive.tier1_reach",
                how="Optional reach step only — missing Wikipedia is not a discoverability defect for small sites.",
                confidence=0.4,
                confidence_note="Limited independent web footprint found; may reflect brand's actual scale rather than a discoverability defect.",
            )
        )

    # FC-PROACT-03: Voice & Audio Assistant Discoverability (schema.org/speakable)
    # HARD GATE: Trigger ONLY when actual Article / NewsArticle / BlogPosting schema
    # is already present on crawled pages, and none of those articles define speakable.
    article_urls: list[str] = []
    any_speakable = False
    for p in snap.get("pages") or []:
        s = p.get("signals") or p
        stypes = set(s.get("schema_types") or [])
        if stypes & {"Article", "NewsArticle", "BlogPosting", "TechArticle"}:
            u = p.get("url") or ""
            if u:
                article_urls.append(u)
            if s.get("has_speakable") or "SpeakableSpecification" in stypes:
                any_speakable = True
                break

    if article_urls and not any_speakable:
        sample = article_urls[0]
        recs.append(
            finding(
                "FC-PROACT-03",
                "Voice & audio assistant discoverability: Add schema.org speakable specification",
                "low",
                f"{len(article_urls)} page(s) have Article/NewsArticle schema without a SpeakableSpecification (e.g. {sample}). "
                "Voice assistants and audio agents (Google Assistant, Siri, AI news briefers) rely on speakable markup "
                "to identify key audio summaries.",
                "Add a 'speakable' property with SpeakableSpecification (cssSelector or xpath) to Article JSON-LD.",
                category="discoverability",
                failure_mode="cite.voice_speakable_missing",
                how=(
                    "Inside your Article/NewsArticle JSON-LD, add: "
                    "'speakable': {'@type': 'SpeakableSpecification', 'cssSelector': ['h1', '.article-summary', '.lead']} "
                    "identifying the exact text suitable for text-to-speech citation."
                ),
                urls=article_urls[:5],
                confidence=0.85,
            )
        )

    return recs


DOM_DEPENDENT_IDS = frozenset(
    {
        "FC-FRESH-01",
        "FC-FRESH-05",
        "FC-FRESH-06",
        "ENG-02",
        "ENG-04",
    }
)


def _js_empty_shell(snap: dict[str, Any]) -> bool:
    for p in snap.get("pages") or []:
        sig = p.get("signals") or {}
        wc = int(sig.get("word_count") or 0)
        if sig.get("next_data") or sig.get("json_ld") or wc >= 25:
            continue
        if sig.get("spa_shell") or (sig.get("script_count") or 0) >= 3:
            return True
    return False


def ensure_crawl_quality(snap: dict[str, Any]) -> dict[str, Any]:
    """Fill crawl_quality for offline snaps and mark empty JS shells incomplete."""
    cons = snap.setdefault("digital_consensus", {})
    cq = cons.get("crawl_quality")
    if not isinstance(cq, dict) or "crawl_incomplete" not in cq:
        cq = crawl_quality(snap)
        cons["crawl_quality"] = cq
    if cq.get("iana_placeholder"):
        return cq
    if cq.get("crawl_incomplete") or _js_empty_shell(snap):
        note = cq.get("note") or JS_SHELL_NOTE
        cq["crawl_incomplete"] = True
        cq["note"] = note
        snap.setdefault("limitations", {})["crawl_incomplete"] = note
    return cq


def apply_js_shell_caveat(snap: dict[str, Any], findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """When CRA-02 fires, DOM absences are not confirmed — they may be Helmet/CSR injected."""
    has_cra02 = any((f.get("id") or "") == "CRA-02" for f in findings)
    cq = (snap.get("digital_consensus") or {}).get("crawl_quality") or {}
    if not has_cra02 and not cq.get("crawl_incomplete") and not _js_empty_shell(snap):
        return findings
    note = cq.get("note") or JS_SHELL_NOTE
    snap.setdefault("limitations", {})["crawl_incomplete"] = note
    for f in findings:
        fid = f.get("id") or ""
        if fid in {"CRA-02", "CRA-02-MENU", "CRA-01", "CRA-03"} or fid.startswith("NET-"):
            continue
        if not (
            fid.startswith("FC-ENT-01")
            or fid.startswith("CRA-04")
            or fid in DOM_DEPENDENT_IDS
        ):
            continue
        if f.get("severity") in {"high", "critical"}:
            f["severity"] = "medium"
            sa = f.get("suggested_action") or {}
            if sa.get("priority") in {"high", "critical"}:
                sa["priority"] = "medium"
        f["confidence"] = min(float(f.get("confidence") or 0.9), 0.5)
        if not f.get("confidence_note"):
            f["confidence_note"] = note
    return findings


SKILL_MAP = {
    "crawl-access-audit": detect_crawl_access,
    "render-quotability-audit": detect_render,
    "freshness-corroboration-audit": lambda snap: detect_freshness(snap) + detect_schema_vertical(snap),
    "engagement-orientation-audit": detect_engagement,
    "nontext-surface-audit": detect_nontext,
}


def run_skill(snap: dict[str, Any], skill: str) -> list[dict[str, Any]]:
    """Single-skill path with the same NET-01 fail-fast as run_all."""
    net = detect_network_failure(snap)
    if net:
        return net
    ensure_crawl_quality(snap)
    fn = SKILL_MAP.get(skill)
    if not fn:
        return []
    out = fn(snap)
    if skill == "freshness-corroboration-audit":
        out = list(out) + proactive(snap)
    return apply_js_shell_caveat(snap, out)


def run_all(snap: dict[str, Any]) -> list[dict[str, Any]]:
    net = detect_network_failure(snap)
    if net:
        return net
    ensure_crawl_quality(snap)
    found: list[dict[str, Any]] = []
    for fn in (
        detect_crawl_access,
        detect_render,
        detect_freshness,
        detect_schema_vertical,
        detect_engagement,
        detect_nontext,
    ):
        found.extend(fn(snap))
    found.extend(proactive(snap))
    return apply_js_shell_caveat(snap, found)
