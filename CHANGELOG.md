# Changelog

All notable changes to `sk-standards` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Versioning: read this before looking for a version number

**This repo has no releases, no tags, and no SemVer line.** `git tag` is empty (verified
2026-08-14) and there is no packaging manifest to carry a version string, because there
is nothing to package: `sk-standards` ships documents, reference configs, four scripts,
and two reusable GitHub Actions workflows. See
[SOP.md section 9](SOP.md#9-maturity-tier--version-reference).

Consequently:

- **The identity of a given state of this repo is its commit SHA.** Entries below are
  keyed by **date and SHA**, not by SemVer, because inventing version numbers after the
  fact would be a claim with nothing behind it.
- **A merge to `main` is the release.** Consumers call the reusable gate as
  `uses: smilinTux/sk-standards/.github/workflows/docs-check.yml@main`, and the workflow
  defaults `standards-ref: main`, so a change here reaches every consumer on their next
  CI run with no action on their part.
- **Adding a tag is a fleet decision, not a repo decision**, because consumers would
  start pinning to it. Do not create one casually.

The `0.1` in the seed commit's subject line was a label in prose, never a tag.

---

## [Unreleased]

### Added

- `standards/SITE_AND_HOST_NAMING_STANDARD.md`: how sites and hosts are named, the layer
  below the `IDENTITY_NAMING_STANDARD` fqid grammar. Replaces the geography-plus-increment scheme
  (`nor`/`chi`/`chi2`) with a closed three-character vocabulary claimed in a registry, and names
  **the incrementing site** as the anti-pattern. Its load-bearing rule is that a site's name and
  its addresses change on separate schedules: CMDB CI ids are keys rather than labels, so renaming
  a CI is a delete plus a create that destroys the folded event log, which disqualifies bulk
  renaming and makes alias-first the only adoptable migration.
  Federation is explicit: the site vocabulary is **estate-local by design**, so every estate
  having its own Zion is correct rather than a collision. A site code MUST NOT be respelled on
  federation (that would re-propose the local/federated split `IDENTITY_NAMING_STANDARD` §3
  overruled); cross-estate reference uses the fqid, whose `<operator>.<org-domain>` segment is
  already the estate discriminator. Registries declare an `estate` and resolvers key sites by
  `(estate, code)`.
  Hostnames are bare (`zioap01`) and identical in every estate: the estate lives in the
  resolution suffix and the fqid, never in the host label, since inside an estate a marker
  carries no information. Each estate therefore owns its resolution namespace, which
  Tailscale enforces for free (a shared device resolves only as `<host>.<tailnet>.ts.net`,
  never by short name). `zio` is reserved and automatic per estate;
  Adds the bridge-node topology that makes that namespace rule usable: estates federate
  through a small enumerated set of user-owned bridge nodes rather than a full mesh, carrying
  an application-layer exchange rather than general reachability, listed in the registry as
  the estate's whole federation surface. Cost is N(N-1) one-time shares and does not grow with
  machine count. Keeping bridges user-owned also sidesteps the one behaviour Tailscale's docs
  leave unanswered, whether a tag-owned node can reach a user-shared machine.
  every other code is claimed only when a site exists to claim it.
  Estate identity defaults to an operator segment under a shared org-domain
  (`cakjr.skworld.io`), not a purchased domain: the PGP primary key is the root identity and
  the domain is a bound label, so sovereignty lives in the key, not the suffix. The cost is
  paid explicitly instead of assumed, via a required permanent non-revocable delegation, with
  `IDENTITY_NAMING_STANDARD` section 2.6 dated aliases as the documented exit. Estate tags are
  `[a-z0-9]{2,12}` with no hyphen so the first hyphen in a hostname is always the delimiter.
  Adds the account rule the estates already follow: a shared ops account NAME is fine, shared
  CREDENTIALS are not, since one compromise would otherwise cross every estate at once.
- Card f0c63c2a adds the backward-compatible v1.3 control-plane discovery
  facet, a public synthetic example, negative controls, and a CI contract gate.
- `standards/AUTONOMY_STANDARD.md` plus `reference/autonomy/actuation-surfaces.json` and
  `scripts/check_actuation_registry.py`: the framework placeholder for the autonomy layer,
  created first under the accretion model so its six constituent standards can land as
  individual PRs that each flip their own row. Read as a set, the other eighteen standards
  all govern nouns; none says what must be true before the estate acts. Two live
  consequences of that gap, found by direct read on 2026-08-25: `skoperator decide --approve`
  wrote a record and stopped, with no code anywhere re-reading a resolved decision, so every
  escalated proposal was a dead end; and the freeze covered neither of two actuation surfaces
  that could act with no gate at all. The registry makes kill-switch coverage a checked
  property, and it ships with both ungoverned surfaces honestly listed, because a standard
  that is green on day one by omission is worse than no standard.

- `proposals/APPLICATION_IDENTITY_AND_CAPAUTH_KEY_MANAGEMENT_BLUEPRINT.md`: a
  review-only, non-normative proposal for stable application identities,
  keyless-by-default workload identities, purpose-bound credential slots,
  human-rooted authority provenance, opaque custody references, and a
  boundary-based test for when another durable key is justified. Architecture
  review amendments distinguish the five-class fqid grammar from registration
  metadata and capability-ceiling classes, scope the keyless model to SKLegal
  with SKGateway as a migration target, and derive two current durable
  credentials instead of using a fixed identity count.
- `standards/SKWORLD_AUTHORIZATION_STANDARD.md`: one PDP (`capauth.authz.decide`), many
  thin PEPs, and the load-bearing rule that **route coverage, not shadow soak, is the
  enforce-safety criterion** (shadow mode structurally cannot see an unmapped route, so
  "divergence == 0" is necessary and never sufficient). Authored 2026-08-06 on
  `feat/module-manifest-v1.2-install-knowledge-facets` and never merged, so it was
  invisible to anyone reading this repo while three other standards already cited it.
  Landed here reconciled against what shipped in the meantime, see Changed below.
- `standards/MCP_TOOL_OWNERSHIP_STANDARD.md`: one owning repo per MCP tool name, thin
  delegates that never reimplement (nor re-authorize), drop preferred over delegate, and
  the domain-assignment rule for new tools. Same provenance, same reconciliation.
- `SOP.md`: four new `docs-evidence` checks guarding the claims this change introduces:
  the standards count, the absence of an `authz` facet in the shipped module schema, the
  schema version the authorization standard cites, and a guard that no standard
  reintroduces the deprecated `operator:`-prefixed subject spelling as canonical.
- `SOP.md`: the 9-section operational SOP required by
  [`SK_REPO_DOC_STANDARD` section 2](standards/SK_REPO_DOC_STANDARD.md), with the
  architecture mermaid diagram, a "Start here" index of the five entry-point files, the
  full reference for both reusable workflows and all four scripts, a Symptom-to-Check
  troubleshooting table, and a `docs-evidence` block of hermetic checks (16 as of this
  entry, see the Added bullet above).
- `SECURITY.md`: threat model, reporting channel with a 72 hour acknowledgement SLA,
  in and out of scope, supported-refs table, and safe harbour. Names the supply-chain
  surface honestly: this repo's validators and reusable workflows execute inside other
  repos' CI at `@main`, docs-check tier 3 runs commands authored in the consumer's own
  `SOP.md`, ci-gate-check pip-installs into the consumer's runner, third-party actions
  are tag-pinned rather than SHA-pinned, and the gitleaks binary is fetched without
  checksum verification.
- `CONTRIBUTING.md`: branch model, commit convention including the `Co-Authored-By`
  trailer, what actually gates a merge, and the extra bar for changing the gate (whose
  blast radius is every consumer repo).
- `CODE_OF_CONDUCT.md`: Contributor Covenant 2.1, extended with the conduct rules a
  standards repo needs (a standard is a tool and never a cudgel; never weaken a check to
  make your own work pass; the standard is allowed to be wrong, but not to be ignored
  silently).
- `.github/workflows/docs-check-self.yml` and `.github/workflows/ci-gate-check-self.yml`:
  **the repo that hosts the gates now runs them against itself.** Both
  `docs-check.yml` and `ci-gate-check.yml` declare `on: workflow_call:` and nothing
  else, so neither ever self-triggered; a grep of every YAML file on `main` on
  2026-08-14 found the only `docs-check.yml@` and `ci-gate-check.yml@` references
  anywhere in the repo were comments in those workflows' own headers. Each new file
  calls its gate by the local `uses: ./.github/workflows/<name>.yml` path,
  `docs-check` at `tiers: "1,2"` and `ci-gate-check` at its `soft-fail: false` default.
- `README.md`: a "This repo, held to its own standard" block linking the required doc
  set and stating the T0 tier, so the hub does not orphan its own docs
  (`SK_REPO_DOC_STANDARD` section 1.5).
- `docs-lint.yml` now lints the new root documents too: the five files are added to the
  lychee offline link check, the `check_fences.py` invocation, and the `paths:` filters.

### Changed

- `standards/SKWORLD_AUTHORIZATION_STANDARD.md` was reconciled before landing, because it
  predates three standards that have since been ratified:
  - **Subject spelling now defers to `IDENTITY_NAMING_STANDARD`.** The draft resolved
    subjects as `operator:<device_fp>` and `<agent>@<operator>.<realm>`. The former is
    listed in `IDENTITY_NAMING_STANDARD` section 2.5 as a **deprecated legacy shape**
    aliased to `device:<fingerprint>`; the latter names a segment (`realm`) that grammar
    does not have. Both were corrected, and the constraint that `decide()` stays a pure
    exact matcher (that standard's section 2.4) is now stated where the lifecycle
    resolves the subject.
  - **The guest subject class is now recorded as an OPEN GAP rather than asserted.** The
    draft used `guest:<invite_id>`, which the `IDENTITY_NAMING_STANDARD` section 1 regex
    rejects. Until that standard defines a guest class, a subapp must bind the guest to a
    real enrolled subject or handle the invite as a self-auth route, never invent a local
    spelling and persist it as a decision subject.
  - **The `authz` module facet is now marked PROPOSED, not available.** The draft
    described it as an optional facet of "contract v1.3". The shipped schema is **v1.2**
    with `additionalProperties: false`, so a manifest declaring `authz` fails validation
    today. Landing that text unqualified would have documented a facet nobody can use.
  - Added the `TESTING_AND_CI_STANDARD` section 6 tie (a coverage gate that is skipped or
    soft-failed is not coverage evidence), the MCP-tool-handler-as-PEP case, a Related
    standards section, and the Apache-2.0 footer the other standards carry. The
    out-of-repo design note is now labelled as such instead of reading like a repo path.
- `standards/PROVENANCE_AND_MUTATION_STANDARD.md` and
  `standards/IDENTITY_NAMING_STANDARD.md`: four references to
  `SKWORLD_AUTHORIZATION_STANDARD` were plain code spans rather than links, because the
  target did not exist on `main`. They are now real relative links.
- `README.md` and `ECOSYSTEM.md`: both new standards indexed in the hub table and in the
  "Start here" question list. An unlinked standard is nearly as invisible as an unmerged
  one, and the `docs-evidence` block already fails the build on a standard the README
  does not link.
- `SOP.md`: the standards count corrected from 15 to 18 in all five places it is claimed
  (it was already stale by one before this change), and the troubleshooting row about the
  diverged local checkout rewritten, since the two standards it called unmerged are no
  longer unmerged. That branch holds nothing else `main` lacks: the module-manifest v1.2
  work it is named for reached `main` by another route, and its remaining files are stale
  copies of documents `main` has since rewritten.

### Fixed

- `standards/PROVENANCE_AND_MUTATION_STANDARD.md` section 1: the `actor.id` row permitted
  the `capauth:` wire form as a legal stored value, contradicting
  `IDENTITY_NAMING_STANDARD` section 2.1, which makes that form a DEPRECATED alias that
  "MUST NOT appear in a policy-decision subject or a device record", and contradicting
  that standard's own Related standards cross-reference, which names this exact field:
  "`actor.id` MUST carry the fqid form defined here, never the deprecated `capauth:` wire
  alias". Both documents were ratified 2026-08-14, so the estate has carried two ratified
  rules for one field ever since, and the ambiguity is live in code: SKGateway bakes a
  `capauth:` URI into its builtin agent registry and strips the scheme by regex when
  building a policy-decision subject. The naming standard's rule stands. This row now
  matches it. Found by the read-only estate review under card `b298a763`.
- `standards/SKWORLD_MODULE_CONTRACT_STANDARD.md` section 1: a failed operator observe
  was told to "fail *safe* and report healthy". Reporting healthy when the sensor is
  broken is not failing safe, it is asserting a falsehood, and it masks the outage from
  everything downstream that trusts the condition. The intended property, that a broken
  sensor must not trigger remediation, is preserved by reporting `Unknown`, which the
  estate already has vocabulary for: `operator.conditions` resolve to
  `True` / `False` / `Unknown` in the module schema, and
  `ITIL_AND_RUNBOOK_OPERATING_MODEL_STANDARD` uses the same tri-state. The sentence also
  contradicted the fail-closed rule in `SKWORLD_AUTHORIZATION_STANDARD`. Found by the
  read-only estate review under card `b298a763`.

- The compliance gap the gate was built to catch: `sk-standards` was missing 5 of the 7
  documents its own `SK_REPO_DOC_STANDARD` section 1 requires
  (`SOP.md`, `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md`).
  Tier 1 of `docs_check.py` would have failed this repo from the day it was written, had
  anything ever run it here.

---

## 2026-08-14

### Added

- **`TESTING_AND_CI_STANDARD` section 6, gate integrity**, plus `scripts/ci_gate_check.py`
  and the reusable `.github/workflows/ci-gate-check.yml`: a red bar on `main` is an
  **incident**, because a gate red for reasons nobody caused stops being read and a real
  failure lands invisibly beside it. Pin your linters, guard every publishing job, tell
  stale red from live red by timestamp, and alert on new breakage only. `audit` is the
  preventive half and `sweep` the detective half. (`d166d42`, PR #15)
- **`DOCS_FRESHNESS_STANDARD`**, plus `scripts/docs_check.py` and the reusable
  `.github/workflows/docs-check.yml` gate: three tiers (presence, changelog-on-code-change,
  and the self-verifying `SOP.md` `docs-evidence` block), with a built-in `--self-test`
  negative control. Companion `docs-evidence` stub added to `templates/SOP.template.md`.
  (`cf2d408`, PR #14)
- **`SERVICE_UNIT_STANDARD`** and its validator `scripts/audit-service-units.sh`: the
  restart-limiter rule `RestartSec x (StartLimitBurst - 1) < StartLimitIntervalSec`, the
  two-tier policy chosen by blast radius, `ExecStart` durability, and the recovery-script
  rules. Distilled from an incident where a `203/EXEC` unit reached 47,187 restarts and
  hung a GPU node twice for 13 hours. Reference drop-ins in `reference/systemd/`.
  (`8fae724`, PR #8)
- **Bounded output** section added to `SERVICE_UNIT_STANDARD`: a service that runs
  forever must not write forever. Cap container logs and journald, and verify the cap on
  the container, because a daemon default only applies to containers created after it.
  (`fb79a6a`, PR #13)
- **`PROVENANCE_AND_MUTATION_STANDARD`**: the Signed Provenance Envelope, the append-only
  mutation log, the reversal rule, and target-validation-before-mutation (grep is
  discovery, never targeting). Added in `91d8190` (PR #6) and ratified in `480b7fb`
  (PR #9).

### Changed

- `secret-scan.yml` now runs the **gitleaks binary** (8.28.0, pinned) instead of
  `gitleaks-action`. The action requires a paid license for organization-owned repos and
  exits before scanning a single byte; a fleet repo carried exactly that gate for
  months, permanently red and therefore ignored, while scanning nothing. Full history
  scanned clean on this date. (`1dfc8eb`, PR #10)

### Fixed

- `audit-service-units.sh` no longer reports clean on a scope it could not see. A
  validator that silently skips a scope produces a green result that certifies nothing.
  (`e462db5`, PR #11)
- Five broken relative links that were failing `docs-lint` on `main`. (`d6d2d71`, PR #7)

## 2026-08-13

### Changed

- `ITIL_AND_RUNBOOK_OPERATING_MODEL_STANDARD` section 5 (change management) gained
  scheduled state and the two-executor model. (`3561d26`)

## 2026-08-02

### Added

- `decisions/ADR-0001-skos-skharness-skcode-layering.md`: one engine, two planes, two
  front doors. Accepted, and written as an assertion of what ships rather than a plan.
  Ecosystem map updated alongside it. (`a66d8f8`, PR #5)

## 2026-07-31

### Added

- **`SKWORLD_MODULE_CONTRACT_STANDARD`** with manifest v1.1 and `skworld_module_api` v0:
  one capauth-signed `skworld.module.json` per subapp, with a UI facet and an operator
  facet, plus the registry and signing rule. (`9c61fe4`, PR #2)
- **`ITIL_AND_RUNBOOK_OPERATING_MODEL_STANDARD`**: the Incident, Problem, Change, and
  KEDB lifecycles drawn as mermaid and grounded in the shipped `itil.py`, with an
  explicit implementation-versus-diagram drift register. (`87c57f7`, PR #3)

### Changed

- Module manifest to **v1.2**: adds the optional install facet and knowledge facet as a
  strict superset of v1.1. JSON Schema and two worked examples in
  `reference/skworld-module/`. (`b797081`, PR #4)

## 2026-07-22

### Changed

- `SK_REPO_DOC_STANDARD` now requires a per-repo `PUBLISHING.md` runbook for any
  third-party app-store or plugin release channel, capturing the account, the signing
  cert, and the store's release API. (`ed073b0`)

## 2026-07-03

### Added

- **`BACKUP_AND_RETENTION_STANDARD`**: Grandfather-Father-Son rotation, the
  irreplaceable-versus-rebuildable split, integrity and free-space guards, off-box 3-2-1,
  and a tested restore path including index rebuild. (`90e6794`)
- **`OBSERVABILITY_AND_SCHEDULING_STANDARD`**: nothing scheduled fails silently and
  nothing inbound is lost. Every job wrapped, external inputs through one `gtd-ingest`
  sink, notify-do-not-nag alerting, and an on-demand status self-report as the evidence.
  (`597bb09`)
- `SK_REPO_DOC_STANDARD` **section 0: AI-first, then human-readable.** Docs are read by
  agents before humans, so optimise for deterministic structure and machine-parseable
  facts first. (`43f4c97`, PR #1)

## 2026-06-30

### Changed

- The repo-docs viewer became a default for every `*-skworld-io` static site.
  (`4353a6d`)

## 2026-06-29

### Changed

- `ECOSYSTEM.md`: added `skvault`, the secrets vault split out of `skingest`.
  (`ac00141`)

## 2026-06-28

### Added

- **`TESTING_AND_CI_STANDARD`** and **`SECURITY_DISCLOSURE_STANDARD`**: the cross-impl
  KAT and parity gate, the green-bar release gate, and honest-claims advisories with the
  mandatory experimental / unaudited posture statement. (`96f1afb`)
- **`CRYPTO_AGILITY_STANDARD`**: the agility thesis, self-describing suite ids and wire
  tags, capability advertisement with downgrade safety, how to roll to the next KEM or
  signature, and the named anti-patterns. (`8437e31`)
- **`UNIFIED_INGRESS_STANDARD`**: the one public `:443` rule, the Tailscale-Funnel and
  Cloudflare-Tunnel adapters, the Caddy-versus-Traefik choice, and the capauth-gate
  middleware. Copy-paste configs in `reference/ingress/`. (`e07be8a`)
- `ECOSYSTEM.md`: a navigable map of the whole `sk-pqc` family, with live edges solid and
  roadmap edges dashed. (`0730cd7`)
- `docs-lint` workflow: lychee relative-link check (offline) and mermaid fence balance.
  (`1d86c18`)

### Changed

- `SK_REPO_DOC_STANDARD`: front-end deployment tiers (Direct, Caddy, SKStacks) and the
  now-required SOP "Front-end / Exposure" subsection. (`b40b9cc`)

## 2026-06-27

### Changed

- Consistent repo naming (`sk-pqc-py` / `sk-pqc-dart` / `sk-pqc-rs`) across every
  repository link and cross-link. (`c3cc26c`)

## 2026-06-25

### Added

- Initial commit: `README.md`, `LICENSE` (Apache-2.0), `CRYPTOGRAPHY_STANDARD`,
  `SK_REPO_DOC_STANDARD`, `ARCHITECTURE_AND_DATAFLOW_STANDARD`, `VERSION_LIFECYCLE`, and
  the README and SOP templates. (`96a43f3`)
