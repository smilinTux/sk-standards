#!/usr/bin/env python3
"""Validate the S7 self-healing tiers contract and repair-target ceiling.

Usage:
  check_self_healing_tiers_standard.py [--repo PATH]
  check_self_healing_tiers_standard.py --probe-repair HEALER:TARGET
  check_self_healing_tiers_standard.py --self-test

Exit 0 = clean, 1 = finding, 2 = the check could not run.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

STANDARD = "standards/SELF_HEALING_TIERS_STANDARD.md"
UMBRELLA = "standards/AUTONOMY_STANDARD.md"
README = "README.md"
MARKER = "self-healing-tiers-contract"

FORBIDDEN = [
    "own_gate",
    "freeze_file",
    "protected_manifest",
    "protected_manifest_floor",
]
EXACT_FORBIDDEN_PATHS = [
    "scripts/check_self_healing_tiers_standard.py",
    "src/skharness/autocode/protected.py",
]
FLOOR_CLASSES = [
    "detector",
    "merge_choke_point",
    "fleet_store",
    "plane_files",
    "rubric",
    "guard_modules",
    "coverage_configuration",
]
EXPECTED = {
    "schema": "skworld.self-healing-tiers/v1",
    "global_forbidden": FORBIDDEN,
    "exact_forbidden_paths": EXACT_FORBIDDEN_PATHS,
    "protected_floor_classes": FLOOR_CLASSES,
    "healers": {
        "self_healing_doctor": {
            "tier": "local_agent_maintenance",
            "scope": "one_agent_own_home_and_process",
            "cadence_seconds": 300,
            "repairs": [
                "create_required_home_dirs",
                "rebuild_memory_index",
                "create_default_sync_manifest",
                "reprobe_llm_backends",
                "restart_inotify_observer",
            ],
            "report_only": ["profile_freshness"],
            "readiness": "not_required_for_exact_bounded_local_repairs",
            "action_contract": "below_contract_while_scope_remains_local",
        },
        "fleet_converge": {
            "tier": "node_mechanical",
            "scope": "one_locally_placed_systemd_unit_per_node",
            "cadence_seconds": 30,
            "repairs": ["start_unit", "restart_failed_unit"],
            "requires": [
                "actuation_ready_and_not_frozen",
                "node_actuate_opt_in",
                "restart_policy_on_failure",
                "exponential_backoff",
            ],
            "action_contract": "below_itil_contract_for_bounded_mechanical_restart",
        },
        "error_queue": {
            "tier": "bounded_same_call_replay",
            "scope": "same_error_entry_to_injected_handler",
            "handler_must_replay_original_call": True,
            "max_retries": 3,
            "backoff": "exponential",
            "diagnoses": False,
            "chooses_different_remedy": False,
            "mints_authority": False,
            "handler_revalidates_current_gates": True,
        },
    },
}


def _read_contract(text: str) -> dict:
    match = re.search(rf"```{re.escape(MARKER)}\s*\n(.*?)\n```", text, re.DOTALL)
    if not match:
        raise ValueError(f"missing fenced {MARKER} contract")
    value = json.loads(match.group(1))
    if not isinstance(value, dict):
        raise ValueError("contract root must be an object")
    return value


def _contract_findings(contract: dict) -> list[str]:
    findings: list[str] = []

    def compare(path: tuple[str, ...], expected: object, actual: object) -> None:
        if actual != expected:
            findings.append(f"{'.'.join(path)}: expected {expected!r}, found {actual!r}")

    compare(("schema",), EXPECTED["schema"], contract.get("schema"))
    compare(("global_forbidden",), FORBIDDEN, contract.get("global_forbidden"))
    compare(
        ("exact_forbidden_paths",),
        EXACT_FORBIDDEN_PATHS,
        contract.get("exact_forbidden_paths"),
    )
    compare(
        ("protected_floor_classes",),
        FLOOR_CLASSES,
        contract.get("protected_floor_classes"),
    )
    healers = contract.get("healers")
    if not isinstance(healers, dict):
        return findings + ["healers: expected an object"]
    if set(healers) != set(EXPECTED["healers"]):
        findings.append(
            f"healers: expected exactly {sorted(EXPECTED['healers'])}, found {sorted(healers)}"
        )
    for name, expected in EXPECTED["healers"].items():
        actual = healers.get(name)
        if not isinstance(actual, dict):
            findings.append(f"healers.{name}: expected an object")
            continue
        for key, value in expected.items():
            compare(("healers", name, key), value, actual.get(key))
        for forbidden in FORBIDDEN:
            if forbidden in actual.get("repairs", []):
                findings.append(f"healers.{name}.repairs includes forbidden target {forbidden}")
    return findings


def _repair_findings(contract: dict, healer: str, target: str) -> list[str]:
    healers = contract.get("healers", {})
    if healer not in healers:
        return [f"unknown healer {healer!r}"]
    forbidden = contract.get("global_forbidden", [])
    if target in forbidden:
        return [f"healer {healer} cannot repair forbidden target {target}"]
    normalized = target.replace("\\", "/").lstrip("./")
    exact_paths = contract.get("exact_forbidden_paths", [])
    if normalized in exact_paths:
        return [f"healer {healer} cannot repair exact forbidden path {normalized}"]
    if target in contract.get("protected_floor_classes", []):
        return [f"healer {healer} cannot repair protected-floor class {target}"]
    if target not in healers[healer].get("repairs", []):
        return [f"healer {healer} repair target {target} is outside its ratified scope"]
    return []


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
        row = "| [SELF_HEALING_TIERS](./SELF_HEALING_TIERS_STANDARD.md) |"
        matches = [line for line in umbrella_path.read_text(encoding="utf-8").splitlines() if row in line]
        if len(matches) != 1 or "| RATIFIED |" not in matches[0]:
            findings.append("umbrella must contain exactly one RATIFIED S7 constituent row")

    readme_path = root / README
    if not readme_path.is_file():
        findings.append(f"{README} is missing")
    else:
        count = readme_path.read_text(encoding="utf-8").count(
            "./standards/SELF_HEALING_TIERS_STANDARD.md"
        )
        if count != 1:
            findings.append(f"README must link S7 exactly once, found {count}")
    return findings


def _self_test() -> int:
    ok = True
    print("self-healing-tiers negative controls")

    for healer, target, label in (
        (
            "self_healing_doctor",
            "scripts/check_self_healing_tiers_standard.py",
            "healer repairs its exact own-gate path",
        ),
        (
            "fleet_converge",
            "src/skharness/autocode/protected.py",
            "healer repairs the exact S5 protected detector path",
        ),
        ("self_healing_doctor", "own_gate", "healer repairs symbolic own gate"),
        (
            "fleet_converge",
            "protected_manifest_floor",
            "healer repairs symbolic protected-floor target",
        ),
    ):
        findings = _repair_findings(EXPECTED, healer, target)
        hit = any("cannot repair" in item for item in findings)
        print(f"  {'ok  ' if hit else 'FAIL'} negative control: {label}")
        if not hit:
            print(f"       got: {findings}")
            ok = False

    fixture = json.loads(json.dumps(EXPECTED))
    fixture["healers"]["self_healing_doctor"]["repairs"].append("own_gate")
    findings = _contract_findings(fixture)
    hit = any("forbidden target own_gate" in item for item in findings)
    print(f"  {'ok  ' if hit else 'FAIL'} negative control: contract grants own-gate repair")
    if not hit:
        print(f"       got: {findings}")
        ok = False

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "standards").mkdir()
        (root / STANDARD).write_text(
            f"```{MARKER}\n{json.dumps(EXPECTED)}\n```\n", encoding="utf-8"
        )
        (root / UMBRELLA).write_text(
            "| [SELF_HEALING_TIERS](./SELF_HEALING_TIERS_STANDARD.md) "
            "| owns | RATIFIED |\n",
            encoding="utf-8",
        )
        (root / README).write_text(
            "[S7](./standards/SELF_HEALING_TIERS_STANDARD.md)\n", encoding="utf-8"
        )
        valid = _findings(root)
        if valid:
            print(f"  FAIL valid fixture did not pass: {valid}")
            ok = False

    print("negative control:", "PASS (the gate can fail)" if ok else "BROKEN")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="repository root")
    parser.add_argument(
        "--probe-repair",
        help="validate one proposed HEALER:TARGET repair against the contract",
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return _self_test()
    try:
        root = Path(args.repo).resolve()
        findings = _findings(root)
        if args.probe_repair and not findings:
            if ":" not in args.probe_repair:
                print("check could not run: --probe-repair requires HEALER:TARGET", file=sys.stderr)
                return 2
            healer, target = args.probe_repair.split(":", 1)
            contract = _read_contract((root / STANDARD).read_text(encoding="utf-8"))
            findings.extend(_repair_findings(contract, healer, target))
    except OSError as exc:
        print(f"check could not run: {exc}", file=sys.stderr)
        return 2
    if findings:
        print("self-healing-tiers standard: FAIL")
        for finding in findings:
            print(f"  FAIL {finding}")
        return 1
    print("self-healing-tiers standard: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
