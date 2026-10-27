#!/usr/bin/env python3
"""Raw signal extraction + signal-grounded prose + grounding check.

Deterministic layer: facts/counts only from this crawl.
Narrative layer: every concrete fact in evidence must appear in signals.
No external LLM API — the harness agent rewrites prose per SKILL.md.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from htmlutil import (
    AUTHORITY_HOSTS,
    MAPS_HOST_RE,
    collect_profile_urls,
    host_tier,
    infer_site_scale,
    merge_consensus_profiles,
)


def _authority_hosts_in(urls: list[str]) -> list[str]:
    found: list[str] = []
    for u in urls or []:
        low = (u or "").lower()
        for h in AUTHORITY_HOSTS:
            if h in low:
                found.append(h)
    return list(dict.fromkeys(found))


def page_raw_signals(snap: dict[str, Any], page: dict[str, Any] | None = None) -> dict[str, Any]:
    """Per-URL raw signals. Null/error fields when fetch failed — never silent defaults."""
    pages = snap.get("pages") or []
    p = page or (pages[0] if pages else {})
    sig = p.get("signals") or {}
    org = sig.get("org") or {}
    caps = sig.get("schema_caps") or {}
    status = p.get("status")
    fetch_error = None
    if status in (0, None) or (isinstance(status, int) and status >= 400 and not sig):
        errs = (snap.get("limitations") or {}).get("fetch_errors") or []
        for e in errs:
            if (e.get("url") or "") == (p.get("url") or ""):
                fetch_error = e.get("error") or f"HTTP {e.get('status')}"
                break
        if fetch_error is None and status in (0, None):
            fetch_error = "fetch_failed_or_empty"
    same = list(org.get("sameAs") or [])
    profiles = merge_consensus_profiles(collect_profile_urls(pages), snap.get("digital_consensus"))
    text = sig.get("text") or ""
    word_count = sig.get("word_count")
    raw_len = None
    if word_count is not None:
        # Approximate from extracted text length (stdlib parse has no raw bytes here).
        raw_len = len(text) if text else 0
    careers = [u for u in (sig.get("internal_links") or []) if re.search(r"/careers|/jobs|/join-us", u, re.I)]
    press = [u for u in (sig.get("internal_links") or []) if re.search(r"/press|/newsroom|/media", u, re.I)]
    investors = [u for u in (sig.get("internal_links") or []) if re.search(r"/investor", u, re.I)]
    return {
        "url": p.get("url"),
        "http_status": status,
        "fetch_error": fetch_error,
        "role": p.get("role"),
        "raw_html_text_length": raw_len,
        "word_count": word_count,
        "ld_json_blocks_found": len(sig.get("json_ld") or []),
        "ld_json_types_found": list(sig.get("schema_types") or caps.get("types") or []),
        "org_or_localbusiness_present": bool(
            org.get("count")
            or (
                set(sig.get("schema_types") or [])
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
        ),
        "org_types": list((org.get("nodes") or [{}])[0].get("types") or [])
        if org.get("nodes")
        else [t for t in (sig.get("schema_types") or []) if t in {
            "Organization", "Corporation", "LocalBusiness", "Restaurant", "Dentist", "Hotel", "Brand", "Person"
        }],
        "same_as_links": same[:20],
        "same_as_authority_domains_matched": _authority_hosts_in(
            same + (org.get("authority_sameAs") or []) + (profiles.get("tier0") or []) + (profiles.get("tier1") or [])
        ),
        "tier0_profile_urls": (profiles.get("tier0") or [])[:10],
        "tier1_profile_urls": (profiles.get("tier1") or [])[:10],
        "postal_address_present": bool(org.get("has_address")),
        "postal_address_complete": bool(org.get("has_complete_postal_address")),
        "postal_address": (org.get("nodes") or [{}])[0].get("address") if org.get("nodes") else None,
        "telephone_present": bool(org.get("has_telephone") or sig.get("phones")),
        "telephones": list(org.get("telephones") or sig.get("phones") or [])[:4],
        "is_local_entity": bool(org.get("is_local_entity")),
        "has_maps_sameAs": bool(org.get("has_maps_sameAs")),
        "robots_txt_status": (snap.get("robots") or {}).get("status"),
        "robots_ai_bots": (snap.get("robots") or {}).get("ai_bots") or {},
        "sitemap_status": (snap.get("sitemap") or {}).get("status"),
        "llms_txt_status": (snap.get("llms_txt") or {}).get("status"),
        "meta_description": sig.get("meta_description"),
        "meta_description_missing": bool(sig.get("meta_description_missing")),
        "og_description": sig.get("og_description"),
        "twitter_description": sig.get("twitter_description"),
        "blank_meta": list(sig.get("blank_meta") or []),
        "internal_link_matches": {
            "careers": careers[:5],
            "press": press[:5],
            "investors": investors[:5],
        },
        "scale_claim_phrases_found": list(sig.get("scale_claims") or [])[:8],
        "priced_card_count": sig.get("priced_card_count"),
        "prices_found": list(sig.get("prices") or [])[:12],
        "has_itemlist": bool(caps.get("has_itemlist")),
        "has_itemlist_elements": bool(caps.get("has_itemlist_elements")),
        "has_product_offer": bool(caps.get("has_product_offer")),
        "spa_shell": bool(sig.get("spa_shell")),
        "next_data": bool(sig.get("next_data")),
        "script_count": sig.get("script_count"),
        "noindex": bool(sig.get("noindex")),
        "h1": sig.get("h1"),
        "title": sig.get("title"),
        "faq_empty_questions": [
            pair.get("question")
            for pair in (sig.get("faq_pairs") or [])
            if pair.get("empty")
        ][:10],
        "faq_schema_answer_count": len(sig.get("faq_schema_answers") or []),
        "img_no_alt_large": sig.get("img_no_alt_large"),
        "pdf_links": list(sig.get("pdf_links") or [])[:5],
        "canvas": sig.get("canvas"),
        "name_collision_check": {
            "on_site_token_ambiguous": None,  # filled by enrich_site_signals
            "unrelated_entities_found": None,
            "top_results": [],
            "note": "No off-site name search in stdlib crawl; on_site_token_ambiguous only.",
        },
        "site_type": snap.get("site_type"),
        "site_scale": snap.get("site_scale"),
        "waf_hint": bool(p.get("waf_hint")),
        "ai_ua_probes": snap.get("ai_ua_probes") or [],
        "facet_pairs": snap.get("facet_pairs") or [],
        "action_status": snap.get("action_status") or [],
        "robots_blocked": (snap.get("limitations") or {}).get("robots_blocked") or [],
        "fetch_errors": (snap.get("limitations") or {}).get("fetch_errors") or [],
    }


def enrich_site_signals(snap: dict[str, Any]) -> dict[str, Any]:
    """Site-level raw signals attached to the snapshot for compose + agent synthesis."""
    pages = snap.get("pages") or []
    home = next((p for p in pages if p.get("role") == "home"), pages[0] if pages else {})
    base = page_raw_signals(snap, home)
    from htmlutil import brand_token_ambiguous

    sig = (home.get("signals") or {}) if home else {}
    ambiguous = brand_token_ambiguous(sig.get("title") or "", sig.get("h1") or "", sig.get("og_site_name"))
    base["name_collision_check"] = {
        "on_site_token_ambiguous": ambiguous,
        "unrelated_entities_found": None,
        "top_results": [],
        "note": "No off-site name search in stdlib crawl; on_site_token_ambiguous only.",
    }
    base["pages_crawled"] = len(pages)
    base["page_roles"] = [p.get("role") for p in pages]
    base["page_urls"] = [p.get("url") for p in pages][:12]
    return base


def _facts_from_signals(signals: dict[str, Any]) -> list[str]:
    """Flatten signal values into searchable fact strings for grounding."""
    facts: list[str] = []

    def walk(obj: Any) -> None:
        if obj is None:
            return
        if isinstance(obj, bool):
            facts.append(str(obj).lower())
        elif isinstance(obj, (int, float)):
            facts.append(str(obj))
        elif isinstance(obj, str):
            s = obj.strip()
            if s:
                facts.append(s)
                # host pieces
                if "://" in s:
                    host = urlparse(s).netloc.lower().replace("www.", "")
                    if host:
                        facts.append(host)
        elif isinstance(obj, dict):
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for x in obj:
                walk(x)

    walk(signals)
    return facts


_NUM_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
_DOMAIN_RE = re.compile(
    r"\b(?:[a-z0-9-]+\.)+(?:com|org|net|io|in|uk|ai|co|edu|gov|info|biz)\b",
    re.I,
)
_QUOTE_RE = re.compile(r"[\"']([^\"']{2,80})[\"']")


def grounding_check(text: str, signals: dict[str, Any]) -> dict[str, Any]:
    """Extract numbers/domains/quotes from prose; confirm each appears in signals."""
    facts = _facts_from_signals(signals)
    fact_blob = " | ".join(facts).lower()
    failures: list[str] = []
    for m in _NUM_RE.findall(text or ""):
        if m not in fact_blob and m not in (text or ""):
            # Allow numbers that are substrings of signal values
            if not any(m in f.lower() for f in facts):
                failures.append(f"number:{m}")
    for m in _DOMAIN_RE.findall(text or ""):
        if m.lower() not in fact_blob and not any(m.lower() in f.lower() for f in facts):
            failures.append(f"domain:{m}")
    for m in _QUOTE_RE.findall(text or ""):
        if m.lower() not in fact_blob and not any(m.lower() in f.lower() for f in facts):
            failures.append(f"quote:{m}")
    # Ban known calibration brand names unless they appear in THIS crawl's signals
    banned = (
        "novatech",
        "suta",
        "uniswap",
        "pine villa",
        "krishna dental",
        "akasa",
        "handloom shop",
        "stripe",
    )
    # apple is only banned as a comparison brand if not this site
    site = (signals.get("url") or "") + " " + (signals.get("title") or "")
    for b in banned:
        if b in (text or "").lower() and b not in fact_blob and b not in site.lower():
            failures.append(f"stale_brand:{b}")
    if "apple" in (text or "").lower() and "apple" not in site.lower() and "apple.com" not in fact_blob:
        if re.search(r"\bapple[- ]?(class|like|baseline)\b", text or "", re.I):
            failures.append("stale_brand:apple")
    return {
        "ok": not failures,
        "ungrounded": failures,
    }


def synthesize_from_signals(
    fid: str,
    severity: str,
    title: str,
    signals: dict[str, Any],
    *,
    category: str,
    failure_mode: str,
    confidence: float = 0.9,
    confidence_note: str | None = None,
    urls: list[str] | None = None,
) -> dict[str, Any]:
    """Build a finding whose evidence/action only interpolate this run's signals."""
    evidence, action, how = _draft_prose(fid, severity, signals)
    gc = grounding_check(evidence + " " + action + " " + how, signals)
    rec: dict[str, Any] = {
        "id": fid,
        "title": title,
        "severity": severity,
        "evidence": evidence,
        "category": category,
        "failure_mode": failure_mode,
        "confidence": confidence,
        "affected_urls": urls or ([signals.get("url")] if signals.get("url") else []),
        "signals": signals,
        "suggested_action": {
            "summary": action,
            "priority": severity,
            "how": how,
        },
        "synthesis": {
            "agent_should_rewrite": True,
            "rule": "Rewrite evidence and suggested_action in your own words using only signals. Do not change id or severity.",
        },
        "grounding": gc,
    }
    if confidence_note:
        rec["confidence_note"] = confidence_note
    if not gc["ok"]:
        rec["self_check_failed"] = True
        rec["self_check_ungrounded"] = gc["ungrounded"]
    return rec


def _draft_prose(fid: str, severity: str, s: dict[str, Any]) -> tuple[str, str, str]:
    """Case-specific drafts from signal fields only — not brand-named templates."""
    url = s.get("url") or "(url unknown)"
    status = s.get("http_status")
    if s.get("fetch_error"):
        err = f"Fetch issue on {url}: {s.get('fetch_error')} (http_status={status})."

    if fid == "NET-01":
        err = s.get("fetch_error") or "transport_failed"
        return (
            f"Crawler aborted on {url} (http_status={status}). {err}. "
            "AI agents cannot securely ingest data from this domain.",
            "Install a valid HTTPS certificate that matches this hostname and confirm the homepage loads over HTTPS.",
            "Issue or renew a TLS certificate for this exact hostname, wait for DNS/TLS propagation, "
            "then verify https:// loads without certificate warnings.",
        )

    if fid == "CRA-01":
        bits = []
        if s.get("robots_txt_status") not in (200,):
            bits.append(f"robots.txt HTTP {s.get('robots_txt_status')}")
        if s.get("sitemap_status") not in (200,):
            bits.append(f"sitemap HTTP {s.get('sitemap_status')}")
        if s.get("noindex"):
            bits.append(f"homepage noindex on {url}")
        blocked = [k for k, v in (s.get("robots_ai_bots") or {}).items() if v == "disallow_root"]
        if blocked:
            bits.append(f"Disallow:/ for {', '.join(blocked)}")
        ev = "; ".join(bits) + f" on {url}." if bits else f"Crawl access weak on {url}."
        return (
            ev,
            "Fix robots/sitemap/noindex so public pages are fetchable; keep noindex only on thank-you/cart.",
            "Allow public HTML. Publish a sitemap of canonical URLs.",
        )

    if fid == "CRA-02":
        return (
            f"{url} returns thin HTML to a text crawler "
            f"(word_count={s.get('word_count')}, scripts={s.get('script_count')}, "
            f"JSON-LD blocks={s.get('ld_json_blocks_found')}). "
            "Assistants that fetch raw HTML cannot quote the page body.",
            "SSR the main copy and structured data into the first HTML response.",
            "Client-only rendering is invisible to most AI fetchers.",
        )

    if fid == "FC-ENT-01":
        cons = s.get("digital_consensus") if isinstance(s.get("digital_consensus"), dict) else {}
        cons = cons or {}
        site_type = s.get("site_type") or "marketing"
        if site_type == "local" or s.get("is_local_entity"):
            want = "LocalBusiness"
        elif site_type == "saas":
            want = "Organization"
        else:
            want = "Organization (or Person on a portfolio)"
        wd = cons.get("wikidata_id")
        wiki_title = cons.get("wikipedia_title")
        wiki_url = cons.get("wikipedia_url")
        anchors = []
        if cons.get("identity_verified"):
            if wiki_url:
                anchors.append(wiki_url)
            elif wiki_title:
                anchors.append(f"https://en.wikipedia.org/wiki/{str(wiki_title).replace(' ', '_')}")
            if wd:
                anchors.append(f"https://www.wikidata.org/wiki/{wd}")
        if cons.get("crawl_incomplete") and cons.get("offsite_identity_strong") and anchors:
            return (
                f"{url} has no Organization JSON-LD in the raw HTML "
                f"(types={s.get('ld_json_types_found') or []}, word_count={s.get('word_count')}). "
                f"Off-site echo on {cons.get('platforms_with_echo') or []}; "
                "the defect is schema missing from the first HTML response, not unknown brand.",
                f"SSR schema.org {want} JSON-LD with name, url, and sameAs including {', '.join(anchors[:2])}.",
                "Do not rely on JavaScript to inject identity markup after load.",
            )
        if anchors:
            return (
                f"{url} has no Organization JSON-LD "
                f"(ld_json_types_found={s.get('ld_json_types_found') or []}); "
                f"consensus platforms_with_echo={cons.get('platforms_with_echo') or []}.",
                f"Add schema.org {want} JSON-LD with name, url, and sameAs including {', '.join(anchors[:2])}.",
                "Put it in the first HTML response so AI crawlers can bind the brand.",
            )
        if site_type == "local" or s.get("is_local_entity"):
            return (
                f"{url} has no LocalBusiness JSON-LD "
                f"(ld_json_types_found={s.get('ld_json_types_found') or []}).",
                "Add LocalBusiness JSON-LD with name, url, telephone, PostalAddress, "
                "and sameAs to your Google Business / Maps listing.",
                "Local NAP + listing sameAs disambiguates single-location brands.",
            )
        return (
            f"{url} has no Organization JSON-LD "
            f"(ld_json_types_found={s.get('ld_json_types_found') or []}).",
            f"Add schema.org {want} JSON-LD with name, url, and sameAs to a LinkedIn "
            "company page or official social you already control.",
            "Put it in the first HTML response so AI crawlers can bind the brand.",
        )

    if fid == "CRA-03":
        probes = s.get("ai_ua_probes") or []
        bits = [f"{p.get('ua')} HTTP {p.get('status')}" for p in probes[:4]]
        st = s.get("http_status")
        return (
            f"Crawler aborted on {url} (http_status={st}). WAF/bot-block; probes={bits}. "
            "AI agents cannot ingest the live HTML.",
            "Allow verified AI crawler UAs in WAF on public HTML, and avoid 429 on the homepage for those bots.",
            "Serve 200 HTML to GPTBot/PerplexityBot/ClaudeBot instead of a JS challenge.",
        )
        probes = s.get("ai_ua_probes") or []
        bits = [f"{p.get('ua')} HTTP {p.get('status')}" for p in probes[:4]]
        return (
            f"WAF/bot-block signals on {url}: waf_hint={s.get('waf_hint')}; probes={bits}.",
            "Allow verified AI crawler UAs in WAF on public HTML.",
            "Skip JS challenges for GPTBot/PerplexityBot/ClaudeBot on public pages.",
        )

    if fid == "CRA-04":
        n = s.get("img_missing_alt") or s.get("img_no_alt_large")
        return (
            f"{n} images or UI elements without alt text on {url}. "
            "Facts in photos are invisible to text fetchers.",
            "Add descriptive alt text so assistants can quote what the image shows.",
            "Ensure all informational images use descriptive alt text to allow AI agents to extract visual facts.",
        )

    if fid == "CRA-04-PDF":
        return (
            f"{url}: word_count={s.get('word_count')}, pdf_links={s.get('pdf_links')}.",
            "Summarize PDF facts as HTML on the same URL.",
            "Do not rely on PDF extraction for core NAP or pricing.",
        )

    if fid == "CRA-04-CANVAS":
        return (
            f"{url}: canvas={s.get('canvas')}, word_count={s.get('word_count')}.",
            "Provide a text equivalent for canvas-rendered facts.",
            "Duplicate titles/values in DOM text nodes.",
        )

    if fid == "CRA-05":
        return (
            f"{url}: thin gated route word_count={s.get('word_count')}, "
            f"meta_description={s.get('meta_description')!r}.",
            "Render public OG/description and short copy when unauthenticated.",
            "Add a meta description and short public explanation of what the page does for signed-out visitors.",
        )

    if fid == "CRA-06":
        pairs = s.get("facet_pairs") or []
        p0 = pairs[0] if pairs else {}
        return (
            f"Facet pair identical_raw={p0.get('identical_raw')}: base={p0.get('base')} "
            f"words={p0.get('base_words')} vs filtered={p0.get('filtered')} words={p0.get('filtered_words')}.",
            "Render filter variants as crawlable URLs with distinct HTML.",
            "Each facet URL must change server HTML, not only JS state.",
        )

    if fid == "CRA-07":
        return (
            f"{url}: Load More / infinite scroll without crawlable pagination "
            f"(rel_next absent in signals for this page role={s.get('role')}).",
            "Add rel=next or sitemap entries for page 2+ of collections.",
            "Real href pagination, not a button with no URL.",
        )

    if fid.startswith("FC-ENT-01-"):
        return (
            f"{url}: role={s.get('role')}, ld_json_types_found={s.get('ld_json_types_found')}, "
            f"has_product_offer={s.get('has_product_offer')}, has_itemlist={s.get('has_itemlist')}.",
            f"Add the schema type that fits this page role ({s.get('role')}).",
            "Boilerplate Organization/WebPage alone does not bind the page's money facts.",
        )

    if fid == "FC-ENT-02":
        auths = s.get("same_as_authority_domains_matched") or []
        return (
            f"{url}: same_as_links={s.get('same_as_links')}, "
            f"same_as_authority_domains_matched={auths}, "
            f"postal_address_complete={s.get('postal_address_complete')}, "
            f"is_local_entity={s.get('is_local_entity')}, "
            f"name_collision_check={s.get('name_collision_check')}.",
            "Add authority sameAs hosts (Wikidata/LinkedIn/Crunchbase + social) when there is no complete local NAP.",
            "LocalBusiness with complete PostalAddress+phone uses geography instead of this bar.",
        )

    if fid == "FC-ENT-03":
        return (
            f"{url}: legal IDs absent; name_collision_check={s.get('name_collision_check')}; "
            f"same_as_authority_domains_matched={s.get('same_as_authority_domains_matched')}.",
            "Optional: add leiCode/taxID only if the name collides globally and sameAs is weak.",
            "Never high severity — many healthy enterprises omit taxID.",
        )

    if fid == "FC-ENT-04":
        return (
            f"{url}: postal_address_present={s.get('postal_address_present')}, "
            f"postal_address_complete={s.get('postal_address_complete')}, "
            f"telephone_present={s.get('telephone_present')}, "
            f"postal_address={s.get('postal_address')}, "
            f"is_local_entity={s.get('is_local_entity')}.",
            "Complete LocalBusiness PostalAddress (street + locality) and telephone.",
            "Geography is the disambiguator for single-location clinics with common names.",
        )

    if fid == "FC-ENT-05":
        return (
            f"{url}: social links present without visible labels (see crawl social signals).",
            "Add aria-label on icon links and list those URLs in Organization.sameAs.",
            "Icon hrefs alone are weak for parsers.",
        )

    if fid == "FC-FRESH-01":
        site_type = s.get("site_type") or ""
        if site_type in {"media", "publisher", "news"}:
            return (
                f"Article/section pages among {s.get('page_urls')} lack dateModified / "
                f"datePublished / visible Updated (roles={s.get('page_roles')}).",
                "Add publish and last-updated timestamps on articles in the first HTML response.",
                "News freshness is judged by dates — not product prices or specs.",
            )
        return (
            f"Load-bearing pages among {s.get('page_urls')} lack dateModified / visible last-updated "
            f"(roles={s.get('page_roles')}).",
            "Add dateModified or visible Updated on next to prices and policies.",
            "Assistants discount undated load-bearing claims.",
        )

    if fid == "FC-FRESH-02":
        return (
            f"On-site prices_found={s.get('prices_found')} disagree with third-party menu prices in snapshot.",
            "Align prices across brand origin and ordering platforms.",
            "Same fact, two surfaces, two values — citation trust failure.",
        )

    if fid == "FC-FRESH-03":
        return (
            f"{url}: opening hours text has identical start/end clock (ambiguous AM/PM).",
            "Publish openingHoursSpecification with explicit opens/closes.",
            "Never rely on identical clock strings alone.",
        )

    if fid == "FC-FRESH-04":
        scale = s.get("site_scale") or {}
        cons = s.get("digital_consensus") if isinstance(s.get("digital_consensus"), dict) else {}
        cons = cons or {}
        claims = list(s.get("scale_claim_phrases_found") or [])
        t0 = list(s.get("tier0_profile_urls") or [])
        t1 = list(s.get("tier1_profile_urls") or [])
        site_type = s.get("site_type") or "marketing"
        ev = (
            f"{url}: scale_claim_phrases_found={claims}, "
            f"tier0_profile_urls={t0}, tier1_profile_urls={t1}, "
            f"platforms_with_echo={cons.get('platforms_with_echo') or []}, "
            f"site_scale.looks_small={scale.get('looks_small')}, "
            f"same_as_authority_domains_matched={s.get('same_as_authority_domains_matched')}."
        )
        # Never advise "substantiate scale claims" when none were found.
        # Never advise Google Business Profile for non-local / scaled brands.
        if claims and not t1 and not cons.get("offsite_identity_strong"):
            return (
                ev,
                "Substantiate those specific scale claims with independent coverage in sameAs, "
                "or moderate the wording.",
                "Tier 1 (Wikipedia/press) only because the site claimed scale.",
            )
        if site_type == "local" or s.get("is_local_entity"):
            return (
                ev,
                "Add a Google Business Profile, Justdial, or Yelp URL to LocalBusiness.sameAs "
                "(and keep NAP consistent).",
                "Local businesses disambiguate via listings + address, not Wikidata.",
            )
        return (
            ev,
            "Add at least one controlled profile you already own (LinkedIn company page or official social) "
            "to Organization.sameAs.",
            "Tier 0 listing only — no scale claims were found, so do not require press/Wikipedia.",
        )

    if fid == "FC-FRESH-05":
        return (
            f"{url}: role={s.get('role')}, priced_card_count={s.get('priced_card_count')}, "
            f"prices_found={s.get('prices_found')}, has_itemlist={s.get('has_itemlist')}, "
            f"has_itemlist_elements={s.get('has_itemlist_elements')}, "
            f"has_product_offer={s.get('has_product_offer')}.",
            "Add ItemList with itemListElement prices on this listing URL. PDP Product schema does not substitute.",
            "Without a listing graph, assistants invent comparisons (e.g. most expensive item) from thin HTML.",
        )

    if fid == "FC-FRESH-06":
        return (
            f"{url}: meta_description={s.get('meta_description')!r}, "
            f"og_description={s.get('og_description')!r}, "
            f"twitter_description={s.get('twitter_description')!r}, "
            f"blank_meta={s.get('blank_meta')}, "
            f"meta_description_missing={s.get('meta_description_missing')}.",
            "Fill name=description first; then og:description. Empty content=\"\" is worse than an absent Twitter card.",
            "Ensure a standard <meta name='description'> tag is populated in the initial HTML response. "
            "Fallback OpenGraph or Twitter descriptions are not sufficient for primary AI crawlers.",
        )

    if fid == "FC-PROACT-01":
        return (
            f"llms_txt_status={s.get('llms_txt_status')} for site_type={s.get('site_type')}.",
            "Optional: publish /llms.txt if you have docs or a knowledge surface.",
            "Not a crawl defect; useful mainly for documentation sites.",
        )

    if fid == "FC-PROACT-02":
        return (
            f"tier1_profile_urls={s.get('tier1_profile_urls')}, "
            f"scale_claim_phrases_found={s.get('scale_claim_phrases_found')}, "
            f"site_scale={s.get('site_scale')}.",
            "Wikipedia/Wikidata only if you later pursue reach — not required for small local brands.",
            "Beyond-defect proactive note.",
        )

    if fid == "FC-PROACT-03":
        return (
            "article_schema_present=True, speakable_specification_missing=True.",
            "Add schema.org speakable specification to Article JSON-LD for voice/audio agents.",
            "Voice-readiness proactive recommendation.",
        )

    if fid == "ENG-01":
        dead = [a for a in (s.get("action_status") or []) if a.get("status") in {404, 410, 403, 0}]
        return (
            f"CTA probes failed: {dead[:5]}.",
            "Fix the broken link, or point visitors to a working booking page or phone number.",
            "Repair reservation and order links so they resolve for visitors.",
        )

    if fid == "ENG-02":
        return (
            f"Orientation gaps on crawled pages page_roles={s.get('page_roles')} "
            f"page_urls={s.get('page_urls')} (missing H1/breadcrumb/home link per detector).",
            "One H1, breadcrumbs, and a crawlable link to / on inner templates.",
            "Structural only — does not score subjective content relevance.",
        )

    if fid == "ENG-04":
        return (
            f"{url}: faq_empty_questions={s.get('faq_empty_questions')}, "
            f"faq_schema_answer_count={s.get('faq_schema_answer_count')}.",
            "Render answer text in the first HTML response, or add FAQPage schema for each question.",
            "Ensure all FAQ headings have their answers visible in the initial HTML load, "
            "or implement FAQPage schema so AI agents can extract the answers without clicking.",
        )

    # Generic catch-all — still signal-bound
    return (
        f"Finding {fid} on {url} (http_status={status}, site_type={s.get('site_type')}). "
        f"Key signals: ld_json_types_found={s.get('ld_json_types_found')}, "
        f"same_as_authority_domains_matched={s.get('same_as_authority_domains_matched')}.",
        f"Address the gap described by finding {fid} using the signals for this URL.",
        "Rewrite this action using only facts present in signals.",
    )
