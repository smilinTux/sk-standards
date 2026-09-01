#!/usr/bin/env python3
"""Fold changelog.d/ fragments into CHANGELOG.md at release time.

Fragments exist so concurrent PRs never conflict on a single file. That only
works if something collects them, otherwise the fragments become the changelog
and CHANGELOG.md rots. This is that step.

Read-only unless --apply is passed.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FRAGMENT_DIR = "changelog.d"
NOT_FRAGMENTS = {"README.md", ".gitkeep"}
UNRELEASED = re.compile(r"^## \[Unreleased\][^\n]*\n", re.M)


def fragments(root: Path) -> list[Path]:
    d = root / FRAGMENT_DIR
    if not d.is_dir():
        return []
    return sorted(p for p in d.rglob("*")
                  if p.is_file() and p.name not in NOT_FRAGMENTS)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--apply", action="store_true",
                    help="write CHANGELOG.md and delete the fragments")
    args = ap.parse_args()
    root = Path(args.repo)

    frags = fragments(root)
    if not frags:
        print("no fragments in %s/, nothing to collect" % FRAGMENT_DIR)
        return 0

    changelog = root / "CHANGELOG.md"
    if not changelog.exists():
        print("CHANGELOG.md not found in %s" % root, file=sys.stderr)
        return 2
    text = changelog.read_text(encoding="utf-8")
    m = UNRELEASED.search(text)
    if not m:
        print("CHANGELOG.md has no '## [Unreleased]' section to fold into",
              file=sys.stderr)
        return 2

    body = "\n".join(f.read_text(encoding="utf-8").rstrip() for f in frags)
    print("collecting %d fragment(s):" % len(frags))
    for f in frags:
        print("  %s" % f.relative_to(root))

    if not args.apply:
        print("\n--- would insert under [Unreleased] ---")
        print(body)
        print("\n(dry run; pass --apply to write)")
        return 0

    changelog.write_text(text[:m.end()] + "\n" + body + "\n" + text[m.end():],
                         encoding="utf-8")
    for f in frags:
        f.unlink()
    print("\nfolded into CHANGELOG.md and removed %d fragment(s)" % len(frags))
    return 0


if __name__ == "__main__":
    sys.exit(main())
