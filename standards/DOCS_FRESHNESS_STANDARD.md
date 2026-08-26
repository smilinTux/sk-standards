# Docs Freshness Standard (CANONICAL)

**Status:** Going-forward ecosystem standard. Applies to every `sk*` repo.
**Companion to:** [`SK_REPO_DOC_STANDARD`](./SK_REPO_DOC_STANDARD.md) (what the docs
must contain) · [`TESTING_AND_CI_STANDARD`](./TESTING_AND_CI_STANDARD.md) (tests as
evidence) · [`OBSERVABILITY_AND_SCHEDULING_STANDARD`](./OBSERVABILITY_AND_SCHEDULING_STANDARD.md)
(nothing fails silently).
**Validator:** [`scripts/docs_check.py`](../scripts/docs_check.py) ·
**Reusable gate:** [`.github/workflows/docs-check.yml`](../.github/workflows/docs-check.yml)

> One sentence: **`SK_REPO_DOC_STANDARD` says what a doc must contain; this says how
> it stays true, because a doc nothing executes rots silently and a periodic
> big-bang migration is the symptom, not the cure.**

---

## 0. The problem this exists to solve

Doc compliance is normally achieved by migration: someone spends a week bringing 30
repos up to standard, and six months later they are stale again. The migration is not
the fix. It is the recurring cost of not having a fix.

Docs rot **silently** because nothing runs them. Code has tests; a wrong function
fails a build. A wrong port in an SOP fails nothing, until 2am, when the person
following the runbook discovers the service moved eight months ago.

The correction is the same one applied to every other silent failure in this
ecosystem: **make something execute the claim**. A gate that fails is what holds. A
convention people are supposed to remember is what rots.

### The failure mode this standard is calibrated against

A presence check ("does `SOP.md` exist?") is nearly worthless on its own. It catches a
*missing* doc. It says nothing about a doc that is present, well-formatted, confidently
worded, and **wrong** — which is the case that actually hurts, because it is trusted.

Worse, a doc that merely exists can score green forever while decaying, producing the
most dangerous artifact in this ecosystem: **a signal that certifies less than it
appears to.** See [`SK_REPO_DOC_STANDARD`](./SK_REPO_DOC_STANDARD.md) §5 (honest
claims): every claim carries its check. This standard is that rule, enforced.

---

## 1. The gate (MUST)

Every `sk*` repo MUST run a `docs-check` gate on `push` and `pull_request`. Repos
SHOULD call the shared reusable workflow rather than copy it, so the rules live in one
place and cannot drift:

```yaml
# .github/workflows/docs-check.yml in each repo
name: docs-check
on: [push, pull_request]
permissions:
  contents: read
jobs:
  docs:
    uses: smilinTux/sk-standards/.github/workflows/docs-check.yml@main
```

The gate performs three checks, in increasing order of value.

### 1.1 Presence (tier 1)

Fail if any file required by `SK_REPO_DOC_STANDARD` §1 is absent: `README.md`,
`SOP.md`, `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md`,
`LICENSE`.

Cheap, and green immediately after a compliance pass. Catches deletion, and catches a
new repo spawned from a bad template.

### 1.2 Changelog-on-code-change (tier 2)

If a pull request touches `src/**` or `pyproject.toml` but does **not** touch
`CHANGELOG.md`, fail.

- Escape hatch: a `docs-exempt` label, or `[skip-changelog]` in the PR title.
- The gate MUST log when the hatch is used. An unlogged escape hatch becomes the
  default path within a quarter.

### 1.3 Source-bound evidence (tier 3 — the one that catches drift)

`SOP.md` MUST carry a machine-readable evidence block. The gate executes every check
in it and fails on any nonzero exit.

```markdown
<!-- docs-evidence
verified: 2026-08-14
checks:
  - name: entry point exists
    run: skcode-hostd --help
  - name: documented port matches config
    run: grep -q '"port": 8420' config/default.json
  - name: unit file present
    run: test -f systemd/skcode-hostd.service
-->
```

| Field | Required | Meaning |
|---|:---:|---|
| `verified` | ✅ | ISO date the SOP was last confirmed against reality by a human or agent. |
| `checks[].name` | ✅ | What fact this proves. Named so a failure reads as "documented port drifted", not "step 3 failed". |
| `checks[].run` | ✅ | A command, run from the repo root, exiting 0 when the documented fact still holds. |

**Rules:**
- **Minimum 3 checks** covering the facts most likely to drift: entry points, ports,
  systemd unit names, config paths.
- Checks MUST be **hermetic**: repo-local, no network, no live-host dependency. A
  check that needs a running service belongs in that service's health endpoint, not
  here. A flaky gate gets disabled, and a disabled gate is worse than none.
- Checks MUST be **cheap** (seconds). This runs on every push.
- Grow the set when drift is found. Each incident that a check would have caught is a
  check to add.

#### Public API, configuration, and SIEM claim inventories

A repo that publishes any of the conventional public references below MUST also commit
`docs/source-evidence.json` and mark one canonical inventory block in each document:

| Kind | Document | Block marker | Authoritative source shape |
|---|---|---|---|
| API routes | `docs/API.md` | `docs-claims:api_routes` | exported JavaScript string array such as `PUBLIC_API_ROUTES` |
| Configuration keys | `docs/CONFIGURATION.md` | `docs-claims:configuration_keys` | exported JavaScript string array such as `PUBLIC_CONFIGURATION_KEYS` |
| SIEM event types | `docs/SIEM.md` | `docs-claims:siem_event_types` | JavaScript string-valued object such as `EventType` |

Each block contains only one claim per Markdown bullet. API claims use
`` `METHOD /path` ``; configuration and SIEM claims use a backticked key. The manifest
binds each kind to one repository-relative source file, one `const` symbol, and either
`array` or `object_values`. Tier 3 compares sets exactly, so a source claim omitted from
the doc is stale and a doc claim absent from source is invented; either fails.

This check is intentionally narrower than general documentation validation. It
**certifies only exact inventory equality** for the three marked blocks. It does not
prove that a route handler is reachable, that configuration keys are consumed or have
the documented defaults/semantics, that an accepted SIEM event reaches a sink, that
unmarked prose is correct, or that live/deployed state matches source. Those require
separate source tests, evidence commands, and where authorized, runtime qualification.

Repos without these conventional public documents report the check as not applicable.
If any one exists without the manifest, tier 3 fails rather than silently certifying
only `SOP.md`.

---

## 2. Rollout rules for the gate itself (MUST)

These are not stylistic. Each is drawn from an ecosystem gate that failed exactly this
way.

- **Green on day one.** Never land a gate that starts red. A red check is triaged as
  known-broken within days and routed around thereafter. A fleet repo carried a red
  `gitleaks` check for months; it was ignored, and it turned out to be scanning **zero
  bytes** the entire time. Land the compliance pass first, then the gate.
- **Verify in both directions before trusting it.** Prove it FAILS: delete a required
  file, or break a documented port, and confirm the build goes red. **A gate that
  passes everything is worth no more than one that never ran.** Record the negative
  test in the PR that introduces the gate.
- **A skip is not a pass.** If a check self-skips (missing tool, absent optional
  sibling), the gate MUST say so loudly, and MUST fail where running it was the point.
- **One canonical source.** The rules live here and in the reusable workflow. Repos
  call it. Thirty copies drift; that is the same trap this standard exists to close.

---

## 3. Compliance checklist

- [ ] `.github/workflows/docs-check.yml` present, calling the shared reusable workflow
- [ ] All 7 required files present (tier 1 green)
- [ ] `CHANGELOG.md` updated by any PR touching `src/**` or `pyproject.toml` (tier 2)
- [ ] `SOP.md` carries a `docs-evidence` block with **>= 3** hermetic checks (tier 3)
- [ ] Conventional `docs/API.md`, `docs/CONFIGURATION.md`, and `docs/SIEM.md` inventories are source-bound through `docs/source-evidence.json`, or none of those documents exists
- [ ] `verified:` date is within the last 6 months
- [ ] The gate's negative test is recorded in the PR that introduced it

---

## 4. What this standard does NOT claim

- It does not make docs **good**. It makes a defined set of facts in them **true**.
  Prose quality, the "why", and the diagram that makes it click remain human work.
- It does not verify claims that are not expressible as a hermetic command. Those
  still rely on the `verified:` date and human review. Prefer moving a fact into a
  checkable form over trusting the date.
- A green `docs-check` means *the checks that exist* passed. Coverage is a property of
  the check list, not of the gate. For marked public inventories, green means equality
  to named source symbols—not reachability, semantics, delivery, or live behavior.
  Grow coverage deliberately.
