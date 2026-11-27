# Agent Instructions Standard (AGENTS.md)

**Status:** Going-forward ecosystem standard. Advisory in `docs-check` until the fleet rollout is done (section 6).
**Applies to:** every `sk*` repo, every `-skworld-io` site repo, and `sk-standards` itself.
**Canonical-home:** <https://github.com/smilinTux/sk-standards/blob/main/standards/AGENT_INSTRUCTIONS_STANDARD.md>
**Related:** [SK_REPO_DOC_STANDARD](./SK_REPO_DOC_STANDARD.md) (the human doc set; this standard is its agent-facing companion) · [TESTING_AND_CI_STANDARD](./TESTING_AND_CI_STANDARD.md) (the commands an agent must run) · [DOCS_FRESHNESS_STANDARD](./DOCS_FRESHNESS_STANDARD.md) (the gate that reports it).

> One sentence: **every repo has exactly one agent instructions file, `AGENTS.md` at the
> repo root, and no tool-specific copy of it.**

---

## 0. Why one file, and why this one

Most of our work in a repo is done by agents: Claude Code, Codex, Pi, OpenCode, Hermes
and the T3 sessions that drive them. Each tool used to want its own file (`CLAUDE.md`,
`GEMINI.md`, `.cursorrules`, `.github/copilot-instructions.md`), and the copies drift.
Before this standard, repos had a `CLAUDE.md` only (so Codex and Pi workers never saw
the rules), an `AGENTS.md` only, or both with different content.

`AGENTS.md` is the tool-neutral name every one of those runtimes reads, Claude Code
included. Two consequences follow, and they are the rule:

1. **`AGENTS.md` is the only agent instructions file in the repo.**
2. **A `CLAUDE.md` must not exist next to it, not even as a one-line shim.** Claude Code
   skips its native `AGENTS.md` loading in a directory that has its own `CLAUDE.md`, so
   a leftover `CLAUDE.md` silently hides the real rules from Claude sessions. The same
   reasoning applies to every other tool-specific file: delete it, move its content into
   `AGENTS.md`.

## 1. Location and scope

| Rule | Detail |
|---|---|
| Root file | `AGENTS.md` at the repo root. MUST exist. |
| Nested files | A subtree with genuinely different rules (a vendored app, a site under `site/`) MAY have its own `AGENTS.md`. The nearest file to the edited path wins, so a nested file states only what differs and links the root one. |
| Forbidden | `CLAUDE.md`, `GEMINI.md`, `.cursorrules`, `.cursor/rules/`, `.github/copilot-instructions.md`, `.windsurfrules` anywhere in the tree. |
| Personal overrides | A person's or agent's own preferences live in their home config (for example `~/AGENTS.md`), never in the repo. |
| Public repos | `AGENTS.md` is public. It follows the same privacy rules as the README (section 3, item 6). |

## 2. What it is for, and what it is not

`AGENTS.md` is the **operating brief for an agent about to change this repo**: what it
must know, run and never do. It is not a second README. Per
[SK_REPO_DOC_STANDARD section 0](./SK_REPO_DOC_STANDARD.md#0-core-principle--ai-first-then-human-readable),
each fact is stated once: architecture lives in `SOP.md` and `docs/ARCHITECTURE.md`,
the pitch lives in `README.md`, and `AGENTS.md` links to them instead of copying them.

Keep it short enough to be read in full on every session: **aim for under 200 lines.**
An agent loads it into context every time, so every line costs every session.

## 3. Required sections, in this order

Same headings, same order, every repo, so an agent finds content by position.

1. **`# AGENTS.md (<repo>)`** and one or two lines on what the repo is, linking
   `README.md` and `SOP.md`.
2. **`## Source of truth and invariants`**: what is canonical and what is derived and
   rebuildable, and the rules that must never break (for example "flat files are the
   truth, the index is a cache"; "the evaluator never selects what a final gate runs").
3. **`## Commands`**: the exact commands CI runs, copy-pasteable, in a fenced block:
   install, test, lint, format, type check, `docs-check`. If CI runs it, it is here; if it
   is here, CI runs it.
4. **`## Start here`**: the 3 to 5 files to open first, each with a one-liner. Link the
   SOP's own Start here when it already exists rather than repeating it.
5. **`## Rules`**: at minimum
   - **Writing style:** no em dashes (U+2014) and no en dashes (U+2013) anywhere: code,
     comments, docs, commits, PR bodies. Hyphens are fine.
   - **Branch and commit:** never commit to the default branch; branch, commit as soon as
     a fast check passes and before any long verification, open a PR.
   - **Attribution:** a `Co-Authored-By` trailer names the agent that actually did the
     work, or is left out. Never one you cannot evidence.
   - **Generated files:** which files are generated, from what, and that they are
     regenerated, never hand-edited.
6. **`## Privacy`**: what must never appear in this repo's code, docs, tests, fixtures,
   commits or site: host names, LAN or tailnet IPs, estate names, personal names and
   data, credentials, and (for memory and chat repos) any real memory or message
   content. Name the test or check that enforces it, if there is one.
7. **`## Hazards`**: the repo-specific traps that have bitten an agent before, each
   with what to do instead. Facts an agent would otherwise learn by breaking something.
8. **`## See also`**: the neighbouring repos and the standards this repo follows.

Optional sections go after Hazards and before See also (for example `## Release`,
`## Concurrent sessions`).

The skeleton is [`templates/AGENTS.template.md`](../templates/AGENTS.template.md).

## 4. Writing it

- **Imperative and specific.** "Run `pytest tests/ -q` before committing", not "make
  sure tests pass".
- **Values, not pointers to values.** Real paths, real commands, real env var names.
- **Every rule earns its line.** A rule nobody has broken and nobody would break is
  noise; delete it.
- **Keep it true.** An `AGENTS.md` change goes in the same PR as the code change that
  made it necessary. A wrong `AGENTS.md` is worse than none, because agents trust it.

## 5. Migrating a repo

| Repo has | Do |
|---|---|
| `CLAUDE.md` only | `git mv CLAUDE.md AGENTS.md`, then reshape it to section 3. |
| Both files | Merge the two into `AGENTS.md` (keep whichever fact is current, check it against the code), then `git rm CLAUDE.md`. |
| Neither | Write `AGENTS.md` from the template, from the repo's own code, CI and docs. |
| Any other tool file | Move its content into `AGENTS.md`, delete the file. |

Search the tree for references to the old file (`grep -rn CLAUDE.md`) and repoint them.
Add a CHANGELOG entry or `changelog.d/` fragment.

If another session is actively working in the repo, do the migration as its own small
PR and tell that session, so it rebases instead of recreating `CLAUDE.md`.

## 6. Enforcement

`scripts/docs_check.py` tier 1 reports, as **advisory warnings that never fail the
build**:

- `AGENTS.md` missing at the repo root;
- a forbidden tool-specific file present at the repo root (section 1).

The checks are advisory because every consumer calls the gate from `@main`, and making
them failing on day one would turn every unmigrated repo red at once. Once the rollout
is done, a separate PR adds `AGENTS.md` to `REQUIRED` in `docs_check.py` and to
[SK_REPO_DOC_STANDARD section 1](./SK_REPO_DOC_STANDARD.md#1-the-required-doc-set-every-sk-repo),
in the same change.

## 7. Compliance checklist

- [ ] `AGENTS.md` exists at the repo root.
- [ ] No `CLAUDE.md` or other tool-specific instructions file anywhere in the tree.
- [ ] The eight sections of section 3 are present, in order.
- [ ] Every command in `## Commands` is one CI actually runs, and it passes.
- [ ] The privacy section names what must never appear, and the file itself follows it.
- [ ] Under about 200 lines; architecture and pitch are linked, not copied.
- [ ] `docs-check` tier 1 prints no `AGENTS.md` warning.
