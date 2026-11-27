# AGENTS.md (<repo>)

<One or two lines: what this repo is.> Read [README.md](./README.md) for the overview and
[SOP.md](./SOP.md) for operations. Standard: [AGENT_INSTRUCTIONS_STANDARD](https://github.com/smilinTux/sk-standards/blob/main/standards/AGENT_INSTRUCTIONS_STANDARD.md).

## Source of truth and invariants

- <What is canonical. What is derived and can be rebuilt from it.>
- <Each rule that must never break, one line each.>

## Commands

```bash
# install
<exact command>
# test (what CI runs)
<exact command>
# lint and format (what CI runs)
<exact command>
# docs gate
python3 <path-to-sk-standards>/scripts/docs_check.py --repo .
```

## Start here

1. `<path>`: <one line>
2. `<path>`: <one line>
3. `<path>`: <one line>

## Rules

- **Writing style:** no em dashes (U+2014) and no en dashes (U+2013) anywhere: code,
  comments, docs, commits, PR bodies. Use commas, parentheses, colons or a new sentence.
  Hyphens are fine.
- **Branch and commit:** never commit to `main`. Branch, commit as soon as a fast check
  passes and before any long verification, then open a PR.
- **Attribution:** a `Co-Authored-By` trailer names the agent that actually did the work,
  or is left out.
- **Generated files:** <which files are generated, from what, and how to regenerate them>.
- <Repo-specific rules.>

## Privacy

Never put any of these in code, docs, tests, fixtures, commits or the site: host names,
LAN or tailnet IPs, estate names, personal names or data, credentials<, and for this
repo: ...>. Enforced by: <test or check, or "review only">.

## Hazards

- <Trap that has bitten an agent before>: <what to do instead>.

## See also

- <neighbour repo>: <why>
- [SK_REPO_DOC_STANDARD](https://github.com/smilinTux/sk-standards/blob/main/standards/SK_REPO_DOC_STANDARD.md)
