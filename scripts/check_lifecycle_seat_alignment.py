#!/usr/bin/env python3
"""Reject lifecycle roster drift from SKCapstone's canonical seat profile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SEATS = ("link", "mero", "seraph", "niobe", "tank", "atlas")
ROSTER_MARKERS = {
    "link": "skfleet-link.service",
    "mero": "skfleet-mero.service",
    "seraph": "skfleet-seraph.service",
    "niobe": "Niobe fenced consumer",
    "tank": "skfleet-tank.service",
    "atlas": "skfleet-atlas.service",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--roster", type=Path, default=Path("ROSTER.md"))
    parser.add_argument("--skcapstone-profile", type=Path, required=True)
    args = parser.parse_args()

    profile = json.loads(args.skcapstone_profile.read_text(encoding="utf-8"))
    roster = args.roster.read_text(encoding="utf-8")
    if set(profile.get("seats", {})) != set(SEATS):
        raise SystemExit("SKCapstone profile does not contain the canonical six seats")
    for seat in SEATS:
        if profile["seats"][seat].get("cadence_seconds") != 300:
            raise SystemExit(f"{seat} cadence is not 300 seconds")
        row = next(
            (line for line in roster.splitlines() if ROSTER_MARKERS[seat] in line),
            "",
        )
        if "Every 5 minutes" not in row:
            raise SystemExit(f"ROSTER cadence diverges for {seat}")
    expected = {
        "default_model_route": "sk-codex-mid",
        "default_model_profile": "gpt-5.6-luna",
        "model_escalation_policy": {
            "scope": "card",
            "mode": "opt_in",
            "automatic": False,
        },
    }
    for key, value in expected.items():
        if profile.get(key) != value:
            raise SystemExit(f"SKCapstone model contract diverges at {key}")
    print("lifecycle seat alignment: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
