#!/usr/bin/env python3
"""Offline smoke tests: SPA, Apple-like schema, collection ItemList, blank meta."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from compose_report import compose
from consensus import apply_identity_guard, names_overlap
from htmlutil import classify_site_type, extract_page, guess_role


def _snap(url: str, html: str, **extra) -> dict:
    sig = extract_page(url, html)
    out = {
        "start": url,
        "origin": "https://example.test",
        "site": "example.test",
        "site_type": extra.get("site_type", "marketing"),
        "robots": {"status": 200, "preview": "User-agent: *\nAllow: /", "ai_bots": {}},
        "sitemap": {"status": extra.get("sitemap_status", 200)},
        "llms_txt": {"status": 404, "bytes": 0},
        "pages": [
            {
                "url": url,
                "status": 200,
                "role": guess_role(url, sig),
                "signals": sig,
                "waf_hint": False,
            }
        ],
        "action_status": [],
        "ai_ua_probes": [],
        "facet_pairs": extra.get("facet_pairs") or [],
        "third_party_prices": [],
        "limitations": {},
    }
    if extra.get("site"):
        out["site"] = extra["site"]
        out["origin"] = extra.get("origin") or f"https://{extra['site']}"
    for item in extra.get("extra_pages") or []:
        u = item["url"]
        s = extract_page(u, item["html"])
        out["pages"].append(
            {
                "url": u,
                "status": 200,
                "role": guess_role(u, s),
                "signals": s,
                "waf_hint": False,
            }
        )
    if "digital_consensus" in extra:
        out["digital_consensus"] = extra["digital_consensus"]
    return out


EMPTY = """<!doctype html><html><head><title>Resume</title></head>
<body><div id="root"></div><script src="/app.js"></script></body></html>"""

APPLEISH = """<!doctype html><html><head>
<title>Acme Outdoors</title>
<meta name="description" content="Outdoor gear.">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Organization","name":"Acme Outdoors",
 "url":"https://example.test/",
 "sameAs":["https://www.wikidata.org/entity/Q312","https://www.linkedin.com/company/acme",
           "https://www.youtube.com/acme"]}
</script></head>
<body><header><nav><a href="/">Home</a><a href="/about">About</a></nav></header>
<main><h1>Acme Outdoors</h1>
<p>We make trail shoes and packs for hikers. Established 1998. Shop waterproof shells,
sleeping bags, and the Trail Runner Pro. Contact us at support@acme.test.
More copy so crawlers see a real document instead of an empty application shell.
More copy so crawlers see a real document instead of an empty application shell.
More copy so crawlers see a real document instead of an empty application shell.</p>
</main></body></html>"""

# Non-Shopify listing URL (/shop/silk) with a priced grid and no ItemList.
COLLECTION = """<!doctype html><html><head>
<title>Silk scarves</title>
<meta name="description" content="Silk scarves in stock.">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Organization","name":"Acme Shop"}
</script></head>
<body><main><h1>Silk scarves</h1>
<article><a href="/p/a">A</a> ₹1200</article>
<article><a href="/p/b">B</a> ₹2400</article>
<article><a href="/p/c">C</a> ₹3600</article>
<article><a href="/p/d">D</a> ₹4800</article>
</main></body></html>"""

COLLECTION_WITH_LIST = """<!doctype html><html><head>
<title>Silk scarves</title>
<meta name="description" content="Silk scarves in stock.">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"ItemList","itemListElement":[
  {"@type":"ListItem","position":1,"item":{"@type":"Product","name":"A","offers":{"@type":"Offer","price":"1200"}}},
  {"@type":"ListItem","position":2,"item":{"@type":"Product","name":"B","offers":{"@type":"Offer","price":"2400"}}}
]}
</script></head>
<body><main><h1>Silk scarves</h1>
<article><a href="/p/a">A</a> ₹1200</article>
<article><a href="/p/b">B</a> ₹2400</article>
<article><a href="/p/c">C</a> ₹3600</article>
<article><a href="/p/d">D</a> ₹4800</article>
</main></body></html>"""

# PDP with Product+Offer plus a related-product strip (must not be FC-FRESH-05).
PDP = """<!doctype html><html><head>
<title>Trail Runner</title>
<meta name="description" content="Trail Runner Pro.">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Product","name":"Trail Runner Pro",
 "offers":{"@type":"Offer","price":"129.99","priceCurrency":"USD"}}
</script></head>
<body><main><h1>Trail Runner Pro</h1>
<p>SKU TRP3. In stock. Add to cart. $129.99</p>
<article>Related one $10</article>
<article>Related two $20</article>
<article>Related three $30</article>
<article>Related four $40</article>
</main></body></html>"""

TWITTER_ONLY = """<!doctype html><html><head>
<title>Acme Outdoors</title>
<meta name="description" content="Outdoor gear.">
<meta name="twitter:description" content="">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Organization","name":"Acme Outdoors",
 "url":"https://example.test/",
 "sameAs":["https://www.wikidata.org/entity/Q312","https://www.linkedin.com/company/acme",
           "https://www.youtube.com/acme"]}
</script></head>
<body><header><nav><a href="/">Home</a></nav></header>
<main><h1>Acme Outdoors</h1>
<p>We make trail shoes and packs for hikers. Established 1998. Shop waterproof shells,
sleeping bags, and the Trail Runner Pro. Contact us at support@acme.test.
More copy so crawlers see a real document instead of an empty application shell.
More copy so crawlers see a real document instead of an empty application shell.
More copy so crawlers see a real document instead of an empty application shell.</p>
</main></body></html>"""

ALL_BLANK_META = """<!doctype html><html><head>
<title>Acme Outdoors</title>
<meta name="description" content="">
<meta property="og:description" content="">
<meta name="twitter:description" content="">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Organization","name":"Acme Outdoors",
 "sameAs":["https://www.wikidata.org/entity/Q312","https://www.linkedin.com/company/acme"]}
</script></head>
<body><header><nav><a href="/">Home</a></nav></header>
<main><h1>Acme Outdoors</h1>
<p>We make trail shoes and packs for hikers. Established 1998. Shop waterproof shells,
sleeping bags, and the Trail Runner Pro. Contact us at support@acme.test.
More copy so crawlers see a real document instead of an empty application shell.
More copy so crawlers see a real document instead of an empty application shell.
More copy so crawlers see a real document instead of an empty application shell.</p>
</main></body></html>"""

FAQ = """<!doctype html><html><head>
<title>Help</title>
<meta name="description" content="Common questions.">
</head>
<body><main><h1>FAQ</h1>
<p>Frequently asked questions about shipping?</p>
<p>How long does delivery take?</p>
<p>Can I return an unused item?</p>
<p>Do you ship internationally?</p>
<p>What is your warranty period?</p>
</main></body></html>"""

# Akasa-style: templated route page with empty FAQ accordion headings (ENG-04).
EMPTY_FAQ = """<!doctype html><html><head>
<title>Flights from Delhi to Mumbai</title>
<meta name="description" content="Delhi to Mumbai flights on Acme Air.">
</head>
<body><main>
<h1>Delhi to Mumbai</h1>
<p>Direct flights from DEL to BOM take about 2 hours. Affordable Fares section with city facts.</p>
<h2>Frequently Asked Questions</h2>
<h3>How long does a flight from Delhi to Mumbai take?</h3>
<h3>What is the ticket price from Delhi to Mumbai?</h3>
<h3>Is there a direct flight from Delhi to Mumbai?</h3>
</main></body></html>"""

# Short answers must NOT trip ENG-04 (threshold bug fix).
SHORT_FAQ = """<!doctype html><html><head>
<title>Flights from Delhi to Mumbai</title>
<meta name="description" content="Delhi to Mumbai flights.">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
  {"@type":"Question","name":"How long does a flight from Delhi to Mumbai take?",
   "acceptedAnswer":{"@type":"Answer","text":"2h 15m"}}
]}
</script></head>
<body><main>
<h1>Delhi to Mumbai</h1>
<h2>Frequently Asked Questions</h2>
<h3>How long does a flight from Delhi to Mumbai take?</h3>
<p>2h 15m</p>
<h3>What is the ticket price from Delhi to Mumbai?</h3>
<p>₹4,999</p>
</main></body></html>"""

# Schema-backed accordion: empty HTML bodies but FAQPage answers → no ENG-04.
SCHEMA_FAQ = """<!doctype html><html><head>
<title>Help</title>
<meta name="description" content="Help.">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
  {"@type":"Question","name":"How long does delivery take?",
   "acceptedAnswer":{"@type":"Answer","text":"3-5 business days"}},
  {"@type":"Question","name":"Can I return an unused item?",
   "acceptedAnswer":{"@type":"Answer","text":"Yes within 30 days"}}
]}
</script></head>
<body><main>
<h2>Frequently Asked Questions</h2>
<h3>How long does delivery take?</h3>
<h3>Can I return an unused item?</h3>
</main></body></html>"""

# Local clinic with complete NAP — must not demand Wikidata via FC-ENT-02 high.
LOCAL_CLINIC = """<!doctype html><html><head>
<title>Krishna Dental Care | Dental Clinic | NSK House, F. C. Road, Pune</title>
<meta name="description" content="Dental clinic in Deccan Gymkhana, Pune.">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Dentist","name":"Krishna Dental Care",
 "telephone":"+91 20 1234 5678",
 "address":{"@type":"PostalAddress","streetAddress":"NSK House 917/20A, F. C. Road",
  "addressLocality":"Pune","addressRegion":"MH","addressCountry":"IN","postalCode":"411004"},
 "sameAs":["https://maps.google.com/?cid=123"]}
</script></head>
<body><header><nav><a href="/">Home</a></nav></header>
<main><h1>Krishna Dental Care</h1>
<p>Single-location clinic at NSK House 917/20A, F. C. Road, Deccan Gymkhana, Pune. Call +91 20 1234 5678.
We provide fillings, root canals, and whitening. Established 2008. Visit us for appointments.</p>
</main></body></html>"""

# Tiny 2-product category URL without ItemList.
TINY_CATALOG = """<!doctype html><html><head>
<title>Rings</title>
<meta name="description" content="Two rings.">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Organization","name":"Baleen Lab"}
</script></head>
<body><main><h1>Rings</h1>
<article><a href="/p/1">Thin band</a> $120</article>
<article><a href="/p/2">Wide band</a> $180</article>
</main></body></html>"""

# Homepage merchandising grid (not /collections/) without ItemList.
HOME_GRID = """<!doctype html><html><head>
<title>Shop</title>
<meta name="description" content="Shop home.">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Organization","name":"Baleen Lab"}
</script></head>
<body><main><h1>Featured</h1>
<article>One $10</article>
<article>Two $20</article>
<article>Three $30</article>
<article>Four $40</article>
<article>Five $50</article>
</main></body></html>"""

# Legal page: many unpriced <li> lists + one incidental currency mention — not a catalog.
TERMS_LEGAL = """<!doctype html><html><head>
<title>Terms and Conditions</title>
<meta name="description" content="Subscription agreement and terms of use for the clinic software.">
</head>
<body>
<main>
<h1>Terms and Conditions</h1>
<p>This is a dense legal subscription agreement. Add on SMS can be availed @ 25 paise per SMS.
More legal copy. More legal copy. More legal copy. More legal copy. More legal copy.</p>
<ul>
<li>Delhi</li><li>Mumbai</li><li>Pune</li><li>Bengaluru</li><li>Hyderabad</li>
<li>Chennai</li><li>Kolkata</li><li>Ahmedabad</li><li>Jaipur</li><li>Lucknow</li>
<li>Indore</li><li>Nagpur</li><li>Surat</li><li>Patna</li><li>Bhopal</li>
<li>Vadodara</li><li>Ghaziabad</li><li>Ludhiana</li><li>Agra</li><li>Nashik</li>
<li>Faridabad</li><li>Meerut</li><li>Rajkot</li>
</ul>
<ul>
<li>Dentist</li><li>Physician</li><li>Pediatrician</li><li>Dermatologist</li>
<li>Orthopedic</li><li>Gynecologist</li><li>ENT</li><li>Cardiologist</li>
<li>Neurologist</li><li>Psychiatrist</li><li>Urologist</li><li>Oncologist</li>
<li>Gastroenterologist</li><li>Ophthalmologist</li>
</ul>
</main></body></html>"""

# Homepage with footer socials and no Organization JSON-LD.
FOOTER_SOCIAL = """<!doctype html><html><head>
<title>KiviHealth</title>
<meta name="description" content="Clinic management and appointment scheduling SaaS for doctors and clinics. Book a demo.">
</head>
<body>
<header><nav><a href="/">Home</a><a href="/pricing">Pricing</a></nav></header>
<main>
<h1>KiviHealth</h1>
<p>Clinic management software and appointment scheduling for doctors. Book a demo of the SaaS platform.
Sign up free. Practice management dashboard. More copy so this is not an empty shell.
More copy so this is not an empty shell. More copy so this is not an empty shell.</p>
</main>
<footer>
<a href="https://www.facebook.com/JioKiviHealth">Facebook</a>
<a href="https://x.com/JioKiviHealth">X</a>
<a href="https://www.linkedin.com/company/jiokivihealth">LinkedIn</a>
<a href="https://www.instagram.com/jiokivihealth">Instagram</a>
</footer>
</body></html>"""

# Thin JS shell that still has marketing meta — Gemini/Apple-class incomplete crawl.
THIN_CORP = """<!doctype html><html><head>
<title>Gemini</title>
<meta name="description" content="Google Gemini is a family of multimodal models from Google DeepMind designed for reasoning, coding, and multimodal understanding across products.">
</head>
<body><div id="root"></div><script src="/app.js"></script>
<script src="/chunk.js"></script>
<script src="/vendor.js"></script>
<script src="/runtime.js"></script>
</body></html>"""

GEMINI_CONSENSUS = {
    "brand_query": "Gemini",
    "crawl_quality": {
        "crawl_incomplete": True,
        "iana_placeholder": False,
        "note": "thin body with rich meta",
    },
    "wikipedia": {
        "titles": ["Gemini (language model)"],
        "summary_title": "Gemini (language model)",
        "page_url": "https://en.wikipedia.org/wiki/Gemini_(language_model)",
        "summary_extract": "Gemini is a family of large language models developed by Google DeepMind.",
        "page_type": "standard",
        "hits": [
            {
                "title": "Gemini (language model)",
                "url": "https://en.wikipedia.org/wiki/Gemini_(language_model)",
                "summary_extract": "Gemini is a family of large language models developed by Google DeepMind.",
                "page_type": "standard",
            }
        ],
    },
    "wikidata": {
        "top_id": "Q124650356",
        "top_label": "Gemini (language model)",
        "top_description": "family of large language models by Google",
        "entities": [
            {
                "id": "Q124650356",
                "label": "Gemini (language model)",
                "description": "family of large language models by Google DeepMind",
            }
        ],
    },
    "duckduckgo": {"abstract": "Gemini is a family of AI models by Google.", "heading": "Gemini"},
    "reddit": {"result_count": 2},
    "echo_score": 4,
    "offsite_identity_strong": True,
    "platforms_with_echo": ["wikipedia", "wikidata", "duckduckgo", "reddit"],
}

# Live failure mode: opensearch returns dab page + zodiac Wikidata — must not become sameAs.
GEMINI_DISAMBIG_CONSENSUS = {
    "brand_query": "Gemini",
    "crawl_quality": {
        "crawl_incomplete": True,
        "iana_placeholder": False,
        "note": "thin body with rich meta",
    },
    "wikipedia": {
        "titles": ["Gemini"],
        "summary_title": "Gemini",
        "page_url": "https://en.wikipedia.org/wiki/Gemini",
        "summary_extract": "Gemini may refer to: Gemini (constellation), Google Gemini, ...",
        "page_type": "disambiguation",
        "hits": [
            {
                "title": "Gemini",
                "url": "https://en.wikipedia.org/wiki/Gemini",
                "summary_extract": "Gemini may refer to: Gemini (constellation), Google Gemini, ...",
                "page_type": "disambiguation",
            }
        ],
    },
    "wikidata": {
        "top_id": "Q8923",
        "top_label": "Gemini",
        "top_description": "constellation of the zodiac",
        "entities": [
            {"id": "Q8923", "label": "Gemini", "description": "constellation of the zodiac"}
        ],
    },
    "duckduckgo": {"heading": "Gemini", "abstract": "A zodiac sign."},
    "reddit": {"result_count": 0},
    "echo_score": 2,
    "offsite_identity_strong": True,
    "platforms_with_echo": ["wikipedia", "wikidata"],
}

KIVI = """<!doctype html><html><head>
<title>KiviHealth | Clinic management software</title>
<meta property="og:site_name" content="KiviHealth">
<meta name="description" content="KiviHealth is an Indian clinic-management and appointment-scheduling SaaS platform for doctors and clinics.">
</head>
<body>
<header><nav><a href="/">Home</a><a href="/aboutus">About</a><a href="/doctor/login">Log in</a>
<a href="/pricing">Pricing</a></nav></header>
<main>
<h1>KiviHealth</h1>
<p>Clinic management software and appointment scheduling for doctors. Book a demo of the SaaS platform.
Sign up free. Multi-sided marketplace connecting clinics and patients. Practice management dashboard.</p>
<p>More copy so this is not an empty shell. More copy so this is not an empty shell.
More copy so this is not an empty shell. More copy so this is not an empty shell.</p>
</main></body></html>"""

NEMOURS_CONSENSUS = {
    "brand_query": "KiviHealth",
    "crawl_quality": {"crawl_incomplete": False, "iana_placeholder": False},
    "wikipedia": {
        "titles": ["Nemours Foundation"],
        "summary_title": "Nemours Foundation",
        "page_url": "https://en.wikipedia.org/wiki/Nemours_Foundation",
        "hits": [{"title": "Nemours Foundation", "url": "https://en.wikipedia.org/wiki/Nemours_Foundation"}],
    },
    "wikidata": {
        "top_id": "Q6991402",
        "top_label": "Nemours Foundation",
        "entities": [{"id": "Q6991402", "label": "Nemours Foundation", "description": "pediatric hospital"}],
    },
    "duckduckgo": {"heading": "Nemours Foundation", "abstract": "A children's health system."},
    "reddit": {"result_count": 0},
    "echo_score": 3,
    "offsite_identity_strong": True,
    "platforms_with_echo": ["wikipedia", "wikidata", "duckduckgo"],
}

STRIPEISH = """<!doctype html><html><head>
<title>Stripe | Payment infrastructure</title>
<meta name="description" content="Stripe is a financial infrastructure platform for businesses. Millions of companies use Stripe to accept payments and manage their businesses online.">
<script id="__NEXT_DATA__" type="application/json">{"props":{"pageProps":{}}}</script>
</head>
<body><div id="__next">
<header><nav><a href="/">Home</a><a href="/docs">Docs</a></nav></header>
<main><h1>Payments infrastructure for the internet</h1>
<p>Stripe builds payments software for platforms and marketplaces. Start a free trial of the SaaS APIs.
More copy so crawlers see a real document instead of an empty application shell.
More copy so crawlers see a real document instead of an empty application shell.</p>
</main></div>
<script src="/a.js"></script><script src="/b.js"></script><script src="/c.js"></script>
<script src="/d.js"></script></body></html>"""

ABOUT_THIN = """<!doctype html><html><head><title>About us</title>
<meta name="description" content="About the company."></head>
<body><header><nav><a href="/">Home</a><a href="/doctor/login">Log in</a></nav></header>
<main><h1>About us</h1><p>We build software.</p></main></body></html>"""

LOGIN_THIN = """<!doctype html><html><head><title>Doctor login</title></head>
<body><h1>Log in</h1><form><input type="password" name="password"><button>Sign in</button></form>
</body></html>"""


def main() -> int:
    empty_report = compose(_snap("https://example.test/", EMPTY, sitemap_status=200))
    empty_ids = {f["id"] for f in empty_report["findings"]}
    apple_report = compose(_snap("https://example.test/", APPLEISH))
    apple_ids = {f["id"] for f in apple_report["findings"]}
    apple_sev = {f["id"]: f["severity"] for f in apple_report["findings"]}
    apple_scale = apple_report.get("site_scale") or {}

    coll_url = "https://example.test/shop/silk"
    coll = compose(_snap(coll_url, COLLECTION, site_type="ecommerce"))
    coll_ids = {f["id"] for f in coll["findings"]}
    coll_role = _snap(coll_url, COLLECTION)["pages"][0]["role"]
    listed = compose(_snap(coll_url, COLLECTION_WITH_LIST, site_type="ecommerce"))
    listed_ids = {f["id"] for f in listed["findings"]}
    pdp = compose(_snap("https://example.test/products/trail-runner", PDP, site_type="ecommerce"))
    pdp_ids = {f["id"] for f in pdp["findings"]}
    tw = compose(_snap("https://example.test/", TWITTER_ONLY))
    tw_sev = {f["id"]: f["severity"] for f in tw["findings"]}
    blank = compose(_snap("https://example.test/", ALL_BLANK_META))
    blank_sev = {f["id"]: f["severity"] for f in blank["findings"]}
    faq = compose(_snap("https://example.test/help", FAQ))
    faq_ids = {f["id"] for f in faq["findings"]}

    empty_faq = compose(
        _snap("https://example.test/flights/delhi-mumbai", EMPTY_FAQ, site_type="airline")
    )
    empty_faq_ids = {f["id"] for f in empty_faq["findings"]}
    short_faq = compose(
        _snap("https://example.test/flights/delhi-mumbai", SHORT_FAQ, site_type="airline")
    )
    short_faq_ids = {f["id"] for f in short_faq["findings"]}
    schema_faq = compose(_snap("https://example.test/help", SCHEMA_FAQ))
    schema_faq_ids = {f["id"] for f in schema_faq["findings"]}

    clinic = compose(_snap("https://example.test/", LOCAL_CLINIC, site_type="local"))
    clinic_ids = {f["id"] for f in clinic["findings"]}
    clinic_sev = {f["id"]: f["severity"] for f in clinic["findings"]}

    tiny = compose(
        _snap("https://example.test/product-category/rings", TINY_CATALOG, site_type="ecommerce")
    )
    tiny_ids = {f["id"] for f in tiny["findings"]}
    home_grid = compose(_snap("https://example.test/", HOME_GRID, site_type="ecommerce"))
    home_ids = {f["id"] for f in home_grid["findings"]}

    gemini_snap = _snap(
        "https://gemini.google.com/",
        THIN_CORP,
        site="gemini.google.com",
        site_type="corporate",
        digital_consensus=GEMINI_CONSENSUS,
    )
    gemini = compose(gemini_snap)
    gemini_dab_snap = _snap(
        "https://gemini.google.com/",
        THIN_CORP,
        site="gemini.google.com",
        site_type="corporate",
        digital_consensus=GEMINI_DISAMBIG_CONSENSUS,
    )
    gemini_dab = compose(gemini_dab_snap)
    gemini_dab_guard = apply_identity_guard("Gemini", GEMINI_DISAMBIG_CONSENSUS, gemini_dab_snap)
    gemini_ids = {f["id"] for f in gemini["findings"]}
    gemini_actions = {
        f["id"]: (f.get("suggested_action") or {}).get("summary") or ""
        for f in gemini["findings"]
    }

    errors = []
    if "problems" in empty_report:
        errors.append("report must not include duplicate problems[]")
    if "CRA-02" not in empty_ids:
        errors.append(f"empty SPA should fire CRA-02, got {empty_ids}")
    if "FC-ENT-01" not in empty_ids:
        errors.append(f"empty SPA should fire FC-ENT-01, got {empty_ids}")
    empty_ent = next((f for f in empty_report["findings"] if f["id"] == "FC-ENT-01"), None)
    if empty_ent and empty_ent.get("severity") in {"high", "critical"}:
        errors.append(
            f"empty SPA FC-ENT-01 must be low-confidence/medium, got severity={empty_ent.get('severity')}"
        )
    empty_note = (empty_ent or {}).get("confidence_note") or ""
    if empty_ent and "low-confidence" not in empty_note.lower() and "thin" not in empty_note.lower():
        errors.append(f"empty SPA FC-ENT-01 needs confidence_note, got {empty_note!r}")
    empty_lim = ((empty_report.get("limitations") or {}).get("crawl_incomplete") or "")
    if "thin" not in empty_lim.lower() and "low-confidence" not in empty_lim.lower():
        errors.append(f"empty SPA report must include crawl_incomplete limitation, got {empty_lim!r}")
    empty_meta = next((f for f in empty_report["findings"] if f["id"] == "FC-FRESH-06"), None)
    if empty_meta and empty_meta.get("severity") in {"high", "critical"}:
        errors.append(
            f"empty SPA FC-FRESH-06 must not be confirmed high, got {empty_meta.get('severity')}"
        )
    helmet = compose(
        _snap(
            "https://portfolio.netlify.app/",
            EMPTY,
            sitemap_status=404,
            site="portfolio.netlify.app",
        )
    )
    helmet_ent = next((f for f in helmet["findings"] if f["id"] == "FC-ENT-01"), None)
    if not helmet_ent:
        errors.append("Helmet/Netlify empty shell should still fire FC-ENT-01")
    elif helmet_ent.get("severity") in {"high", "critical"}:
        errors.append(
            f"Helmet SPA without sitemap must not treat missing schema as confirmed, got {helmet_ent.get('severity')}"
        )
    helmet_lim = ((helmet.get("limitations") or {}).get("crawl_incomplete") or "")
    if "thin" not in helmet_lim.lower() and "low-confidence" not in helmet_lim.lower():
        errors.append(f"Helmet SPA must surface crawl_incomplete limitation, got {helmet_lim!r}")
    if apple_sev.get("FC-ENT-03") in {"high", "critical"}:
        errors.append("Apple-like schema must not get high FC-ENT-03")
    if "CRA-02" in apple_ids:
        errors.append("Apple-like HTML must not fire empty-shell CRA-02")
    if apple_scale.get("looks_small") is True:
        errors.append(f"Apple-like authority sameAs must not look_small, got {apple_scale}")
    if "FC-PROACT-02" in apple_ids:
        errors.append("Apple-like site must not get SMB Wikipedia proactive FC-PROACT-02")
    if coll_role != "collection":
        errors.append(f"/shop/silk grid should be role=collection, got {coll_role}")
    if "FC-FRESH-05" not in coll_ids:
        errors.append(f"priced collection without ItemList should fire FC-FRESH-05, got {coll_ids}")
    if "FC-FRESH-05" in listed_ids:
        errors.append("ItemList collection must not fire FC-FRESH-05")
    if "FC-FRESH-05" in pdp_ids:
        errors.append(f"PDP with related prices must not fire FC-FRESH-05, got {pdp_ids}")
    if tw_sev.get("FC-FRESH-06") not in {None, "low"}:
        errors.append(f"twitter-only blank meta must be low, got {tw_sev.get('FC-FRESH-06')}")
    if blank_sev.get("FC-FRESH-06") not in {"high", "medium"}:
        errors.append(f"all-three blank meta should be high/medium, got {blank_sev.get('FC-FRESH-06')}")
    blank_how = next(
        (
            (f.get("suggested_action") or {}).get("how") or ""
            for f in blank["findings"]
            if f["id"] == "FC-FRESH-06"
        ),
        "",
    )
    if "Severity:" in blank_how or "→" in blank_how:
        errors.append(f"FC-FRESH-06 how must not leak scoring rules, got {blank_how!r}")
    if "meta name='description'" not in blank_how:
        errors.append(f"FC-FRESH-06 how must tell owners to populate meta description, got {blank_how!r}")
    if "FC-ENT-01-FAQ" not in faq_ids:
        errors.append(f"FAQ prose should fire FC-ENT-01-FAQ, got {faq_ids}")
    if "ENG-04" not in empty_faq_ids:
        errors.append(f"empty accordion FAQ should fire ENG-04, got {empty_faq_ids}")
    if "ENG-04" in short_faq_ids:
        errors.append(f"short factual FAQ answers must not fire ENG-04, got {short_faq_ids}")
    if "ENG-04" in schema_faq_ids:
        errors.append(f"schema-backed empty accordion must not fire ENG-04, got {schema_faq_ids}")

    # BBC-style question headlines are journalism, not FAQ accordions.
    bbc_news = """<!doctype html><html><head>
<title>Can Europe recharge its battery industry? - BBC Business</title>
<meta name="description" content="Europe's battery makers face tough competition.">
</head>
<body>
<nav><a href="/">Home</a><a href="/business">Business</a></nav>
<main>
<h1>Business</h1>
<h2>Can Europe recharge its battery industry?</h2>
<p>Europe's battery makers face tough competition from Asia as demand for electric cars grows.</p>
<h2>Will central banks cut rates next month?</h2>
<p>Markets are pricing in a pause as inflation cools more slowly than expected.</p>
<h2>What does the jobs report mean for markets?</h2>
</main></body></html>"""
    bbc_rep = compose(
        _snap("https://www.bbc.com/business", bbc_news, site="bbc.com", site_type="media")
    )
    bbc_ids = {f["id"] for f in bbc_rep["findings"]}
    if "ENG-04" in bbc_ids:
        errors.append(f"BBC question headlines must not fire ENG-04, got {bbc_ids}")
    if "FC-ENT-01-FAQ" in bbc_ids:
        errors.append(f"BBC section front must not fire FC-ENT-01-FAQ, got {bbc_ids}")
    from htmlutil import classify_page

    bbc_sig = extract_page("https://www.bbc.com/business", bbc_news)
    if bbc_sig.get("faq_pairs"):
        errors.append(
            f"BBC question headlines must not become faq_pairs, got {bbc_sig.get('faq_pairs')}"
        )
    if classify_page("https://www.bbc.com/business", bbc_sig, site_type="media") == "faq":
        errors.append("BBC business section must not classify as faq")
    if classify_page("https://www.bbc.com/sport", bbc_sig, site_type="media") == "faq":
        errors.append("BBC sport-like question headlines must not classify as faq")

    # Accordion chrome without an FAQ heading must still be eligible for ENG-04.
    accordion_only = """<!doctype html><html><head><title>Help</title></head>
<body><div class="accordion">
<h3>How long does shipping take?</h3>
<h3>Do you offer free returns?</h3>
<h3>Where is my order?</h3>
</div></body></html>"""
    acc_rep = compose(_snap("https://shop.test/help/shipping", accordion_only))
    if "ENG-04" not in {f["id"] for f in acc_rep["findings"]}:
        errors.append("empty accordion (class=accordion) should still fire ENG-04")

    # Domain-anchored publisher consensus must accept BBC Wikipedia (not over-reject).
    from consensus import (
        domain_anchored_brand,
        is_ambiguous_brand_query,
        wikipedia_candidate_ok,
    )

    bbc_snap = {
        "site": "bbc.com",
        "pages": [
            {
                "role": "home",
                "url": "https://www.bbc.com/",
                "signals": {
                    "og_site_name": "BBC",
                    "title": "BBC - Home",
                    "h1": "BBC",
                    "meta_description": "Breaking news from the BBC.",
                },
            }
        ],
    }
    if not domain_anchored_brand(bbc_snap, "BBC"):
        errors.append("bbc.com + BBC must be domain_anchored_brand")
    if is_ambiguous_brand_query("BBC", bbc_snap):
        errors.append("bbc.com brand BBC must not be treated as ambiguous like Gemini")
    if not names_overlap("BBC", "BBC"):
        errors.append("names_overlap must accept exact short brand BBC==BBC")
    bbc_wiki_hit = {
        "title": "BBC",
        "summary_extract": (
            "The British Broadcasting Corporation (BBC) is a British public service broadcaster "
            "headquartered at Broadcasting House in London."
        ),
        "url": "https://en.wikipedia.org/wiki/BBC",
    }
    if not wikipedia_candidate_ok(
        bbc_snap, "BBC", bbc_wiki_hit, {"summary_extract": bbc_wiki_hit["summary_extract"]}
    ):
        errors.append("domain-anchored BBC Wikipedia primary article must be accepted")
    bbc_guard = apply_identity_guard(
        "BBC",
        {
            "wikipedia": {
                "hits": [bbc_wiki_hit],
                "summary_extract": bbc_wiki_hit["summary_extract"],
                "page_url": bbc_wiki_hit["url"],
                "titles": ["BBC"],
            },
            "wikidata": {
                "entities": [
                    {
                        "id": "Q9531",
                        "label": "BBC",
                        "description": "British public service broadcaster",
                    }
                ],
                "top_id": "Q9531",
                "top_label": "BBC",
                "top_description": "British public service broadcaster",
            },
            "duckduckgo": {},
            "reddit": {"result_count": 0},
        },
        bbc_snap,
    )
    if not (bbc_guard.get("wikipedia") or {}).get("name_match"):
        errors.append(f"BBC identity guard must keep Wikipedia match, got {bbc_guard.get('wikipedia')}")
    if not bbc_guard.get("offsite_identity_strong"):
        errors.append("BBC with Wikipedia/Wikidata match must set offsite_identity_strong")

    if clinic_sev.get("FC-ENT-02") in {"high", "critical"}:
        errors.append("local clinic with NAP must not get high FC-ENT-02")
    if "FC-ENT-04" in clinic_ids and clinic_sev.get("FC-ENT-04") in {"high", "critical"}:
        errors.append("complete local NAP should not fire high FC-ENT-04")
    if "FC-FRESH-05" not in tiny_ids:
        errors.append(f"tiny 2-SKU category should fire FC-FRESH-05, got {tiny_ids}")
    if "FC-FRESH-05" not in home_ids:
        errors.append(f"homepage priced grid should fire FC-FRESH-05, got {home_ids}")

    terms = compose(
        _snap("https://example.test/terms-and-conditions", TERMS_LEGAL, site_type="saas")
    )
    terms_ids = {f["id"] for f in terms["findings"]}
    terms_role = _snap("https://example.test/terms-and-conditions", TERMS_LEGAL)["pages"][0]["role"]
    if terms_role != "legal":
        errors.append(f"terms URL should be role=legal, got {terms_role}")
    if "FC-FRESH-05" in terms_ids:
        errors.append(f"legal terms page must not fire FC-FRESH-05, got {terms_ids}")

    social = compose(_snap("https://example.test/", FOOTER_SOCIAL, site_type="saas"))
    social_ent = next(
        (f for f in social["findings"] if f["id"] == "FC-ENT-01"),
        None,
    )
    if social_ent is None:
        errors.append("footer-social homepage should still fire FC-ENT-01 for missing JSON-LD")
    else:
        blob = (
            (social_ent.get("suggested_action") or {}).get("summary", "")
            + " "
            + (social_ent.get("evidence") or "")
        ).lower()
        if "linkedin.com/company/jiokivihealth" not in blob:
            errors.append(f"FC-ENT-01 must name on-page LinkedIn href, got {blob[:400]}")
        if "a linkedin company page or official social you already control" in blob:
            errors.append("FC-ENT-01 must not ignore existing footer socials")

    ssl_err = (
        "certificate verify failed: Hostname mismatch, certificate is not valid for 'vugb.com'"
    )
    dead = {
        "start": "https://vugb.com/",
        "origin": "https://vugb.com",
        "site": "vugb.com",
        "site_type": "unknown",
        "robots": {"status": 0, "preview": "", "ai_bots": {}},
        "sitemap": {"status": 0},
        "llms_txt": {"status": 0, "bytes": 0},
        "pages": [
            {
                "url": "https://vugb.com/",
                "status": 0,
                "role": "home",
                "signals": {},
                "waf_hint": False,
            }
        ],
        "action_status": [],
        "ai_ua_probes": [],
        "facet_pairs": [],
        "third_party_prices": [],
        "limitations": {
            "fetch_errors": [
                {"url": "https://vugb.com/", "status": 0, "error": ssl_err},
                {"url": "https://vugb.com/robots.txt", "status": 0, "error": ssl_err},
            ]
        },
        "digital_consensus": {
            "brand_query": "vugb",
            "offsite_identity_strong": False,
            "platforms_with_echo": [],
            "echo_score": 0,
            "crawl_quality": {"crawl_incomplete": True},
            "limitations": ["consensus_skipped_origin_unreachable"],
            "platforms_checked": [],
            "identity_verified": False,
        },
    }
    dead_report = compose(dead)
    dead_ids = {f["id"] for f in dead_report["findings"]}
    if dead_ids != {"NET-01"}:
        errors.append(f"SSL-dead origin must emit only NET-01, got {sorted(dead_ids)}")
    net = next(f for f in dead_report["findings"] if f["id"] == "NET-01")
    if net.get("severity") != "critical":
        errors.append(f"NET-01 must be critical, got {net.get('severity')}")
    if "ssl" not in (net.get("evidence") or "").lower() and "certificate" not in (
        net.get("evidence") or ""
    ).lower():
        errors.append(f"NET-01 evidence should cite SSL/certificate, got {net.get('evidence')}")
    net_how = ((net.get("suggested_action") or {}).get("how") or "").lower()
    for leak in (
        "do not treat",
        "do not grade",
        "json-ld as confirmed",
        "until the origin returns",
        "abort",
        "fail-fast",
    ):
        if leak in net_how:
            errors.append(f"NET-01 how must not leak crawler instructions ({leak!r}): {net_how}")
    if "certificate" not in net_how and "tls" not in net_how and "https" not in net_how:
        errors.append(f"NET-01 how should tell the owner to fix TLS/certificate, got {net_how}")

    waf403 = compose(
        {
            **_snap("https://example.test/", EMPTY),
            "pages": [
                {
                    "url": "https://example.test/",
                    "status": 403,
                    "role": "home",
                    "signals": extract_page("https://example.test/", EMPTY),
                    "waf_hint": True,
                }
            ],
            "ai_ua_probes": [{"ua": "GPTBot/1.2", "status": 403, "waf": True}],
            "limitations": {"fetch_errors": [{"url": "https://example.test/", "status": 403, "error": "HTTP 403"}]},
        }
    )
    waf_ids = {f["id"] for f in waf403["findings"]}
    if waf_ids != {"CRA-03"}:
        errors.append(f"HTTP 403 WAF must emit only CRA-03 (abort DOM skills), got {sorted(waf_ids)}")
    if "NET-01" in waf_ids:
        errors.append(f"HTTP 403 WAF must not fail-fast as NET-01, got {waf_ids}")
    if "FC-ENT-01" in waf_ids or "FC-FRESH-06" in waf_ids:
        errors.append(f"403 challenge HTML must not invent schema/meta findings, got {waf_ids}")

    rate429 = compose(
        {
            **_snap("https://meesho.test/", EMPTY, site="meesho.test"),
            "pages": [
                {
                    "url": "https://meesho.test/",
                    "status": 429,
                    "role": "home",
                    "signals": {},
                    "waf_hint": False,
                }
            ],
            "limitations": {"fetch_errors": [{"url": "https://meesho.test/", "status": 429, "error": "HTTP 429"}]},
        }
    )
    rate_ids = {f["id"] for f in rate429["findings"]}
    if rate_ids != {"CRA-03"}:
        errors.append(f"HTTP 429 must emit only CRA-03, got {sorted(rate_ids)}")

    leak_re = (
        "suta",
        "appendix d",
        "akasa",
        "novatech",
        "readme limitation",
        "fabricated prices",
    )
    for f in empty_report["findings"] + coll["findings"] + terms["findings"] + social["findings"] + dead_report["findings"]:
        blob = json.dumps(f).lower()
        for tok in leak_re:
            if tok in blob:
                errors.append(f"dev-note {tok!r} leaked on {f.get('id')}")
        how = ((f.get("suggested_action") or {}).get("how") or "").lower()
        for tok in ("do not treat", "do not grade", "until the origin returns"):
            if tok in how:
                errors.append(f"crawler instruction leaked in how on {f.get('id')}: {how}")

    if "FC-FRESH-04" in gemini_ids:
        errors.append(
            f"thin corp with strong Wikipedia/Wikidata consensus must not fire FC-FRESH-04, got {gemini_ids}"
        )
    if "FC-ENT-01" in gemini_ids:
        act = gemini_actions.get("FC-ENT-01", "").lower()
        if "google business" in act or "justdial" in act:
            errors.append(f"FC-ENT-01 on consensus-strong brand must not suggest GBP: {act}")
        if "q124650356" not in act and "language_model" not in act:
            errors.append(f"FC-ENT-01 should name verified Wikipedia/Wikidata anchors, got: {act}")
    else:
        errors.append(f"thin corp incomplete crawl should still fire FC-ENT-01 (SSR), got {gemini_ids}")
    if gemini_dab_guard.get("identity_verified"):
        errors.append("Gemini dab+zodiac consensus must not verify identity")
    dab_blob = json.dumps(gemini_dab).lower()
    if "wikipedia/wiki/gemini" in dab_blob.replace("_", "") and "language_model" not in dab_blob:
        errors.append("must not suggest Wikipedia /wiki/Gemini disambiguation page as sameAs")
    if "q8923" in dab_blob:
        errors.append("must not suggest Wikidata Q8923 (zodiac constellation) as sameAs")
    dab_ent = next(
        ((f.get("suggested_action") or {}).get("summary") or "")
        for f in gemini_dab["findings"]
        if f.get("id") == "FC-ENT-01"
    ) if "FC-ENT-01" in {f["id"] for f in gemini_dab["findings"]} else ""
    if dab_ent and ("wikipedia/wiki/gemini" in dab_ent.lower().replace("_", "") and "language" not in dab_ent.lower()):
        errors.append(f"FC-ENT-01 must not cite Gemini dab page: {dab_ent}")
    empty_ent = next(
        ((f.get("suggested_action") or {}).get("summary") or "")
        for f in empty_report["findings"]
        if f["id"] == "FC-ENT-01"
    )
    gemini_ent = gemini_actions.get("FC-ENT-01", "")
    if empty_ent and gemini_ent and empty_ent == gemini_ent:
        errors.append("FC-ENT-01 actions must differ between unknown SPA and consensus-strong brand")

    if names_overlap("KiviHealth", "Nemours Foundation"):
        errors.append("KiviHealth must not name-overlap Nemours Foundation")
    if not names_overlap("Gemini", "Gemini (language model)"):
        errors.append("Gemini must overlap Gemini (language model)")
    if not names_overlap("Apple", "Apple Inc."):
        errors.append("Apple must overlap Apple Inc.")

    kivi_snap = _snap(
        "https://kivihealth.com/",
        KIVI,
        site="kivihealth.com",
        digital_consensus=NEMOURS_CONSENSUS,
        extra_pages=[
            {"url": "https://kivihealth.com/aboutus", "html": ABOUT_THIN},
            {"url": "https://kivihealth.com/doctor/login", "html": LOGIN_THIN},
        ],
    )
    kivi_snap["site_type"] = classify_site_type(kivi_snap["pages"])
    kivi = compose(kivi_snap)
    kivi_ids = {f["id"] for f in kivi["findings"]}
    kivi_blob = json.dumps(kivi).lower()
    kivi_ent = next(
        ((f.get("suggested_action") or {}).get("summary") or "")
        for f in kivi["findings"]
        if f["id"] == "FC-ENT-01"
    ) if "FC-ENT-01" in kivi_ids else ""
    if kivi_snap["site_type"] != "saas":
        errors.append(f"KiviHealth-like clinic software should classify as saas, got {kivi_snap['site_type']}")
    if "nemours" in kivi_blob:
        errors.append("KiviHealth report must not mention Nemours (false entity sameAs)")
    if "FC-ENT-01-LOCAL" in kivi_ids:
        errors.append(f"SaaS clinic platform must not fire FC-ENT-01-LOCAL, got {kivi_ids}")
    if "restaurant" in kivi_ent.lower():
        errors.append(f"SaaS FC-ENT-01 must not suggest Restaurant schema, got {kivi_ent}")
    if "FC-ENT-01" in kivi_ids and "FC-ENT-01-LOCAL" in kivi_ids:
        errors.append("do not double-count homepage schema as both FC-ENT-01 and FC-ENT-01-LOCAL")
    cra05 = next((f for f in kivi["findings"] if f["id"] == "CRA-05"), None)
    if cra05:
        urls = " ".join(cra05.get("affected_urls") or [])
        if "aboutus" in urls:
            errors.append(f"CRA-05 must not treat /aboutus as state-gated, urls={urls}")
    slash_urls = []
    for f in kivi["findings"]:
        slash_urls.extend(f.get("affected_urls") or [])
    if "https://kivihealth.com/" in slash_urls and "https://kivihealth.com" in slash_urls:
        errors.append(f"trailing-slash URL double-count: {slash_urls}")

    stripe = compose(_snap("https://stripe.test/", STRIPEISH, site="stripe.test", site_type="saas"))
    stripe_ids = {f["id"] for f in stripe["findings"]}
    if "CRA-02" in stripe_ids:
        errors.append(f"Stripe-like Next.js SSR must not fire empty-shell CRA-02, got {stripe_ids}")
    for f in stripe["findings"]:
        if not f.get("id"):
            errors.append(f"finding missing required id: {f}")
        ev = (f.get("evidence") or "").lower()
        if "playwright" in ev or "0.70" in ev:
            errors.append(f"CRA-02 evidence must not include internal Playwright debug text: {f.get('evidence')}")

    # --- Content-type / travel / CRA-04 consistency ---
    from htmlutil import hard_travel_signal, is_html_content_type

    vpat_html = """<!doctype html><html><head><title>VPAT Checkout</title></head>
<body><h1>Voluntary Product Accessibility Template</h1>
<p>This report covers dropdowns, from/to fields, departure and arrival date pickers,
and form labels used in checkout. No airline content.</p>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"WebPage","name":"VPAT Checkout"}
</script></body></html>"""
    vpat = compose(
        _snap(
            "https://shopify.test/accessibility/vpat-checkout",
            vpat_html,
            site="shopify.test",
            site_type="ecommerce",
        )
    )
    vpat_ids = {f["id"] for f in vpat["findings"]}
    if "FC-ENT-01-FLIGHT" in vpat_ids:
        errors.append(f"VPAT accessibility page must not fire FC-ENT-01-FLIGHT, got {vpat_ids}")
    vpat_role = _snap(
        "https://shopify.test/accessibility/vpat-checkout", vpat_html
    )["pages"][0]["role"]
    if vpat_role == "flight":
        errors.append(f"VPAT URL must not classify as role=flight, got {vpat_role}")
    if hard_travel_signal(
        "https://shopify.test/accessibility/vpat-checkout",
        extract_page("https://shopify.test/accessibility/vpat-checkout", vpat_html),
    ):
        errors.append("VPAT copy with bare departure/arrival date must not hard_travel_signal")

    flight_html = """<!doctype html><html><head><title>DEL to BOM flights</title></head>
<body><h1>Delhi to Mumbai flights</h1>
<p>Book a flight from DEL to BOM. Departure airport Indira Gandhi (DEL).</p>
</body></html>"""
    if not hard_travel_signal(
        "https://airline.test/flights/delhi-mumbai",
        extract_page("https://airline.test/flights/delhi-mumbai", flight_html),
    ):
        errors.append("real flight page must hard_travel_signal")

    if is_html_content_type("text/plain", "https://shopify.test/SKILL.md", "# Skill"):
        errors.append("text/plain SKILL.md must not count as HTML")
    if not is_html_content_type("text/html; charset=utf-8", "https://shopify.test/", "<html>"):
        errors.append("text/html must count as HTML")

    home_html = """<!doctype html><html><head><title>Shop</title></head>
<body><nav><a href="/">Home</a></nav><h1>Shop</h1><p>Welcome to the store with enough copy.</p>
</body></html>"""
    thin_html = """<!doctype html><html><head><title>About</title></head>
<body><p>About us.</p></body></html>"""
    skill_snap = _snap("https://shopify.test/", home_html, site="shopify.test", site_type="ecommerce")
    skill_snap["pages"].append(
        {
            "url": "https://shopify.test/SKILL.md",
            "status": 200,
            "content_type": "text/plain",
            "role": "agent_resource",
            "signals": {
                "non_html": True,
                "content_type": "text/plain",
                "word_count": 40,
                "text": "# Skill\nAgent instructions. No H1 tag here.",
                "h1": None,
                "has_breadcrumb": False,
                "has_home_href": False,
                "has_nav": False,
                "schema_types": [],
                "travelish_text": False,
            },
            "waf_hint": False,
        }
    )
    skill_snap["pages"].append(
        {
            "url": "https://shopify.test/about",
            "status": 200,
            "content_type": "text/html",
            "role": "about",
            "signals": extract_page("https://shopify.test/about", thin_html),
            "waf_hint": False,
        }
    )
    skill_rep = compose(skill_snap)
    skill_ids = {f["id"] for f in skill_rep["findings"]}
    if "ENG-02" in skill_ids:
        eng02 = next(f for f in skill_rep["findings"] if f["id"] == "ENG-02")
        urls = " ".join(eng02.get("affected_urls") or [])
        if "SKILL.md" in urls:
            errors.append(f"ENG-02 must not flag text/plain SKILL.md as missing H1, urls={urls}")
        # Only one thin HTML page + agent resource: should not meet >=2 no-H1 HTML threshold
        # unless home also counted — home has H1 so ENG-02 should not fire at all.
        errors.append(f"ENG-02 must not fire when only non-HTML + one thin HTML lack H1, got {skill_ids}")

    # CRA-04: duplicate page records for same URL must not claim "2 pages" with 1 affected_url
    img_html = """<!doctype html><html><head><title>Home</title></head>
<body><h1>Home</h1>
<img src="/hero.jpg" width="1200" height="600">
<img src="/banner.jpg" width="900" height="500">
<p>Storefront with enough copy for a real document shell and more words here.</p>
</body></html>"""
    img_sig = extract_page("https://shopify.test/", img_html)
    img_snap = _snap("https://shopify.test/", img_html, site="shopify.test")
    # Second record same URL (trailing-slash twin) — composition must dedupe.
    img_snap["pages"].append(
        {
            "url": "https://shopify.test",
            "status": 200,
            "role": "home",
            "signals": dict(img_sig),
            "waf_hint": False,
        }
    )
    img_rep = compose(img_snap)
    cra04 = next((f for f in img_rep["findings"] if f["id"] == "CRA-04"), None)
    if cra04:
        aff = cra04.get("affected_urls") or []
        ev = cra04.get("evidence") or ""
        # Page count in evidence must match unique affected_urls length
        import re as _re

        m = _re.search(r"across (\d+) pages", ev)
        if m and int(m.group(1)) != len(aff):
            errors.append(
                f"CRA-04 evidence page count {m.group(1)} must match affected_urls len {len(aff)}: {ev} / {aff}"
            )

    chrome_html = """<!doctype html><html><head><title>Shop</title></head>
<body><nav><a href="/">Home</a></nav><h1>Shop</h1>
<img src="/icon-cart.svg" class="icon" width="24" height="24">
<img src="/logo.png" class="site-logo" width="180" height="48">
<img src="/spacer.gif" class="spacer" width="1" height="1">
<p>Storefront with enough copy for a real document shell and more words here for parsers.</p>
</body></html>"""
    chrome_rep = compose(_snap("https://shop.test/", chrome_html, site="shop.test"))
    if any(f["id"] == "CRA-04" for f in chrome_rep["findings"]):
        errors.append("CRA-04 must ignore icon/logo/spacer images even when alt is missing")

    small_html = """<!doctype html><html><head><title>Shop</title></head>
<body><h1>Shop</h1>
<img src="/thumb.jpg" width="80" height="80">
<p>Storefront with enough copy for a real document shell and more words here for parsers.</p>
</body></html>"""
    small_rep = compose(_snap("https://shop.test/", small_html, site="shop.test"))
    if any(f["id"] == "CRA-04" for f in small_rep["findings"]):
        errors.append("CRA-04 must ignore images with width and height ≤100px")

    mix_html = """<!doctype html><html><head><title>Shop</title></head>
<body><h1>Shop</h1>
<img src="/icon.svg" class="icon" width="24" height="24">
<img src="/hero.jpg" width="1200" height="400">
<p>Storefront with enough copy for a real document shell and more words here for parsers.</p>
</body></html>"""
    mix_rep = compose(_snap("https://shop.test/", mix_html, site="shop.test"))
    mix04 = next((f for f in mix_rep["findings"] if f["id"] == "CRA-04"), None)
    if mix04 is None:
        errors.append("CRA-04 must still fire on a >100px photo missing alt")
    else:
        ev = mix04.get("evidence") or ""
        if not ev.startswith("1 "):
            errors.append(f"CRA-04 must count only the hero, not the icon, got {ev}")
        if "large/hero" in ev.lower():
            errors.append(f"CRA-04 evidence must not claim hero size, got {ev}")
        how = ((mix04.get("suggested_action") or {}).get("how") or "")
        if "image1" in how.lower():
            errors.append(f"CRA-04 how must be owner-facing, got {how}")

    # --- Shared classify_page gate: fire / lookalike-silent / unrelated per specialist ---
    from htmlutil import classify_page

    def _cls(url: str, html: str, **kw) -> str:
        sig = extract_page(url, html)
        return classify_page(url, sig, site_type=kw.get("site_type", ""), role=guess_role(url, sig))

    # Flight / vehicle niche checks are disabled (too many false positives on news/marketing).
    flight_ok = """<!doctype html><html><head><title>DEL-BOM flights</title></head>
<body><h1>Delhi to Mumbai flights</h1>
<p>Book a flight from DEL to BOM. Departure airport Indira Gandhi.</p></body></html>"""
    if _cls("https://akasa.test/flights/delhi-mumbai", flight_ok) != "flight":
        errors.append("classify_page must label real flight page as flight")
    flight_fire = compose(
        _snap(
            "https://akasa.test/flights/delhi-mumbai",
            flight_ok,
            site="akasa.test",
            site_type="airline",
        )
    )
    flight_ids = {f["id"] for f in flight_fire["findings"]}
    if "FC-ENT-01-FLIGHT" in flight_ids:
        errors.append("FC-ENT-01-FLIGHT niche check must stay disabled")
    if "FC-ENT-01-VEHICLE" in flight_ids:
        errors.append("FC-ENT-01-VEHICLE niche check must stay disabled")

    vehicle_ok = """<!doctype html><html><head><title>Used cars</title></head>
<body><h1>Used cars for sale</h1>
<p>Browse our inventory of SUVs and sedans. Fuel type petrol and diesel models in stock.</p>
</body></html>"""
    vehicle_rep = compose(
        _snap("https://dealer.test/inventory", vehicle_ok, site="dealer.test", site_type="local")
    )
    if "FC-ENT-01-VEHICLE" in {f["id"] for f in vehicle_rep["findings"]}:
        errors.append("FC-ENT-01-VEHICLE niche check must stay disabled on inventory pages")

    eng04 = next((f for f in empty_faq["findings"] if f["id"] == "ENG-04"), None)
    if eng04:
        how04 = ((eng04.get("suggested_action") or {}).get("how") or "")
        for leak in ("alphanumeric", "acceptedAnswer", "Schema fallback", "fallback skips"):
            if leak.lower() in how04.lower():
                errors.append(f"ENG-04 how must not leak {leak!r}: {how04}")
        if "initial HTML load" not in how04:
            errors.append(f"ENG-04 how should be owner-facing FAQ advice, got {how04!r}")

    # Flight: lookalike-silent (VPAT / a11y)
    vpat2 = """<!doctype html><html><head><title>VPAT</title></head>
<body><h1>Accessibility VPAT</h1>
<p>Covers dropdowns, from/to fields, departure and arrival date pickers.</p></body></html>"""
    if _cls("https://shopify.test/accessibility/vpat-checkout", vpat2) != "general":
        errors.append(
            f"VPAT must classify general, got {_cls('https://shopify.test/accessibility/vpat-checkout', vpat2)}"
        )

    # Flight: unrelated homepage (Shopify-like marketing)
    shop_home = """<!doctype html><html><head><title>Shopify</title>
<meta name="description" content="Shopify is a commerce platform for businesses. Start selling online.">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Organization","name":"Shopify",
 "url":"https://www.shopify.com/","sameAs":["https://www.wikidata.org/wiki/Q216821"]}
</script></head>
<body><nav><a href="/">Home</a></nav><h1>Shopify</h1>
<p>Build your business with online store tools, checkout, and payments. Trusted by millions of brands worldwide.
More marketing copy so this is a real document shell, not an empty app.</p></body></html>"""
    if _cls("https://www.shopify.com/in", shop_home) != "general":
        errors.append(
            f"Shopify homepage must classify general, got {_cls('https://www.shopify.com/in', shop_home)}"
        )
    # Regression: case-insensitive IATA pair must NOT match English "how to get"
    from htmlutil import IATA_PAIR_RE, hard_travel_signal

    if IATA_PAIR_RE.search("Learn how to get started with commerce"):
        errors.append("IATA_PAIR_RE must not match 'how to get'")
    if hard_travel_signal(
        "https://www.shopify.com/in",
        {"text": "Learn how to get started. Build your business online.", "title": "Shopify"},
    ):
        errors.append("hard_travel_signal must stay false on Shopify 'how to get' marketing copy")

    shop_rep = compose(
        _snap("https://www.shopify.com/in", shop_home, site="shopify.com", site_type="saas")
    )
    shop_ids = {f["id"] for f in shop_rep["findings"]}
    for bad_id in ("FC-ENT-01-FLIGHT", "FC-ENT-01-PRODUCT", "FC-ENT-01-VEHICLE", "FC-FRESH-05"):
        if bad_id in shop_ids:
            errors.append(f"Shopify homepage must not fire vertical {bad_id}, got {shop_ids}")

    # Catalog: should-fire (priced grid)
    cat_html = """<!doctype html><html><head><title>Silk scarves</title></head>
<body><h1>Silk</h1>
<ul>
<li><a href="/p/1">A</a> $10</li><li><a href="/p/2">B</a> $12</li>
<li><a href="/p/3">C</a> $14</li><li><a href="/p/4">D</a> $16</li>
</ul></body></html>"""
    # Lookalike-silent: Terms with currency mentions
    terms_html = """<!doctype html><html><head><title>Terms</title></head>
<body><h1>Terms of Service</h1>
<p>SMS rates may apply up to $0.50 per message. Shipping fees vary. List: Delhi, Mumbai, Chennai.</p>
<ul><li>Delhi</li><li>Mumbai</li><li>Chennai</li><li>Kolkata</li></ul>
</body></html>"""
    if _cls("https://shop.test/terms", terms_html) != "general":
        errors.append(
            f"Terms page must classify general (not product_catalog), got {_cls('https://shop.test/terms', terms_html)}"
        )
    terms_rep = compose(_snap("https://shop.test/terms", terms_html, site_type="ecommerce"))
    if "FC-FRESH-05" in {f["id"] for f in terms_rep["findings"]}:
        errors.append("Terms page must not fire FC-FRESH-05 ItemList miss")

    # FAQ: should-fire vs unrelated
    faq_html = """<!doctype html><html><head><title>FAQ</title></head>
<body><h1>FAQ</h1>
<h2>What is your return policy?</h2><p>30 days with receipt.</p>
<h2>Do you ship internationally?</h2><p>Yes, to 40 countries.</p>
<h2>How long is shipping?</h2><p>3-5 business days.</p>
</body></html>"""
    if _cls("https://shop.test/faq", faq_html) != "faq":
        errors.append(f"FAQ page must classify faq, got {_cls('https://shop.test/faq', faq_html)}")
    if _cls("https://www.shopify.com/in", shop_home) == "faq":
        errors.append("Shopify homepage must not classify as faq")

    # Local: clinic contact should-fire class; SaaS homepage silent
    clinic_html = """<!doctype html><html><head><title>Clinic</title>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Dentist","name":"Smile Dental",
 "telephone":"+91-9876543210",
 "address":{"@type":"PostalAddress","streetAddress":"12 MG Road","addressLocality":"Pune","postalCode":"411001","addressCountry":"IN"}}
</script></head>
<body><h1>Smile Dental</h1><p>Call +91-9876543210. Visit 12 MG Road, Pune.</p></body></html>"""
    if _cls("https://smile.test/", clinic_html, site_type="local") != "local_business":
        errors.append(
            f"local clinic home must classify local_business, got {_cls('https://smile.test/', clinic_html, site_type='local')}"
        )
    if _cls("https://www.shopify.com/in", shop_home, site_type="saas") == "local_business":
        errors.append("Shopify homepage must not classify as local_business")

    # ── WAF HTTP-200 challenge page (Gap 1 / Meesho-class fix) ──
    # A Cloudflare "Just a moment" page that returns HTTP 200.
    # Only CRA-03 must fire; no schema/engagement findings.
    waf200_html = """<!doctype html><html><head><title>Just a moment...</title></head>
<body>
<div id="challenge-platform" style="display:none">
<div id="cf-chl-widget">Enable JavaScript and cookies to continue</div>
<noscript>Please enable JavaScript and cookies to continue.</noscript>
</div>
<p>Checking your browser before accessing the site.</p>
</body></html>"""
    waf200_sig = extract_page("https://meesho-test.example/", waf200_html)
    waf200_snap = {
        "start": "https://meesho-test.example/",
        "origin": "https://meesho-test.example",
        "site": "meesho-test.example",
        "site_type": "ecommerce",
        "robots": {"status": 200, "preview": "User-agent: *\nAllow: /", "ai_bots": {}},
        "sitemap": {"status": 200},
        "llms_txt": {"status": 404, "bytes": 0},
        "pages": [
            {
                "url": "https://meesho-test.example/",
                "status": 200,
                "role": "home",
                "signals": waf200_sig,
                "waf_hint": True,
            }
        ],
        "action_status": [],
        "ai_ua_probes": [],
        "facet_pairs": [],
        "third_party_prices": [],
        "limitations": {},
    }
    waf200_rep = compose(waf200_snap)
    waf200_ids = {f["id"] for f in waf200_rep["findings"]}
    if "CRA-03" not in waf200_ids:
        errors.append(f"WAF-200 challenge page must fire CRA-03, got {waf200_ids}")
    waf200_bad = waf200_ids - {"CRA-03", "NET-01"}
    if waf200_bad:
        errors.append(
            f"WAF-200 challenge page must NOT fire schema/engagement findings, "
            f"but got: {sorted(waf200_bad)}"
        )
    # ── Robots-blocked homepage (WSJ-class case) ──
    # When robots.txt Disallow: / blocks the homepage, fail-fast must fire CRA-01
    # and NOT fire any DOM schema/engagement findings or leak "None" into evidence.
    wsj_snap = {
        "start": "https://www.wsj-test.example/",
        "origin": "https://www.wsj-test.example",
        "site": "wsj-test.example",
        "site_type": "media",
        "robots": {
            "status": 200,
            "preview": "User-agent: *\nDisallow: /\n",
            "ai_bots": {"*": "disallow_root", "GPTBot": "disallow_root"},
            "home_disallowed": True,
        },
        "sitemap": {"status": 200},
        "llms_txt": {"status": 404, "bytes": 0},
        "pages": [],
        "action_status": [],
        "ai_ua_probes": [],
        "facet_pairs": [],
        "third_party_prices": [],
        "limitations": {
            "robots_blocked": [
                "https://www.wsj-test.example/",
                "https://www.wsj-test.example/world",
            ],
            "home_robots_blocked": True,
        },
    }
    wsj_rep = compose(wsj_snap)
    wsj_ids = {f["id"] for f in wsj_rep["findings"]}
    if "CRA-01" not in wsj_ids:
        errors.append(f"Robots-blocked site must fire CRA-01, got {wsj_ids}")
    wsj_bad = wsj_ids - {"CRA-01"}
    if wsj_bad:
        errors.append(
            f"Robots-blocked site must NOT fire schema/content findings, but got: {sorted(wsj_bad)}"
        )
    for f in wsj_rep["findings"]:
        ev = f.get("evidence") or ""
        if "None" in ev:
            errors.append(f"Robots-blocked site leaked 'None' in evidence: {ev}")
        if not f.get("affected_urls"):
            errors.append(f"Robots-blocked site finding {f['id']} missing affected_urls")

    # ── BBC-style domain-anchored brand (Gap 2) ──
    # A well-known, domain-anchored brand should NOT get FC-FRESH-04 high.
    bbc_html = """<!doctype html><html><head><title>BBC</title>
<meta name="description" content="Breaking news, sport, TV, radio and a whole lot more.">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Organization","name":"BBC",
 "url":"https://www.bbc.com/"}
</script></head>
<body><nav><a href="/">Home</a><a href="/news">News</a></nav>
<h1>BBC</h1>
<p>Breaking news, sport, TV, radio and a whole lot more from the BBC.
The British Broadcasting Corporation is the world's leading public service broadcaster.
More text to ensure the body is substantial and not a thin shell for AI crawlers.</p></body></html>"""
    bbc_cons = {
        "brand_query": "BBC",
        "crawl_quality": {"crawl_incomplete": False, "iana_placeholder": False},
        "wikipedia": {
            "queried": "BBC",
            "status": 200,
            "titles": ["BBC"],
            "summary_title": "BBC",
            "summary_extract": "The British Broadcasting Corporation (BBC) is a British public service broadcaster headquartered at Broadcasting House in London.",
            "page_url": "https://en.wikipedia.org/wiki/BBC",
            "page_type": "standard",
            "hits": [{"title": "BBC", "url": "https://en.wikipedia.org/wiki/BBC",
                       "summary_extract": "The British Broadcasting Corporation (BBC) is a British public service broadcaster headquartered at Broadcasting House in London.",
                       "page_type": "standard"}],
        },
        "wikidata": {
            "queried": "BBC",
            "status": 200,
            "entities": [{"id": "Q9531", "label": "BBC", "description": "British public service broadcaster"}],
            "top_id": "Q9531",
            "top_label": "BBC",
            "top_description": "British public service broadcaster",
        },
        "duckduckgo": {"queried": "BBC", "status": 200, "heading": "BBC", "abstract": "The British Broadcasting Corporation"},
        "reddit": {"queried": "BBC", "status": 200, "result_count": 5, "top_titles": ["BBC News"]},
        "platforms_checked": ["wikipedia", "wikidata", "duckduckgo", "reddit"],
        "limitations": [],
    }
    bbc_snap = _snap(
        "https://www.bbc.com/",
        bbc_html,
        site="bbc.com",
        origin="https://www.bbc.com",
        site_type="media",
        digital_consensus=bbc_cons,
    )
    bbc_rep = compose(bbc_snap)
    bbc_ids = {f["id"] for f in bbc_rep["findings"]}
    bbc_fc04 = [f for f in bbc_rep["findings"] if f["id"] == "FC-FRESH-04"]
    if bbc_fc04 and bbc_fc04[0].get("severity") in ("high", "critical"):
        errors.append(
            f"BBC (domain-anchored global brand) must NOT get FC-FRESH-04 high, "
            f"got severity={bbc_fc04[0]['severity']}"
        )

    # ── Verification steps presence (Gap 3) ──
    # Every finding in the Apple-like report must have verification_steps.
    for f in apple_report["findings"]:
        sa = f.get("suggested_action") or {}
        if "verification_steps" not in sa:
            errors.append(f"Finding {f['id']} in Apple-like report is missing verification_steps")

    # ── FC-PROACT-03 (Voice / Speakable proactive recommendation) ──
    # Gated strictly on actual Article/NewsArticle schema present without speakable.
    article_html = """<!doctype html><html><head><title>Test Article</title>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"NewsArticle","headline":"AI Audit Revolution",
 "url":"https://test-news.example/article-1"}
</script></head>
<body><nav><a href="/">Home</a></nav><h1>AI Audit Revolution</h1><p>Full article text here.</p></body></html>"""
    article_snap = {
        "start": "https://test-news.example/",
        "origin": "https://test-news.example",
        "site": "test-news.example",
        "site_type": "media",
        "robots": {"status": 200, "preview": "User-agent: *\nAllow: /\n", "ai_bots": {}},
        "sitemap": {"status": 200},
        "llms_txt": {"status": 200, "bytes": 100},
        "pages": [
            {
                "url": "https://test-news.example/article-1",
                "role": "article",
                "status": 200,
                "signals": extract_page("https://test-news.example/article-1", article_html),
            }
        ],
        "action_status": [],
        "ai_ua_probes": [],
        "facet_pairs": [],
        "third_party_prices": [],
        "limitations": {},
    }
    article_rep = compose(article_snap)
    article_ids = {f["id"] for f in article_rep["findings"]}
    if "FC-PROACT-03" not in article_ids:
        errors.append(f"Page with NewsArticle schema lacking speakable must fire FC-PROACT-03, got {article_ids}")

    # Negative test: if page does not have Article schema (e.g. Apple-like), FC-PROACT-03 must NOT fire
    if "FC-PROACT-03" in apple_ids:
        errors.append("Apple-like site without Article schema must NOT fire FC-PROACT-03")

    # Spot-check: site_type must appear in default report output.
    if "site_type" not in apple_report:
        errors.append("Default report must include site_type field")
    if errors:
        print("SELFTEST FAIL", file=sys.stderr)
        for e in errors:
            print(" -", e, file=sys.stderr)
        print(
            json.dumps(
                {
                    "empty": sorted(empty_ids),
                    "apple": sorted(apple_ids),
                    "collection": sorted(coll_ids),
                    "pdp": sorted(pdp_ids),
                    "empty_faq": sorted(empty_faq_ids),
                    "clinic": sorted(clinic_ids),
                    "tiny": sorted(tiny_ids),
                    "home_grid": sorted(home_ids),
                    "gemini": sorted(gemini_ids),
                },
                indent=2,
            )
        )
        return 1
    print("SELFTEST OK")
    print("empty", sorted(empty_ids))
    print("apple-like", sorted(apple_ids))
    print("collection", sorted(coll_ids))
    print("eng-04", "fired" if "ENG-04" in empty_faq_ids else "missing")
    print("clinic", sorted(clinic_ids))
    print("tiny", sorted(tiny_ids))
    print("home_grid", sorted(home_ids))
    print("gemini-like", sorted(gemini_ids))
    print("waf-200", sorted(waf200_ids))
    print("robots-blocked", sorted(wsj_ids))
    print("bbc", sorted(bbc_ids))
    print("article", sorted(article_ids))
    print("verification_steps", "all present" if all(
        "verification_steps" in (f.get("suggested_action") or {})
        for f in apple_report["findings"]
    ) else "MISSING")
    print("site_type_in_report", "yes" if "site_type" in apple_report else "no")
    return 0


if __name__ == "__main__":
    sys.exit(main())
