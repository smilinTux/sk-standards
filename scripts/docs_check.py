#!/usr/bin/env python3
"""Docs freshness validator (DOCS_FRESHNESS_STANDARD).

Three tiers, in increasing order of value:

  1. presence   - the 7 files SK_REPO_DOC_STANDARD requires exist.
  2. changelog  - a PR touching src/** or pyproject.toml also touches CHANGELOG.md,
                  OR adds a changelog.d/<slug>.md fragment.
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
EVIDENCE_RE = re.compile(r"<!--\s*docs-evidence(.*?)-->", re.S)
MIN_CHECKS = 3

# changelog.d/ fragments (see skcapstone's changelog.d/README.md for the
# authoring workflow): a fragment is an ADDITIONAL way to satisfy tier 2,
# never a replacement for editing CHANGELOG.md directly, which still works.
CHANGELOG_FRAGMENT_DIR = "changelog.d/"
CHANGELOG_FRAGMENT_IGNORE = {"README.md", ".gitkeep", ".gitignore"}


def _is_changelog_fragment(path: str) -> bool:
    """A fragment must be a .md file sitting DIRECTLY in changelog.d/ - not a
    nested subdirectory, and not one of the directory's own housekeeping
    files (which would satisfy tier 2 for free just by existing)."""
    if not path.startswith(CHANGELOG_FRAGMENT_DIR):
        return False
    rest = path[len(CHANGELOG_FRAGMENT_DIR):]
    if not rest or "/" in rest:
        return False
    if rest in CHANGELOG_FRAGMENT_IGNORE:
        return False
    return rest.endswith(".md")

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
def tier2_changelog(repo: Path, changed: list[str] | None) -> bool:
    if changed is None:
        return _ok("changelog check skipped (no diff context; not a PR)")
    touches_code = any(c.startswith(CODE_GLOBS) for c in changed)
    if not touches_code:
        return _ok("changelog check n/a (no code touched)")
    if any(c == "CHANGELOG.md" for c in changed):
        return _ok("code changed and CHANGELOG.md updated")
    fragments = [c for c in changed if _is_changelog_fragment(c)]
    if fragments:
        return _ok(f"code changed and changelog.d/ fragment added: {fragments[0]}")
    return _fail("code under src/ or pyproject.toml changed but neither CHANGELOG.md "
                 "nor a changelog.d/<slug>.md fragment was added. "
                 "Add an entry, or use the docs-exempt label / [skip-changelog] for a "
                 "genuinely trivial change.")


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
    """Prove the checks can FAIL. A gate that passes everything is worth no more
    than one that never ran, so this is not optional ceremony."""
    print("negative control: building a repo that SHOULD fail every tier")
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        (repo / "README.md").write_text("x")          # 6 of 7 required files missing
        (repo / "SOP.md").write_text(
            "# SOP\n<!-- docs-evidence\nverified: 2026-01-01\n"
            "checks:\n  - name: deliberately broken\n    run: exit 3\n"
            "  - name: also broken\n    run: test -f definitely-not-here\n"
            "  - name: third\n    run: false\n-->\n")
        results = {
            "tier1 (presence)": tier1_presence(repo),
            "tier2 (changelog)": tier2_changelog(repo, ["src/app.py"]),
            "tier3 (evidence)": tier3_evidence(repo),
        }
    print()
    passed = all(v is False for v in results.values())
    for k, v in results.items():
        print(f"  {k}: {'correctly FAILED' if v is False else 'WRONGLY PASSED'}")
    print()
    print("negative control:", "PASS (the gate can fail)" if passed
          else "BROKEN (a tier passed when it must not)")

    # ---------------------------------------------------------------- additive control
    # The negative control above proves the gate CAN fail. This proves the
    # changelog.d/ fragment widening is correctly ADDITIVE: a fragment opens a
    # new way to pass tier 2, a fragment-less src/ change still fails it, and
    # the directory's own housekeeping files (README.md) or a nested
    # subdirectory do not count as an entry for free.
    print("\nadditive control: changelog.d/ fragment is an ALTERNATE pass path for tier 2")
    repo = Path(tempfile.mkdtemp())  # no CHANGELOG.md here at all - fragment must be enough
    checks = {
        "src/ change + CHANGELOG.md edit still passes":
            tier2_changelog(repo, ["src/app.py", "CHANGELOG.md"]) is True,
        "src/ change + changelog.d/<slug>.md fragment passes":
            tier2_changelog(repo, ["src/app.py", "changelog.d/my-fix.md"]) is True,
        "src/ change + changelog.d/README.md ALONE still fails":
            tier2_changelog(repo, ["src/app.py", "changelog.d/README.md"]) is False,
        "src/ change + nested changelog.d/sub/x.md still fails":
            tier2_changelog(repo, ["src/app.py", "changelog.d/sub/x.md"]) is False,
        "src/ change + neither still fails (gate not weakened)":
            tier2_changelog(repo, ["src/app.py"]) is False,
    }
    additive_ok = True
    for name, ok in checks.items():
        print(f"  {'correct' if ok else 'WRONG '}: {name}")
        additive_ok = additive_ok and ok
    print()
    print("additive control:", "PASS (fragment widening is strictly additive)" if additive_ok
          else "BROKEN (the fragment widening changed the gate's existing behaviour)")

    return passed and additive_ok


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
