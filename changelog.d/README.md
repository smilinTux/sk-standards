# changelog.d

One file per change. Never edit `CHANGELOG.md` in a feature branch.

## Why this exists

Requiring every PR to edit the single `CHANGELOG.md` made concurrent PRs
conflict with each other on a file that has nothing to do with their code.
Measured on the chi estate on 2026-09-01: 15 open pull requests failed the
docs-check gate on the changelog rule, and others conflicted on `CHANGELOG.md`
alone, none of them for a reason connected to what they changed.

A fragment is a new file. Two PRs adding two fragments cannot conflict,
because git has nothing to merge between files that do not both exist yet.

## How to add one

Create a file named for your card or PR, so it is traceable:

```
changelog.d/c75f1c98-changelog-fragments.md
```

Write the entry exactly as it should appear under `## [Unreleased]`:

```markdown
### Fixed

- **Card c75f1c98: changelog fragments.** docs-check tier 2 now accepts a
  fragment under `changelog.d/` as satisfying the changelog requirement.
```

That is the whole convention. `README.md` and `.gitkeep` in this directory are
deliberately NOT treated as fragments, so their presence never satisfies the
gate for you.

## At release

```
python scripts/collect_changelog_fragments.py --apply
```

That folds every fragment into the `## [Unreleased]` section of `CHANGELOG.md`
and deletes the fragments. `CHANGELOG.md` remains the released record; this
directory only ever holds unreleased entries.

Run it without `--apply` first to see what it would write.
