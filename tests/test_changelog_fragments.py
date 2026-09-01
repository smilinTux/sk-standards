"""Tier 2 accepts a changelog.d/ fragment as well as CHANGELOG.md.

The single CHANGELOG.md made every concurrent PR edit the same [Unreleased]
block, so PRs conflicted with each other on a file unrelated to their code.
A fragment is one new file per PR, so two PRs cannot collide.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import docs_check as dc

REPO = Path(".")


def check(changed):
    return dc.tier2_changelog(REPO, changed)


def main():
    cases = [
        (["src/x.py", "CHANGELOG.md"], True, "CHANGELOG.md still satisfies it"),
        (["src/x.py", "changelog.d/1234-thing.md"], True, "a fragment satisfies it"),
        (["src/x.py", "changelog.d/nested/5678.md"], True, "a nested fragment satisfies it"),
        (["src/x.py"], False, "code with neither still fails"),
        (["src/x.py", "changelog.d/README.md"], False,
         "the fragment dir README is NOT a fragment"),
        (["src/x.py", "changelog.d/.gitkeep"], False,
         ".gitkeep is NOT a fragment"),
        (["docs/x.md"], True, "no code touched, gate not applicable"),
        (["pyproject.toml", "changelog.d/9.md"], True, "pyproject counts as code"),
    ]
    failed = 0
    for changed, want, why in cases:
        got = bool(check(changed))
        ok = got == want
        failed += not ok
        print("  %-46s got=%-5s want=%-5s %s" % (why, got, want, "PASS" if ok else "FAIL"))
    print("FAILED" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
