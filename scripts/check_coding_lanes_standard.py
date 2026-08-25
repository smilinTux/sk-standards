#!/usr/bin/env python3
"""Validate the S6 coding-lanes contract and maintained brief vocabulary.

The check is stdlib-only and hermetic. Runtime repositories remain responsible
for exercising their real spawn guards and controller lifecycle.

Usage:
  check_coding_lanes_standard.py [--repo PATH]
  check_coding_lanes_standard.py --self-test

Exit 0 = clean, 1 = finding, 2 = the check could not run.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
import tempfile
from itertools import product
from pathlib import Path

STANDARD = "standards/CODING_LANES_STANDARD.md"
UMBRELLA = "standards/AUTONOMY_STANDARD.md"
ADR = "decisions/ADR-0002-two-coding-lanes.md"
README = "README.md"
MARKER = "coding-lanes-contract"

# Encoded fragments keep the forbidden retired literals out of maintained
# standards, scripts, and templates while still making their reintroduction red.
RETIRED_PHRASES = (
    "review" + "-verdict " + "PASS",
    "content-addressed " + "manifest bundle",
)

EXPECTED = {
    "schema": "skworld.coding-lanes/v1",
    "lane_1": {
        "driver": "human",
        "controller": "versioned_pool_controller",
        "harness": "pi",
        "guards": ["profile", "repo_allowlist_deny_all", "git_ref", "session_name"],
        "teardown": "transcript_before_stop",
        "activity_authority": "observation",
        "ralph_loop": False,
    },
    "lane_2": {
        "driver": "managed_orchestrator",
        "task_plane": "skharness",
        "action_authorization_required": True,
        "operator_flags": ["live_execution", "automerge_repos"],
    },
    "router": {
        "predicates": [
            "executable_acceptance",
            "no_midflight_steering",
            "enrolled_repo",
        ],
        "all_true": "lane_2",
        "otherwise": "lane_1",
    },
    "shared": ["coord_card", "imported_twin_gate", "run_record_vocabulary"],
    "context": {
        "lane_1": "operator_context_allowed",
        "lane_2": "lean_sandbox",
    },
    "fleet_codex_meaning": "skgateway_model_identity",
    "brief_globs": ["templates/*.md"],
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


def _route(contract: dict, executable: bool, no_steering: bool, enrolled: bool) -> str:
    router = contract.get("router", {})
    return router.get("all_true") if all((executable, no_steering, enrolled)) else router.get(
        "otherwise"
    )


def _contract_findings(contract: dict) -> list[str]:
    findings: list[str] = []

    def compare(path: tuple[str, ...], expected: object, actual: object) -> None:
        label = ".".join(path)
        if actual != expected:
            findings.append(f"{label}: expected {expected!r}, found {actual!r}")

    compare(("schema",), EXPECTED["schema"], contract.get("schema"))
    for section in ("lane_1", "lane_2", "router", "context"):
        actual = contract.get(section)
        if not isinstance(actual, dict):
            findings.append(f"{section}: expected an object")
            continue
        for key, expected in EXPECTED[section].items():
            compare((section, key), expected, actual.get(key))
    for key in ("shared", "fleet_codex_meaning", "brief_globs"):
        compare((key,), EXPECTED[key], contract.get(key))

    for executable, no_steering, enrolled in product((False, True), repeat=3):
        expected = "lane_2" if all((executable, no_steering, enrolled)) else "lane_1"
        actual = _route(contract, executable, no_steering, enrolled)
        if actual != expected:
            bits = f"{int(executable)}{int(no_steering)}{int(enrolled)}"
            findings.append(f"router truth table {bits}: expected {expected!r}, found {actual!r}")
    return findings


def _brief_paths(root: Path, globs: list[str]) -> list[Path]:
    found: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if any(fnmatch.fnmatch(rel, pattern) for pattern in globs):
            found.append(path)
    return sorted(set(found))


def _vocabulary_findings(root: Path, globs: list[str]) -> list[str]:
    findings: list[str] = []
    paths = _brief_paths(root, globs)
    if not paths:
        return [f"maintained brief globs matched no files: {globs}"]
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        for phrase in RETIRED_PHRASES:
            if phrase in text:
                findings.append(
                    f"maintained brief {path.relative_to(root)} uses retired private vocabulary"
                )
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
    globs = contract.get("brief_globs")
    if isinstance(globs, list) and all(isinstance(value, str) for value in globs):
        findings.extend(_vocabulary_findings(root, globs))

    umbrella_path = root / UMBRELLA
    if not umbrella_path.is_file():
        findings.append(f"{UMBRELLA} is missing")
    else:
        umbrella = umbrella_path.read_text(encoding="utf-8")
        expected_row = "| [CODING_LANES](./CODING_LANES_STANDARD.md) |"
        matching = [line for line in umbrella.splitlines() if expected_row in line]
        if len(matching) != 1 or "| RATIFIED |" not in matching[0]:
            findings.append("umbrella must contain exactly one RATIFIED S6 constituent row")

    readme_path = root / README
    if not readme_path.is_file():
        findings.append(f"{README} is missing")
    else:
        readme = readme_path.read_text(encoding="utf-8")
        count = readme.count("./standards/CODING_LANES_STANDARD.md")
        if count != 1:
            findings.append(f"README must link S6 exactly once, found {count}")

    adr_path = root / ADR
    if not adr_path.is_file():
        findings.append(f"{ADR} is missing")
    else:
        adr = adr_path.read_text(encoding="utf-8")
        if "**Status:** Accepted" not in adr:
            findings.append("ADR-0002 must be Accepted")
        if "**Extends:** [`ADR-0001`]" not in adr:
            findings.append("ADR-0002 must extend ADR-0001")
    return findings


def _write_valid_fixture(root: Path) -> None:
    (root / "standards").mkdir(parents=True)
    (root / "decisions").mkdir(parents=True)
    (root / "templates").mkdir(parents=True)
    (root / STANDARD).write_text(
        f"```{MARKER}\n{json.dumps(EXPECTED)}\n```\n",
        encoding="utf-8",
    )
    (root / UMBRELLA).write_text(
        "| [CODING_LANES](./CODING_LANES_STANDARD.md) | owns | RATIFIED |\n",
        encoding="utf-8",
    )
    (root / README).write_text(
        "[S6](./standards/CODING_LANES_STANDARD.md)\n", encoding="utf-8"
    )
    (root / ADR).write_text(
        "**Status:** Accepted\n**Extends:** [`ADR-0001`](./ADR-0001.md)\n",
        encoding="utf-8",
    )
    (root / "templates" / "brief.md").write_text(
        "Record the twin-gate verdict and RunRecord content hash.\n",
        encoding="utf-8",
    )


def _self_test() -> int:
    ok = True
    print("coding-lanes negative controls")

    bad_router = json.loads(json.dumps(EXPECTED))
    bad_router["router"]["otherwise"] = "lane_2"
    router_findings = _contract_findings(bad_router)
    router_hit = any("router truth table" in finding for finding in router_findings)
    print(f"  {'ok  ' if router_hit else 'FAIL'} negative control: router needs all three predicates")
    ok &= router_hit

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_valid_fixture(root)
        valid_findings = _findings(root)
        if valid_findings:
            print(f"  FAIL valid fixture did not pass: {valid_findings}")
            ok = False

        brief = root / "templates" / "brief.md"
        brief.write_text(
            "Private label: " + RETIRED_PHRASES[0] + "\n",
            encoding="utf-8",
        )
        findings = _findings(root)
        hit = any("retired private vocabulary" in finding for finding in findings)
        print(
            f"  {'ok  ' if hit else 'FAIL'} negative control: retired phrase in maintained brief"
        )
        if not hit:
            print(f"       got: {findings}")
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
        print("coding-lanes standard: FAIL")
        for finding in findings:
            print(f"  FAIL {finding}")
        return 1
    print("coding-lanes standard: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
