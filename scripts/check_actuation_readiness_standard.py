#!/usr/bin/env python3
"""Validate the machine-readable contract in the S2 readiness standard.

The standard owns the policy contract. Runtime implementations remain responsible
for testing their imported guard against real stores and status surfaces.

Usage:
  check_actuation_readiness_standard.py [--repo PATH]
  check_actuation_readiness_standard.py --self-test

Exit 0 = clean, 1 = finding, 2 = the check could not run.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

STANDARD = "standards/ACTUATION_READINESS_AND_FREEZE_STANDARD.md"
UMBRELLA = "standards/AUTONOMY_STANDARD.md"
README = "README.md"
MARKER = "actuation-readiness-contract"

EXPECTED = {
    "schema": "skworld.actuation-readiness/v1",
    "is_frozen": {
        "absent": "not_frozen",
        "corrupt": "frozen",
    },
    "actuation_gate": {
        "absent": {"allowed": False, "reason": "unprovisioned"},
        "corrupt": {"allowed": False, "reason": "frozen"},
        "valid_switch_on": {"allowed": False, "reason": "frozen"},
        "valid_switch_off": {"allowed": True, "reason": None},
    },
    "status": {
        "absent": "unprovisioned",
        "corrupt": "frozen",
        "valid_switch_on": "frozen",
        "valid_switch_off": "active",
    },
    "provisioner_role": "human_operator",
    "gate_timing": "before_effect",
}


def _read_contract(text: str) -> dict:
    match = re.search(
        rf"```{re.escape(MARKER)}\s*\n(.*?)\n```",
        text,
        re.DOTALL,
    )
    if not match:
        raise ValueError(f"missing fenced {MARKER} contract")
    value = json.loads(match.group(1))
    if not isinstance(value, dict):
        raise ValueError("contract root must be an object")
    return value


def _contract_findings(contract: dict) -> list[str]:
    findings: list[str] = []

    def compare(path: tuple[str, ...], expected: object, actual: object) -> None:
        label = ".".join(path)
        if actual != expected:
            findings.append(f"{label}: expected {expected!r}, found {actual!r}")

    compare(("schema",), EXPECTED["schema"], contract.get("schema"))
    for section in ("is_frozen", "actuation_gate", "status"):
        actual_section = contract.get(section)
        if not isinstance(actual_section, dict):
            findings.append(f"{section}: expected an object")
            continue
        for key, expected in EXPECTED[section].items():
            compare((section, key), expected, actual_section.get(key))
    compare(
        ("provisioner_role",),
        EXPECTED["provisioner_role"],
        contract.get("provisioner_role"),
    )
    compare(("gate_timing",), EXPECTED["gate_timing"], contract.get("gate_timing"))
    return findings


def _findings(root: Path) -> list[str]:
    standard_path = root / STANDARD
    if not standard_path.is_file():
        return [f"{STANDARD} is missing"]
    try:
        contract = _read_contract(standard_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        return [f"{STANDARD}: {exc}"]

    findings = _contract_findings(contract)

    umbrella_path = root / UMBRELLA
    if not umbrella_path.is_file():
        findings.append(f"{UMBRELLA} is missing")
    else:
        umbrella = umbrella_path.read_text(encoding="utf-8")
        expected_row = (
            "| [ACTUATION_READINESS_AND_FREEZE]"
            "(./ACTUATION_READINESS_AND_FREEZE_STANDARD.md) |"
        )
        matching = [line for line in umbrella.splitlines() if expected_row in line]
        if len(matching) != 1 or "| RATIFIED |" not in matching[0]:
            findings.append("umbrella must contain exactly one RATIFIED S2 constituent row")

    readme_path = root / README
    if not readme_path.is_file():
        findings.append(f"{README} is missing")
    else:
        readme = readme_path.read_text(encoding="utf-8")
        count = readme.count("./standards/ACTUATION_READINESS_AND_FREEZE_STANDARD.md")
        if count != 1:
            findings.append(f"README must link S2 exactly once, found {count}")
    return findings


def _self_test() -> int:
    cases = (
        (
            "absent store allowed instead of refusing unprovisioned",
            ("actuation_gate", "absent"),
            {"allowed": True, "reason": None},
            "actuation_gate.absent",
        ),
        (
            "corrupt store does not refuse frozen",
            ("actuation_gate", "corrupt"),
            {"allowed": True, "reason": None},
            "actuation_gate.corrupt",
        ),
        (
            "status collapses unprovisioned into active",
            ("status", "absent"),
            "active",
            "status.absent",
        ),
    )
    ok = True
    print("actuation-readiness negative controls")
    for name, path, bad_value, expected_finding in cases:
        fixture = json.loads(json.dumps(EXPECTED))
        fixture[path[0]][path[1]] = bad_value
        findings = _contract_findings(fixture)
        hit = any(expected_finding in finding for finding in findings)
        print(f"  {'ok  ' if hit else 'FAIL'} negative control: {name}")
        if not hit:
            print(f"       expected {expected_finding!r}, got {findings}")
            ok = False

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "standards").mkdir()
        (root / STANDARD).write_text(
            f"```{MARKER}\n{json.dumps(EXPECTED)}\n```\n",
            encoding="utf-8",
        )
        (root / UMBRELLA).write_text(
            "| [ACTUATION_READINESS_AND_FREEZE]"
            "(./ACTUATION_READINESS_AND_FREEZE_STANDARD.md) | owns | RATIFIED |\n",
            encoding="utf-8",
        )
        (root / README).write_text(
            "[S2](./standards/ACTUATION_READINESS_AND_FREEZE_STANDARD.md)\n",
            encoding="utf-8",
        )
        if _findings(root):
            print("  FAIL valid fixture did not pass")
            ok = False
    print("negative control:", "PASS (the gate can fail)" if ok else "BROKEN")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="repository root")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return _self_test()
    try:
        findings = _findings(Path(args.repo).resolve())
    except OSError as exc:
        print(f"check could not run: {exc}", file=sys.stderr)
        return 2
    if findings:
        print("actuation-readiness standard: FAIL")
        for finding in findings:
            print(f"  FAIL {finding}")
        return 1
    print("actuation-readiness standard: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
