#!/usr/bin/env python3
"""Entrypoint CLI: crawl URL → problem list JSON on stdout."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compose_report import compose, ground_agent_report
from crawl_site import crawl


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(
            "usage: run_audit.py <url> [--skill skill-id] [--snapshot out.json] "
            "[--from-snapshot snap.json] [--verbose] [--signals-only] [--ground-report report.json]",
            file=sys.stderr,
        )
        sys.exit(2)
    skill = None
    snap_path = None
    from_snap = None
    signals_only = False
    verbose = False
    ground_path = None
    positional: list[str] = []
    args = argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--skill" and i + 1 < len(args):
            skill = args[i + 1]
            i += 2
            continue
        if args[i] == "--snapshot" and i + 1 < len(args):
            snap_path = args[i + 1]
            i += 2
            continue
        if args[i] == "--from-snapshot" and i + 1 < len(args):
            from_snap = args[i + 1]
            i += 2
            continue
        if args[i] == "--signals-only":
            signals_only = True
            i += 1
            continue
        if args[i] == "--verbose":
            verbose = True
            i += 1
            continue
        if args[i] == "--ground-report" and i + 1 < len(args):
            ground_path = args[i + 1]
            i += 2
            continue
        positional.append(args[i])
        i += 1
    if ground_path:
        report = json.loads(Path(ground_path).read_text(encoding="utf-8"))
        print(json.dumps(ground_agent_report(report), indent=2))
        return
    if from_snap:
        snap = json.loads(Path(from_snap).read_text(encoding="utf-8"))
    else:
        if not positional:
            print("url required unless --from-snapshot / --ground-report is set", file=sys.stderr)
            sys.exit(2)
        snap = crawl(positional[0])
        if snap_path:
            Path(snap_path).write_text(json.dumps(snap, indent=2), encoding="utf-8")
    print(json.dumps(compose(snap, skill, signals_only=signals_only, verbose=verbose), indent=2))


if __name__ == "__main__":
    main(sys.argv)
