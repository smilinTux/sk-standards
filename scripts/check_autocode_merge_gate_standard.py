#!/usr/bin/env python3
"""Validate the machine-readable contract in the S5 autocode merge standard.

Runtime repositories remain responsible for resolving imported symbols and
exercising the real verdict boundary. This stdlib-only check makes the policy
contract, README index, and umbrella status mechanically stable.

Usage:
  check_autocode_merge_gate_standard.py [--repo PATH]
  check_autocode_merge_gate_standard.py --self-test

Exit 0 = clean, 1 = finding, 2 = the check could not run.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

STANDARD = "standards/AUTOCODE_MERGE_GATE_STANDARD.md"
UMBRELLA = "standards/AUTONOMY_STANDARD.md"
README = "README.md"
MARKER = "autocode-merge-gate-contract"

FLOOR_CLASSES = [
    "detector",
    "merge_choke_point",
    "fleet_store",
    "plane_files",
    "rubric",
    "guard_modules",
    "coverage_configuration",
]
COVERAGE_CHECKS = [
    "delete_preexisting_report",
    "successful_exit_code",
    "fresh_report_mtime",
    "changed_source_present",
]
EXPECTED = {
    "schema": "skworld.autocode-merge-gate/v1",
    "merge_gate": {
        "symbol": "twin_gate_passed",
        "binding": "import_identity",
        "paths": ["ralph", "ratify"],
    },
    "grader": {
        "capability_class": "m",
        "card_selectable": False,
        "inherits_build_class": False,
    },
    "protected_manifest": {
        "fail_closed": True,
        "floor_policy": "append_only",
        "floor_classes": FLOOR_CLASSES,
    },
    "diff_coverage": {"required_checks": COVERAGE_CHECKS},
    "activity": {"authority": "observation", "control_input": False},
    "run_record": {
        "required_at": "every_verdict",
        "content_addressed": True,
        "hash_must_verify": True,
        "paths": ["ralph", "ratify"],
    },
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
    for section in (
        "merge_gate",
        "grader",
        "protected_manifest",
        "diff_coverage",
        "activity",
        "run_record",
    ):
        actual = contract.get(section)
        if not isinstance(actual, dict):
            findings.append(f"{section}: expected an object")
            continue
        for key, expected in EXPECTED[section].items():
            value = actual.get(key)
            path = (section, key)
            if path in {
                ("protected_manifest", "floor_classes"),
                ("diff_coverage", "required_checks"),
            }:
                if not isinstance(value, list):
                    findings.append(f"{'.'.join(path)}: expected a list")
                    continue
                missing = [item for item in expected if item not in value]
                if missing:
                    findings.append(
                        f"{'.'.join(path)}: missing required item(s): {', '.join(missing)}"
                    )
                if len(value) != len(set(value)):
                    findings.append(f"{'.'.join(path)}: duplicate items are not allowed")
                continue
            compare(path, expected, value)
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
            "| [AUTOCODE_MERGE_GATE]"
            "(./AUTOCODE_MERGE_GATE_STANDARD.md) |"
        )
        matching = [line for line in umbrella.splitlines() if expected_row in line]
        if len(matching) != 1 or "| RATIFIED |" not in matching[0]:
            findings.append("umbrella must contain exactly one RATIFIED S5 constituent row")

    readme_path = root / README
    if not readme_path.is_file():
        findings.append(f"{README} is missing")
    else:
        readme = readme_path.read_text(encoding="utf-8")
        count = readme.count("./standards/AUTOCODE_MERGE_GATE_STANDARD.md")
        if count != 1:
            findings.append(f"README must link S5 exactly once, found {count}")
    return findings


def _set_path(fixture: dict, path: tuple[str, ...], value: object) -> None:
    target = fixture
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value


def _self_test() -> int:
    cases = (
        (
            "second gate implementation replaces import identity",
            ("merge_gate", "binding"),
            "reimplemented",
            "merge_gate.binding",
        ),
        (
            "protected floor entry deleted",
            ("protected_manifest", "floor_classes"),
            FLOOR_CLASSES[:-1],
            "protected_manifest.floor_classes",
        ),
        (
            "verdict allowed without a RunRecord",
            ("run_record", "required_at"),
            "optional",
            "run_record.required_at",
        ),
    )
    ok = True
    print("autocode-merge-gate negative controls")
    for name, path, bad_value, expected_finding in cases:
        fixture = json.loads(json.dumps(EXPECTED))
        _set_path(fixture, path, bad_value)
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
            "| [AUTOCODE_MERGE_GATE]"
            "(./AUTOCODE_MERGE_GATE_STANDARD.md) | owns | RATIFIED |\n",
            encoding="utf-8",
        )
        (root / README).write_text(
            "[S5](./standards/AUTOCODE_MERGE_GATE_STANDARD.md)\n",
            encoding="utf-8",
        )
        valid_findings = _findings(root)
        if valid_findings:
            print(f"  FAIL valid fixture did not pass: {valid_findings}")
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
        print("autocode-merge-gate standard: FAIL")
        for finding in findings:
            print(f"  FAIL {finding}")
        return 1
    print("autocode-merge-gate standard: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
