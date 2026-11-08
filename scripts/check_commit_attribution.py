#!/usr/bin/env python3
"""Reject co-author credit that has no exact material-contribution evidence."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys

COAUTHOR = re.compile(r"^Co-Authored-By:\s*(.+?)\s*<[^<>]+>\s*$", re.I)
EVIDENCE = re.compile(
    r"^Co-Authored-Evidence:\s*(.+?)\s*\|\s*"
    r"(request|session):(\S+)\s*\|\s*material:(\S.*)$",
    re.I,
)


def messages(revision_range: str) -> list[tuple[str, str]]:
    raw = subprocess.check_output(
        ["git", "log", "--format=%H%x00%B%x00", revision_range],
        text=True,
    )
    fields = raw.split("\x00")
    return [(fields[i].strip(), fields[i + 1]) for i in range(0, len(fields) - 1, 2)]


def violations(sha: str, message: str) -> list[str]:
    coauthors: list[str] = []
    evidence: list[str] = []
    for line in message.splitlines():
        match = COAUTHOR.match(line)
        if match:
            coauthors.append(match.group(1).strip().casefold())
        match = EVIDENCE.match(line)
        if match:
            evidence.append(match.group(1).strip().casefold())
    missing = [name for name in coauthors if name not in evidence]
    return [f"{sha}: co-author {name!r} lacks exact request or session evidence" for name in missing]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("revision_range", help="Git revision range, such as base..head")
    args = parser.parse_args()
    errors = [error for sha, body in messages(args.revision_range) for error in violations(sha, body)]
    if errors:
        print("commit attribution check: FAIL", file=sys.stderr)
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("commit attribution check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
