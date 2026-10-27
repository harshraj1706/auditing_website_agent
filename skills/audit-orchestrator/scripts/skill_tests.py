#!/usr/bin/env python3
"""Verify every marketplace skill CLI returns valid JSON with expected finding IDs."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ORCH = ROOT / "skills" / "audit-orchestrator" / "scripts"
SELFTEST = ORCH / "selftest.py"

SKILLS = [
    ("audit-orchestrator", None, {"FC-ENT-01", "CRA-01"}),
    ("crawl-access-audit", "crawl-access-audit", {"CRA-01"}),
    ("render-quotability-audit", "render-quotability-audit", set()),
    ("freshness-corroboration-audit", "freshness-corroboration-audit", {"FC-ENT-01"}),
    ("engagement-orientation-audit", "engagement-orientation-audit", set()),
    ("nontext-surface-audit", "nontext-surface-audit", set()),
]

URL = "https://example.com"
INTERNAL_LEAKS = (
    "do not attach",
    "never say",
    "never paste",
    "wikipedia is not required",
    "tier 0",
    "tier 1",
    "suta-style",
    "suta",
    "appendix d",
    "delhi–mumbai",
    "delhi-mumbai",
    "akasa",
    "novatech",
    "readme limitation",
    "fabricated prices",
    "see readme",
    "do not treat missing",
    "do not grade",
    "until the origin returns",
    "abort DOM",
    "fail-fast",
    "Severity:",
    "→ low",
)


def _validate_marketplace() -> list[str]:
    errors: list[str] = []
    manifest = ROOT / "marketplace.json"
    if not manifest.is_file():
        return ["marketplace.json missing at repo root"]
    data = json.loads(manifest.read_text(encoding="utf-8"))
    skills = data.get("skills") or []
    if not skills:
        errors.append("marketplace.json: skills[] empty")
    entrypoints = [s for s in skills if s.get("entrypoint")]
    if len(entrypoints) != 1 or entrypoints[0].get("id") != "audit-orchestrator":
        errors.append("marketplace.json: exactly one entrypoint audit-orchestrator required")
    for s in skills:
        sid = s.get("id") or "?"
        rel = s.get("path") or ""
        skill_dir = ROOT / rel
        if not skill_dir.is_dir():
            errors.append(f"{sid}: path missing {rel}")
            continue
        if not (skill_dir / "SKILL.md").is_file():
            errors.append(f"{sid}: missing SKILL.md")
        if sid != "audit-orchestrator":
            if not (skill_dir / "scripts" / "run.py").is_file():
                errors.append(f"{sid}: missing scripts/run.py")
        else:
            if not (skill_dir / "scripts" / "run_audit.py").is_file():
                errors.append(f"{sid}: missing scripts/run_audit.py")
    if not (ROOT / "assets" / "report.schema.json").is_file():
        errors.append("assets/report.schema.json missing")
    if not (ROOT / "README.md").is_file():
        errors.append("README.md missing")
    return errors


def _run_skill(skill_id: str | None) -> dict:
    if skill_id is None:
        cmd = [sys.executable, str(ORCH / "run_audit.py"), URL]
    else:
        cmd = [
            sys.executable,
            str(ROOT / "skills" / skill_id / "scripts" / "run.py"),
            URL,
        ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT), timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(f"{skill_id or 'orchestrator'} exit {proc.returncode}: {proc.stderr[:500]}")
    return json.loads(proc.stdout)


def _validate_report(report: dict, label: str) -> list[str]:
    errors = []
    for key in ("site", "audited_at", "summary", "findings"):
        if key not in report:
            errors.append(f"{label}: missing {key}")
    if "digital_consensus" in report:
        errors.append(f"{label}: default report must not dump digital_consensus (use --verbose)")
    if "raw_signals" in report:
        errors.append(f"{label}: default report must not dump raw_signals (use --verbose)")
    if "problems" in report:
        errors.append(f"{label}: must not emit duplicate problems[] (schema wants findings[] only)")
    if "findings" in report:
        for f in report["findings"]:
            for req in ("id", "title", "severity", "evidence", "suggested_action"):
                if req not in f:
                    errors.append(f"{label}: finding missing {req}")
            sa = f.get("suggested_action") or {}
            if "summary" not in sa or "priority" not in sa:
                errors.append(f"{label}: suggested_action incomplete on {f.get('id')}")
            if "signals" in f or "synthesis" in f:
                errors.append(f"{label}: public finding must not include signals/synthesis dumps")
            how = (sa.get("how") or "").lower()
            ev = (f.get("evidence") or "").lower()
            act = (sa.get("summary") or "").lower()
            blob = f"{how} {ev} {act}"
            if any(x in blob for x in INTERNAL_LEAKS):
                errors.append(f"{label}: dev-note leaked on {f.get('id')}")
    return errors


def main() -> int:
    errors: list[str] = []

    st = subprocess.run([sys.executable, str(SELFTEST)], cwd=str(ORCH))
    if st.returncode != 0:
        errors.append("selftest.py failed")

    merr = _validate_marketplace()
    if merr:
        errors.extend(merr)
    else:
        print("OK marketplace.json + folder layout")

    for label, skill_id, must_have in SKILLS:
        try:
            report = _run_skill(skill_id)
        except Exception as e:
            errors.append(f"{label}: {e}")
            continue
        errors.extend(_validate_report(report, label))
        ids = {f["id"] for f in report.get("findings") or []}
        missing = must_have - ids
        if missing:
            errors.append(f"{label}: expected IDs {sorted(missing)}, got {sorted(ids)}")
        # Skill slices must not leak unrelated families (smoke check).
        if skill_id == "crawl-access-audit" and ids & {"ENG-04", "FC-FRESH-05"}:
            errors.append(f"{label}: leaked non-crawl IDs {ids}")
        if skill_id == "engagement-orientation-audit" and ids & {"CRA-01", "FC-FRESH-05"}:
            errors.append(f"{label}: leaked non-engagement IDs {ids}")
        print(f"OK {label}: {len(ids)} findings {sorted(ids)[:6]}")

    if errors:
        print("SKILL_TESTS FAIL", file=sys.stderr)
        for e in errors:
            print(" -", e, file=sys.stderr)
        return 1
    print("SKILL_TESTS OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
