# Archify diagrams for `-skworld-io` site repos

**Status:** Authoring guide for the "Required for every `-skworld-io` site repo"
rule in [`ARCHITECTURE_AND_DATAFLOW_STANDARD`](./ARCHITECTURE_AND_DATAFLOW_STANDARD.md#required-for-every--skworld-io-site-repo).
This file is the how-to; that standard is the rule.

**Reference implementation:** [`skpatch-skworld-io`](https://github.com/smilinTux/skpatch-skworld-io),
`diagrams/skpatch.architecture.json` plus its generated `diagrams/skpatch.architecture.html`,
linked from `index.html` and listed on the site.

---

## 1. What is required, in one line

Every `<name>-skworld-io` site repo carries `diagrams/<name>.architecture.json`
(required), optionally `<name>.dataflow.json` and `<name>.workflow.json`, each
with its generated `<name>.<type>.html` committed beside it, both linked from the
site nav and from the generated-HTML links shown on the page the site uses as its
own docs index. The JSON is derived from the service repo's mermaid docs and must
never contradict them.

## 2. Schema essentials

[Archify](https://github.com/tt-a1i/archify) (pinned `v3.2.0`, commit
`208acba8d412335185b2056fedf54b3405df43fb`, MIT license, reviewed in
`~/clawd/skills/archify-upstream/SK-REVIEW.md` on the SKWorld side) renders a
JSON-IR candidate into one self-contained HTML file. For the `architecture` type
used by this rule:

| Field | Required | Notes |
|---|:---:|---|
| `schema_version` | yes | `1` |
| `diagram_type` | yes | `"architecture"` |
| `meta.title` | yes | Page title |
| `meta.output` | yes | Portable relative output filename, e.g. `"example.architecture.html"` |
| `meta.quality_profile` | no | `"showcase"` (default look for a site) or `"standard"` (denser) |
| `components[]` | yes (>=1) | Each needs `id`, `type`, `label`. `type` is one of `frontend`, `backend`, `database`, `cloud`, `security`, `messagebus`, `external` |
| `boundaries[]` | no | Each needs `kind` (`region` or `security-group`), `label`, `wraps` (component ids) |
| `connections[]` | no | Each needs `from`, `to`; `variant` is one of `default`, `emphasis`, `security`, `dashed` |
| `cards[]` | no | Short callouts rendered beside the diagram |

Full schema: `schemas/architecture.schema.json` and `schemas/common.schema.json`
in the pinned Archify clone. Use the `dataflow` / `workflow` schemas the same way
for the optional companions; same pinned clone, same regeneration command, just a
different `diagram_type`.

**Never invent new shape here.** The components, connections, and boundaries in
the JSON are the same ones the service repo's mermaid component/data-flow
diagrams already name. Author fresh JSON that reads the mermaid for topology and
meaning (Archify's mermaid-input mode); do not mechanically transcribe mermaid
styling, and do not add a component, connection, or boundary that has no mermaid
counterpart.

## 3. Regenerating locally

Archify is **not** the npm package named `archify` (that is an unrelated,
unreviewed package at version `0.0.4`; checked 2026-11-06, `npm view archify
versions` returns `["0.0.2","0.0.3","0.0.4"]`, nothing near `3.2.0`). The real
tool is only published as source on GitHub, so pin by **tag and commit SHA
together**, never a floating tag:

```bash
git clone --branch v3.2.0 https://github.com/tt-a1i/archify.git /tmp/archify-v3.2.0
cd /tmp/archify-v3.2.0
test "$(git rev-parse HEAD)" = "208acba8d412335185b2056fedf54b3405df43fb" || { echo "commit mismatch, abort"; exit 1; }
cd archify
npm install --no-audit --no-fund
ARCHIFY_UPDATE_CHECK_DISABLED=1 node bin/archify.mjs finalize architecture \
  ../../<site-repo>/diagrams/<name>.architecture.json \
  ../../<site-repo>/diagrams/<name>.architecture.html \
  --quality showcase --json
```

- `ARCHIFY_UPDATE_CHECK_DISABLED=1` is mandatory on every invocation: it is the
  one env var that silences Archify's single network call (a bounded update
  check against `tt-a1i.github.io`), and this rule requires that call stay off.
- `finalize` runs validate, deliver, a strict HTML/SVG check, and a real headless
  browser check, and exits nonzero on the first failing gate. A passing JSON
  exit is the evidence a reviewer looks for in the PR.
- Repeat per diagram type (`architecture`, `dataflow`, `workflow`) for whichever
  companions the site carries.
- The `archify` skill at `~/.skskills/installed/archify` on an SKWorld agent host
  already carries this pin and review; an agent authoring a diagram there follows
  that skill's own instructions instead of re-cloning, same command shape.

## 4. CI: the reusable workflow

Site repos drop in a caller workflow rather than hand-rolling regeneration:

```yaml
# .github/workflows/archify.yml in the site repo
name: archify
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: write

jobs:
  build:
    uses: smilinTux/.github/.github/workflows/archify-build.yml@<pinned-sha>
```

The called workflow (`archify-build.yml`, published from `smilinTux/.github`)
installs the pinned Archify, regenerates `diagrams/*.html` from every
`diagrams/*.json`, fails a pull request if the committed HTML is stale against
its JSON, and on a push to `main` commits the regenerated HTML back with a
bot-style commit. See that repo's workflow header for the exact pin and the
caller snippet it documents.

## 5. Review checklist row

Add this row wherever a reviewer checks a `-skworld-io` site PR (alongside the
checklist in [`SK_REPO_DOC_STANDARD`](./SK_REPO_DOC_STANDARD.md#6-per-repo-compliance-checklist)):

```
[ ] diagrams/<name>.architecture.json present, generated diagrams/<name>.architecture.html committed next to it
[ ] Generated HTML matches its JSON (archify-build CI check is green, or was just regenerated in this PR)
[ ] Archify JSON components/connections/boundaries do not contradict the service repo's mermaid docs
[ ] Site nav and the site's docs index both link to every diagrams/*.html
[ ] ARCHIFY_UPDATE_CHECK_DISABLED=1 was set for every local regeneration in this PR
```

## 6. Related standards

- [`ARCHITECTURE_AND_DATAFLOW_STANDARD`](./ARCHITECTURE_AND_DATAFLOW_STANDARD.md)
  states the rule this guide implements.
- [`SK_REPO_DOC_STANDARD`](./SK_REPO_DOC_STANDARD.md) carries the general
  per-repo compliance checklist this guide's row is added alongside.
- [`templates/site/diagrams/example.architecture.json`](../templates/site/diagrams/example.architecture.json)
  is the starting point for a new site's required diagram.
