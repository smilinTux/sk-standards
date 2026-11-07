# AGENTS.md (sk-standards)

The canonical home of the SKWorld engineering standards, their templates, reference configs,
validators and two reusable CI gates. Overview: [README.md](./README.md). Operations:
[SOP.md](./SOP.md). This file follows [AGENT_INSTRUCTIONS_STANDARD](./standards/AGENT_INSTRUCTIONS_STANDARD.md).

## Source of truth and invariants

- `standards/*.md` are canonical. Every `sk*` repo conforms to them; nothing here installs or runs.
- A merge to `main` is the release. Consumers call the gates from `@main`, so a change to
  `scripts/docs_check.py` or `.github/workflows/` reaches every consumer on its next CI run.
- A new check that could fail a consumer starts advisory, and becomes failing in its own PR once
  the fleet complies. Never turn the whole fleet red in one merge.
- Counts stated in `SOP.md` (standards, ADRs, validators) are checked by its `docs-evidence` block.
  Adding a standard means updating every count, the README index row and the CHANGELOG.

## Commands

```bash
python3 scripts/docs_check.py --repo . --tier 1 --tier 3   # this repo against the standard
python3 scripts/docs_check.py --self-test                  # proves the gate can fail
pip install pyyaml==6.0.2 && python3 scripts/ci_gate_check.py audit --repo .
python3 scripts/ci_gate_check.py --self-test
python3 scripts/check_fences.py README.md ECOSYSTEM.md SOP.md standards/*.md decisions/*.md templates/*.md
```

## Start here

1. `README.md`: the hub, one row per standard.
2. `SOP.md`: what runs in CI and the `docs-evidence` block that keeps this repo honest.
3. `standards/SK_REPO_DOC_STANDARD.md`: what every repo's docs must contain.
4. `scripts/docs_check.py`: the reusable docs gate, tiers 1 to 3 plus its self-test.
5. `CHANGELOG.md`: keyed by date and SHA; there are no tags or versions.

## Rules

- **Writing style:** no em dashes (U+2014) and no en dashes (U+2013) in anything you write or
  edit. Hyphens are fine. Older text still has some; fix them in lines you touch.
- **Branch and commit:** never commit to `main`. Branch, commit once a fast check passes, then PR.
- **Attribution:** a `Co-Authored-By` trailer names the agent that actually did the work, or is
  left out.
- **Generated files:** Archify `*.html` diagrams under `reference/` are generated from the `*.json`
  next to them by the pinned Archify build (`standards/archify-diagrams.md`); regenerate, never
  hand-edit.
- **A standard states facts it can back.** Cite the code, incident or test it was distilled from.

## Privacy

This repo is public. Never add host names, LAN or tailnet IPs, estate names, personal names or
data, or credentials. `secret-scan.yml` catches secrets only; the rest is on review.

## Hazards

- A validator change ships to every consumer immediately: run its `--self-test`, and add a control
  case to it when you add a check.
- `docs-lint.yml` checks relative links offline: a renamed standard breaks every link to it.

## See also

- [ECOSYSTEM.md](./ECOSYSTEM.md): the project graph these standards govern.
- [templates/](./templates/): README, SOP and AGENTS.md skeletons for new repos.
