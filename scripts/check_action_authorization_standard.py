#!/usr/bin/env python3
"""Validate the S3 action-authorization contract and dispatch import boundary.

The check is stdlib-only and hermetic. With --dispatch-source it parses a
read-only skcapstone dispatch module but never imports or modifies that runtime.

Usage:
  check_action_authorization_standard.py [--repo PATH] [--dispatch-source PATH]
  check_action_authorization_standard.py --self-test

Exit 0 = clean, 1 = finding, 2 = the check could not run.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import tempfile
from pathlib import Path

STANDARD = "standards/ACTION_AUTHORIZATION_STANDARD.md"
ITIL_STANDARD = "standards/ITIL_AND_RUNBOOK_OPERATING_MODEL_STANDARD.md"
UMBRELLA = "standards/AUTONOMY_STANDARD.md"
README = "README.md"
MARKER = "action-authorization-contract"
DENYLISTED_MODULES = {"brain", "brief", "proposer"}

EXPECTED = {
    "schema": "skworld.action-authorization/v1",
    "intent": {
        "schema": "skcapstone.atlas.action-intent/v1",
        "durable_at": "proposal_time",
        "ledger_roles": ["evidence", "queue"],
        "ledger_authorizes": False,
        "binds": ["target", "action", "catalog_generation", "itil_change_id"],
    },
    "approval": {
        "sole_store": "itil_change_fold",
        "decision_store_role": "projection_write_through",
        "resolved_actor_required": True,
    },
    "authorized_event": {
        "sole_appender": "dispatcher",
        "requires_approved_fold": True,
        "required_detail": [
            "itil_change_id",
            "approval_provenance",
            "reclassification",
        ],
    },
    "dispatcher_inputs": {
        "closed": True,
        "allowed": [
            "action_ledger",
            "itil_fold",
            "freeze_readiness",
            "ratified_catalog",
            "postcondition_observation",
        ],
        "excluded": ["model_output", "brain", "brief", "proposal", "activity_stream"],
    },
    "dispatch_reclassification": {
        "function": "policy.classify_change",
        "catalog": "current_ratified",
        "generation_mismatch": "refuse_and_escalate",
        "hardened_class": "refuse_and_escalate",
    },
    "human_gate_relaxation": {
        "mechanism": "catalog_change",
        "code_branch_allowed": False,
        "required_justification": "ledger_lineage_citation",
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
    for section in (
        "intent",
        "approval",
        "authorized_event",
        "dispatcher_inputs",
        "dispatch_reclassification",
        "human_gate_relaxation",
    ):
        actual = contract.get(section)
        if not isinstance(actual, dict):
            findings.append(f"{section}: expected an object")
            continue
        for key, expected in EXPECTED[section].items():
            compare((section, key), expected, actual.get(key))
    return findings


def _authorized_event_findings(event: dict) -> list[str]:
    findings: list[str] = []
    if event.get("state") != "authorized":
        return ["fixture must be an authorized event"]
    if event.get("actor") != "dispatcher":
        findings.append("AUTHORIZED actor must be dispatcher")
    detail = event.get("detail")
    if not isinstance(detail, dict):
        return findings + ["AUTHORIZED detail must be an object"]
    for field in EXPECTED["authorized_event"]["required_detail"]:
        value = detail.get(field)
        if value is None or value == "" or value == {}:
            findings.append(f"AUTHORIZED detail missing {field}")
    provenance = detail.get("approval_provenance")
    if not isinstance(provenance, dict) or provenance.get("change_status") != "approved":
        findings.append("AUTHORIZED approval_provenance must prove an approved fold")
    reclassification = detail.get("reclassification")
    if not isinstance(reclassification, dict) or not reclassification.get("change_class"):
        findings.append("AUTHORIZED reclassification must carry dispatch-time change_class")
    return findings


def _dispatch_import_findings(source: str, filename: str = "dispatch.py") -> list[str]:
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as exc:
        return [f"dispatch source does not parse: {exc}"]
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                leaf = alias.name.rsplit(".", 1)[-1]
                if leaf in DENYLISTED_MODULES:
                    offenders.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            leaf = module.rsplit(".", 1)[-1]
            if leaf in DENYLISTED_MODULES:
                offenders.append(module)
            for alias in node.names:
                if alias.name in DENYLISTED_MODULES:
                    offenders.append(f"{module}.{alias.name}".strip("."))
    if offenders:
        return [
            "dispatch imports excluded brain or propose-path module(s): "
            + ", ".join(sorted(set(offenders)))
        ]
    return []


def _document_findings(root: Path) -> list[str]:
    findings: list[str] = []
    standard_path = root / STANDARD
    if not standard_path.is_file():
        return [f"{STANDARD} is missing"]
    try:
        contract = _read_contract(standard_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        return [f"{STANDARD}: {exc}"]
    findings.extend(_contract_findings(contract))

    umbrella_path = root / UMBRELLA
    if not umbrella_path.is_file():
        findings.append(f"{UMBRELLA} is missing")
    else:
        umbrella = umbrella_path.read_text(encoding="utf-8")
        row_start = "| [ACTION_AUTHORIZATION](./ACTION_AUTHORIZATION_STANDARD.md) |"
        rows = [line for line in umbrella.splitlines() if row_start in line]
        if len(rows) != 1 or "| RATIFIED |" not in rows[0]:
            findings.append("umbrella must contain exactly one RATIFIED S3 constituent row")

    readme_path = root / README
    if not readme_path.is_file():
        findings.append(f"{README} is missing")
    else:
        count = readme_path.read_text(encoding="utf-8").count(
            "./standards/ACTION_AUTHORIZATION_STANDARD.md"
        )
        if count != 1:
            findings.append(f"README must link S3 exactly once, found {count}")

    itil_path = root / ITIL_STANDARD
    if not itil_path.is_file():
        findings.append(f"{ITIL_STANDARD} is missing")
    else:
        text = itil_path.read_text(encoding="utf-8")
        if text.count("**The one approval store.**") != 1:
            findings.append("ITIL standard must contain exactly one one-approval-store rule")
        drift_rows = [
            line
            for line in text.splitlines()
            if line.startswith("| D10 |") and "dispatcher" in line.lower()
        ]
        if len(drift_rows) != 1:
            findings.append("ITIL drift register must contain exactly one dispatcher D10 row")
    return findings


def _findings(root: Path, dispatch_source: Path | None = None) -> list[str]:
    findings = _document_findings(root)
    if dispatch_source is not None:
        if not dispatch_source.is_file():
            findings.append(f"dispatch source is missing: {dispatch_source}")
        else:
            findings.extend(
                _dispatch_import_findings(
                    dispatch_source.read_text(encoding="utf-8"), str(dispatch_source)
                )
            )
    return findings


def _set_path(fixture: dict, path: tuple[str, ...], value: object) -> None:
    target = fixture
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value


def _self_test() -> int:
    ok = True
    print("action-authorization negative controls")

    valid_event = {
        "state": "authorized",
        "actor": "dispatcher",
        "detail": {
            "itil_change_id": "chg-approved",
            "approval_provenance": {"change_status": "approved", "timeline_tail": {}},
            "reclassification": {"change_class": "normal"},
        },
    }
    valid_event_findings = _authorized_event_findings(valid_event)
    if valid_event_findings:
        print(f"  FAIL valid AUTHORIZED fixture did not pass: {valid_event_findings}")
        ok = False

    forged = json.loads(json.dumps(valid_event))
    forged["actor"] = "atlas"
    forged["detail"].pop("approval_provenance")
    forged_findings = _authorized_event_findings(forged)
    forged_hit = any("approval_provenance" in item for item in forged_findings)
    print(
        f"  {'ok  ' if forged_hit else 'FAIL'} negative control: "
        "hand-forged AUTHORIZED lacks approved-fold evidence"
    )
    if not forged_hit:
        print(f"       got: {forged_findings}")
        ok = False

    brain_findings = _dispatch_import_findings("from . import action_ledger, brain\n")
    brain_hit = any("brain" in item for item in brain_findings)
    print(
        f"  {'ok  ' if brain_hit else 'FAIL'} negative control: dispatch imports the brain"
    )
    if not brain_hit:
        print(f"       got: {brain_findings}")
        ok = False

    relaxed = json.loads(json.dumps(EXPECTED))
    _set_path(
        relaxed,
        ("human_gate_relaxation", "required_justification"),
        "none",
    )
    catalog_findings = _contract_findings(relaxed)
    catalog_hit = any("required_justification" in item for item in catalog_findings)
    print(
        f"  {'ok  ' if catalog_hit else 'FAIL'} negative control: "
        "catalog relaxation omits ledger lineage"
    )
    if not catalog_hit:
        print(f"       got: {catalog_findings}")
        ok = False

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "standards").mkdir()
        (root / STANDARD).write_text(
            f"```{MARKER}\n{json.dumps(EXPECTED)}\n```\n", encoding="utf-8"
        )
        (root / UMBRELLA).write_text(
            "| [ACTION_AUTHORIZATION](./ACTION_AUTHORIZATION_STANDARD.md) "
            "| owns | RATIFIED |\n",
            encoding="utf-8",
        )
        (root / README).write_text(
            "[S3](./standards/ACTION_AUTHORIZATION_STANDARD.md)\n", encoding="utf-8"
        )
        (root / ITIL_STANDARD).write_text(
            "**The one approval store.** Rule.\n\n"
            "| D10 | operator loop | dispatcher inserted | shipped |\n",
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
    parser.add_argument(
        "--dispatch-source",
        help="optional read-only path to a runtime dispatch.py for AST boundary checking",
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return _self_test()
    try:
        findings = _findings(
            Path(args.repo).resolve(),
            Path(args.dispatch_source).resolve() if args.dispatch_source else None,
        )
    except OSError as exc:
        print(f"check could not run: {exc}", file=sys.stderr)
        return 2
    if findings:
        print("action-authorization standard: FAIL")
        for finding in findings:
            print(f"  FAIL {finding}")
        return 1
    print("action-authorization standard: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
