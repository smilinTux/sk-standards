### Fixed

- **Card c75f1c98: changelog fragments.** docs-check tier 2 now accepts a file
  under `changelog.d/` as satisfying the changelog requirement, alongside
  `CHANGELOG.md`. Requiring the single file made concurrent PRs conflict with
  each other on a file unrelated to their code: 15 open PRs on the chi estate
  failed this gate on 2026-09-01. A fragment is one new file, so two PRs cannot
  collide. `scripts/collect_changelog_fragments.py` folds them in at release.
