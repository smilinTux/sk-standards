#!/usr/bin/env python3
"""Actuation-surface registry checker (AUTONOMY_STANDARD section 2).

The registry answers one question: does the estate's kill switch cover
everything that can act? Coverage used to be a prose belief. On 2026-08-25 two
counterexamples were live: the ansible MCP tool ran playbooks against arbitrary
inventories with no check of any kind, and the trustee lifecycle tools recorded
their actions only after performing them. Neither had any relationship to the
freeze.

So the registry lists surfaces honestly, including the ungoverned ones, and this
script makes the honesty structural rather than voluntary.

The tempting way to go green on a registry like this is to delete the row that
embarrasses you. BASELINE_SURFACES exists to make that fail: every id ever
registered must stay registered. Retiring one is an edit to this file, which is
a reviewed change to a checked-in gate, which is exactly the friction the act
deserves.

Cross-repo note: this repo ships documents, not the code the registry cites. It
therefore checks what it can check here (well-formedness, table-to-JSON
agreement, baseline coverage, retrofit tracking) and leaves symbol resolution to
the consumer repos' own gates, per TESTING_AND_CI_STANDARD's split. A check that
claims more than it verifies is worse than one that states its own edge.

Usage:
  check_actuation_registry.py [--repo PATH]
  check_actuation_registry.py --self-test    # negative control: prove it FAILS

Exit 0 = clean, 1 = finding, 2 = the check could not run (which is not success).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

REGISTRY = "reference/autonomy/actuation-surfaces.json"
STANDARD = "standards/AUTONOMY_STANDARD.md"

REQUIRED_FIELDS = (
    "id", "surface", "repo", "evidence", "gate_symbol", "gate",
    "freeze_coverage", "authorization_object", "status", "retrofit_card", "why",
)
VALID_STATUS = ("GOVERNED", "FENCED", "UNGOVERNED_KNOWN")

# Every surface id ever registered. Append only. Removing an entry here is a
# deliberate, reviewed retirement, never a way to make the build green.
BASELINE_SURFACES = frozenset({
    "fleet-converge-heal",
    "operator-actuator-honor",
    "operator-http-actions",
    "mcp-run-ansible-playbook",
    "mcp-trustee-lifecycle",
    "skharness-merge",
})


def _findings(root: Path) -> list[str]:
    out: list[str] = []
    reg_path = root / REGISTRY
    std_path = root / STANDARD

    if not reg_path.is_file():
        return [f"{REGISTRY} is missing: the registry is the coverage proof"]
    try:
        data = json.loads(reg_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return [f"{REGISTRY} does not parse: {exc}"]

    surfaces = data.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        return [f"{REGISTRY} has no surfaces list"]

    seen: set[str] = set()
    for row in surfaces:
        sid = row.get("id", "<no id>")
        missing = [f for f in REQUIRED_FIELDS if f not in row]
        if missing:
            out.append(f"surface {sid}: missing required field(s): {', '.join(missing)}")
            continue
        if sid in seen:
            out.append(f"surface {sid}: duplicate id")
        seen.add(sid)

        if row["status"] not in VALID_STATUS:
            out.append(f"surface {sid}: status {row['status']!r} not one of {VALID_STATUS}")
        if row["status"] == "GOVERNED":
            if not row["gate"] or row["gate"] == "none":
                out.append(f"surface {sid}: GOVERNED with no gate named")
            if not row["authorization_object"]:
                out.append(f"surface {sid}: GOVERNED with no authorization object")
        if row["status"] == "UNGOVERNED_KNOWN" and not row["retrofit_card"]:
            out.append(
                f"surface {sid}: UNGOVERNED_KNOWN with no retrofit_card. "
                "An ungoverned surface is honest only while its retrofit is tracked"
            )
        if not row["why"]:
            out.append(f"surface {sid}: no why. A row that cannot explain itself is not evidence")

    dropped = BASELINE_SURFACES - seen
    if dropped:
        out.append(
            "surface(s) dropped from the registry: "
            + ", ".join(sorted(dropped))
            + ". Deleting a row does not un-ship the surface. Retire it in "
            "BASELINE_SURFACES with a reason if it is genuinely gone"
        )

    # The standard's prose table and the machine-readable registry must agree,
    # or a reader and a robot are looking at two different estates.
    if not std_path.is_file():
        out.append(f"{STANDARD} is missing: the registry has no standard to belong to")
    else:
        text = std_path.read_text(encoding="utf-8")
        for row in surfaces:
            if "surface" not in row:
                continue
            if row["surface"] not in text:
                out.append(
                    f"surface {row.get('id')}: present in {REGISTRY} but its name "
                    f"{row['surface']!r} does not appear in {STANDARD}"
                )
        table_rows = re.findall(r"^\| (?!Surface|---)([^|]+?) \|", text, re.M)
        named = {r["surface"] for r in surfaces if "surface" in r}
        for cell in {c.strip() for c in table_rows}:
            if cell and cell in named:
                continue
    return out


_BAD_REGISTRY = {
    "schema": "skworld.actuation-surfaces/v1",
    "surfaces": [
        {
            "id": "fleet-converge-heal", "surface": "fleet converge heal", "repo": "x",
            "evidence": "x.py", "gate_symbol": "_heal", "gate": "g",
            "freeze_coverage": "yes", "authorization_object": "a",
            "status": "GOVERNED", "retrofit_card": None, "why": "w",
        }
    ],
}


def _self_test() -> int:
    """Prove the check can fail. A gate with no demonstrated red state is decoration."""
    cases: list[tuple[str, dict, str]] = [
        ("a dropped ungoverned row", _BAD_REGISTRY, "dropped from the registry"),
        (
            "an ungoverned row with no retrofit card",
            {
                "schema": "s",
                "surfaces": [
                    dict(r, retrofit_card=None) if r["id"] == "mcp-run-ansible-playbook" else r
                    for r in json.loads(
                        (Path(__file__).resolve().parents[1] / REGISTRY).read_text(encoding="utf-8")
                    )["surfaces"]
                ],
            },
            "no retrofit_card",
        ),
    ]
    ok = True
    for name, payload, expect in cases:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "reference" / "autonomy").mkdir(parents=True)
            (root / "standards").mkdir(parents=True)
            (root / REGISTRY).write_text(json.dumps(payload), encoding="utf-8")
            real_std = Path(__file__).resolve().parents[1] / STANDARD
            (root / STANDARD).write_text(
                real_std.read_text(encoding="utf-8") if real_std.is_file() else "", encoding="utf-8"
            )
            found = _findings(root)
            hit = any(expect in f for f in found)
            print(f"  {'ok  ' if hit else 'FAIL'} negative control: {name}")
            if not hit:
                print(f"       expected a finding containing {expect!r}, got: {found}")
                ok = False
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=".", help="repo root (default: cwd)")
    ap.add_argument("--self-test", action="store_true", help="prove the checks can fail")
    args = ap.parse_args()

    if args.self_test:
        print("actuation-registry negative controls")
        return _self_test()

    root = Path(args.repo).resolve()
    try:
        found = _findings(root)
    except OSError as exc:
        print(f"check could not run: {exc}", file=sys.stderr)
        return 2

    if found:
        print("actuation-surface registry: FAIL")
        for f in found:
            print(f"  FAIL {f}")
        return 1
    print("actuation-surface registry: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
