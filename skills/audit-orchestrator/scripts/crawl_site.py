"""Robots-aware crawl. Stdlib only. Snapshot JSON for detectors."""

from __future__ import annotations

import json
import re
import ssl
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

from htmlutil import (
    PRICE_RE,
    classify_site_type,
    extract_page,
    guess_role,
    is_html_content_type,
)


def _origin_html_dead(pages: list[dict[str, Any]]) -> bool:
    """True when homepage HTML was never retrieved (0, 403, 429, or ≥500)."""
    blocked = {0, 403, 429}

    def _dead(st: Any) -> bool:
        return st in blocked or (isinstance(st, int) and st >= 500)

    for p in pages or []:
        if p.get("role") != "home":
            continue
        return _dead(p.get("status"))
    if pages and all(_dead(p.get("status")) for p in pages):
        return True
    return False

UA = "BrandAI-Readiness-Audit/1.0 (+https://agentskills.io; research-audit)"
TIMEOUT = 12
MAX_PAGES = 12
MAX_BYTES = 1_500_000


def _ssl():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def fetch(url: str, method: str = "GET", ua: str | None = None) -> dict[str, Any]:
    req = Request(
        url,
        method=method,
        headers={"User-Agent": ua or UA, "Accept": "text/html,*/*"},
    )
    t0 = time.time()
    try:
        with urlopen(req, timeout=TIMEOUT, context=_ssl()) as resp:
            raw = resp.read(MAX_BYTES) if method != "HEAD" else b""
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return {
                "url": resp.geturl(),
                "status": resp.status,
                "headers": headers,
                "body": raw.decode("utf-8", errors="replace") if raw else "",
                "ms": int((time.time() - t0) * 1000),
                "error": None,
            }
    except HTTPError as e:
        body = ""
        try:
            body = e.read(8000).decode("utf-8", errors="replace")
        except Exception:
            pass
        return {
            "url": url,
            "status": e.code,
            "headers": {k.lower(): v for k, v in (e.headers.items() if e.headers else [])},
            "body": body,
            "ms": int((time.time() - t0) * 1000),
            "error": str(e),
        }
    except (URLError, TimeoutError, ssl.SSLError, OSError) as e:
        return {
            "url": url,
            "status": 0,
            "headers": {},
            "body": "",
            "ms": int((time.time() - t0) * 1000),
            "error": str(e),
        }


def origin_of(url: str) -> str:
    p = urlparse(url if "://" in url else "https://" + url)
    scheme = p.scheme or "https"
    netloc = p.netloc or p.path.split("/")[0]
    return f"{scheme}://{netloc}"


def load_robots(origin: str) -> RobotFileParser:
    rp = RobotFileParser()
    rp.set_url(urljoin(origin, "/robots.txt"))
    got = fetch(urljoin(origin, "/robots.txt"))
    if got["status"] == 200 and got["body"]:
        rp.parse(got["body"].splitlines())
    else:
        rp.parse(["User-agent: *", "Allow: /"])
    return rp


def parse_sitemap_locs(xml: str, limit: int = 40) -> list[str]:
    return re.findall(r"<loc>\s*([^<]+)\s*</loc>", xml, re.I)[:limit]


def crawl(start: str) -> dict[str, Any]:
    if not start.startswith("http"):
        start = "https://" + start
    origin = origin_of(start)
    limitations: dict[str, Any] = {"fetch_errors": [], "robots_blocked": []}
    robots_txt = fetch(urljoin(origin, "/robots.txt"))
    sitemap = fetch(urljoin(origin, "/sitemap.xml"))
    if sitemap["status"] != 200:
        sitemap = fetch(urljoin(origin, "/sitemap_index.xml"))
    llms = fetch(urljoin(origin, "/llms.txt"))
    rp = load_robots(origin)

    seeds = [origin + "/"]
    if urlparse(start).path not in ("", "/"):
        seeds.append(start)
    if sitemap["status"] == 200:
        for loc in parse_sitemap_locs(sitemap["body"]):
            if origin_of(loc) == origin:
                seeds.append(loc)
            if len(seeds) > 30:
                break

    pages: list[dict[str, Any]] = []
    seen: set[str] = set()
    for seed in seeds:
        if len(pages) >= MAX_PAGES:
            break
        canon = seed.split("#")[0]
        if canon in seen:
            continue
        seen.add(canon)
        if not rp.can_fetch(UA, canon):
            limitations["robots_blocked"].append(canon)
            if canon.rstrip("/") == origin or canon == origin + "/":
                limitations["home_robots_blocked"] = True
            continue
        got = fetch(canon)
        if got["status"] >= 400 or got["status"] == 0:
            limitations["fetch_errors"].append({"url": canon, "status": got["status"], "error": got["error"]})
            if canon.rstrip("/") == origin or canon == origin + "/":
                pages.append(
                    {
                        "url": canon,
                        "status": got["status"],
                        "role": "home",
                        "signals": {},
                        "waf_hint": _waf_hint(got),
                    }
                )
                # Origin HTML never loaded — stop spending fetches on DOM extras.
                if got["status"] == 0 or got["status"] in (403, 429) or got["status"] >= 500:
                    break
            continue
        html = got["body"]
        ctype = (got.get("headers") or {}).get("content-type") or ""
        if not is_html_content_type(ctype, got["url"], html):
            # Agent-facing or binary resources (text/plain SKILL.md, JSON, etc.):
            # record them, but do not run HTML structural extractors.
            words = len(re.findall(r"[A-Za-z0-9']+", html or ""))
            rec = {
                "url": got["url"],
                "status": got["status"],
                "content_type": ctype.split(";")[0].strip().lower() or "unknown",
                "role": "agent_resource"
                if (got["url"] or "").lower().endswith((".md", ".txt"))
                or "markdown" in ctype.lower()
                or ctype.lower().startswith("text/plain")
                else "non_html",
                "signals": {
                    "non_html": True,
                    "content_type": ctype.split(";")[0].strip().lower() or "unknown",
                    "word_count": words,
                    "text": (html or "")[:4000],
                    "h1": None,
                    "has_breadcrumb": False,
                    "has_home_href": False,
                    "has_nav": False,
                    "schema_types": [],
                    "travelish_text": False,
                },
                "waf_hint": _waf_hint(got),
                "cf": "cloudflare" in (got["headers"].get("server") or "").lower()
                or "cf-mitigated" in got["headers"],
            }
            pages.append(rec)
            continue
        sig = extract_page(got["url"], html)
        sig["content_type"] = ctype.split(";")[0].strip().lower() or "text/html"
        rec = {
            "url": got["url"],
            "status": got["status"],
            "content_type": sig["content_type"],
            "role": guess_role(got["url"], sig),
            "signals": sig,
            "waf_hint": _waf_hint(got),
            "cf": "cloudflare" in (got["headers"].get("server") or "").lower()
            or "cf-mitigated" in got["headers"],
        }
        pages.append(rec)
        if rec["role"] == "home":
            for href in (sig.get("internal_links") or [])[:25]:
                if href not in seen and origin_of(href) == origin:
                    seeds.append(href)

    # Fail-fast: no HTML from origin → skip action/AI/facet/consensus probes.
    if _origin_html_dead(pages):
        return {
            "start": start,
            "origin": origin,
            "site": urlparse(origin).netloc.replace("www.", ""),
            "site_type": "unknown",
            "robots": {
                "status": robots_txt["status"],
                "preview": (robots_txt["body"] or "")[:2500],
                "ai_bots": _ai_bot_rules(robots_txt["body"] or ""),
            },
            "sitemap": {"status": sitemap["status"]},
            "llms_txt": {"status": llms["status"], "bytes": len(llms.get("body") or "")},
            "pages": pages,
            "action_status": [],
            "ai_ua_probes": [],
            "facet_pairs": [],
            "third_party_prices": [],
            "limitations": limitations,
            "digital_consensus": {
                "brand_query": None,
                "offsite_identity_strong": False,
                "platforms_with_echo": [],
                "echo_score": 0,
                "crawl_quality": {"crawl_incomplete": True, "note": "origin_unreachable"},
                "limitations": ["consensus_skipped_origin_unreachable"],
                "platforms_checked": [],
                "identity_verified": False,
            },
            "site_scale": {"looks_small": False, "scale_claims": [], "note": "origin_unreachable"},
        }

    # probe a few action URLs
    action_status = []
    probed = 0
    for p in pages:
        for a in (p.get("signals") or {}).get("action_links") or []:
            if probed >= 6:
                break
            u = a.get("url")
            if not u or u in seen:
                continue
            probed += 1
            head = fetch(u, method="HEAD")
            if head["status"] in (0, 405, 501):
                head = fetch(u)
            action_status.append({"url": u, "status": head["status"]})

    ai_ua_probes = []
    for bot in ("GPTBot/1.2", "PerplexityBot/1.0"):
        got = fetch(origin + "/", ua=bot)
        ai_ua_probes.append(
            {
                "ua": bot,
                "status": got["status"],
                "waf": _waf_hint(got),
                "cf-mitigated": "cf-mitigated" in (got.get("headers") or {}),
            }
        )

    facet_pairs = []
    for p in pages:
        sig = p.get("signals") or {}
        base = p.get("url") or ""
        fl = sig.get("filter_links") or []
        if not fl:
            continue
        filt = fl[0]
        if origin_of(filt) != origin:
            continue
        got = fetch(filt)
        if got["status"] != 200:
            continue
        fsig = extract_page(got["url"], got["body"])
        base_t = (sig.get("text") or "")[:1500]
        filt_t = (fsig.get("text") or "")[:1500]
        same = base_t == filt_t or (
            sig.get("word_count")
            and abs((sig.get("word_count") or 0) - (fsig.get("word_count") or 0)) < 15
            and (sig.get("word_count") or 0) > 40
        )
        facet_pairs.append(
            {
                "base": base,
                "filtered": got["url"],
                "identical_raw": same,
                "base_words": sig.get("word_count"),
                "filtered_words": fsig.get("word_count"),
            }
        )
        break

    third_prices = []
    for p in pages:
        for u in (p.get("signals") or {}).get("third_party_menu") or []:
            got = fetch(u)
            if got.get("body"):
                third_prices.append(
                    {
                        "url": u,
                        "status": got["status"],
                        "prices": PRICE_RE.findall(got["body"][:20000])[:15],
                    }
                )
            break
        if third_prices:
            break

    from consensus import build_consensus
    from htmlutil import classify_site_type, infer_site_scale

    snap = {
        "start": start,
        "origin": origin,
        "site": urlparse(origin).netloc.replace("www.", ""),
        "site_type": "unknown",
        "robots": {
            "status": robots_txt["status"],
            "preview": (robots_txt["body"] or "")[:2500],
            "ai_bots": _ai_bot_rules(robots_txt["body"] or ""),
            "home_disallowed": bool(limitations.get("home_robots_blocked")),
        },
        "sitemap": {"status": sitemap["status"]},
        "llms_txt": {"status": llms["status"], "bytes": len(llms.get("body") or "")},
        "pages": pages,
        "action_status": action_status,
        "ai_ua_probes": ai_ua_probes,
        "facet_pairs": facet_pairs,
        "third_party_prices": third_prices,
        "limitations": limitations,
    }
    consensus = build_consensus(snap)
    snap["digital_consensus"] = consensus
    snap["site_type"] = classify_site_type(pages, consensus)
    cq = consensus.get("crawl_quality") or {}
    if cq.get("iana_placeholder"):
        snap["site_type"] = "placeholder"
    snap["site_scale"] = infer_site_scale(pages, consensus=consensus)
    if cq.get("crawl_incomplete"):
        snap["limitations"]["crawl_incomplete"] = cq.get("note")
    return snap


def _waf_hint(got: dict[str, Any]) -> bool:
    if got.get("status") == 403:
        return True
    body = (got.get("body") or "").lower()
    if "cf-mitigated" in (got.get("headers") or {}):
        return True
    if "just a moment" in body and "cloudflare" in body:
        return True
    return False


def _ai_bot_rules(robots: str) -> dict[str, str]:
    out = {}
    for bot in ("GPTBot", "Google-Extended", "PerplexityBot", "ClaudeBot", "Applebot-Extended"):
        m = re.search(
            rf"user-agent:\s*{re.escape(bot)}\s*(.*?)(?:user-agent:|\Z)",
            robots,
            re.I | re.S,
        )
        if not m:
            out[bot] = "unspecified"
            continue
        block = m.group(1)
        if re.search(r"disallow:\s*/\s*$", block, re.M | re.I):
            out[bot] = "disallow_root"
        else:
            out[bot] = "allow_or_partial"

    # RFC 9309 / standard robots.txt semantics: if a bot is not specifically listed,
    # it inherits the User-agent: * directive.
    m_star = re.search(
        r"user-agent:\s*\*\s*(.*?)(?:user-agent:|\Z)",
        robots,
        re.I | re.S,
    )
    if m_star:
        star_block = m_star.group(1)
        if re.search(r"disallow:\s*/\s*$", star_block, re.M | re.I):
            out["*"] = "disallow_root"
            for bot in ("GPTBot", "Google-Extended", "PerplexityBot", "ClaudeBot", "Applebot-Extended"):
                if out.get(bot) == "unspecified":
                    out[bot] = "disallow_root"
        else:
            out["*"] = "allow_or_partial"
    return out


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print("usage: crawl_site.py <url> [out.json]", file=sys.stderr)
        sys.exit(2)
    snap = crawl(argv[1])
    out = argv[2] if len(argv) > 2 else "-"
    text = json.dumps(snap, indent=2)
    if out == "-":
        print(text)
    else:
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)


if __name__ == "__main__":
    main(sys.argv)
