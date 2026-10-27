#!/usr/bin/env python3
"""Digital consensus probes — free public endpoints, stdlib only (no paid APIs).

Corroborates the on-site brand token against Wikipedia, Wikidata, and public Reddit
search so the audit is not a laundry list of on-origin absences alone.
"""

from __future__ import annotations

import json
import re
import ssl
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

UA = "BrandAI-Readiness-Audit/1.0 (+https://agentskills.io; research-audit; consensus)"
TIMEOUT = 10


def _ssl():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _get(url: str, accept: str = "application/json,text/plain,*/*") -> dict[str, Any]:
    req = Request(url, headers={"User-Agent": UA, "Accept": accept})
    t0 = time.time()
    try:
        with urlopen(req, timeout=TIMEOUT, context=_ssl()) as resp:
            raw = resp.read(800_000)
            return {
                "url": resp.geturl(),
                "status": resp.status,
                "body": raw.decode("utf-8", errors="replace"),
                "ms": int((time.time() - t0) * 1000),
                "error": None,
            }
    except HTTPError as e:
        body = ""
        try:
            body = e.read(4000).decode("utf-8", errors="replace")
        except Exception:
            pass
        return {"url": url, "status": e.code, "body": body, "ms": int((time.time() - t0) * 1000), "error": str(e)}
    except (URLError, TimeoutError, ssl.SSLError, OSError) as e:
        return {"url": url, "status": 0, "body": "", "ms": int((time.time() - t0) * 1000), "error": str(e)}


GENERIC_NAME_TOKENS = {
    "the",
    "a",
    "an",
    "and",
    "of",
    "for",
    "inc",
    "llc",
    "ltd",
    "corp",
    "corporation",
    "company",
    "co",
    "group",
    "holdings",
    "foundation",
    "trust",
    "hospital",
    "hospitals",
    "clinic",
    "clinics",
    "health",
    "healthcare",
    "care",
    "medical",
    "dental",
    "pediatric",
    "children",
    "childrens",
    "network",
    "international",
    "national",
    "american",
    "india",
    "indian",
    "official",
    "home",
    "welcome",
    "software",
    "platform",
    "app",
    "apps",
    "doctor",
    "doctors",
    "appointment",
    "appointments",
    "management",
    "services",
    "service",
    "solutions",
    "solution",
    "center",
    "centre",
    "org",
    "organization",
    "language",
    "model",
}


def tokenize_name(value: str) -> list[str]:
    split_camel = re.sub(r"([a-z])([A-Z])", r"\1 \2", value or "")
    return re.findall(r"[a-z0-9]+", split_camel.lower())


def distinctive_name_tokens(value: str) -> set[str]:
    toks = tokenize_name(value)
    out = {t for t in toks if t not in GENERIC_NAME_TOKENS and len(t) >= 4}
    joined = "".join(toks)
    if len(joined) >= 6 and joined not in GENERIC_NAME_TOKENS:
        out.add(joined)
    return out


def names_overlap(brand: str, candidate: str) -> bool:
    """True only when brand and candidate share a distinctive name string — not topical keywords."""
    if not brand or not candidate:
        return False
    bn = re.sub(r"[^a-z0-9]", "", brand.lower())
    cn = re.sub(r"[^a-z0-9]", "", candidate.lower())
    # Exact compact match (BBC == BBC) even when under the usual 4-char distinctive floor.
    if bn and bn == cn and len(bn) >= 2:
        return True
    b = distinctive_name_tokens(brand)
    c = distinctive_name_tokens(candidate)
    if b & c:
        return True
    if len(bn) >= 5 and bn in cn:
        return True
    if len(cn) >= 5 and cn in bn:
        return True
    for x in b:
        for y in c:
            shorter, longer = (x, y) if len(x) <= len(y) else (y, x)
            if len(shorter) >= 4 and shorter in longer and len(shorter) / len(longer) >= 0.5:
                return True
    return False


# Single-token brands that collide with zodiac, NASA, crypto, actors, etc.
OVERLOADED_BRAND_TOKENS = frozenset(
    {
        "gemini",
        "nova",
        "delta",
        "unity",
        "sage",
        "atlas",
        "mercury",
        "pulse",
        "apex",
        "orbit",
        "nexus",
        "vector",
        "horizon",
        "pioneer",
        "jaguar",
        "ace",
        "aurora",
        "summit",
        "apple",
        "amazon",
        "target",
        "gap",
        "shell",
        "meta",
    }
)

WD_WRONG_ENTITY_RE = re.compile(
    r"\b(zodiac|constellation|gémeaux|gemeaux|cryptocurrency|crypto exchange|"
    r"spacecraft|space program|nasa|film|song|album|actor|actress|dj|"
    r"disambiguation)\b",
    re.I,
)


def _home_signals(snap: dict[str, Any] | None) -> dict[str, Any]:
    if not snap:
        return {}
    pages = snap.get("pages") or []
    home = next((p for p in pages if p.get("role") == "home"), pages[0] if pages else {})
    return home.get("signals") or {}


def domain_anchored_brand(snap: dict[str, Any] | None, brand: str) -> bool:
    """True when the registrable label is the brand (bbc.com → BBC) and not an overloaded token.

    Short publisher/domain brands were over-flagged as ambiguous after the Gemini/Nemours
    disambiguation guard, which then rejected the primary Wikipedia article for lack of
    'extra' corroboration tokens beyond the brand itself.
    """
    if not snap:
        return False
    site = (snap.get("site") or "").lower()
    domain = re.sub(r"^www\.", "", site).split(".")[0]
    brand_c = re.sub(r"[^a-z0-9]", "", (brand or "").lower())
    if not domain or domain != brand_c or len(domain) < 2:
        return False
    if brand_c in OVERLOADED_BRAND_TOKENS:
        return False
    return True


def is_ambiguous_brand_query(brand: str, snap: dict[str, Any] | None = None) -> bool:
    """Short / overloaded names need corroboration — never accept first Wikipedia hit."""
    compact = re.sub(r"[^a-z0-9]", "", (brand or "").lower())
    if compact in OVERLOADED_BRAND_TOKENS:
        return True
    # bbc.com / cnn.com / nytimes-style: domain IS the brand — not Gemini-class ambiguity.
    if domain_anchored_brand(snap, brand):
        return False
    dist = distinctive_name_tokens(brand)
    if len(dist) <= 1 and len(compact) <= 10:
        return True
    sig = _home_signals(snap)
    site = (snap.get("site") or "").lower() if snap else ""
    domain = re.sub(r"^www\.", "", site).split(".")[0]
    blob = " ".join(
        str(sig.get(k) or "")
        for k in ("og_site_name", "h1", "title", "meta_description", "og_description")
    ).lower()
    # Domain-anchored multi-word brand on-site is usually not ambiguous.
    if domain and len(domain) >= 3 and domain in re.sub(r"[^a-z0-9]", "", blob):
        return False
    return len(dist) <= 1 and len(compact) <= 12


def _brand_compact(brand: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (brand or "").lower())


def corroboration_signals(snap: dict[str, Any] | None, brand: str) -> set[str]:
    """Domain + on-site anchors that must appear in a Wikipedia/Wikidata candidate — not bare name."""
    out: set[str] = set()
    brand_c = _brand_compact(brand)
    ambiguous = is_ambiguous_brand_query(brand, snap)
    if snap:
        site = (snap.get("site") or "").lower()
        host = re.sub(r"^www\.", "", site)
        domain = host.split(".")[0]
        # Do not treat the overloaded brand slug (gemini.google.com → "gemini") as corroboration.
        if len(domain) >= 4 and domain != brand_c and domain not in OVERLOADED_BRAND_TOKENS:
            out.add(domain)
        if "." in host:
            # e.g. gemini.google.com → google (parent org), not gemini
            parts = [p for p in host.split(".") if p not in {"com", "org", "net", "io", "in", "co", "ai"}]
            for p in parts:
                if len(p) >= 4 and p != domain and p != brand_c and p not in OVERLOADED_BRAND_TOKENS:
                    out.add(p)
    sig = _home_signals(snap)
    blob = " ".join(
        str(sig.get(k) or "")
        for k in ("og_site_name", "h1", "title", "meta_description", "og_description", "text")
    ).lower()
    for hint in (
        "google",
        "deepmind",
        "alphabet",
        "microsoft",
        "openai",
        "anthropic",
        "meta platforms",
        "kivihealth",
        "flipkart",
        "stripe",
        "shopify",
        "language model",
        "chatbot",
        "clinic management",
        "appointment scheduling",
        "saas",
    ):
        if hint in blob:
            out.add(hint.replace(" ", ""))
    if not ambiguous:
        bn = _brand_compact(brand)
        if len(bn) >= 6:
            out.add(bn)
        for t in distinctive_name_tokens(brand):
            if len(t) >= 5:
                out.add(t)
    return {s for s in out if len(s) >= 4 and s != brand_c and s not in OVERLOADED_BRAND_TOKENS}


def has_entity_corroboration(snap: dict[str, Any] | None, brand: str, candidate_text: str) -> bool:
    text = (candidate_text or "").lower()
    if not text.strip():
        return False
    brand_c = _brand_compact(brand)
    signals = corroboration_signals(snap, brand)
    for s in signals:
        if s == brand_c or s in OVERLOADED_BRAND_TOKENS:
            continue
        if s in text:
            return True
    return False


def is_wikipedia_disambiguation(
    hit: dict[str, Any],
    wiki: dict[str, Any],
    brand: str,
    snap: dict[str, Any] | None = None,
) -> bool:
    ptype = (hit.get("page_type") or wiki.get("page_type") or "").lower()
    if "disambiguation" in ptype:
        return True
    title = (hit.get("title") or "").strip()
    extract = (hit.get("summary_extract") or wiki.get("summary_extract") or "").strip()
    if re.search(r"\bmay refer to:\b", extract[:120], re.I):
        return True
    if title.lower() == (brand or "").strip().lower() and "(" not in title:
        # Bare title on an overloaded token is usually a dab/wrong entity —
        # but domain-anchored publishers (bbc.com → BBC) have a primary article.
        if domain_anchored_brand(snap, brand):
            return False
        if is_ambiguous_brand_query(brand, snap):
            return True
    return False


def topical_mismatch(snap: dict[str, Any] | None, candidate_text: str) -> bool:
    if not snap:
        return False
    site_type = snap.get("site_type") or ""
    text = (candidate_text or "").lower()
    if site_type == "saas" and re.search(
        r"\b(hospital|pediatric|nonprofit|foundation|charity|zodiac|constellation)\b", text
    ):
        return True
    return False


def wikipedia_candidate_ok(
    snap: dict[str, Any] | None, brand: str, hit: dict[str, Any], wiki: dict[str, Any]
) -> bool:
    title = hit.get("title") or ""
    if not names_overlap(brand, title):
        return False
    if is_wikipedia_disambiguation(hit, wiki, brand, snap):
        return False
    extract = (hit.get("summary_extract") or wiki.get("summary_extract") or "")
    blob = f"{title} {extract}"
    if topical_mismatch(snap, blob):
        return False
    # Domain-anchored publishers (bbc.com → BBC): accept the primary article without
    # demanding extra corroboration tokens that short brand extracts often omit.
    if domain_anchored_brand(snap, brand):
        tlow = title.lower().strip()
        blow = (brand or "").lower().strip()
        if tlow == blow or tlow.startswith(blow + " ") or tlow.startswith(blow + "("):
            return len(extract) >= 20 or bool(extract)
        return has_entity_corroboration(snap, brand, blob)
    if is_ambiguous_brand_query(brand, snap):
        return has_entity_corroboration(snap, brand, blob)
    # Non-ambiguous: still require corroboration OR a qualified title (e.g. "Gemini (language model)").
    if "(" in title and ")" in title:
        return has_entity_corroboration(snap, brand, blob) or len(extract) >= 40
    return has_entity_corroboration(snap, brand, blob)


def wikidata_candidate_ok(snap: dict[str, Any] | None, brand: str, ent: dict[str, Any]) -> bool:
    label = ent.get("label") or ""
    desc = ent.get("description") or ""
    if not names_overlap(brand, label):
        return False
    blob = f"{label} {desc}"
    if topical_mismatch(snap, blob):
        return False
    if WD_WRONG_ENTITY_RE.search(desc) and not has_entity_corroboration(snap, brand, blob):
        return False
    if domain_anchored_brand(snap, brand):
        llow = label.lower().strip()
        blow = (brand or "").lower().strip()
        if llow == blow or llow.startswith(blow + " ") or blow in re.sub(r"[^a-z0-9]", "", llow):
            return len(desc) >= 8 or has_entity_corroboration(snap, brand, blob)
        return has_entity_corroboration(snap, brand, blob)
    if is_ambiguous_brand_query(brand, snap):
        return has_entity_corroboration(snap, brand, blob)
    if "(" in label:
        return has_entity_corroboration(snap, brand, blob) or len(desc) >= 20
    return has_entity_corroboration(snap, brand, blob)


def brand_query(snap: dict[str, Any]) -> str:
    pages = snap.get("pages") or []
    home = next((p for p in pages if p.get("role") == "home"), pages[0] if pages else {})
    sig = home.get("signals") or {}
    site = (snap.get("site") or "").split(":")[0]
    domain = re.sub(r"^www\.", "", site).split(".")[0]
    og = (sig.get("og_site_name") or "").strip()
    h1 = (sig.get("h1") or "").strip()
    title = (sig.get("title") or "").strip()
    blob = f"{og} {h1} {title}".lower()
    compact = re.sub(r"[^a-z0-9]", "", blob)
    if domain and len(domain) >= 4 and domain.lower() in compact:
        if og:
            return og[:80]
        return domain
    for cand in (og, h1, title):
        if not cand:
            continue
        tokens = re.split(r"[\s|/–—:-]+", cand.strip())
        while tokens and tokenize_name(tokens[0]) and all(
            t in GENERIC_NAME_TOKENS or len(t) < 3 for t in tokenize_name(tokens[0])
        ):
            tokens.pop(0)
        if not tokens:
            continue
        token = re.sub(r"[^A-Za-z0-9.&]", "", tokens[0])
        if len(token) >= 2:
            return token
    return domain or "brand"


def apply_identity_guard(
    query: str, cons: dict[str, Any] | None, snap: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Accept Wikipedia/Wikidata only after disambiguation rejection + entity corroboration.

    Wrong link is worse than no link: overloaded names (Gemini, Delta, …) never get a guessed sameAs.
    """
    cons = dict(cons or {})
    wiki = dict(cons.get("wikipedia") or {})
    wd = dict(cons.get("wikidata") or {})
    ddg = dict(cons.get("duckduckgo") or {})
    rejected: list[dict[str, str]] = []

    wiki_hits = list(wiki.get("hits") or [])
    if not wiki_hits and wiki.get("titles"):
        wiki_hits = [
            {
                "title": wiki.get("summary_title") or (wiki.get("titles") or [None])[0],
                "url": wiki.get("page_url"),
                "page_type": wiki.get("page_type"),
                "summary_extract": wiki.get("summary_extract"),
            }
        ]
        for t in wiki.get("titles") or []:
            if t != wiki_hits[0].get("title"):
                wiki_hits.append({"title": t, "url": None})

    matched_wiki = None
    for hit in wiki_hits:
        title = hit.get("title") or ""
        if wikipedia_candidate_ok(snap, query, hit, wiki):
            matched_wiki = hit
            break
        if title:
            reason = (
                "disambiguation"
                if is_wikipedia_disambiguation(hit, wiki, query, snap)
                else "no_corroboration"
            )
            rejected.append({"source": "wikipedia", "title": title, "reason": reason})
    if matched_wiki:
        wiki["name_match"] = True
        wiki["summary_title"] = matched_wiki.get("title")
        wiki["page_url"] = matched_wiki.get("url") or wiki.get("page_url")
        if not wiki.get("page_url") and matched_wiki.get("title"):
            wiki["page_url"] = (
                "https://en.wikipedia.org/wiki/"
                + quote(str(matched_wiki.get("title")).replace(" ", "_"))
            )
        wiki["titles"] = [matched_wiki.get("title")] + [
            t for t in (wiki.get("titles") or []) if t != matched_wiki.get("title")
        ]
    else:
        wiki["name_match"] = False
        wiki["page_url"] = None
        wiki["summary_title"] = None
        wiki["titles"] = []

    matched_wd = None
    for ent in wd.get("entities") or []:
        if wikidata_candidate_ok(snap, query, ent):
            matched_wd = ent
            break
        label = ent.get("label") or ""
        if label:
            rejected.append({"source": "wikidata", "title": label, "reason": "no_corroboration"})
    if not matched_wd and wd.get("top_label"):
        ent = {
            "id": wd.get("top_id"),
            "label": wd.get("top_label"),
            "description": wd.get("top_description"),
        }
        if wikidata_candidate_ok(snap, query, ent):
            matched_wd = ent
        else:
            rejected.append(
                {"source": "wikidata", "title": wd.get("top_label") or "", "reason": "no_corroboration"}
            )
    if matched_wd:
        wd["name_match"] = True
        wd["top_id"] = matched_wd.get("id")
        wd["top_label"] = matched_wd.get("label")
        wd["top_description"] = matched_wd.get("description")
    else:
        wd["name_match"] = False
        wd["top_id"] = None
        wd["top_label"] = None
        wd["entities"] = []

    heading = ddg.get("heading") or ""
    abstract = ddg.get("abstract") or ""
    if heading and names_overlap(query, heading) and has_entity_corroboration(
        snap, query, f"{heading} {abstract}"
    ):
        ddg["name_match"] = True
    else:
        if heading:
            rejected.append({"source": "duckduckgo", "title": heading, "reason": "no_corroboration"})
        ddg["name_match"] = False
        ddg["heading"] = None
        ddg["abstract"] = None
        ddg["abstract_url"] = None

    wiki_hit = bool(wiki.get("name_match") and wiki.get("page_url"))
    wd_hit = bool(wd.get("name_match") and wd.get("top_id"))
    ddg_hit = bool(ddg.get("name_match"))
    reddit = cons.get("reddit") or {}
    reddit_hit = int(reddit.get("result_count") or 0) > 0
    echoes = sum(1 for x in (wiki_hit, wd_hit, ddg_hit) if x)
    offsite = wiki_hit or wd_hit

    cons["brand_query"] = query
    cons["wikipedia"] = wiki
    cons["wikidata"] = wd
    cons["duckduckgo"] = ddg
    cons["identity_verified"] = offsite
    cons["identity_ambiguous"] = is_ambiguous_brand_query(query, snap)
    cons["rejected_identity_candidates"] = rejected[:12]
    cons["echo_score"] = echoes + (1 if reddit_hit else 0)
    cons["offsite_identity_strong"] = offsite
    if is_ambiguous_brand_query(query, snap) and not offsite:
        cons.setdefault("limitations", [])
        if not any("ambiguous_brand" in str(x) for x in cons["limitations"]):
            cons["limitations"] = list(cons.get("limitations") or []) + [
                "ambiguous_brand: no confident Wikipedia/Wikidata match — sameAs not suggested"
            ]
    cons["platforms_with_echo"] = [
        name
        for name, ok in (
            ("wikipedia", wiki_hit),
            ("wikidata", wd_hit),
            ("duckduckgo", ddg_hit),
            ("reddit", reddit_hit and offsite),
        )
        if ok
    ]
    return cons


def probe_wikipedia(query: str) -> dict[str, Any]:
    """MediaWiki opensearch + REST summary — free, no key."""
    out: dict[str, Any] = {
        "queried": query,
        "status": None,
        "titles": [],
        "summary_title": None,
        "summary_extract": None,
        "page_url": None,
        "error": None,
    }
    if not query:
        out["error"] = "empty_query"
        return out
    search_url = (
        "https://en.wikipedia.org/w/api.php?"
        + urlencode(
            {
                "action": "opensearch",
                "search": query,
                "limit": 5,
                "namespace": 0,
                "format": "json",
            }
        )
    )
    got = _get(search_url)
    out["status"] = got["status"]
    if got["status"] != 200 or not got["body"]:
        out["error"] = got.get("error") or f"HTTP {got['status']}"
        return out
    try:
        data = json.loads(got["body"])
        titles = list(data[1]) if isinstance(data, list) and len(data) > 1 else []
        urls = list(data[3]) if isinstance(data, list) and len(data) > 3 else []
        out["titles"] = titles[:5]
        out["hits"] = [
            {"title": t, "url": urls[i] if i < len(urls) else None} for i, t in enumerate(titles[:5])
        ]
        if titles:
            title = titles[0]
            out["summary_title"] = title
            out["page_url"] = urls[0] if urls else f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
            sum_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title.replace(' ', '_'))}"
            sg = _get(sum_url)
            if sg["status"] == 200 and sg["body"]:
                try:
                    sj = json.loads(sg["body"])
                    out["summary_extract"] = (sj.get("extract") or "")[:400]
                    out["page_type"] = sj.get("type")
                    canonical_page = sj.get("content_urls", {}).get("desktop", {}).get("page")
                    if canonical_page:
                        out["page_url"] = canonical_page
                    canonical_title = sj.get("title") or sj.get("titles", {}).get("canonical")
                    if canonical_title:
                        out["summary_title"] = canonical_title
                    if out.get("hits"):
                        out["hits"][0]["summary_extract"] = out["summary_extract"]
                        out["hits"][0]["page_type"] = out.get("page_type")
                        if canonical_page:
                            out["hits"][0]["url"] = canonical_page
                        if canonical_title:
                            out["hits"][0]["title"] = canonical_title
                except json.JSONDecodeError:
                    pass
    except json.JSONDecodeError as e:
        out["error"] = f"json:{e}"
    return out


def probe_wikidata(query: str) -> dict[str, Any]:
    out: dict[str, Any] = {
        "queried": query,
        "status": None,
        "entities": [],
        "top_id": None,
        "top_label": None,
        "top_description": None,
        "error": None,
    }
    if not query:
        out["error"] = "empty_query"
        return out
    url = (
        "https://www.wikidata.org/w/api.php?"
        + urlencode(
            {
                "action": "wbsearchentities",
                "search": query,
                "language": "en",
                "limit": 5,
                "format": "json",
            }
        )
    )
    got = _get(url)
    out["status"] = got["status"]
    if got["status"] != 200 or not got["body"]:
        out["error"] = got.get("error") or f"HTTP {got['status']}"
        return out
    try:
        data = json.loads(got["body"])
        rows = []
        for hit in data.get("search") or []:
            rows.append(
                {
                    "id": hit.get("id"),
                    "label": hit.get("label"),
                    "description": hit.get("description"),
                    "url": hit.get("concepturi") or f"https://www.wikidata.org/wiki/{hit.get('id')}",
                }
            )
        out["entities"] = rows[:5]
        if rows:
            out["top_id"] = rows[0].get("id")
            out["top_label"] = rows[0].get("label")
            out["top_description"] = rows[0].get("description")
    except json.JSONDecodeError as e:
        out["error"] = f"json:{e}"
    return out


def probe_reddit(query: str) -> dict[str, Any]:
    """Public Reddit search JSON — best-effort; often rate-limited."""
    out: dict[str, Any] = {
        "queried": query,
        "status": None,
        "result_count": 0,
        "top_titles": [],
        "error": None,
    }
    if not query:
        out["error"] = "empty_query"
        return out
    url = "https://www.reddit.com/search.json?" + urlencode({"q": query, "limit": 5, "sort": "relevance"})
    got = _get(url)
    out["status"] = got["status"]
    if got["status"] != 200 or not got["body"]:
        out["error"] = got.get("error") or f"HTTP {got['status']}"
        return out
    try:
        data = json.loads(got["body"])
        children = ((data.get("data") or {}).get("children")) or []
        titles = []
        for ch in children[:5]:
            d = ch.get("data") or {}
            t = d.get("title")
            if t:
                titles.append(t[:120])
        out["top_titles"] = titles
        out["result_count"] = len(titles)
    except json.JSONDecodeError as e:
        out["error"] = f"json:{e}"
    return out


def probe_duckduckgo_instant(query: str) -> dict[str, Any]:
    """DuckDuckGo Instant Answer API — free, no key (Abstract / RelatedTopics)."""
    out: dict[str, Any] = {
        "queried": query,
        "status": None,
        "heading": None,
        "abstract": None,
        "abstract_url": None,
        "related": [],
        "error": None,
    }
    if not query:
        out["error"] = "empty_query"
        return out
    url = "https://api.duckduckgo.com/?" + urlencode({"q": query, "format": "json", "no_html": 1, "skip_disambig": 1})
    got = _get(url)
    out["status"] = got["status"]
    if got["status"] != 200 or not got["body"]:
        out["error"] = got.get("error") or f"HTTP {got['status']}"
        return out
    try:
        data = json.loads(got["body"])
        out["heading"] = data.get("Heading") or None
        out["abstract"] = (data.get("AbstractText") or "")[:400] or None
        out["abstract_url"] = data.get("AbstractURL") or None
        related = []
        for r in (data.get("RelatedTopics") or [])[:5]:
            if isinstance(r, dict) and r.get("Text"):
                related.append(r.get("Text")[:160])
            elif isinstance(r, dict) and r.get("Topics"):
                for t in r["Topics"][:2]:
                    if t.get("Text"):
                        related.append(t["Text"][:160])
        out["related"] = related[:5]
    except json.JSONDecodeError as e:
        out["error"] = f"json:{e}"
    return out


JS_SHELL_NOTE = (
    "Raw HTML is thin (JS application shell). "
    "On-site schema, meta, and alt absences are low-confidence until they appear in the first HTML response."
)
RICH_META_THIN_NOTE = (
    "Raw HTML is thin while marketing meta/scripts/sitemap look real — "
    "likely JS-rendered or bot-minimized HTML; on-site schema absences are low-confidence."
)


def crawl_quality(snap: dict[str, Any]) -> dict[str, Any]:
    """Detect thin JS shells — incomplete view, not a real placeholder.

    Empty CRA/Vite/Helmet shells often have no rich meta, few scripts, and no sitemap.
    Those still hide schema/meta from HTML-only crawlers, so mark crawl_incomplete.
    """
    pages = snap.get("pages") or []
    home = next((p for p in pages if p.get("role") == "home"), pages[0] if pages else {})
    sig = home.get("signals") or {}
    wc = int(sig.get("word_count") or 0)
    meta = (sig.get("meta_description") or sig.get("og_description") or "").strip()
    scripts = int(sig.get("script_count") or 0)
    ld = len(sig.get("json_ld") or [])
    sitemap_ok = (snap.get("sitemap") or {}).get("status") == 200
    robots_ok = (snap.get("robots") or {}).get("status") == 200
    rich_meta = len(meta) >= 80
    thin_body = wc < 100
    # Do not treat "has a sitemap" or short SSR copy as an empty shell.
    # next_data / JSON-LD means the first HTML response already carries structure.
    empty_shell = (
        ld == 0
        and wc < 25
        and not sig.get("next_data")
        and (bool(sig.get("spa_shell")) or scripts >= 3)
    )
    rich_thin = (
        ld == 0
        and not sig.get("next_data")
        and thin_body
        and (rich_meta or scripts >= 4)
        and (bool(sig.get("spa_shell")) or scripts >= 4)
    )
    incomplete = rich_thin or empty_shell
    iana_placeholder = (
        thin_body
        and not rich_meta
        and not empty_shell
        and (snap.get("site") or "").lower() in {"example.com", "example.org", "example.net"}
    )
    if incomplete and not iana_placeholder:
        note = RICH_META_THIN_NOTE if rich_thin else JS_SHELL_NOTE
    else:
        note = None
    return {
        "pages_crawled": len(pages),
        "home_word_count": wc,
        "home_script_count": scripts,
        "home_ld_json_blocks": ld,
        "meta_description_len": len(meta),
        "rich_meta_thin_body": bool(rich_meta and thin_body),
        "js_empty_shell": bool(empty_shell and not iana_placeholder),
        "crawl_incomplete": bool(incomplete and not iana_placeholder),
        "iana_placeholder": iana_placeholder,
        "sitemap_ok": sitemap_ok,
        "robots_ok": robots_ok,
        "note": note,
    }


def build_consensus(snap: dict[str, Any]) -> dict[str, Any]:
    q = brand_query(snap)
    quality = crawl_quality(snap)
    wiki = probe_wikipedia(q)
    wikidata = probe_wikidata(q)
    ddg = probe_duckduckgo_instant(q)
    reddit = probe_reddit(q)

    raw = {
        "brand_query": q,
        "crawl_quality": quality,
        "wikipedia": wiki,
        "wikidata": wikidata,
        "duckduckgo": ddg,
        "reddit": reddit,
        "platforms_checked": ["wikipedia", "wikidata", "duckduckgo", "reddit"],
        "limitations": [
            x
            for x in [
                wiki.get("error") and f"wikipedia:{wiki.get('error')}",
                wikidata.get("error") and f"wikidata:{wikidata.get('error')}",
                ddg.get("error") and f"duckduckgo:{ddg.get('error')}",
                reddit.get("error") and f"reddit:{reddit.get('error')}",
                "linkedin/quora: no unauthenticated public search API in stdlib budget — not probed",
            ]
            if x
        ],
        "live_probes": {
            "wikipedia_http": wiki.get("status"),
            "wikidata_http": wikidata.get("status"),
            "duckduckgo_http": ddg.get("status"),
            "reddit_http": reddit.get("status"),
            "attempted": True,
        },
    }
    return apply_identity_guard(q, raw, snap)
