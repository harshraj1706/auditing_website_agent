"""Stdlib HTML extraction for AI-crawler-visible signals."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

SKIP_TAGS = {
    "script",
    "style",
    "noscript",
    "template",
    "svg",
    "iframe",
}

LOGIN_RE = re.compile(
    r"\b(log\s*in|sign\s*in|sign\s*up|create account|password|subscribe to continue|"
    r"paywall|members? only|premium content)\b",
    re.I,
)
COOKIE_RE = re.compile(
    r"\b(cookie|consent|gdpr|we use cookies|accept all|privacy preference)\b", re.I
)
BREADCRUMB_RE = re.compile(r"breadcrumb", re.I)
SEARCH_RE = re.compile(r'type=["\']search["\']|role=["\']search["\']|name=["\']q["\']', re.I)
# UI chrome — never treat as CRA-04 load-bearing photos.
UI_CHROME_IMG_RE = re.compile(
    r"(?:^|[\s/_-])(?:icon|logo|spacer|pixel|sprite|favicon|avatar|emoji|badge|spinner|"
    r"tracking|1x1|blank)(?:$|[\s/_.-])",
    re.I,
)
INFORMATIONAL_IMG_CLASS_RE = re.compile(
    r"\b(hero|banner|og[-_]?image|featured|photo|product[-_]?image)\b",
    re.I,
)
RELATED_RE = re.compile(
    r"\b(related (articles|posts|products)|you may also|recommended|more like this)\b",
    re.I,
)
SOCIAL_HOSTS = (
    "instagram.com",
    "facebook.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "youtube.com",
    "wikidata.org",
    "wikipedia.org",
    "crunchbase.com",
    "github.com",
)
ACTION_RE = re.compile(
    r"\b(book|booking|reserve|reservation|order|menu|contact|enquiry|inquiry)\b",
    re.I,
)
HOURS_IDENTICAL_RE = re.compile(
    r"\b((?:1[0-2]|0?[1-9])(?::[0-5][0-9])?\s*(?:am|pm))\s*[-–to]+\s*\1\b",
    re.I,
)
THIRD_PARTY_MENU = (
    "petpooja.com",
    "toasttab.com",
    "zomato.com",
    "swiggy.com",
    "ubereats.com",
    "doordash.com",
)
ORG_TYPES = {
    "Organization",
    "Corporation",
    "LocalBusiness",
    "Restaurant",
    "Dentist",
    "Hotel",
    "Store",
    "Brand",
    "Person",
}
AUTHORITY_HOSTS = (
    "wikidata.org",
    "wikipedia.org",
    "linkedin.com",
    "crunchbase.com",
    "bloomberg.com",
    "github.com",
    "youtube.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "instagram.com",
)
# Independently-controlled profiles any SMB can claim (Tier 0). Not fame.
TIER0_PROFILE_HOSTS = (
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "youtube.com",
    "x.com",
    "twitter.com",
    "justdial.com",
    "indiamart.com",
    "yelp.com",
    "tripadvisor.com",
    "maps.google.",
    "google.com/maps",
    "business.google.com",
    "zomato.com",
    "sulekha.com",
    "tradeindia.com",
)
TIER1_REACH_HOSTS = (
    "wikipedia.org",
    "wikidata.org",
    "bloomberg.com",
    "reuters.com",
    "forbes.com",
    "techcrunch.com",
    "crunchbase.com",
)
PRICE_RE = re.compile(
    r"(?:₹|rs\.?\s*|inr\s*|usd\s*|eur\s*|gbp\s*|\$|€|£)\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
PHONE_RE = re.compile(
    r"(?:\+?\d[\d\s\-().]{8,}\d)",
)
LEGAL_PATH_RE = re.compile(
    r"/(?:terms(?:[-_]?and[-_]?conditions)?|privacy(?:[-_]?policy)?|legal|"
    r"tos|conditions|cookie[-_]?policy|disclaimer|"
    r"accessibility|vpat|wcag|compliance)(?:/|$|\.)",
    re.I,
)
# Hard travel tokens only — bare "departure"/"arrival"/"arrival date" (common in a11y form
# docs and checkout VPATs) is NOT enough. Prefer "flight", airline, IATA, or
# departure/arrival tied to airport/flight/gate.
# NOTE: IATA pairs are a SEPARATE case-sensitive regex — never use re.I on [A-Z]{3} to [A-Z]{3}
# or it matches English "how to get" / "and to the".
HARD_TRAVEL_RE = re.compile(
    r"(?:"
    r"\bflights?\b|"
    r"\bairlines?\b|"
    r"\biata\b|"
    r"\b(?:departure|arrival)\s+(?:airport|flight|gate)\b|"
    r"\b(?:departing|arriving)\s+(?:from|at|to)\b|"
    r"\bbook\s+(?:a\s+)?(?:flight|ticket)\b|"
    r"\b(?:one[\s-]?way|round[\s-]?trip)\s+(?:flight|ticket|fare)\b"
    r")",
    re.I,
)
IATA_PAIR_RE = re.compile(r"\b[A-Z]{3}\s*(?:[-–—/]|to)\s*[A-Z]{3}\b")
HARD_VEHICLE_RE = re.compile(
    r"(?:"
    r"\bvin\b|"
    r"\bmsrp\b|"
    r"\btest\s+drive\b|"
    r"\bdealership\s+inventory\b|"
    r"\b(?:new|used)\s+cars?\b|"
    r"\bhorsepower\b|"
    r"\bfuel\s+type\b|"
    r"\bmileage\b"
    r")",
    re.I,
)
HARD_PRODUCT_PATH_RE = re.compile(
    r"/(?:products?|item|sku|p)/[^/]+",
    re.I,
)
HARD_FAQ_PATH_RE = re.compile(r"/(?:faq|faqs|help|support|knowledge[-_]?base)(?:/|$)", re.I)
HARD_ARTICLE_PATH_RE = re.compile(r"/(?:blog|news|insights|articles|press)/[^/]+", re.I)
HARD_LOCAL_PATH_RE = re.compile(
    r"/(?:contact|locations?|stores?|find[-_]?us|visit)(?:/|$)",
    re.I,
)
NON_HTML_CT_RE = re.compile(
    r"^(?:text/(?:plain|markdown|csv|css|javascript|xml)|"
    r"application/(?:json|pdf|javascript|xml|octet-stream)|"
    r"image/|audio/|video/|font/)",
    re.I,
)
HTML_CT_RE = re.compile(r"^(?:text/html|application/xhtml\+xml)\b", re.I)
SCALE_CLAIM_RE = re.compile(
    r"(?:trusted by\s+\d[\d,+]*|"
    r"featured in|"
    r"fortune\s*500|"
    r"\bforbes\b|"
    r"india'?s\s+(?:#1|no\.?\s*1|leading|largest)|"
    r"world'?s\s+leading|"
    r"operating in\s+\d+|"
    r"\d+\+?\s+(?:countries|cities|stores|retailers|businesses|clients)|"
    r"series\s+[abc]\b|"
    r"\bfunded\b|"
    r"award[- ]winning|"
    r"unicorn\b)",
    re.I,
)
HEADING_RE = re.compile(r"<h([1-4])\b[^>]*>(.*?)</h\1>", re.I | re.S)
TAG_STRIP_RE = re.compile(r"<[^>]+>")
FAQ_SECTION_RE = re.compile(r"\b(faq|frequently\s+asked)\b", re.I)
# Accordion / disclosure UI — required before treating "?" headings as FAQ questions.
FAQ_UI_RE = re.compile(
    r"<details\b|<summary\b|aria-expanded\s*="
    r"""|(?:class|id)\s*=\s*["'][^"']*\b(?:accordion|faq[-_]?(?:item|question|answer|list|section)|collapse|expander)\b""",
    re.I,
)
ACCORDION_CHROME_RE = re.compile(
    r"^(expand|collapse|show(\s+answer)?|hide|read\s+more|more|\+|−|–|-|▼|▲|›|››)\s*$",
    re.I,
)
MAPS_HOST_RE = re.compile(
    r"(maps\.google\.|google\.com/maps|business\.google\.|goo\.gl/maps|maps\.app\.goo\.gl)",
    re.I,
)


def _img_px(raw: str) -> int | None:
    s = (raw or "").strip().lower().replace("px", "")
    if s.isdigit():
        return int(s)
    m = re.search(r"(\d+)", s)
    return int(m.group(1)) if m else None


def is_informational_img(ad: dict[str, str]) -> bool:
    """True for load-bearing photos (CRA-04). Icons/logos/spacers and tiny UI art are False."""
    src = ad.get("src") or ad.get("data-src") or ""
    blob = " ".join(
        [ad.get("class") or "", ad.get("id") or "", src, ad.get("role") or "", ad.get("alt") or ""]
    )
    if UI_CHROME_IMG_RE.search(blob) or UI_CHROME_IMG_RE.search(src.replace(".", " ")):
        return False
    if (ad.get("role") or "").lower() == "presentation":
        return False
    w = _img_px(ad.get("width") or "")
    h = _img_px(ad.get("height") or "")
    style = ad.get("style") or ""
    if w is None:
        m = re.search(r"\bwidth\s*:\s*(\d+)", style, re.I)
        w = int(m.group(1)) if m else None
    if h is None:
        m = re.search(r"\bheight\s*:\s*(\d+)", style, re.I)
        h = int(m.group(1)) if m else None
    if (w is not None and w > 100) or (h is not None and h > 100):
        return True
    # Authors often omit width/height on heroes; class is enough if not chrome.
    if w is None and h is None and INFORMATIONAL_IMG_CLASS_RE.search(blob):
        return True
    return False


class PageParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self._skip = 0
        self._in_title = False
        self._in_ld = False
        self._in_h1 = False
        self._ld_buf: list[str] = []
        self._h1_buf: list[str] = []
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.h1 = ""
        self.canonical: str | None = None
        self.meta_robots: str | None = None
        self.og_site_name: str | None = None
        self.og_title: str | None = None
        self.json_ld: list[Any] = []
        self.internal_links: list[str] = []
        self.external_links: list[str] = []
        self.pdf_links: list[str] = []
        self.img_count = 0
        self.img_missing_alt = 0
        self.img_no_alt_large = 0
        self.has_nav = False
        self.has_header = False
        self.has_main = False
        self.has_footer = False
        self.has_breadcrumb = False
        self.has_search = False
        self.canvas = 0
        self.script_count = 0
        self.root_or_app = False
        self.next_data = False
        self.spa_empty_hint = False
        self._seen_href: set[str] = set()
        self.social_links: list[dict[str, Any]] = []
        self.iframes: list[str] = []
        self.action_links: list[dict[str, str]] = []
        self.meta_description: str | None = None
        self.x_robots: str | None = None
        self.og_description: str | None = None
        self.twitter_description: str | None = None
        self.blank_meta: list[str] = []
        self.rel_next: list[str] = []
        self.filter_links: list[str] = []
        self.has_home_href = False
        self.load_more_js = False
        self.onclick_nav = 0
        self._nav_depth = 0
        self._header_depth = 0
        self._footer_depth = 0
        self._card_stack: list[dict[str, bool]] = []
        self.priced_cards = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = {k.lower(): (v or "") for k, v in attrs}
        tag = tag.lower()
        if tag in SKIP_TAGS:
            self._skip += 1
            if tag == "script":
                self.script_count += 1
                t = ad.get("type", "").lower()
                if "ld+json" in t:
                    self._in_ld = True
                    self._skip -= 1  # parse ld+json text
                    self._ld_buf = []
                if "application/json" in t and ad.get("id") == "__NEXT_DATA__":
                    self.next_data = True
            return
        if self._skip:
            return
        if tag == "title":
            self._in_title = True
        if tag == "h1":
            self._in_h1 = True
            self._h1_buf = []
        if tag in {"nav"} or ad.get("role") == "navigation":
            self.has_nav = True
            self._nav_depth += 1
        if tag == "header":
            self.has_header = True
            self._header_depth += 1
        if tag == "main":
            self.has_main = True
        if tag == "footer":
            self.has_footer = True
            self._footer_depth += 1
        if (
            (tag in {"article", "li"} or ad.get("role") == "listitem")
            and not self._nav_depth
            and not self._header_depth
            and not self._footer_depth
        ):
            self._card_stack.append({"has_price": False})
        if tag == "canvas":
            self.canvas += 1
        eid = ad.get("id", "")
        cls = ad.get("class", "")
        if eid in {"root", "app", "__next", "nuxt"} or "id=\"root\"" in str(attrs):
            self.root_or_app = True
        if BREADCRUMB_RE.search(eid + " " + cls) or ad.get("aria-label", "").lower().find("breadcrumb") >= 0:
            self.has_breadcrumb = True
        if tag == "input" and (ad.get("type") == "search" or ad.get("name") in {"q", "query", "s"}):
            self.has_search = True
        if tag == "form" and ad.get("role") == "search":
            self.has_search = True
        if tag == "link" and ad.get("rel", "").lower() == "canonical":
            href = ad.get("href")
            if href:
                self.canonical = urljoin(self.base_url, href)
        if tag == "link" and "next" in ad.get("rel", "").lower():
            href = ad.get("href")
            if href:
                self.rel_next.append(urljoin(self.base_url, href))
        if tag == "meta":
            name = (ad.get("name") or ad.get("property") or "").lower()
            content = ad.get("content", "")
            if name in {"robots", "googlebot"}:
                self.meta_robots = content
            if name == "og:site_name":
                self.og_site_name = content
            if name == "og:title":
                self.og_title = content
            if name == "description":
                self.meta_description = content
                if content == "":
                    self.blank_meta.append("description")
            if name == "og:description":
                self.og_description = content
                if content == "":
                    self.blank_meta.append("og:description")
            if name in {"twitter:description", "twitter:title"}:
                if name == "twitter:description":
                    self.twitter_description = content
                if content == "":
                    self.blank_meta.append(name)
        if tag in {"button", "div", "span", "a"}:
            blob = (ad.get("class", "") + " " + ad.get("id", "")).lower()
            if re.search(r"load[- ]more|show[- ]more|infinite", blob) and tag != "a":
                self.load_more_js = True
            if tag == "a" and re.search(r"load[- ]more|show[- ]more", blob) and not ad.get("href"):
                self.load_more_js = True
        if ad.get("onclick") and tag in {"button", "div", "span"}:
            self.onclick_nav += 1
        if tag == "iframe":
            src = ad.get("src") or ad.get("data-src") or ""
            if src:
                self.iframes.append(urljoin(self.base_url, src))
        if tag == "a":
            href = ad.get("href", "").strip()
            label = (ad.get("aria-label") or ad.get("title") or "").strip()
            if href and not href.startswith(("javascript:",)):
                absu = urljoin(self.base_url, href)
                host = urlparse(absu).netloc.lower()
                if any(h in host for h in SOCIAL_HOSTS):
                    self.social_links.append(
                        {
                            "href": absu,
                            "host": host,
                            "aria": label,
                            "text": "",
                        }
                    )
                if href and href not in self._seen_href and not href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    self._seen_href.add(href)
                    if href.lower().endswith(".pdf") or "application/pdf" in ad.get("type", ""):
                        self.pdf_links.append(absu)
                    base_host = urlparse(self.base_url).netloc
                    if host and host.replace("www.", "") == base_host.replace("www.", ""):
                        self.internal_links.append(absu)
                        self.action_links.append(
                            {
                                "url": absu,
                                "label": label,
                            }
                        )
                        path = urlparse(absu).path.rstrip("/") or "/"
                        if path == "/":
                            self.has_home_href = True
                        q = urlparse(absu).query.lower()
                        if q and re.search(
                            r"f\.|filter|category|color|size|sort|collection", q
                        ):
                            self.filter_links.append(absu)
                    elif host:
                        self.external_links.append(absu)
        if tag == "img":
            self.img_count += 1
            alt = ad.get("alt")
            if alt is None or not str(alt).strip():
                self.img_missing_alt += 1
                if is_informational_img(ad):
                    self.img_no_alt_large += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "script" and self._in_ld:
            raw = "".join(self._ld_buf).strip()
            self._in_ld = False
            self._ld_buf = []
            if raw:
                try:
                    self.json_ld.append(json.loads(raw))
                except json.JSONDecodeError:
                    self.json_ld.append({"_invalid": True, "_raw_preview": raw[:180]})
            return
        if tag in SKIP_TAGS and self._skip:
            self._skip -= 1
            return
        if self._skip:
            return
        if tag == "title":
            self._in_title = False
        if tag == "h1":
            self._in_h1 = False
            if not self.h1:
                self.h1 = " ".join("".join(self._h1_buf).split())
        if tag in {"nav"} or tag == "header" or tag == "footer":
            if tag in {"nav"}:
                self._nav_depth = max(0, self._nav_depth - 1)
            elif tag == "header":
                self._header_depth = max(0, self._header_depth - 1)
            else:
                self._footer_depth = max(0, self._footer_depth - 1)
        if tag in {"article", "li"} and self._card_stack:
            card = self._card_stack.pop()
            if card.get("has_price"):
                self.priced_cards += 1

    def handle_data(self, data: str) -> None:
        if self._in_ld:
            self._ld_buf.append(data)
            return
        if self._skip:
            return
        if self._in_title:
            self.title_parts.append(data)
        if self._in_h1:
            self._h1_buf.append(data)
        text = data.strip()
        if text:
            self.text_parts.append(text)
            if self._card_stack and PRICE_RE.search(text):
                self._card_stack[-1]["has_price"] = True


def extract_page(url: str, html: str) -> dict[str, Any]:
    parser = PageParser(url)
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        pass
    while parser._card_stack:
        card = parser._card_stack.pop()
        if card.get("has_price"):
            parser.priced_cards += 1
    title = " ".join("".join(parser.title_parts).split())
    full_text = " ".join(parser.text_parts)
    words = [w for w in re.findall(r"[A-Za-z0-9']+", full_text)]
    html_l = html.lower()
    if SEARCH_RE.search(html):
        parser.has_search = True
    related = bool(RELATED_RE.search(full_text))
    loginish = bool(LOGIN_RE.search(full_text[:2500]) or LOGIN_RE.search(html_l[:4000]))
    cookish = bool(COOKIE_RE.search(full_text[:1500]))
    spa = False
    if parser.root_or_app and len(words) < 80:
        spa = True
    if re.search(r'<div id=["\'](root|app|__next)["\']', html, re.I) and len(words) < 80:
        spa = True
    if parser.script_count >= 8 and len(words) < 40:
        spa = True
    first = " ".join(words[:120])
    types = _schema_types(parser.json_ld)
    org = extract_org_nodes(parser.json_ld)
    hours_hit = HOURS_IDENTICAL_RE.search(full_text)
    action = []
    for a in parser.action_links[:40]:
        blob = (a.get("label") or "") + " " + a.get("url", "")
        if ACTION_RE.search(blob):
            action.append(a)
    unlabeled_social = 0
    for m in re.finditer(
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        html,
        re.I | re.S,
    ):
        href, inner = m.group(1), m.group(2)
        host = urlparse(urljoin(url, href)).netloc.lower()
        if not any(h in host for h in SOCIAL_HOSTS if h not in {"wikidata.org", "wikipedia.org", "crunchbase.com"}):
            continue
        textish = re.sub(r"<[^>]+>", "", inner)
        has_aria = bool(re.search(r'aria-label=|title=', m.group(0), re.I))
        if not textish.strip() and not has_aria:
            unlabeled_social += 1
    third_party = []
    for src in parser.iframes + parser.external_links[:40]:
        host = urlparse(src).netloc.lower()
        if any(t in host for t in THIRD_PARTY_MENU):
            third_party.append(src)
    return {
        "title": title,
        "h1": parser.h1,
        "word_count": len(words),
        "text": full_text[:20000],
        "first_words": first,
        "canonical": parser.canonical,
        "meta_robots": parser.meta_robots,
        "og_site_name": parser.og_site_name,
        "og_title": parser.og_title,
        "json_ld": parser.json_ld[:20],
        "schema_types": types,
        "has_speakable": _has_speakable(parser.json_ld),
        "internal_link_count": len(parser.internal_links),
        "external_link_count": len(parser.external_links),
        "internal_links": parser.internal_links[:80],
        "external_links": parser.external_links[:40],
        "pdf_links": parser.pdf_links[:20],
        "img_count": parser.img_count,
        "img_missing_alt": parser.img_missing_alt,
        "img_no_alt_large": parser.img_no_alt_large,
        "has_nav": parser.has_nav or parser.has_header,
        "has_main": parser.has_main,
        "has_footer": parser.has_footer,
        "has_breadcrumb": parser.has_breadcrumb,
        "has_search": parser.has_search,
        "has_related": related,
        "canvas": parser.canvas,
        "script_count": parser.script_count,
        "next_data": parser.next_data,
        "spa_shell": spa,
        "login_markers": loginish,
        "cookie_markers": cookish,
        "noindex": _is_noindex(parser.meta_robots),
        "meta_description": parser.meta_description,
        "org": org,
        "social_links": parser.social_links[:30],
        "unlabeled_social_count": unlabeled_social,
        "iframes": parser.iframes[:15],
        "action_links": action[:15],
        "identical_hours": hours_hit.group(0) if hours_hit else None,
        "third_party_menu": third_party[:8],
        "schema_caps": schema_capabilities(parser.json_ld),
        "visible_updated": bool(
            re.search(r"\b(last\s+updated|updated\s+on|published)\b", full_text[:4000], re.I)
        ),
        "faq_questionish": len(re.findall(r"\?", full_text[:8000])) >= 4
        or bool(re.search(r"\b(faq|frequently asked)\b", full_text[:3000], re.I)),
        "productish_text": bool(
            re.search(r"\b(add to cart|buy now|sku|in stock|out of stock)\b", full_text[:4000], re.I)
        ),
        "travelish_text": bool(
            HARD_TRAVEL_RE.search(full_text[:6000]) or IATA_PAIR_RE.search(full_text[:6000])
        ),
        "vehicleish_text": bool(
            re.search(
                r"\b(vin|mpg|fuel type|mileage|test drive|msrp|horsepower|dealership inventory)\b",
                full_text[:4000],
                re.I,
            )
        ),
        "phones": _phones(full_text[:8000]),
        "scale_claims": SCALE_CLAIM_RE.findall(full_text[:8000])[:8],
        "prices": [m.replace(",", "") for m in PRICE_RE.findall(full_text[:12000])][:20],
        "priced_card_count": parser.priced_cards,
        "blank_meta": parser.blank_meta[:8],
        "meta_description_missing": parser.meta_description is None,
        "twitter_description": parser.twitter_description,
        "rel_next": parser.rel_next[:5],
        "filter_links": parser.filter_links[:8],
        "has_home_href": parser.has_home_href,
        "load_more_js": parser.load_more_js
        or bool(re.search(r"load more|show more", full_text[:3000], re.I))
        and not parser.rel_next,
        "page_links": bool(re.search(r"[?&]page=\d+|rel=[\"']next", html, re.I)),
        "onclick_nav": parser.onclick_nav,
        "og_description": parser.og_description,
        "faq_pairs": extract_faq_heading_pairs(html),
        "faq_schema_answers": extract_faq_schema_answers(parser.json_ld),
        "has_faq_ui": page_has_faq_ui(html),
        "has_faq_section": page_has_faq_section_heading(html),
    }


def _schema_types(blocks: list[Any]) -> list[str]:
    found: set[str] = set()

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            t = obj.get("@type")
            if isinstance(t, str):
                found.add(t)
            elif isinstance(t, list):
                found.update(str(x) for x in t)
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for x in obj:
                walk(x)

    walk(blocks)
    return sorted(found)


def _has_speakable(blocks: list[Any]) -> bool:
    found = False

    def walk(obj: Any) -> None:
        nonlocal found
        if found:
            return
        if isinstance(obj, dict):
            if "speakable" in obj:
                found = True
                return
            t = obj.get("@type")
            if t == "SpeakableSpecification" or (isinstance(t, list) and "SpeakableSpecification" in t):
                found = True
                return
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for x in obj:
                walk(x)

    walk(blocks)
    return found


def _is_noindex(meta: str | None) -> bool:
    if not meta:
        return False
    return "noindex" in meta.lower()


def extract_org_nodes(blocks: list[Any]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            t = obj.get("@type")
            types = [t] if isinstance(t, str) else list(t or [])
            types_s = {str(x) for x in types}
            if types_s & ORG_TYPES or obj.get("sameAs"):
                same = obj.get("sameAs") or []
                if isinstance(same, str):
                    same = [same]
                nodes.append(
                    {
                        "types": sorted(types_s),
                        "name": obj.get("name"),
                        "sameAs": [str(x) for x in same if x],
                        "taxID": obj.get("taxID") or obj.get("vatID"),
                        "duns": obj.get("duns"),
                        "leiCode": obj.get("leiCode"),
                        "industry": obj.get("industry") or obj.get("naics") or obj.get("isicV4"),
                        "address": obj.get("address"),
                        "telephone": obj.get("telephone") or obj.get("phone"),
                    }
                )
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for x in obj:
                walk(x)

    walk(blocks)
    same_all: list[str] = []
    for n in nodes:
        same_all.extend(n.get("sameAs") or [])
    auth = [
        u
        for u in same_all
        if any(h in u.lower() for h in AUTHORITY_HOSTS)
    ]
    telephones = [
        str(n.get("telephone")).strip()
        for n in nodes
        if n.get("telephone") and str(n.get("telephone")).strip()
    ]
    local_types = {
        "LocalBusiness",
        "Restaurant",
        "Dentist",
        "Physician",
        "Store",
        "AutoDealer",
        "Hotel",
    }
    return {
        "count": len(nodes),
        "nodes": nodes[:8],
        "sameAs": same_all[:20],
        "authority_sameAs": auth[:12],
        "has_legal_id": any(n.get("taxID") or n.get("duns") or n.get("leiCode") for n in nodes),
        "has_industry": any(n.get("industry") for n in nodes),
        "has_address": any(_has_address(n.get("address")) for n in nodes),
        "has_complete_postal_address": any(
            _address_completeness(n.get("address")) == "complete" for n in nodes
        ),
        "has_telephone": bool(telephones),
        "telephones": telephones[:4],
        "is_local_entity": any(local_types & set(n.get("types") or []) for n in nodes),
        "has_maps_sameAs": any(MAPS_HOST_RE.search(u) for u in same_all),
        "has_wikidata": any("wikidata.org" in u.lower() for u in same_all),
    }


def _has_address(addr: Any) -> bool:
    return _address_completeness(addr) in {"partial", "complete"}


def _address_completeness(addr: Any) -> str:
    """none | partial | complete (street + locality/region for single-location NAP)."""
    if isinstance(addr, str) and len(addr.strip()) > 12:
        # Free-text NAP often includes street + city in one string.
        return "complete" if re.search(r"\d", addr) and len(addr.strip()) > 20 else "partial"
    if not isinstance(addr, dict):
        return "none"
    street = bool(addr.get("streetAddress"))
    locality = bool(addr.get("addressLocality") or addr.get("addressRegion"))
    country = bool(addr.get("addressCountry") or addr.get("postalCode"))
    if street and locality:
        return "complete"
    if locality or country or street:
        return "partial"
    return "none"


def _phones(text: str) -> list[str]:
    found = []
    for m in PHONE_RE.findall(text or ""):
        digits = re.sub(r"\D", "", m)
        if 10 <= len(digits) <= 13:
            found.append(digits)
    return list(dict.fromkeys(found))[:8]


def host_tier(url: str) -> str | None:
    u = (url or "").lower()
    if any(h in u for h in TIER1_REACH_HOSTS):
        return "tier1"
    if any(h in u for h in TIER0_PROFILE_HOSTS):
        return "tier0"
    return None


def collect_profile_urls(pages: list[dict[str, Any]]) -> dict[str, list[str]]:
    t0: list[str] = []
    t1: list[str] = []
    for p in pages:
        s = p.get("signals") or {}
        blobs: list[str] = []
        org = s.get("org") or {}
        for u in org.get("sameAs") or []:
            blobs.append(u)
        for item in s.get("social_links") or []:
            blobs.append(item.get("href") or "")
        for u in s.get("external_links") or []:
            blobs.append(u)
        for u in blobs:
            t = host_tier(u)
            if t == "tier1":
                t1.append(u)
            elif t == "tier0":
                t0.append(u)
    return {
        "tier0": list(dict.fromkeys(t0))[:15],
        "tier1": list(dict.fromkeys(t1))[:15],
    }


def merge_consensus_profiles(
    profiles: dict[str, list[str]], cons: dict[str, Any] | None
) -> dict[str, list[str]]:
    """Fold Wikipedia/Wikidata consensus hits into Tier-1 before FC-FRESH-04 decisions."""
    cons = cons or {}
    t0 = list(profiles.get("tier0") or [])
    t1 = list(profiles.get("tier1") or [])
    wiki = cons.get("wikipedia") or {}
    wd = cons.get("wikidata") or {}
    if not cons.get("identity_verified"):
        return {
            "tier0": list(dict.fromkeys(t0))[:15],
            "tier1": list(dict.fromkeys(t1))[:15],
        }
    page_url = wiki.get("page_url") if wiki.get("name_match") else None
    if page_url:
        t1.append(page_url)
    top_id = wd.get("top_id") if wd.get("name_match") else None
    if top_id:
        t1.append(f"https://www.wikidata.org/wiki/{top_id}")
    return {
        "tier0": list(dict.fromkeys(t0))[:15],
        "tier1": list(dict.fromkeys(t1))[:15],
    }


def infer_site_scale(pages: list[dict[str, Any]], consensus: dict[str, Any] | None = None) -> dict[str, Any]:
    """On-site signals + optional digital consensus — do not treat missing Wikipedia as an SMB defect.

    Authority sameAs (Wikidata, multi-social) OR strong off-site echo means NOT looks_small.
    Thin JS shells with rich meta are crawl_incomplete, not IANA placeholders.
    """
    claims: list[str] = []
    paths = " ".join((p.get("url") or "") for p in pages).lower()
    has_careers = any(x in paths for x in ("/careers", "/jobs", "/join-us"))
    has_press = any(x in paths for x in ("/press", "/newsroom", "/media"))
    has_investors = any(x in paths for x in ("/investors", "/investor", "/ir/"))
    phones: list[str] = []
    auth_hosts: list[str] = []
    has_wikidata = False
    total_words = 0
    rich_meta = False
    for p in pages:
        s = p.get("signals") or {}
        claims.extend(s.get("scale_claims") or [])
        phones.extend(s.get("phones") or [])
        total_words += int(s.get("word_count") or 0)
        meta = (s.get("meta_description") or s.get("og_description") or "").strip()
        if len(meta) >= 80:
            rich_meta = True
        org = s.get("org") or {}
        if org.get("has_wikidata"):
            has_wikidata = True
        for u in org.get("authority_sameAs") or org.get("sameAs") or []:
            low = (u or "").lower()
            for h in AUTHORITY_HOSTS:
                if h in low:
                    auth_hosts.append(h)
    claims = [c if isinstance(c, str) else " ".join(c) for c in claims]
    flat = []
    for c in claims:
        if isinstance(c, tuple):
            flat.append(next((x for x in c if x), ""))
        else:
            flat.append(str(c))
    flat = [x for x in flat if x]
    auth_n = len(set(auth_hosts))
    has_authority_graph = has_wikidata or auth_n >= 2
    cons = consensus or {}
    offsite = bool(cons.get("offsite_identity_strong"))
    cq = cons.get("crawl_quality") or {}
    looks_scaled = (
        bool(flat)
        or has_press
        or has_investors
        or (has_careers and len(pages) >= 8)
        or has_authority_graph
        or offsite
    )
    # True IANA-style placeholder only — not Apple-thin-shell.
    looks_placeholder = bool(cq.get("iana_placeholder")) or (
        total_words < 80
        and len(pages) <= 2
        and not has_authority_graph
        and not flat
        and not rich_meta
        and not offsite
        and not cq.get("crawl_incomplete")
    )
    looks_small = (
        not looks_scaled
        and not has_press
        and not has_authority_graph
        and not offsite
        and len(pages) <= 10
        and not looks_placeholder
        and not cq.get("crawl_incomplete")
    )
    return {
        "looks_small": looks_small,
        "looks_scaled": looks_scaled,
        "looks_placeholder": looks_placeholder,
        "crawl_incomplete": bool(cq.get("crawl_incomplete")),
        "offsite_identity_strong": offsite,
        "scale_claims": list(dict.fromkeys(flat))[:8],
        "has_careers": has_careers,
        "has_press": has_press,
        "has_investors": has_investors,
        "authority_sameAs_host_count": auth_n,
        "has_wikidata": has_wikidata,
        "page_count": len(pages),
        "phones": list(dict.fromkeys(phones))[:8],
        "total_word_count": total_words,
        "consensus_echo_score": cons.get("echo_score"),
        "consensus_platforms": cons.get("platforms_with_echo") or [],
    }


def classify_site_type(pages: list[dict[str, Any]], consensus: dict[str, Any] | None = None) -> str:
    types: set[str] = set()
    text = ""
    urls = []
    total_words = 0
    rich_meta = False
    for p in pages:
        s = p.get("signals") or {}
        types.update(s.get("schema_types") or [])
        text += " " + (s.get("text") or "")[:2000]
        text += " " + (s.get("meta_description") or "") + " " + (s.get("og_description") or "")
        urls.append(p.get("url") or "")
        total_words += int(s.get("word_count") or 0)
        meta = (s.get("meta_description") or s.get("og_description") or "").strip()
        if len(meta) >= 80:
            rich_meta = True
    blob = " ".join(urls).lower() + " " + text.lower()
    cons = consensus or {}
    cq = cons.get("crawl_quality") or {}
    if cq.get("iana_placeholder"):
        return "placeholder"
    if not pages:
        # Zero pages fetched (robots disallow, WAF block, or network failure) is not a placeholder site.
        summary_lower = str(cons.get("wikipedia", {}).get("summary_extract") or "").lower()
        if any(w in summary_lower for w in ("newspaper", "news", "journal", "publisher", "magazine", "media")):
            return "media"
        return "corporate"
    # Thin IANA-style placeholders only when meta is also empty.
    if (
        total_words < 80
        and 1 <= len(pages) <= 2
        and not rich_meta
        and not cons.get("offsite_identity_strong")
        and not (types & {"Product", "Offer", "LocalBusiness", "Organization", "Flight", "FAQPage"})
    ):
        return "placeholder"
    if any(t in types for t in ("Flight", "Airline", "Airport")) or re.search(
        r"\b(flights? from|book flights?|airlines?)\b", blob
    ):
        return "airline"
    if any(t in types for t in ("Car", "Vehicle")) or re.search(
        r"\b(dealership|new cars?|used cars?|vin |msrp)\b", blob
    ):
        return "automotive"
    if any(t in types for t in ("Product", "Offer", "ItemList")) or "add to cart" in blob:
        return "ecommerce"
    if any(t in types for t in ("TechArticle",)) or "/docs" in blob or "api reference" in blob:
        return "docs"
    if any(t in types for t in ("NewsArticle", "Article", "BlogPosting")) or "/blog" in blob:
        return "media"
    # Software/SaaS before local: "clinic management" is not a walk-in clinic.
    if (
        "/pricing" in blob
        or "start free trial" in blob
        or re.search(
            r"\b(saas|clinic management|practice management|appointment schedul|"
            r"for doctors|for clinics|software (?:for|platform)|book a demo|"
            r"sign up free|multi-?sided)\b",
            blob,
        )
    ):
        return "saas"
    local_schema = any(t in types for t in ("LocalBusiness", "Restaurant", "Dentist", "Hotel"))
    local_visit = bool(re.search(r"\b(hours|directions|visit us|opening hours)\b", blob))
    if local_schema or (
        local_visit
        and not re.search(r"\b(software|saas|platform|dashboard|for doctors)\b", blob)
    ):
        return "local"
    if cons.get("offsite_identity_strong") and (cq.get("crawl_incomplete") or total_words < 120):
        return "corporate"
    if types & {"Organization", "Corporation", "Brand"} and total_words >= 200:
        return "corporate"
    if rich_meta and total_words < 120:
        return "unknown"
    if total_words < 120:
        return "unknown"
    return "marketing"


def brand_token_ambiguous(title: str, h1: str, og_site: str | None) -> bool:
    raw = (og_site or h1 or title or "").strip()
    token = re.split(r"[\s|/–—-]+", raw)[0] if raw else ""
    token = re.sub(r"[^A-Za-z0-9]", "", token)
    generic = {
        "delta",
        "unity",
        "sage",
        "nova",
        "novatech",
        "pioneer",
        "jaguar",
        "ace",
        "apex",
        "pulse",
        "orbit",
        "mercury",
        "atlas",
        "summit",
        "aurora",
        "nexus",
        "vector",
        "horizon",
    }
    return token.lower() in generic


def schema_capabilities(blocks: list[Any]) -> dict[str, Any]:
    types: set[str] = set()
    flags = {
        "has_offer": False,
        "has_iata": False,
        "has_date_published": False,
        "has_date_modified": False,
        "has_opening_hours_spec": False,
        "has_postal_address": False,
        "has_author": False,
        "has_itemlist": False,
        "has_itemlist_elements": False,
    }

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            t = obj.get("@type")
            if isinstance(t, str):
                types.add(t)
            elif isinstance(t, list):
                types.update(str(x) for x in t)
            if obj.get("offers") is not None or t == "Offer" or (
                isinstance(t, list) and "Offer" in t
            ):
                flags["has_offer"] = True
            if obj.get("iataCode") or obj.get("iata"):
                flags["has_iata"] = True
            if obj.get("datePublished"):
                flags["has_date_published"] = True
            if obj.get("dateModified"):
                flags["has_date_modified"] = True
            if t == "OpeningHoursSpecification" or obj.get("openingHoursSpecification"):
                flags["has_opening_hours_spec"] = True
            if t == "PostalAddress" or obj.get("address"):
                flags["has_postal_address"] = True
            if obj.get("author"):
                flags["has_author"] = True
            if t == "ItemList" or (isinstance(t, list) and "ItemList" in t):
                flags["has_itemlist"] = True
            if obj.get("itemListElement") is not None:
                flags["has_itemlist_elements"] = True
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for x in obj:
                walk(x)

    walk(blocks)
    money = types & {
        "Product",
        "Offer",
        "Flight",
        "Airline",
        "Airport",
        "Car",
        "Vehicle",
        "FAQPage",
        "Article",
        "NewsArticle",
        "BlogPosting",
        "LocalBusiness",
        "Restaurant",
    }
    return {
        "types": sorted(types),
        "has_product": bool(types & {"Product", "IndividualProduct"}),
        "has_product_offer": bool(types & {"Product", "IndividualProduct"}) and flags["has_offer"],
        "has_flight": bool(types & {"Flight", "TouristTrip", "TravelAction"}),
        "has_airline": "Airline" in types,
        "has_airport": "Airport" in types,
        "has_vehicle": bool(types & {"Car", "Vehicle", "Motorcycle"}),
        "has_local": bool(
            types
            & {
                "LocalBusiness",
                "Restaurant",
                "Dentist",
                "Physician",
                "Store",
                "AutoDealer",
                "Hotel",
            }
        ),
        "has_article": bool(types & {"Article", "NewsArticle", "BlogPosting"}),
        "has_faq": "FAQPage" in types,
        "has_itemlist": flags.get("has_itemlist") or "ItemList" in types,
        "has_itemlist_elements": flags.get("has_itemlist_elements", False),
        "boilerplate_only": bool(types)
        and not money
        and bool(types & {"WebPage", "WebSite", "Organization", "Brand"}),
        **flags,
    }


def is_html_content_type(content_type: str | None, url: str = "", body: str = "") -> bool:
    """True only when the response is (or clearly is) HTML. Skip text/plain, markdown, JSON, etc."""
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct and HTML_CT_RE.match(ct):
        return True
    if ct and NON_HTML_CT_RE.match(ct):
        return False
    path = urlparse(url).path.lower()
    if path.endswith((".md", ".txt", ".json", ".pdf", ".csv", ".xml", ".yaml", ".yml")):
        return False
    head = (body or "").lstrip()[:200].lower()
    if head.startswith("<!doctype html") or head.startswith("<html"):
        return True
    # Missing/ambiguous Content-Type on extensionless URLs: assume HTML (normal sites).
    if not ct:
        return True
    return "html" in ct


def hard_travel_signal(url: str, signals: dict[str, Any] | None = None) -> bool:
    """Require a real travel token before treating a page as a flight/route surface."""
    signals = signals or {}
    path = urlparse(url).path.lower()
    if LEGAL_PATH_RE.search(path):
        return False
    if any(
        x in path
        for x in ("/flights", "/flight/", "book-flight", "/routes", "/timetable", "/pnr")
    ):
        return True
    types = set(signals.get("schema_types") or [])
    if types & {"Flight", "Airport", "Airline", "TouristTrip", "TravelAction"}:
        return True
    if signals.get("travelish_text"):
        return True
    blob = " ".join(
        [
            signals.get("title") or "",
            signals.get("h1") or "",
            (signals.get("text") or "")[:6000],
            " ".join(signals.get("schema_types") or []),
        ]
    )
    return bool(HARD_TRAVEL_RE.search(blob) or IATA_PAIR_RE.search(blob))


def hard_vehicle_signal(url: str, signals: dict[str, Any] | None = None) -> bool:
    """Strong vehicle/inventory proof — not 'car' in marketing copy alone."""
    signals = signals or {}
    path = urlparse(url).path.lower()
    if LEGAL_PATH_RE.search(path):
        return False
    if any(x in path for x in ("/inventory", "/vehicles", "/vehicle/", "/cars/", "/car/")):
        return True
    types = set(signals.get("schema_types") or [])
    if types & {"Car", "Vehicle", "MotorizedBicycle"}:
        return True
    blob = " ".join(
        [
            signals.get("title") or "",
            signals.get("h1") or "",
            (signals.get("text") or "")[:6000],
        ]
    )
    return bool(HARD_VEHICLE_RE.search(blob))


def hard_product_signal(url: str, signals: dict[str, Any] | None = None) -> bool:
    """PDP proof: product path or Product schema, plus buy/sku/stock language — never site_type alone."""
    signals = signals or {}
    path = urlparse(url).path.lower()
    if LEGAL_PATH_RE.search(path):
        return False
    if looks_like_collection(url, signals, allow_home=True):
        return False
    types = set(signals.get("schema_types") or [])
    path_ok = bool(HARD_PRODUCT_PATH_RE.search(path)) or any(
        x in path for x in ("/product/", "/products/", "/item/")
    )
    text_ok = bool(signals.get("productish_text"))
    schema_ok = bool(types & {"Product", "Offer", "IndividualProduct"})
    if path_ok and (text_ok or schema_ok):
        return True
    if schema_ok and text_ok:
        return True
    return False


def hard_faq_signal(url: str, signals: dict[str, Any] | None = None) -> bool:
    """FAQ only with FAQ path, FAQPage schema, or real accordion/FAQ-section Q&A — not '?' headlines."""
    signals = signals or {}
    path = urlparse(url).path.lower()
    if LEGAL_PATH_RE.search(path):
        return False
    types = set(signals.get("schema_types") or [])
    if "FAQPage" in types:
        return True
    pairs = signals.get("faq_pairs") or []
    nonempty = [p for p in pairs if not p.get("empty")]
    path_ok = bool(HARD_FAQ_PATH_RE.search(path))
    if path_ok and (signals.get("faq_questionish") or len(pairs) >= 2):
        return True
    # Require accordion/FAQ-section chrome before treating Q&A pairs as an FAQ page.
    # Bare news section fronts with question-style headlines must stay "general".
    faq_chrome = bool(
        signals.get("has_faq_ui")
        or signals.get("has_faq_section")
        or pairs  # pairs are only emitted when chrome/section was present at extract time
    )
    if faq_chrome and len(nonempty) >= 2:
        return True
    if faq_chrome and len(pairs) >= 3:
        return True
    return False


def hard_article_signal(url: str, signals: dict[str, Any] | None = None) -> bool:
    signals = signals or {}
    path = urlparse(url).path.lower()
    if LEGAL_PATH_RE.search(path):
        return False
    types = set(signals.get("schema_types") or [])
    if types & {"Article", "NewsArticle", "BlogPosting"}:
        return True
    return bool(HARD_ARTICLE_PATH_RE.search(path))


def hard_local_signal(
    url: str, signals: dict[str, Any] | None = None, *, site_type: str = ""
) -> bool:
    """LocalBusiness surface: NAP/hours proof on contact/home — not 'clinic' in SaaS copy."""
    signals = signals or {}
    path = urlparse(url).path.lower().rstrip("/") or "/"
    if LEGAL_PATH_RE.search(path):
        return False
    types = set(signals.get("schema_types") or [])
    local_types = types & {
        "LocalBusiness",
        "Restaurant",
        "Dentist",
        "Hotel",
        "Store",
        "Physician",
        "AutoDealer",
    }
    org = signals.get("org") or {}
    nap = bool(
        org.get("has_complete_postal_address")
        or (org.get("has_address") and (org.get("has_telephone") or signals.get("phones")))
    )
    hours = bool(org.get("has_opening_hours") or signals.get("identical_hours") is not None)
    path_ok = path in {"/", ""} or bool(HARD_LOCAL_PATH_RE.search(path))
    if local_types and (nap or hours or path_ok):
        return True
    if site_type == "local" and path_ok and (nap or hours or signals.get("phones")):
        return True
    return False


# Vertical page classes specialists may claim. Default is always "general".
PAGE_CLASSES = frozenset(
    {
        "flight",
        "product",
        "product_catalog",
        "faq",
        "local_business",
        "vehicle",
        "article",
        "general",
    }
)


def classify_page(
    url: str,
    signals: dict[str, Any] | None = None,
    *,
    site_type: str = "",
    role: str | None = None,
) -> str:
    """Which room is this? Strong proof only — if unsure, return general.

    Vertical specialists must call this and skip unless the class matches.
    Defaults to \"general\" (no vertical check) — never \"yes, probably\".
    """
    signals = signals or {}
    path = urlparse(url).path.lower().rstrip("/") or "/"
    if signals.get("non_html"):
        return "general"
    if not is_html_content_type(
        signals.get("content_type"),
        url,
        (signals.get("text") or "")[:200],
    ):
        return "general"
    if LEGAL_PATH_RE.search(path):
        return "general"

    # Order: most specific verticals first. First strong match wins.
    if hard_travel_signal(url, signals):
        return "flight"
    if hard_vehicle_signal(url, signals):
        return "vehicle"
    if looks_like_collection(url, signals, allow_home=True):
        return "product_catalog"
    if hard_product_signal(url, signals) or role == "product":
        # role==product alone is weak on marketing sites — still require product proof
        if hard_product_signal(url, signals):
            return "product"
    if hard_faq_signal(url, signals):
        return "faq"
    if hard_article_signal(url, signals):
        return "article"
    if hard_local_signal(url, signals, site_type=site_type):
        return "local_business"
    return "general"


def annotate_page_classes(snap: dict[str, Any]) -> list[dict[str, str]]:
    """Stamp each page with page_class and return a verbose-friendly log."""
    site_type = snap.get("site_type") or ""
    log: list[dict[str, str]] = []
    for p in snap.get("pages") or []:
        url = p.get("url") or ""
        sig = p.get("signals") or {}
        cls = classify_page(url, sig, site_type=site_type, role=p.get("role"))
        p["page_class"] = cls
        log.append({"url": url, "page_class": cls, "role": p.get("role") or ""})
    snap["page_classifications"] = log
    return log


def pages_of_class(snap: dict[str, Any], *classes: str) -> list[dict[str, Any]]:
    """Pages whose classify_page class is in classes. Skips non-matches entirely."""
    want = set(classes)
    if "page_classifications" not in snap:
        annotate_page_classes(snap)
    return [p for p in (snap.get("pages") or []) if (p.get("page_class") or "general") in want]


def guess_role(url: str, signals: dict[str, Any]) -> str:
    path = urlparse(url).path.lower().rstrip("/") or "/"
    if path == "/":
        return "home"
    if LEGAL_PATH_RE.search(path):
        return "legal"
    if any(x in path for x in ("/about", "/company", "/who-we-are")):
        return "about"
    if any(x in path for x in ("/pricing", "/plans", "/price")):
        return "pricing"
    if any(x in path for x in ("/faq", "/help", "/support", "/returns")):
        return "faq"
    if any(
        x in path
        for x in ("/flights", "/flight/", "book-flight", "/routes", "/timetable", "/pnr")
    ):
        return "flight"
    if any(x in path for x in ("/inventory", "/vehicles", "/vehicle", "/cars/", "/car/")):
        return "vehicle"
    # Listing grids before PDP URL patterns: a WooCommerce /shop/silk grid is not a product.
    if looks_like_collection(url, signals):
        return "collection"
    if any(x in path for x in ("/product", "/products/", "/item", "/p/")):
        return "product"
    if any(x in path for x in ("/blog", "/news", "/insights", "/articles")):
        return "blog"
    if "/contact" in path:
        return "contact"
    if any(x in path for x in ("/docs", "/documentation", "/api")):
        return "docs"
    types = signals.get("schema_types") or []
    if "Product" in types:
        return "product"
    if "FAQPage" in types:
        return "faq"
    if any(t in types for t in ("Flight", "TouristTrip")) and hard_travel_signal(url, signals):
        return "flight"
    if any(t in types for t in ("Car", "Vehicle")):
        return "vehicle"
    if any(t in types for t in ("Article", "BlogPosting", "NewsArticle")):
        return "blog"
    # travelish_text alone is not enough on compliance/docs surfaces — hard_travel_signal gates.
    if hard_travel_signal(url, signals) and signals.get("travelish_text"):
        # Prefer flight only when path/schema already lean travel, or airline-ish copy is strong.
        if classify_page_template(url, signals) == "flight":
            return "flight"
    return classify_page_template(url, signals)


def _plain(html_frag: str) -> str:
    return " ".join(TAG_STRIP_RE.sub(" ", html_frag or "").split())


def page_has_faq_ui(html: str) -> bool:
    """True only for real FAQ/accordion chrome — not a news headline that ends in '?'."""
    return bool(FAQ_UI_RE.search(html or ""))


def page_has_faq_section_heading(html: str) -> bool:
    for m in HEADING_RE.finditer(html or ""):
        q = _plain(m.group(2))
        if FAQ_SECTION_RE.search(q) and "?" not in q:
            return True
    return False


def answer_is_empty(text: str) -> bool:
    """True only when there is no extractable answer — short facts like '2h 15m' count.

    Do not use a raw character floor (that false-positives on duration/price answers).
    """
    cleaned = " ".join((text or "").split()).strip()
    if not cleaned:
        return True
    if ACCORDION_CHROME_RE.match(cleaned):
        return True
    # Need at least one alphanumeric token (digits alone OK: "₹499", "2h", "15m").
    tokens = re.findall(r"[A-Za-z0-9]+", cleaned)
    return len(tokens) == 0


def extract_faq_heading_pairs(html: str) -> list[dict[str, Any]]:
    """FAQ/accordion Q&A pairs only — never bare news headlines that end in '?'."""
    matches = list(HEADING_RE.finditer(html or ""))
    if not matches:
        return []
    has_ui = page_has_faq_ui(html)
    has_section = page_has_faq_section_heading(html)
    # Without accordion chrome or an FAQ section heading, "?" titles are journalism, not FAQs.
    if not has_ui and not has_section:
        return []
    in_faq_section = False
    pairs: list[dict[str, Any]] = []
    for i, m in enumerate(matches):
        level = int(m.group(1))
        q = _plain(m.group(2))
        if not q:
            continue
        if FAQ_SECTION_RE.search(q) and "?" not in q:
            in_faq_section = True
            continue
        # Inside an FAQ section: question marks OR long subheads. With only accordion UI
        # (no FAQ heading), require an actual "?" so random accordion labels stay out.
        if in_faq_section:
            is_question = q.rstrip().endswith("?") or (level >= 2 and len(q) > 12)
        elif has_ui:
            is_question = q.rstrip().endswith("?")
        else:
            is_question = False
        if not is_question:
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else len(html)
        body = _plain(html[m.end() : end])
        pairs.append(
            {
                "question": q[:240],
                "answer": body[:500],
                "empty": answer_is_empty(body),
            }
        )
    return pairs[:20]


def extract_faq_schema_answers(blocks: list[Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []

    def answer_text(ans: Any) -> str:
        if isinstance(ans, str):
            return ans
        if isinstance(ans, dict):
            t = ans.get("text") or ans.get("name") or ""
            if isinstance(t, list):
                return " ".join(str(x) for x in t)
            return str(t or "")
        return ""

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            t = obj.get("@type")
            types = {t} if isinstance(t, str) else set(t or [])
            if "Question" in types or obj.get("acceptedAnswer") is not None:
                q = obj.get("name") or obj.get("text") or ""
                ans = answer_text(obj.get("acceptedAnswer"))
                if q:
                    out.append({"question": str(q)[:240], "answer": ans[:500]})
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for x in obj:
                walk(x)

    walk(blocks)
    return out[:30]


def schema_covers_question(question: str, schema_answers: list[dict[str, str]]) -> bool:
    qn = re.sub(r"\W+", " ", (question or "").lower()).strip()
    if not qn:
        return False
    q_tokens = set(qn.split())
    for row in schema_answers:
        sn = re.sub(r"\W+", " ", (row.get("question") or "").lower()).strip()
        ans = row.get("answer") or ""
        if not sn or answer_is_empty(ans):
            continue
        s_tokens = set(sn.split())
        if not q_tokens or not s_tokens:
            continue
        overlap = len(q_tokens & s_tokens) / max(1, len(q_tokens))
        if overlap >= 0.5 or qn in sn or sn in qn:
            return True
    return False


def local_geo_disambiguated(
    org: dict[str, Any],
    profiles: dict[str, list[str]],
    page_phones: list[str],
) -> bool:
    """Single-location LocalBusiness: street NAP + phone beats global sameAs count."""
    complete = bool(org.get("has_complete_postal_address"))
    partial = bool(org.get("has_address"))
    if not (complete or partial):
        return False
    if not (org.get("is_local_entity") or complete or partial):
        return False
    phone_ok = bool(org.get("has_telephone") or page_phones)
    if not phone_ok:
        return False
    # Complete street + locality + phone is enough (Krishna Dental / Novatech contrast).
    if complete:
        return True
    t0 = profiles.get("tier0") or []
    maps_ok = bool(org.get("has_maps_sameAs")) or any(
        MAPS_HOST_RE.search(u)
        or "justdial.com" in u.lower()
        or "yelp.com" in u.lower()
        for u in t0
    )
    return bool(partial and maps_ok)


def looks_like_collection(url: str, signals: dict[str, Any], *, allow_home: bool = False) -> bool:
    """Catalog grid: each repeated card must carry its own price — not nav lists + a stray rupee.

    Page-level PRICE_RE hits (legal SMS rates, shipping notes) must not AND with unpriced
    <li> city/specialty lists. PDPs with Product+Offer stay products.
    """
    path = urlparse(url).path.lower().rstrip("/") or "/"
    if LEGAL_PATH_RE.search(path):
        return False
    if path == "/" and not allow_home:
        return False
    caps = signals.get("schema_caps") or {}
    cards = int(signals.get("priced_card_count") or 0)
    if caps.get("has_product_offer") and signals.get("productish_text"):
        return False
    if cards >= 4:
        return True
    if cards >= 2 and is_collection_url(url):
        return True
    return False


def is_collection_url(url: str) -> bool:
    path = urlparse(url).path.lower().rstrip("/")
    parts = [p for p in path.split("/") if p]
    hints = (
        "/collections/",
        "/collection/",
        "/category/",
        "/categories/",
        "/product-category/",
        "/product_category/",
        "/catalog",
        "/c/",
    )
    if any(x in path for x in hints):
        return True
    if parts and parts[0] in {"shop", "products", "collections", "category", "catalog"} and len(parts) <= 2:
        # /products/foo-sku is often a PDP (2 parts). Treat 1-part index as collection.
        return len(parts) == 1
    return False


def classify_page_template(url: str, signals: dict[str, Any]) -> str:
    path = urlparse(url).path.lower().rstrip("/") or "/"
    if path == "/":
        return "home"
    if looks_like_collection(url, signals):
        return "collection"
    if signals.get("productish_text"):
        return "product"
    # Hard travel tokens required — a11y/VPAT copy with bare "departure" must not become flight.
    if hard_travel_signal(url, signals):
        return "flight"
    if signals.get("vehicleish_text"):
        return "vehicle"
    if signals.get("faq_questionish"):
        return "faq"
    return "other"
