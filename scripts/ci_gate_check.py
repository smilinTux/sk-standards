#!/usr/bin/env python3
"""CI gate integrity checker (TESTING_AND_CI_STANDARD §6).

Two modes, answering two different questions:

  sweep   - across repos: which workflows are RED ON MAIN right now?
  audit   - inside one repo: does its CI obey the §6 structural rules?

`sweep` is the monitor (§6.4). It is the one that catches "a gate has been red
for ten hours and two merges landed on top of it". `audit` is the preventive
half (§6.1): it reads the workflow YAML and flags the shapes that PRODUCE
always-red gates, before they do.

Why sweep tracks state
----------------------
It alerts on NEW breakage only, carrying known-red in a state file. A recurring
alert everyone has learned to skip is the same disease the monitor exists to
cure, relocated from CI into the alert channel.

Why sweep separates stale from live
-----------------------------------
A tag-triggered workflow shows its last completed run indefinitely. If the
workflow file was touched AFTER the failing run, someone already fixed it and it
simply has not re-triggered. Compare timestamps, not dates: two repos in the
2026-08-14 sweep were fixed 29 minutes after their failing run, on the same day.

Usage:
  ci_gate_check.py sweep --repos a,b,c [--owner O] [--state PATH]
  ci_gate_check.py audit [--repo PATH]
  ci_gate_check.py --self-test      # negative control: prove the checks can FAIL

Exit 0 = clean, 1 = finding, 2 = the check itself could not run (which is NOT
success: a monitor that cannot run is not a green monitor, §6.1).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - environment problem, not a finding
    yaml = None

DEFAULT_STATE = Path.home() / ".skcapstone" / "state" / "ci-gate-health.json"


# ---------------------------------------------------------------- helpers --

# Absolute fallbacks first, then PATH. A scheduler's PATH is minimal and often
# excludes /home/linuxbrew/... entirely, so resolving by PATH alone is how a job
# that works in a shell silently never runs from cron (see
# OBSERVABILITY_AND_SCHEDULING_STANDARD; sk-alert was unreachable this exact way).
GH_CANDIDATES = ("/usr/bin/gh", "/usr/local/bin/gh", "/home/linuxbrew/.linuxbrew/bin/gh")


def _gh_exe() -> str | None:
    for cand in GH_CANDIDATES:
        if Path(cand).is_file():
            return cand
    return shutil.which("gh")


def gh(args: list[str]) -> object | None:
    """Run gh and parse JSON. None on any failure; never raises."""
    exe = _gh_exe()
    if not exe:
        return None
    try:
        r = subprocess.run([exe, *args], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return None


def load_yaml(text: str) -> dict | None:
    """Parse with duplicate keys FATAL.

    GitHub Actions rejects a duplicate key and the run dies in ~0s with zero
    jobs, which reads as an unexplained failure. yaml.safe_load silently keeps
    the last value, so a plain parse cannot see the bug that killed the run.
    """
    if yaml is None:
        return None

    class DupFatal(yaml.SafeLoader):
        pass

    def no_dup(loader, node, deep=False):
        out = {}
        for k, v in node.value:
            key = loader.construct_object(k, deep=deep)
            if key in out:
                raise ValueError(f"duplicate key {key!r}")
            out[key] = loader.construct_object(v, deep=deep)
        return out

    DupFatal.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, no_dup)
    return yaml.load(text, DupFatal)


# ------------------------------------------------------------------ sweep --

def newest_completed_per_workflow(owner: str, repo: str) -> dict[str, dict]:
    """Newest COMPLETED run per workflow on main. Pending runs are not evidence."""
    rows = gh([
        "run", "list", "--repo", f"{owner}/{repo}", "--branch", "main",
        "--limit", "60", "--json",
        "workflowName,conclusion,status,createdAt,databaseId,url",
    ])
    if not isinstance(rows, list):
        return {}
    out: dict[str, dict] = {}
    for row in rows:
        if row.get("status") == "completed":
            out.setdefault(row.get("workflowName", "?"), row)
    return out


def is_stale(owner: str, repo: str, run: dict) -> bool:
    """True if the workflow file was touched AFTER this run started (§6.2)."""
    meta = gh(["api", f"repos/{owner}/{repo}/actions/runs/{run['databaseId']}"])
    path = meta.get("path") if isinstance(meta, dict) else None
    if not path:
        return False
    commits = gh(["api", f"repos/{owner}/{repo}/commits?path={path}&per_page=1"])
    if not isinstance(commits, list) or not commits:
        return False
    touched = commits[0].get("commit", {}).get("author", {}).get("date", "")
    return bool(touched) and touched > run.get("createdAt", "")


def sweep(owner: str, repos: list[str], state_path: Path) -> int:
    # `gh api user` returns an OBJECT. An earlier version probed with
    # `--jq .login`, which prints a BARE unquoted string: json.loads then throws,
    # the probe reads as "unauthenticated", and sweep exited 2 every single run.
    # It failed closed and loudly, which is the design working, but a monitor that
    # can never run is not a green monitor (TESTING_AND_CI §6.1 rule 6).
    if gh(["api", "user"]) is None:
        print("ci_gate_check: gh missing or unauthenticated; sweep could not run",
              file=sys.stderr)
        return 2

    live: dict[str, str] = {}
    stale: list[str] = []
    unreachable: list[str] = []

    for repo in repos:
        runs = newest_completed_per_workflow(owner, repo)
        if not runs:
            unreachable.append(repo)
            continue
        for wf, run in runs.items():
            if run.get("conclusion") != "failure":
                continue
            key = f"{repo}/{wf}"
            (stale.append(key) if is_stale(owner, repo, run)
             else live.update({key: run.get("url", "")}))

    try:
        known = set(json.loads(state_path.read_text()).get("live", []))
    except (OSError, json.JSONDecodeError):
        known = set()

    new = sorted(set(live) - known)
    fixed = sorted(known - set(live))

    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({"live": sorted(live), "stale": sorted(stale)},
                                     indent=1))

    print(f"red-on-main: {len(live)} live, {len(stale)} stale(already-fixed), "
          f"{len(unreachable)} unreachable")
    for k in sorted(live):
        print(f"  {'NEW ' if k in new else '    '}{k}  {live[k]}")
    for k in fixed:
        print(f"  FIXED {k}")
    if unreachable:
        print(f"  unreachable: {', '.join(unreachable)}")

    if new:
        print(f"\nNEW red gate(s) on main: {', '.join(new)}", file=sys.stderr)
        return 1
    return 0


# ------------------------------------------------------------------ audit --

def audit_workflows(repo: Path) -> list[str]:
    """Structural rules from §6.1 that produce always-red gates. Returns findings."""
    findings: list[str] = []
    wf_dir = repo / ".github" / "workflows"
    if not wf_dir.is_dir():
        return [f"{repo}: no .github/workflows"]

    for wf in sorted(wf_dir.glob("*.y*ml")):
        text = wf.read_text(encoding="utf-8", errors="replace")

        # Duplicate keys: GitHub rejects these and the run dies in ~0s, zero jobs.
        try:
            doc = load_yaml(text)
        except ValueError as exc:
            findings.append(f"{wf.name}: {exc} (GitHub rejects this; run dies in 0s)")
            continue
        if doc is None:
            findings.append(f"{wf.name}: could not parse (pyyaml missing?)")
            continue

        jobs = doc.get("jobs") or {}

        # Unpinned linters: main can go red with no code change.
        for tool in ("ruff", "black", "mypy", "flake8", "isort"):
            if f"pip install {tool}\n" in text or text.rstrip().endswith(f"pip install {tool}"):
                findings.append(
                    f"{wf.name}: `pip install {tool}` is unpinned; a new release can "
                    f"turn main red with no code change (§6.1 rule 4)")

        # Unguarded jobs in a publish graph run on branch pushes they never meant to.
        #
        # Narrow deliberately, because a noisy check is the same disease this
        # standard is about. Both conditions must hold:
        #   1. the workflow can actually fire on a NON-tag push (`on.push.branches`),
        #      so a tags-only publish workflow is never flagged; and
        #   2. the job publishes, rather than merely being the root of the graph.
        #      A root `test` job legitimately has no `needs:`.
        looks_like_release = "publish" in wf.name.lower() or "release" in wf.name.lower()
        on = doc.get("on") or doc.get(True) or {}  # bare `on:` parses as the bool True
        push = on.get("push") if isinstance(on, dict) else None
        fires_on_branch = isinstance(push, dict) and bool(push.get("branches"))

        if looks_like_release and fires_on_branch:
            for name, spec in jobs.items():
                if not isinstance(spec, dict):
                    continue
                publishes = any(
                    kw in name.lower() for kw in ("publish", "upload", "release", "deploy")
                )
                if publishes and not spec.get("needs") and not spec.get("if"):
                    findings.append(
                        f"{wf.name}: job `{name}` publishes but has neither `needs:` nor "
                        f"`if:`, and this workflow fires on branch pushes, so it runs "
                        f"where it was never meant to (§6.1 rule 5)")
    return findings


def audit(repo: Path) -> int:
    findings = audit_workflows(repo)
    if not findings:
        print(f"ci_gate_check: {repo} clean (§6 structural rules)")
        return 0
    print(f"ci_gate_check: {len(findings)} finding(s) in {repo}")
    for f in findings:
        print(f"  {f}")
    return 1


# -------------------------------------------------------------- self-test --

def self_test() -> int:
    """Negative control: a check that cannot fail is not a check (§6.1 rule 6)."""
    ok = True
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        wfd = root / ".github" / "workflows"
        wfd.mkdir(parents=True)

        # 1. clean workflow -> no findings
        (wfd / "ci.yml").write_text(
            "name: ci\non: [push]\njobs:\n  lint:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - run: pip install ruff==0.15.4\n"
        )
        if audit_workflows(root):
            print("  FAIL: clean workflow produced findings"); ok = False
        else:
            print("  ok: clean workflow is clean")

        # 2. unpinned linter -> must be caught
        (wfd / "ci.yml").write_text(
            "name: ci\non: [push]\njobs:\n  lint:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - run: pip install ruff\n"
        )
        if any("unpinned" in f for f in audit_workflows(root)):
            print("  ok: unpinned linter caught")
        else:
            print("  FAIL: unpinned linter NOT caught"); ok = False

        # 3. unguarded publish job on a branch-firing workflow -> must be caught
        (wfd / "ci.yml").unlink()
        (wfd / "publish.yml").write_text(
            "name: publish\non:\n  push:\n    branches: [main]\n    tags: ['v*']\n"
            "jobs:\n  publish-npm:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - run: npm publish\n"
        )
        if any("publishes but has neither" in f for f in audit_workflows(root)):
            print("  ok: unguarded publish job caught")
        else:
            print("  FAIL: unguarded publish job NOT caught"); ok = False

        # 3b. the two documented NON-findings, so the rule stays narrow.
        # A tags-only workflow cannot fire on a branch push.
        (wfd / "publish.yml").write_text(
            "name: publish\non:\n  push:\n    tags: ['v*']\n"
            "jobs:\n  publish-npm:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - run: npm publish\n"
        )
        if any("publishes but has neither" in f for f in audit_workflows(root)):
            print("  FAIL: flagged a tags-only workflow (false positive)"); ok = False
        else:
            print("  ok: tags-only workflow not flagged")

        # A root `test` job legitimately has no `needs:`.
        (wfd / "publish.yml").write_text(
            "name: publish\non:\n  push:\n    branches: [main]\n"
            "jobs:\n  test:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - run: pytest\n"
        )
        if any("publishes but has neither" in f for f in audit_workflows(root)):
            print("  FAIL: flagged a root test job (false positive)"); ok = False
        else:
            print("  ok: root test job not flagged")

        # 4. duplicate key -> must be caught (the 0s-failure shape)
        (wfd / "publish.yml").write_text(
            "name: publish\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n        with:\n"
            "          fetch-depth: 0\n        with:\n          fetch-tags: true\n"
        )
        if any("duplicate key" in f for f in audit_workflows(root)):
            print("  ok: duplicate key caught")
        else:
            print("  FAIL: duplicate key NOT caught"); ok = False

    # 5. The gh() JSON contract. The sweep preflight is a live-network call, so it
    #    cannot be exercised hermetically; what CAN be pinned is the shape it
    #    depends on. A `--jq .login` probe returns a BARE string, which json.loads
    #    rejects, so the preflight reported "unauthenticated" on a perfectly
    #    authenticated host and sweep exited 2 on every run. Pin the rule that
    #    broke it: gh() only ever accepts JSON, so callers must request an object.
    if json_is_object('{"login":"x"}') and not json_is_object("x"):
        print("  ok: gh() JSON contract (bare --jq output is not valid JSON)")
    else:
        print("  FAIL: gh() JSON contract wrong"); ok = False

    # 6. gh must resolve without relying on PATH (scheduler PATH is minimal).
    if _gh_exe() is None:
        print("  ok: gh absent here, resolver returned None rather than guessing")
    elif Path(_gh_exe()).is_absolute():
        print(f"  ok: gh resolved to an absolute path ({_gh_exe()})")
    else:
        print("  FAIL: gh resolved to a relative path"); ok = False

    print("self-test:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def json_is_object(text: str) -> bool:
    """True if text parses as JSON. Used by the self-test to pin gh()'s contract."""
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False


# ------------------------------------------------------------------- main --

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", nargs="?", choices=["sweep", "audit"], default="audit")
    ap.add_argument("--owner", default="smilinTux")
    ap.add_argument("--repos", default="", help="comma-separated repo names (sweep)")
    ap.add_argument("--repo", default=".", type=Path, help="repo path (audit)")
    ap.add_argument("--state", default=DEFAULT_STATE, type=Path)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()
    if a.mode == "sweep":
        repos = [r.strip() for r in a.repos.split(",") if r.strip()]
        if not repos:
            print("ci_gate_check: sweep needs --repos", file=sys.stderr)
            return 2
        return sweep(a.owner, repos, a.state)
    return audit(a.repo)


if __name__ == "__main__":
    sys.exit(main())
