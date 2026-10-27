#!/usr/bin/env python3
import sys
from pathlib import Path

ORCH = Path(__file__).resolve().parents[2] / "audit-orchestrator" / "scripts"
sys.path.insert(0, str(ORCH))
from run_audit import main  # noqa: E402

SKILL = "crawl-access-audit"

if __name__ == "__main__":
    rest = sys.argv[1:]
    if rest and not rest[0].startswith("-"):
        main([sys.argv[0], rest[0], "--skill", SKILL, *rest[1:]])
    else:
        main([sys.argv[0], *rest, "--skill", SKILL])
