#!/usr/bin/env python3
"""Check the actuation registry and optional MCP effect-tool source.

The registry is the coverage proof for AUTONOMY_STANDARD section 2 and
ACTUATION_SURFACE_GOVERNANCE_STANDARD. Historical ids remain append-only.
Removed implementations retain a REMOVED row and move to RETIRED_SURFACES with
an explicit reason, so deleting an embarrassing row never makes the gate green.

Usage:
  check_actuation_registry.py [--repo PATH] [--mcp-source PATH ...]
  check_actuation_registry.py --self-test

Exit 0 = clean, 1 = finding, 2 = the check could not run.
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
S4_STANDARD = "standards/ACTUATION_SURFACE_GOVERNANCE_STANDARD.md"
MCP_STANDARD = "standards/MCP_TOOL_OWNERSHIP_STANDARD.md"

REQUIRED_FIELDS = (
    "id",
    "surface",
    "repo",
    "evidence",
    "gate_symbol",
    "gate",
    "freeze_coverage",
    "authorization_object",
    "status",
    "retrofit_card",
    "why",
)
VALID_STATUS = ("GOVERNED", "FENCED", "UNGOVERNED_KNOWN", "REMOVED")

# Active historical ids remain append-only. A removed implementation moves to
# RETIRED_SURFACES with a reason, but its registry row remains present.
BASELINE_SURFACES = frozenset(
    {
        "fleet-converge-heal",
        "operator-actuator-honor",
        "operator-http-actions",
        "mcp-trustee-lifecycle",
        "skharness-merge",
    }
)
RETIRED_SURFACES = {
    "mcp-run-ansible-playbook": (
        "Removed from implementation and MCP registration by skcapstone PR 199, "
        "merge 9c4b8f5dc80288ae892b9bb2587bb540c05e1232; no consumers or successful runs."
    ),
}
TRUSTEE_GATE_EXPECTED = {
    "evidence": (
        "src/skcapstone/mcp_tools/trustee_tools.py, "
        "src/skcapstone/trustee_actuation.py"
    ),
    "gate_symbol": "trustee_actuation.guard",
    "gate": (
        "store.check_actuation_gate (readiness/freeze) then a capauth PDP allow "
        "(trustee.restart/trustee.scale/trustee.rotate capabilities, VERIFIED "
        "enrollment tier, fails closed when capauth is unreachable) then, for "
        "trustee_rotate only, an approved ITIL change (change_is_approved)"
    ),
    "freeze_coverage": "yes",
    "authorization_object": (
        "capauth policy decision; trustee_rotate additionally requires an ITIL "
        "change fold to APPROVED status (narrow stand-in pending "
        "operator_seat/dispatch.py's shared verifier, card cf12b21d)"
    ),
    "status": "GOVERNED",
    "retrofit_card": None,
}

# This explicit, narrow set detects registry-review candidates. It is not an
# authorization policy and MUST NOT be broadened into an unrelated buckets regex.
ACTUATION_VERBS = frozenset(
    {"start", "stop", "restart", "scale", "rotate", "execute", "apply", "send"}
)
TOOL_NAME_RE = re.compile(r"\bname\s*=\s*['\"]([^'\"]+)['\"]")


def _tool_candidates(source: str) -> set[str]:
    names = set(TOOL_NAME_RE.findall(source))
    return {
        name
        for name in names
        if any(part in ACTUATION_VERBS for part in re.split(r"[_-]+", name.lower()))
    }


def _mcp_source_findings(paths: list[Path], registered_ids: set[str]) -> list[str]:
    out: list[str] = []
    direct_names = {
        sid.removeprefix("mcp-").replace("-", "_")
        for sid in registered_ids
        if sid.startswith("mcp-")
    }
    for path in paths:
        if not path.is_file():
            out.append(f"MCP source is missing: {path}")
            continue
        source = path.read_text(encoding="utf-8")
        declared_names = set(TOOL_NAME_RE.findall(source))
        retired_names = {
            sid.removeprefix("mcp-").replace("-", "_") for sid in RETIRED_SURFACES
        }
        for name in sorted(declared_names & retired_names):
            out.append(
                f"retired MCP actuation tool {name!r} is reintroduced in {path}; "
                "retired ids cannot be reused"
            )
        for name in sorted(_tool_candidates(source) - retired_names):
            governed = name in direct_names or (
                name in {"trustee_restart", "trustee_scale", "trustee_rotate"}
                and "mcp-trustee-lifecycle" in registered_ids
            )
            if not governed:
                out.append(
                    f"detected MCP actuation tool {name!r} in {path} has no registry row"
                )
    return out


def _findings(root: Path, mcp_sources: list[Path] | None = None) -> list[str]:
    out: list[str] = []
    reg_path = root / REGISTRY
    std_path = root / STANDARD

    if not reg_path.is_file():
        return [f"{REGISTRY} is missing: the registry is the coverage proof"]
    try:
        data = json.loads(reg_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return [f"{REGISTRY} does not parse: {exc}"]

    if data.get("schema") != "skworld.actuation-surfaces/v1":
        out.append(f"{REGISTRY}: unsupported schema {data.get('schema')!r}")
    surfaces = data.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        return out + [f"{REGISTRY} has no surfaces list"]

    seen: set[str] = set()
    active_ids: set[str] = set()
    for row in surfaces:
        if not isinstance(row, dict):
            out.append("registry surface row must be an object")
            continue
        sid = row.get("id", "<no id>")
        missing = [field for field in REQUIRED_FIELDS if field not in row]
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
            if not row["gate_symbol"]:
                out.append(f"surface {sid}: GOVERNED with no gate_symbol")
            if not row["authorization_object"]:
                out.append(f"surface {sid}: GOVERNED with no authorization object")
        if row["status"] == "UNGOVERNED_KNOWN" and not row["retrofit_card"]:
            out.append(
                f"surface {sid}: UNGOVERNED_KNOWN with no retrofit_card. "
                "An ungoverned surface is honest only while its retrofit is tracked"
            )
        if row["status"] == "REMOVED":
            if sid not in RETIRED_SURFACES:
                out.append(f"surface {sid}: REMOVED without an explicit retirement reason")
            if row["retrofit_card"] is not None:
                out.append(f"surface {sid}: REMOVED must not retain a retrofit_card")
        elif sid in RETIRED_SURFACES:
            out.append(f"surface {sid}: retired baseline id must have status REMOVED")
        else:
            active_ids.add(sid)
        if not row["why"]:
            out.append(f"surface {sid}: no why. A row that cannot explain itself is not evidence")

    expected = BASELINE_SURFACES | RETIRED_SURFACES.keys()
    dropped = expected - seen
    if dropped:
        out.append(
            "surface(s) dropped from the registry: "
            + ", ".join(sorted(dropped))
            + ". Deleting a row does not un-ship or retire the surface. Preserve "
            "the row and record an explicit RETIRED_SURFACES reason if it is gone"
        )
    for sid, reason in RETIRED_SURFACES.items():
        if not isinstance(reason, str) or not reason.strip():
            out.append(f"surface {sid}: retirement reason is empty")

    trustee_rows = [
        row for row in surfaces
        if isinstance(row, dict) and row.get("id") == "mcp-trustee-lifecycle"
    ]
    if len(trustee_rows) == 1:
        trustee = trustee_rows[0]
        for field, expected_value in TRUSTEE_GATE_EXPECTED.items():
            if trustee.get(field) != expected_value:
                out.append(
                    f"surface mcp-trustee-lifecycle: {field} does not match "
                    "the landed PR 200 registry evidence"
                )

    if not std_path.is_file():
        out.append(f"{STANDARD} is missing: the registry has no standard to belong to")
    else:
        text = std_path.read_text(encoding="utf-8")
        for row in surfaces:
            if isinstance(row, dict) and row.get("surface") and row["surface"] not in text:
                out.append(
                    f"surface {row.get('id')}: present in {REGISTRY} but its name "
                    f"{row['surface']!r} does not appear in {STANDARD}"
                )

    s4_path = root / S4_STANDARD
    if not s4_path.is_file():
        out.append(f"{S4_STANDARD} is missing")
    else:
        s4 = s4_path.read_text(encoding="utf-8")
        for phrase in (
            "registered_or_not_shipped",
            '"row_preserved": true',
            '"pdp_unreachable": "deny"',
            '"audit_after_effect_is_gate": false',
        ):
            if phrase not in s4:
                out.append(f"{S4_STANDARD}: missing contract marker {phrase!r}")

    mcp_path = root / MCP_STANDARD
    if not mcp_path.is_file():
        out.append(f"{MCP_STANDARD} is missing")
    elif mcp_path.read_text(encoding="utf-8").count("**Actuation-capable tools.**") != 1:
        out.append("MCP ownership standard must contain exactly one E13 amendment")

    out.extend(_mcp_source_findings(mcp_sources or [], active_ids))
    return out


def _self_test() -> int:
    """Prove row deletion and an unregistered new effect tool both fail."""
    repo = Path(__file__).resolve().parents[1]
    data = json.loads((repo / REGISTRY).read_text(encoding="utf-8"))
    ok = True
    print("actuation-registry negative controls")

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "reference" / "autonomy").mkdir(parents=True)
        (root / "standards").mkdir(parents=True)
        missing = json.loads(json.dumps(data))
        missing["surfaces"] = [
            row for row in missing["surfaces"] if row["id"] != "mcp-run-ansible-playbook"
        ]
        (root / REGISTRY).write_text(json.dumps(missing), encoding="utf-8")
        for document in (STANDARD, S4_STANDARD, MCP_STANDARD):
            (root / document).write_text((repo / document).read_text(encoding="utf-8"), encoding="utf-8")
        found = _findings(root)
        hit = any("mcp-run-ansible-playbook" in item and "dropped" in item for item in found)
        print(f"  {'ok  ' if hit else 'FAIL'} negative control: removed row is deleted")
        if not hit:
            print(f"       got: {found}")
            ok = False

    with tempfile.TemporaryDirectory() as td:
        source = Path(td) / "fixture_tools.py"
        source.write_text("Tool(name='deployment_apply_hotfix', inputSchema={})\n", encoding="utf-8")
        found = _mcp_source_findings([source], BASELINE_SURFACES)
        hit = any("deployment_apply_hotfix" in item and "no registry row" in item for item in found)
        print(
            f"  {'ok  ' if hit else 'FAIL'} negative control: "
            "new MCP actuation tool has no registry row"
        )
        if not hit:
            print(f"       got: {found}")
            ok = False

        source.write_text("Tool(name='run_ansible_playbook', inputSchema={})\n", encoding="utf-8")
        found = _mcp_source_findings([source], BASELINE_SURFACES)
        hit = any("run_ansible_playbook" in item and "cannot be reused" in item for item in found)
        print(
            f"  {'ok  ' if hit else 'FAIL'} negative control: "
            "retired MCP actuation id is reintroduced"
        )
        if not hit:
            print(f"       got: {found}")
            ok = False

    print("negative control:", "PASS (the gate can fail)" if ok else "BROKEN")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="repository root")
    parser.add_argument(
        "--mcp-source",
        action="append",
        default=[],
        help="optional read-only MCP source path to scan for unregistered effect tools",
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return _self_test()
    try:
        found = _findings(
            Path(args.repo).resolve(),
            [Path(path).resolve() for path in args.mcp_source],
        )
    except OSError as exc:
        print(f"check could not run: {exc}", file=sys.stderr)
        return 2
    if found:
        print("actuation-surface registry: FAIL")
        for finding in found:
            print(f"  FAIL {finding}")
        return 1
    print("actuation-surface registry: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
