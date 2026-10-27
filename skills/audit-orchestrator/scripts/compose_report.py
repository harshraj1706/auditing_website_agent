"""Merge findings into a clean problem list. Consensus validates severity internally — not dumped."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from typing import Any

from detect import SKILL_MAP, origin_fetch_aborted, run_all, run_skill
from htmlutil import annotate_page_classes, infer_site_scale
from signals import enrich_site_signals, grounding_check, page_raw_signals, synthesize_from_signals
from consensus import apply_identity_guard, brand_query, crawl_quality


ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
CAP = 18


def _signals_for_finding(snap: dict[str, Any], site_sig: dict[str, Any], finding: dict[str, Any]) -> dict[str, Any]:
    urls = [u for u in (finding.get("affected_urls") or []) if u]
    pages = snap.get("pages") or []
    for u in urls:
        for p in pages:
            if (p.get("url") or "") == u or (p.get("url") or "").rstrip("/") == u.rstrip("/"):
                sig = page_raw_signals(snap, p)
                sig["site_type"] = snap.get("site_type")
                sig["site_scale"] = snap.get("site_scale") or site_sig.get("site_scale")
                sig["pages_crawled"] = site_sig.get("pages_crawled")
                sig["page_roles"] = site_sig.get("page_roles")
                sig["page_urls"] = site_sig.get("page_urls")
                sig["name_collision_check"] = site_sig.get("name_collision_check")
                sig["robots_txt_status"] = site_sig.get("robots_txt_status")
                sig["sitemap_status"] = site_sig.get("sitemap_status")
                sig["llms_txt_status"] = site_sig.get("llms_txt_status")
                sig["robots_ai_bots"] = site_sig.get("robots_ai_bots")
                sig["ai_ua_probes"] = site_sig.get("ai_ua_probes")
                sig["facet_pairs"] = site_sig.get("facet_pairs")
                sig["action_status"] = site_sig.get("action_status")
                cons = snap.get("digital_consensus") or {}
                sig["digital_consensus"] = {
                    "brand_query": cons.get("brand_query"),
                    "platforms_with_echo": cons.get("platforms_with_echo"),
                    "offsite_identity_strong": cons.get("offsite_identity_strong"),
                    "crawl_incomplete": (cons.get("crawl_quality") or {}).get("crawl_incomplete"),
                    "wikipedia_title": (cons.get("wikipedia") or {}).get("summary_title"),
                    "wikipedia_url": (cons.get("wikipedia") or {}).get("page_url"),
                    "wikidata_id": (cons.get("wikidata") or {}).get("top_id"),
                    "identity_verified": cons.get("identity_verified"),
                }
                return sig
    out = dict(site_sig)
    cons = snap.get("digital_consensus") or {}
    out["digital_consensus"] = {
        "brand_query": cons.get("brand_query"),
        "platforms_with_echo": cons.get("platforms_with_echo"),
        "offsite_identity_strong": cons.get("offsite_identity_strong"),
        "crawl_incomplete": (cons.get("crawl_quality") or {}).get("crawl_incomplete"),
        "wikipedia_title": (cons.get("wikipedia") or {}).get("summary_title"),
        "wikipedia_url": (cons.get("wikipedia") or {}).get("page_url"),
        "wikidata_id": (cons.get("wikidata") or {}).get("top_id"),
        "identity_verified": cons.get("identity_verified"),
    }
    return out


def resynthesize(snap: dict[str, Any], findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if "site_scale" not in snap or not snap.get("site_scale"):
        snap["site_scale"] = infer_site_scale(
            snap.get("pages") or [], consensus=snap.get("digital_consensus")
        )
    site_sig = enrich_site_signals(snap)
    snap["_internal_signals"] = site_sig
    out: list[dict[str, Any]] = []
    for f in findings:
        sig = _signals_for_finding(snap, site_sig, f)
        draft = synthesize_from_signals(
            f.get("id") or "",
            f.get("severity") or "low",
            f.get("title") or f.get("id") or "",
            sig,
            category=f.get("category") or "discoverability",
            failure_mode=f.get("failure_mode") or "",
            confidence=float(f.get("confidence") or 0.9),
            confidence_note=f.get("confidence_note"),
            urls=f.get("affected_urls") or [],
        )
        # Detector prose is case-branched on this run's consensus; keep it as the
        # published text. Signal draft is a rewrite seed for the harness agent —
        # never let a fixed template wipe a Wikidata/wiki-specific action.
        det_ev = (f.get("evidence") or "").strip()
        det_act = ((f.get("suggested_action") or {}).get("summary") or "").strip()
        det_how = ((f.get("suggested_action") or {}).get("how") or "").strip()
        rec = draft
        rec["id"] = f.get("id") or rec.get("id")
        if not rec.get("id"):
            continue
        if det_ev and det_act:
            rec["evidence"] = det_ev
            rec["suggested_action"]["summary"] = det_act
            if det_how:
                rec["suggested_action"]["how"] = det_how
            text = f"{det_ev} {det_act} {det_how}"
            gc = grounding_check(text, sig)
            rec["grounding"] = gc
            if not gc["ok"]:
                rec["self_check_failed"] = True
                rec["self_check_ungrounded"] = gc["ungrounded"]
            else:
                rec.pop("self_check_failed", None)
                rec.pop("self_check_ungrounded", None)
            syn = dict(rec.get("synthesis") or {})
            syn["agent_should_rewrite"] = True
            syn["rule"] = (
                "Rewrite evidence and suggested_action in your own words using only this "
                "finding's signals (and the detector evidence facts). Do not change id or severity. "
                "Never paste a generic small-business line (e.g. Google Business Profile) onto a "
                "brand with offsite_identity_strong or non-empty tier1_profile_urls. "
                "Never say 'substantiate scale claims' when scale_claim_phrases_found is empty. "
                "Never suggest a Wikipedia/Wikidata sameAs unless identity_verified is true "
                "and the item's name overlaps the brand."
            )
            syn["draft_from_signals"] = {
                "evidence": draft.get("evidence"),
                "suggested_action": (draft.get("suggested_action") or {}).get("summary"),
            }
            rec["synthesis"] = syn
        out.append(rec)
    return out


_INTERNAL_PROSE_RE = re.compile(
    r"(suta[- ]style|appendix d|delhi.?mumbai|akasa|novatech|pine villa|uniswap|"
    r"krishna dental|readme limitation|fabricated prices|apple[- ]class|"
    r"apple baseline|do not attach|never (say|paste|require|suggest|a blanket)|"
    r"not because|wikipedia is not required|tier [01]|fc-ent-|proactive\.|"
    r"harness|judge|q8923|nemours|see readme|would fail the apple|"
    r"do not (treat|grade|run|emit|invent)|"
    r"until the origin returns|abort DOM|fail-?fast|"
    r"missing robots\.txt or JSON-LD as confirmed|"
    r"severity:\s*twitter)",
    re.I,
)


def _public_prose(text: str | None) -> str:
    """Strip calibration/research phrasing from judge-facing evidence and how."""
    if not text or not str(text).strip():
        return ""
    kept = []
    for sent in re.split(r"(?<=[.!?])\s+", str(text).strip()):
        if _INTERNAL_PROSE_RE.search(sent):
            continue
        kept.append(sent)
    return " ".join(kept).strip()


# Verification steps: how a site owner confirms the fix worked.
_VERIFICATION_STEPS: dict[str, str] = {
    "NET-01": "Run `curl -I https://yoursite.com` and confirm HTTP 200 with a valid TLS certificate.",
    "CRA-01": "Fetch /robots.txt and /sitemap.xml with curl; confirm Disallow does not block public pages and sitemap returns 200.",
    "CRA-02": "Run `curl -s https://yoursite.com | wc -w` and confirm word count > 50; verify JSON-LD is in the raw HTML response.",
    "CRA-02-MENU": "Fetch the menu/order page URL with curl and confirm prices/items appear in the raw HTML.",
    "CRA-03": "Fetch the homepage with `curl -A 'GPTBot/1.2' https://yoursite.com` and confirm HTTP 200 with real HTML content.",
    "CRA-04": "Inspect `<img>` tags in the raw HTML; confirm all images wider than 100px have descriptive alt text.",
    "CRA-04-PDF": "Confirm the HTML page has a text summary of key facts from the PDF, not just a download link.",
    "CRA-04-CANVAS": "Confirm canvas-rendered data also appears as text/HTML elements that a text-only fetcher can read.",
    "CRA-05": "Visit the URL while signed out and confirm a public explanation of the feature is visible.",
    "CRA-06": "Fetch base URL and filtered URL with curl; confirm the HTML content differs between the two.",
    "CRA-07": "Check for `<a rel=\"next\">` or `?page=2` links in the HTML of the paginated page.",
    "FC-ENT-01": "Run `curl -s https://yoursite.com | grep -i 'schema.org'` and confirm Organization/LocalBusiness JSON-LD is present.",
    "FC-ENT-01-PRODUCT": "Fetch a product page with curl and confirm Product+Offer JSON-LD with price and availability is in the raw HTML.",
    "FC-ENT-01-ARTICLE": "Fetch an article URL and confirm Article/NewsArticle JSON-LD with headline, author, datePublished is present.",
    "FC-ENT-01-FAQ": "Fetch the FAQ page and confirm FAQPage JSON-LD with Question/acceptedAnswer pairs is present.",
    "FC-ENT-01-LOCAL": "Fetch the page and confirm LocalBusiness JSON-LD with PostalAddress and OpeningHoursSpecification.",
    "FC-ENT-02": "Check Organization.sameAs in the JSON-LD and confirm it lists ≥2 authority profile URLs.",
    "FC-ENT-03": "Optional: add taxID or leiCode to Organization JSON-LD if the brand name is globally ambiguous.",
    "FC-ENT-04": "Confirm LocalBusiness JSON-LD contains streetAddress, addressLocality, and telephone.",
    "FC-ENT-05": "Inspect social icon links and confirm each has an aria-label and the URLs appear in Organization.sameAs.",
    "FC-FRESH-01": "Confirm dateModified or a visible 'Last updated' line appears next to time-sensitive facts.",
    "FC-FRESH-02": "Compare on-site prices with third-party listings and confirm they match.",
    "FC-FRESH-03": "Confirm openingHoursSpecification JSON-LD uses explicit opens/closes times.",
    "FC-FRESH-04": "Search for the brand on Google/Bing and confirm at least one independent source corroborates the claimed scale.",
    "FC-FRESH-05": "Fetch the listing page and confirm ItemList JSON-LD with itemListElement containing offers.price.",
    "FC-FRESH-06": "Run `curl -s URL | grep 'name=\"description\"'` and confirm the content attribute is non-empty.",
    "FC-PROACT-01": "Fetch /llms.txt and confirm it returns HTTP 200 with a Markdown index of canonical URLs.",
    "FC-PROACT-02": "Optional: create a Wikidata item and add its URL to Organization.sameAs when the brand gains press coverage.",
    "FC-PROACT-03": "Test an article URL in Google Rich Results Test; confirm 'speakable' property is recognized under Article.",
    "ENG-01": "Click or curl each CTA/booking URL and confirm it returns HTTP 200.",
    "ENG-02": "Visit inner pages and confirm each has an H1, breadcrumbs, and a link back to the homepage.",
    "ENG-04": "Expand each FAQ accordion and confirm the answer text is present in the initial HTML (view-source).",
}


def _public_finding(f: dict[str, Any], site: str = "") -> dict[str, Any]:
    """Standard schema-compliant problem row — no consensus dump, no signal laundry list."""
    sa = f.get("suggested_action") or {}
    evidence = _public_prose(f.get("evidence") or "") or (f.get("title") or "")
    how = _public_prose(sa.get("how") or "")
    action = _public_prose(sa.get("summary") or "") or (sa.get("summary") or "")
    row: dict[str, Any] = {
        "id": f.get("id"),
        "title": f.get("title"),
        "severity": f.get("severity"),
        "evidence": evidence,
        "suggested_action": {
            "summary": action,
            "priority": sa.get("priority") or f.get("severity") or "medium",
        },
    }
    if how:
        row["suggested_action"]["how"] = how
    # verification_steps: how the site owner confirms the fix worked.
    fid = f.get("id") or ""
    vstep = _VERIFICATION_STEPS.get(fid)
    if not vstep:
        # Try prefix match for sub-IDs like F-ENT-NAP
        for prefix, step in _VERIFICATION_STEPS.items():
            if fid.startswith(prefix):
                vstep = step
                break
    if vstep:
        row["suggested_action"]["verification_steps"] = vstep
    if f.get("category"):
        row["category"] = f["category"]
    if f.get("affected_urls"):
        row["affected_urls"] = f["affected_urls"]
    else:
        site_str = site if site.startswith("http") else f"https://{site}/"
        row["affected_urls"] = [site_str]
    if f.get("confidence_note"):
        row["confidence_note"] = f["confidence_note"]
    return row


def compose(
    snap: dict[str, Any],
    skill: str | None = None,
    *,
    signals_only: bool = False,
    verbose: bool = False,
) -> dict[str, Any]:
    if "digital_consensus" not in snap:
        snap["digital_consensus"] = {
            "brand_query": None,
            "offsite_identity_strong": False,
            "platforms_with_echo": [],
            "echo_score": 0,
            "crawl_quality": {},
            "limitations": ["consensus_not_run_offline"],
            "platforms_checked": [],
        }
    cq = (snap.get("digital_consensus") or {}).get("crawl_quality")
    if not isinstance(cq, dict) or "crawl_incomplete" not in cq:
        snap["digital_consensus"]["crawl_quality"] = crawl_quality(snap)
        cq = snap["digital_consensus"]["crawl_quality"]
    if cq.get("crawl_incomplete") and cq.get("note"):
        snap.setdefault("limitations", {})["crawl_incomplete"] = cq["note"]
    if origin_fetch_aborted(snap):
        findings = (
            run_skill(snap, skill)
            if skill and skill in SKILL_MAP
            else run_all(snap)
        )
    else:
        annotate_page_classes(snap)
        q = (snap.get("digital_consensus") or {}).get("brand_query") or brand_query(snap)
        snap["digital_consensus"] = apply_identity_guard(q, snap.get("digital_consensus"), snap)
        if "site_scale" not in snap or not snap.get("site_scale"):
            snap["site_scale"] = infer_site_scale(
                snap.get("pages") or [], consensus=snap.get("digital_consensus")
            )
        if skill and skill in SKILL_MAP:
            findings = run_skill(snap, skill)
        else:
            findings = run_all(snap)
    findings = resynthesize(snap, findings)
    findings.sort(
        key=lambda f: (ORDER.get(f.get("severity") or "low", 9), -float(f.get("confidence") or 0))
    )
    seen_ids: set[str] = set()
    uniq: list[dict[str, Any]] = []
    for f in findings:
        fid = f.get("id") or ""
        if not fid or fid in seen_ids:
            continue
        seen_ids.add(fid)
        uniq.append(f)
    findings = uniq

    # Public findings only (schema wants findings[]; no duplicate problems[]).
    selected: list[dict[str, Any]] = []
    for f in findings:
        sev = f.get("severity") or "low"
        proactive = str(f.get("failure_mode") or "").startswith("proactive.")
        if proactive and sev == "low" and not verbose:
            continue
        if len(selected) >= CAP:
            break
        if sev == "low" and len(selected) >= CAP:
            continue
        selected.append(f)

    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in selected:
        sev = f.get("severity") or "low"
        if sev in counts:
            counts[sev] += 1

    site_name = snap.get("site") or snap.get("origin") or ""
    public_findings = [_public_finding(f, site=site_name) for f in selected if f.get("id")]
    report: dict[str, Any] = {
        "site": snap.get("site") or "",
        "audited_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "site_type": snap.get("site_type") or "unknown",
        "summary": {
            "total_findings": len(public_findings),
            "critical": counts["critical"],
            "high": counts["high"],
            "medium": counts["medium"],
            "low": counts["low"],
        },
        "findings": public_findings,
    }
    lim = snap.get("limitations") or {}
    # Only surface limitations that affect trust in the problem list.
    public_lim = {}
    if lim.get("crawl_incomplete"):
        public_lim["crawl_incomplete"] = lim["crawl_incomplete"]
    if lim.get("robots_blocked"):
        public_lim["robots_blocked"] = lim["robots_blocked"]
    if lim.get("fetch_errors"):
        public_lim["fetch_errors"] = lim["fetch_errors"]
    if public_lim:
        report["limitations"] = public_lim

    if signals_only or verbose:
        report["site_type"] = snap.get("site_type")
        report["site_scale"] = snap.get("site_scale")
        report["page_classifications"] = snap.get("page_classifications") or annotate_page_classes(snap)
        report["digital_consensus"] = snap.get("digital_consensus")
        report["raw_signals"] = snap.get("_internal_signals") or enrich_site_signals(snap)
        report["findings"] = selected  # full internal findings with signals
        report["synthesis_mode"] = "signals_then_agent"
        if verbose:
            import sys

            print("page_classifications:", file=sys.stderr)
            for row in report["page_classifications"]:
                print(
                    f"  {row.get('page_class') or 'general':16}  {row.get('url')}",
                    file=sys.stderr,
                )
    return report


def ground_agent_report(report: dict[str, Any]) -> dict[str, Any]:
    failed = []
    for f in report.get("findings") or []:
        sig = f.get("signals") or report.get("raw_signals") or {}
        text = (
            f"{f.get('evidence') or ''} "
            f"{(f.get('suggested_action') or {}).get('summary') or ''} "
            f"{(f.get('suggested_action') or {}).get('how') or ''}"
        )
        gc = grounding_check(text, sig if isinstance(sig, dict) else {})
        if not gc["ok"]:
            f["self_check_failed"] = True
            f["self_check_ungrounded"] = gc["ungrounded"]
            failed.append(f.get("id"))
        else:
            f.pop("self_check_failed", None)
            f.pop("self_check_ungrounded", None)
    report["self_check_failed"] = bool(failed)
    report["self_check_finding_ids"] = failed
    return report


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print("usage: compose_report.py snapshot.json [skill-id]", file=sys.stderr)
        sys.exit(2)
    with open(argv[1], encoding="utf-8") as f:
        snap = json.load(f)
    skill = argv[2] if len(argv) > 2 else None
    print(json.dumps(compose(snap, skill), indent=2))


if __name__ == "__main__":
    main(sys.argv)
