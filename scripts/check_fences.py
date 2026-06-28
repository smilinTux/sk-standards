#!/usr/bin/env python3
"""Markdown code-fence balance checker (mermaid-aware).

Walks the given markdown files and verifies that every fenced code block is
closed, with explicit attention to ```mermaid blocks. A docs-only repo has no
runtime to catch a half-open diagram fence, so this is the guard.

Rules enforced per file:
  * Every opening ``` fence has a matching closing ```.
  * No file ends while still inside a fence (unbalanced / unterminated block).
  * Every ```mermaid block is closed (it is just the balance rule, but we count
    and report mermaid blocks separately so a broken diagram is obvious).

Exit code 0 = all good, 1 = at least one problem.
"""
from __future__ import annotations

import sys
from pathlib import Path

FENCE = "```"


def check_file(path: Path) -> list[str]:
    errors: list[str] = []
    in_fence = False
    fence_lang = ""
    open_line = 0
    mermaid_blocks = 0

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = raw.lstrip()
        if not stripped.startswith(FENCE):
            continue
        # A fence delimiter line: ``` optionally followed by an info string.
        info = stripped[len(FENCE):].strip()
        if not in_fence:
            in_fence = True
            fence_lang = info.split()[0] if info else ""
            open_line = lineno
            if fence_lang == "mermaid":
                mermaid_blocks += 1
        else:
            # Closing fences must not carry an info string.
            if info:
                errors.append(
                    f"{path}:{lineno}: closing fence carries info string '{info}' "
                    f"(opened at line {open_line}); looks like an unbalanced fence"
                )
            in_fence = False
            fence_lang = ""

    if in_fence:
        errors.append(
            f"{path}:{open_line}: unterminated '{fence_lang or 'code'}' fence "
            f"(file ends inside the block)"
        )

    return errors


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv[1:]]
    if not paths:
        print("usage: check_fences.py <file.md> [file.md ...]", file=sys.stderr)
        return 2

    all_errors: list[str] = []
    checked = 0
    for path in paths:
        if not path.is_file():
            all_errors.append(f"{path}: not a file")
            continue
        checked += 1
        all_errors.extend(check_file(path))

    if all_errors:
        print("Fence balance check FAILED:")
        for err in all_errors:
            print(f"  {err}")
        return 1

    print(f"Fence balance check OK ({checked} file(s), all mermaid blocks closed).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
