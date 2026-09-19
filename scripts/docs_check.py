#!/usr/bin/env python3
"""Docs freshness validator (DOCS_FRESHNESS_STANDARD).

Three tiers, in increasing order of value:

  1. presence   - the 7 files SK_REPO_DOC_STANDARD requires exist.
  2. changelog  - a PR touching src/** or pyproject.toml also records a changelog
                  entry: either a new changelog.d/<slug>.md fragment (preferred)
                  or a CHANGELOG.md edit.
  3. evidence   - every check in SOP.md's `docs-evidence` block still exits 0.

Tier 3 is the one that catches drift. Tiers 1 and 2 catch a MISSING doc; tier 3
catches a doc that is present, confident, and WRONG, which is the case that hurts
because it is trusted. A doc nothing executes rots silently.

Usage:
  docs_check.py [--repo PATH] [--tier 1|2|3] [--base-ref REF] [--changed-files FILE]
  docs_check.py --self-test        # negative control: prove the checks can FAIL

Exit 0 = all selected tiers pass, 1 = at least one failure.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REQUIRED = ["README.md", "SOP.md", "SECURITY.md", "CONTRIBUTING.md",
            "CODE_OF_CONDUCT.md", "CHANGELOG.md", "LICENSE"]
CODE_GLOBS = ("src/", "pyproject.toml")
# One file per PR, so two PRs never touch the same lines and the rebase conflict
# that a single shared CHANGELOG.md guarantees becomes structurally impossible.
FRAGMENT_DIR = "changelog.d/"
# Scaffolding inside the fragment dir is not itself an entry. Without this a repo
# that merely HAS a changelog.d/README.md would satisfy the gate for free.
FRAGMENT_NON_ENTRIES = {"README.md", ".gitkeep", ".gitignore"}
EVIDENCE_RE = re.compile(r"<!--\s*docs-evidence(.*?)-->", re.S)
MIN_CHECKS = 3

OK, BAD = "  ok   ", "  FAIL "


def _fail(msg: str) -> bool:
    print(f"{BAD}{msg}")
    return False


def _ok(msg: str) -> bool:
    print(f"{OK}{msg}")
    return True


# ---------------------------------------------------------------- tier 1
def tier1_presence(repo: Path) -> bool:
    good = True
    missing = [f for f in REQUIRED if not (repo / f).exists()]
    for f in REQUIRED:
        if f in missing:
            good = _fail(f"missing required doc: {f}")
    if good:
        _ok(f"all {len(REQUIRED)} required docs present")
    return good


# ---------------------------------------------------------------- tier 2
def _is_fragment(path: str) -> bool:
    """True for a real changelog.d entry, false for the dir's own scaffolding."""
    if not path.startswith(FRAGMENT_DIR):
        return False
    rest = path[len(FRAGMENT_DIR):]
    if not rest or "/" in rest:          # nested dirs are not entries
        return False
    return rest not in FRAGMENT_NON_ENTRIES and rest.endswith(".md")


def tier2_changelog(repo: Path, changed: list[str] | None) -> bool:
    if changed is None:
        return _ok("changelog check skipped (no diff context; not a PR)")
    touches_code = any(c.startswith(CODE_GLOBS) for c in changed)
    if not touches_code:
        return _ok("changelog check n/a (no code touched)")
    fragments = [c for c in changed if _is_fragment(c)]
    if fragments:
        return _ok(f"code changed and changelog fragment added ({fragments[0]})")
    if any(c == "CHANGELOG.md" for c in changed):
        return _ok("code changed and CHANGELOG.md updated")
    return _fail(
        "code under src/ or pyproject.toml changed but no changelog entry was "
        "recorded. Add ONE of:\n"
        "           1. a NEW fragment file  changelog.d/<slug>.md   <- preferred.\n"
        "              One file per PR, so concurrent PRs never conflict on rebase.\n"
        "              e.g.  changelog.d/fix-lane-admission-timeout.md\n"
        "           2. an entry in the shared CHANGELOG.md (still accepted; expect\n"
        "              a rebase conflict when other PRs are open).\n"
        "         Or waive it for a genuinely trivial change: add the `docs-exempt`\n"
        "         label, or put [skip-changelog] in the PR title."
    )


# ---------------------------------------------------------------- tier 3
def parse_evidence(sop: Path) -> tuple[str | None, list[dict], str | None]:
    """Return (verified_date, checks, error). Hand-rolled: the block is a tiny,
    fixed shape, and requiring PyYAML would make the gate fail for the wrong
    reason on a minimal runner."""
    if not sop.exists():
        return None, [], "SOP.md not found"
    m = EVIDENCE_RE.search(sop.read_text(encoding="utf-8", errors="replace"))
    if not m:
        return None, [], "SOP.md has no <!-- docs-evidence --> block"
    verified, checks, cur = None, [], None
    for raw in m.group(1).splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if re.match(r"\s*verified:", line):
            verified = line.split(":", 1)[1].strip()
        elif re.match(r"\s*-\s+name:", line):
            cur = {"name": line.split("name:", 1)[1].strip(), "run": None}
            checks.append(cur)
        elif re.match(r"\s*run:", line) and cur is not None:
            cur["run"] = line.split("run:", 1)[1].strip()
    return verified, [c for c in checks if c.get("run")], None


def tier3_evidence(repo: Path) -> bool:
    verified, checks, err = parse_evidence(repo / "SOP.md")
    if err:
        return _fail(err)
    if len(checks) < MIN_CHECKS:
        return _fail(f"docs-evidence has {len(checks)} check(s); the standard requires "
                     f">= {MIN_CHECKS}. Cover the facts most likely to drift: entry "
                     f"points, ports, unit names, config paths.")
    good = True
    if not verified:
        good = _fail("docs-evidence has no `verified:` date")
    else:
        _ok(f"SOP last verified: {verified}")
    for c in checks:
        r = subprocess.run(["bash", "-lc", c["run"]], cwd=repo,
                           capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            _ok(f"{c['name']}")
        else:
            good = _fail(f"{c['name']}  ->  `{c['run']}` exited {r.returncode}. "
                         f"The SOP documents something that is no longer true.")
            tail = (r.stderr or r.stdout or "").strip().splitlines()[-2:]
            for t in tail:
                print(f"         {t[:120]}")
    return good


# ---------------------------------------------------------------- negative control
def self_test() -> bool:
    """Prove the checks can FAIL, and that the accepted paths actually pass.

    A gate that passes everything is worth no more than one that never ran, so the
    negative control is not optional ceremony. The positive control is the other
    half: it is the standing proof that a fragment-only PR clears tier 2, so the
    changelog.d path cannot silently rot back into "CHANGELOG.md or nothing"."""
    print("negative control: cases that MUST fail")
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        (repo / "README.md").write_text("x")          # 6 of 7 required files missing
        (repo / "SOP.md").write_text(
            "# SOP\n<!-- docs-evidence\nverified: 2026-01-01\n"
            "checks:\n  - name: deliberately broken\n    run: exit 3\n"
            "  - name: also broken\n    run: test -f definitely-not-here\n"
            "  - name: third\n    run: false\n-->\n")
        must_fail = {
            "tier1 (presence)": tier1_presence(repo),
            "tier2 (src change, no changelog of either kind)":
                tier2_changelog(repo, ["src/app.py"]),
            # changelog.d scaffolding is not an entry. If this ever passes, every
            # repo that merely HAS the directory satisfies tier 2 for free.
            "tier2 (src change, only changelog.d/README.md)":
                tier2_changelog(repo, ["src/app.py", "changelog.d/README.md"]),
            "tier2 (src change, fragment in a nested subdir)":
                tier2_changelog(repo, ["src/app.py", "changelog.d/old/x.md"]),
            "tier3 (evidence)": tier3_evidence(repo),
        }

        print("\npositive control: inputs that MUST satisfy the changelog gate")
        must_pass = {
            "tier2 (src change + changelog.d fragment)":
                tier2_changelog(repo, ["src/app.py", "changelog.d/fix-lane-pin.md"]),
            "tier2 (src change + CHANGELOG.md, the legacy path)":
                tier2_changelog(repo, ["src/app.py", "CHANGELOG.md"]),
            "tier2 (no code touched)":
                tier2_changelog(repo, ["docs/architecture.md"]),
        }
    print()
    passed = (all(v is False for v in must_fail.values())
              and all(v is True for v in must_pass.values()))
    for k, v in must_fail.items():
        print(f"  {k}: {'correctly FAILED' if v is False else 'WRONGLY PASSED'}")
    for k, v in must_pass.items():
        print(f"  {k}: {'correctly passed' if v is True else 'WRONGLY FAILED'}")
    print()
    print("self-test:", "PASS (the gate fails what it must and passes what it must)"
          if passed else "BROKEN (a case came out the wrong way)")
    return passed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--tier", type=int, choices=[1, 2, 3], action="append")
    ap.add_argument("--changed-files", help="file with one changed path per line")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return 0 if self_test() else 1

    repo = Path(a.repo).resolve()
    tiers = a.tier or [1, 2, 3]
    changed = None
    if a.changed_files and os.path.exists(a.changed_files):
        changed = [ln.strip() for ln in open(a.changed_files) if ln.strip()]

    print(f"docs-check: {repo.name}  tiers={tiers}")
    good = True
    if 1 in tiers:
        print("\n[tier 1] required docs present"); good &= tier1_presence(repo)
    if 2 in tiers:
        print("\n[tier 2] changelog on code change"); good &= tier2_changelog(repo, changed)
    if 3 in tiers:
        print("\n[tier 3] SOP evidence still true"); good &= tier3_evidence(repo)
    print("\nRESULT:", "pass" if good else "FAIL")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
