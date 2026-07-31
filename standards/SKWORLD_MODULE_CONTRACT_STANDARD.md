# SKWorld Module Contract Standard

How every SKWorld subapp declares itself to the platform, so the umbrella shell
can render it and the Atlas operator seat can run it from **one** agreed
contract. This is the **module contract freeze** (`skworld_module_api` v0 +
manifest schema v1.2): one signed manifest per subapp, two required facets, one
registry rule, and (schema v1.2) **two optional facets that turn the manifest
into a pluggable capability pack**.

> One sentence: **a first-class subapp ships ONE capauth-signed
> `skworld.module.json` that declares BOTH a UI facet (how the shell mounts it)
> and an operator facet (how Atlas watches and steers it); a subapp without both
> facets is not first-class. A manifest MAY additionally declare an install
> facet (how a pluggable capability pack installs) and a knowledge facet (the
> retriever Atlas auto-enables for RAG).**

**Status:** the required surface is frozen at `skworld_module_api` **v0**
(card `f60f4e27`, milestone U0; ratified in the reconciled platform design 2.3,
Chef, 2026-07-30). The manifest schema is **v1.2**: v1.1 (the two required
facets) plus the two **optional** `install` and `knowledge` facets added for the
pluggable-capability-pack contract (design `2026-07-31-sk-ops-pluggable-bolton-and-ootb-install`
§2.3, card OPS0.1). **v1.2 is a strict superset of v1.1:** a v1.1 manifest
(schemaVersion `1.1`, neither optional facet) is still valid unchanged, so the
four shipped manifests need no edit. The optional facets are documented in
§2.5-§2.6.

**Source of truth:** this standard and its
[JSON Schema](../reference/skworld-module/skworld.module.schema.json). Where a
subapp's manifest builder and this schema disagree, the standard wins (or the
standard is wrong and we fix it here).

**Reference material:**
- Schema: [`reference/skworld-module/skworld.module.schema.json`](../reference/skworld-module/skworld.module.schema.json)
- Documented UI+operator example (the real shipped skchat manifest): [`reference/skworld-module/skworld.module.example.json`](../reference/skworld-module/skworld.module.example.json)
- Documented capability-pack example (v1.2, all four facets, the skbrain ops pack): [`reference/skworld-module/skworld.module.pack-example.json`](../reference/skworld-module/skworld.module.pack-example.json)
- Shipped manifest builders cross-checked against this schema: skchat
  (`skchat/src/skchat/skworld_manifest.py`), skcode
  (`skharness/src/skharness/manifest.py`), skos
  (`skos/src/skos/skworld_manifest.py`), skdashboard
  (`skcapstone/src/skcapstone/skdashboard_manifest.py`). All four emit
  `schemaVersion: "1.1"` and validate unchanged under v1.2.
- Shipped Dart contract: `skchat-app/packages/skworld_module_api`.

---

## 1. Why one contract, two facets

The shell's `skworld_module_api` (Dart: `SkworldModule`, `ShellContext`,
`AuthContext`, `ShellBus`) and Atlas's operator adapter (`explain` / `observe` /
`act`, dict-shaped, validated by `operator_seat/adapter.py`) both describe *what
a subapp exposes to the platform*. They are **not merged into one interface**,
and they are **not two separate contracts**. They are **ONE contract document
with TWO technical seams**:

- **The UI facet** is consumed **in-process by the Dart shell** (widgets, a
  theme object, a nullable `ShellContext`). Its consumer is the umbrella shell.
- **The operator facet** is consumed **by a Python loop across process
  boundaries** (Atlas), deliberately CLI-first
  (`<app> operator explain|observe|act --json`) so a Starlette app, a Flutter
  daemon, and a bash script can all conform.

They stay distinct because they have **different runtimes/languages**,
**different trust postures** (a human UI session vs. an AI operator seat),
and **different failure semantics** (a failed UI pane renders grey with a
reason; a failed operator observe must fail *safe* and report healthy). But they
share **one identity, one registration, one signature**: the manifest is the
single thing Chef signs and the single thing both the shell registry and the
fleet `Operatorapp` object point at, so a subapp cannot drift into "renders but
is invisible to Atlas" (or vice versa) without the divergence being visible in
one file. They also share **one vocabulary**: `operator.conditions` names are
the same names Atlas observes and the same names the shell's grey-with-a-reason
availability can render; `deeplinkPrefix` is the same prefix Atlas escalations
and the shell router both use.

---

## 2. The manifest (`skworld.module.json`), schema v1.2

One file per subapp. Public discovery metadata (**no secrets**): the shell reads
it to learn a subapp's entry, nav, and required audience/scopes *before* it has
a token. Served unauthenticated by the subapp's own daemon at
`/.well-known/skworld-module.json`, and also referenced by local file from the
shell registry (section 4). Built origin-relative to the serving request so
`entry`/`health` URLs never hardcode a host or port.

The JSON Schema is
[`reference/skworld-module/skworld.module.schema.json`](../reference/skworld-module/skworld.module.schema.json)
(JSON Schema draft 2020-12, `additionalProperties: false` — the contract is
frozen, including inside every install step). The documented UI+operator example
is
[`reference/skworld-module/skworld.module.example.json`](../reference/skworld-module/skworld.module.example.json)
(the real shipped skchat Grade A manifest); the documented capability-pack
example (all four facets) is
[`reference/skworld-module/skworld.module.pack-example.json`](../reference/skworld-module/skworld.module.pack-example.json).
Every field below is validated by that schema against all four shipped
manifests.

### 2.1 The UI facet

| Field | Type | Required | Meaning |
|---|---|---|---|
| `schemaVersion` | `"1.1"` \| `"1.2"` | yes | The sk-standards manifest schema version. `1.1` = the two required facets (v1 UI shape + the operator block). `1.2` = the same, plus at least one of the optional `install` / `knowledge` facets. A manifest that declares either optional facet MUST be `1.2`; a manifest with neither MAY stay `1.1`. |
| `id` | string (`^[a-z][a-z0-9_-]*$`) | yes | Stable module id. Equals `SkworldModule.id`, the `skworld://<id>/` authority, and the shell/Atlas registry key. |
| `name` | string | yes | Human-visible name (shipped manifests set it to the nav label: `Chats`, `Code`, `Board`). |
| `grade` | `"A"` \| `"B"` | yes | Composition grade. **A** = native in-process Flutter module. **B** = web embed. |
| `entry` | object | yes | How the shell mounts it. Grade A: `entry.flutter_package`. Grade B: `entry.url`. |
| `nav` | `{icon, order, label}` | yes | Primary-navigation placement. `icon` is a design-system **token name**, never a URL. `order` sorts ascending (shipped: Chats 20, Code 30, Board 40). Mirrors the Dart `ModuleNav`. |
| `deeplinkPrefix` | string (`^skworld://<id>/$`) | yes | The `skworld://<id>/` prefix this module answers to. |
| `auth` | `{audience, scopes[]}` | yes | The audience the shell mints a short-lived token for, and the full scope set it may grant a subset of. |
| `memory` | `{opt_in, scope?}` | yes | Whether it opts into skmemory; `scope` is required when `opt_in` is true. |
| `health` | string | yes | Health endpoint (path or absolute URL); shipped daemons build it origin-relative to the serving request. |

**`entry` by grade.** Grade A supplies
`entry.flutter_package` — the shipped workspace form is
`{ "path": "packages/<pkg>", "package": "<pkg>" }`; a package promoted to its own
repo uses `{ "git": "<url>", "ref": "<tag>", "package": "<pkg>" }`. Grade B
supplies `entry.url` (the web surface the shell embeds). A **grade promotion**
(B to A) is a manifest edit plus a package, **never a contract change**.

### 2.2 The operator facet (the `operator` block)

| Field | Type | Required | Meaning |
|---|---|---|---|
| `contractVersion` | integer `1` | yes | The operator-facet contract version. Frozen at `1`. |
| `cli` | string | yes | The CLI-first conformance entry point: `<cli> explain\|observe\|act --json`. |
| `repos` | string[] | yes | The repos implementing this subapp (Atlas escalation routing). |
| `conditions` | string[] | yes | The condition names Atlas observes (each resolves to `True` / `False` / `Unknown`). |
| `proposedStandardActions` | string[] | yes | Standard actions the subapp **proposes** Atlas may auto-apply. |

Two hard rules on the operator facet:

1. **`conditions` MUST equal the app's Atlas adapter `CONDITIONS`, in order.**
   Each subapp ships a manifest-adapter drift-guard test asserting
   `manifest.operator.conditions == <app>_adapter.CONDITIONS` exactly, so the
   manifest and `operator_seat/<app>_adapter.py` never drift apart.
2. **`proposedStandardActions` is a PROPOSAL ONLY.** Ratification of what Atlas
   may actually auto-apply is **human-only**, and lives in the fleet
   `Operatorapp` object's `ratifiedStandardActions`, never in the manifest.
   Irreversible/high-blast actions can never be auto-applied regardless of the
   manifest (`policy.py` forces MAJOR by construction).

### 2.3 Grade B example (skcode)

```json
{
  "schemaVersion": "1.1",
  "id": "skcode",
  "name": "Code",
  "grade": "B",
  "entry": { "url": "http://<host>:9394/app" },
  "nav": { "icon": "terminal", "order": 30, "label": "Code" },
  "deeplinkPrefix": "skworld://skcode/",
  "auth": {
    "audience": "skcode",
    "scopes": ["skcode.stream", "skcode.inject", "skcode.dispatch"]
  },
  "memory": { "opt_in": false },
  "health": "http://<host>:9394/api/v1/hosts/self",
  "operator": {
    "contractVersion": 1,
    "cli": "skcode-hostd operator",
    "repos": ["skharness"],
    "conditions": ["HostdReady", "SessionsHealthy", "RegistryConsistent", "AuthEnforced"],
    "proposedStandardActions": ["restart-hostd", "archive-stale-session"]
  }
}
```

### 2.4 The install facet (the `install` block, optional, v1.2)

A manifest that packages a **pluggable capability pack** adds an `install`
block. It declares, declaratively, how the pack ACTIVATES its capability on a
node: schema, roles, content, seeds, scheduled fleet objects, and doctor checks,
in one reversible install. It is consumed **exactly once per node** by the skos
planner/provisioner (`skos install <id>`), **never by Atlas**, and is
re-runnable idempotently (every step has done / pending / failed check
semantics). A plain first-class subapp omits `install` entirely.

The block has two fields:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `requires` | object | no | The gate the planner checks before running any step. `requires.capabilities` is a list of node capability ids (skos catalog, e.g. `skmem-pg`) that must be present; `requires.packages` maps a package name to a version constraint the node must satisfy (e.g. `{"skcapstone": ">=0.16"}`). |
| `steps` | array | yes | The ordered install steps (≥1). Each is one of the six typed **step kinds** below, discriminated by `kind` (a JSON Schema `oneOf`). The provisioner runs them top to bottom and records per-step state in `registry/installed.json`. |

**The step-kind vocabulary.** Each kind is a closed object
(`additionalProperties: false`); the columns are its fields.

| `kind` | Fields | Does |
|---|---|---|
| `sql_migration` | `db` (req), `script` (req), `pre_dump`, `verify` | Applies an idempotent SQL `script` to database `db`. `script` and `verify` are package-qualified paths (`"<package>:<repo-relative-path>"`, e.g. `skmemory:deploy/skmem-pg/03-ops-namespace.sql`). `pre_dump: true` takes a `pg_dump` before applying (live-node safety); `verify` is a query run after apply whose mismatch fails the step. |
| `db_roles` | `logins` (req), `password_source` (req), `db`, `vault_entries`, `env_drop_in` | Creates login roles and binds each to the migration's NOLOGIN group role. `logins` maps a login-role name to the group role it is `GRANT`ed (e.g. `{"skbrain_projector": "skbrain_ops_rw"}`). `password_source` is the credential convention (`skvault` is the only value defined today). `vault_entries` optionally names each login's skvault entry; `env_drop_in` optionally names the `environment.d` file the provisioner writes DSNs into. This closes the "bind roles out-of-band" gap with a defined convention. |
| `content_repo` | `name` (req), `dest` (req), `remotes`, `private`, `marker`, `syncthing` | Clones a git repo to serve as the pack's canon content: `name` (logical repo), `dest` (checkout path). Clones only if absent, verifies the `marker` file (e.g. `CLAUDE.md`), never touches an existing checkout. `remotes` optionally lists clone URLs (else resolved from the named repo's own config); `private` selects operator git credentials; `syncthing: true` PRINTS (never auto-applies) the share instruction. |
| `seed` | `cmd` (req), `defer_ok` | Runs an idempotent seed command `cmd` (argv array, e.g. `["skoperator", "kedb-seed"]`); create-or-skip is the command's own job. `defer_ok: true` records the step as **pending** (not failed) when the command does not exist yet, so a pack can ship before a dependency lands. |
| `fleet_objects` | `objects` (req) | Writes per-node service/cron object specs (pack-relative paths, e.g. `cronjob/skbrain-sync.json`) into the fleet store as the **human operator role** (single-writer-per-file preserved). Existing objects are diffed, never blind-overwritten. |
| `doctor` | `checks` (req) | Registers a doctor check family (ids like `skbrain:schema`) so `skcapstone doctor` and `skos status` cover the pack from the first run. |

These six kinds are exactly what the ops-pack DDL + the skos planner/provisioner
need and no more: `sql_migration` + `db_roles` reflect the real
`03-ops-namespace.sql` (which creates `ops` / `ops_brain`, `hybrid_search_ops`,
and the NOLOGIN `skbrain_ops_rw` / `skbrain_ops_ro` group roles it tells the
operator to bind out-of-band); `content_repo` acquires the canon (`skbrain-ops`);
`seed` runs the idempotent KEDB-floor / CMDB-inventory / initial-projection
commands; `fleet_objects` installs the scheduling the seat needs to run
unattended; `doctor` makes the capability assertable. Adding a **source** is a
new step-kind entry here plus one planner branch, never a parallel installer.

**Coupling is by construction.** There is no step-selection or facet-selection
field: a capability pack is indivisible. `skos install <id>` has no `--only`
flag by design, and the pack's own doctor family fails a half-present capability
(e.g. `skbrain:kedb` fails when ITIL is active but canon coverage is missing).

**Migration policy.** `sql_migration` is the one-command guarded apply for LIVE
nodes (auto `pre_dump`, idempotent script, auto `verify`, operator-initiated,
`.158`-first, ITIL change record). FRESH DBs get the same script via the compose
first-boot init path instead (no live data, no risk). CI never applies
migrations. The install facet declares the WHAT; where it runs decides the HOW.

### 2.5 The knowledge facet (the `knowledge` block, optional, v1.2)

A pack that ships retrievable knowledge adds a `knowledge` block so the operator
seat can **auto-enable RAG enrichment** the moment the capability is present. At
bootstrap the seat reads this facet from each verified manifest, probes for the
declared namespace + search function as the read-only role, and builds the
declared retriever only if the probe passes (fail-safe: probe fails, retriever
is disabled with a logged reason and the relevant condition reports `False`;
briefs flow unenriched). It declares **retrieval only, never policy** — knowledge
is not authority, so the operator-seat constitutional carve-out holds untouched.

| Field | Type | Required | Meaning |
|---|---|---|---|
| `namespace` | string | yes | The skmem-pg schema/namespace the pack's content lives in (e.g. `ops`). The seat's probe checks `information_schema.schemata` for this before enabling the retriever. |
| `search_fn` | string | yes | The schema-qualified hybrid-search function the retriever calls (e.g. `ops.hybrid_search_ops`, the RRF sibling of `public.hybrid_search_docs`). |
| `retriever` | string | yes | The `<module>:<callable>` the seat imports to build the retriever object (e.g. `skos.skbrain.read_api:build_retriever`). |
| `reader_role` | string | no | The **read-only** database role the seat connects as to probe and retrieve (e.g. `skbrain_ops_ro`). Scopes retrieval to a role that cannot mutate the namespace. |
| `graph` | string | no | An AGE graph name exposing the pack's knowledge graph (e.g. `ops_brain`). |
| `kinds` | string[] | no | The content kinds the namespace holds (e.g. `runbook`, `known-error`, `postmortem`). |
| `kedb` | boolean | no | Whether this pack's knowledge feeds the Known-Error Database linkage. |

**Declarative generality.** Any future bolt-on that ships a `knowledge` facet (a
security pack with its own namespace, a client-work pack) gets the same
treatment with zero seat code changes: schema probe, scoped retriever, enrichment
gated on its own conditions. That is the "a bolt-on Atlas has never seen becomes
usable by dropping in its signed manifest" property, met for both optional
facets: `install` (activation) and `knowledge` (retrieval).

### 2.6 Capability-pack example (skbrain, all four facets, v1.2)

The full documented example is
[`reference/skworld-module/skworld.module.pack-example.json`](../reference/skworld-module/skworld.module.pack-example.json).
Abbreviated (UI + operator facets elided; see §2.1-§2.3 and the example file):

```json
{
  "schemaVersion": "1.2",
  "id": "skbrain",
  "name": "Ops Wiki",
  "grade": "B",
  "entry": { "url": "http://127.0.0.1:7778/skbrain" },
  "nav": { "icon": "book", "order": 60, "label": "Ops Wiki" },
  "deeplinkPrefix": "skworld://skbrain/",
  "auth": { "audience": "skdashboard", "scopes": ["skbrain.read"] },
  "memory": { "opt_in": false },
  "health": "http://127.0.0.1:7778/api/status",
  "operator": {
    "contractVersion": 1,
    "cli": "skbrain operator",
    "repos": ["skos", "skcapstone", "skbrain-ops", "skmemory"],
    "conditions": ["OpsSchemaPresent", "ProjectorFresh",
                   "CmdbDriftBounded", "KedbCanonCovered"],
    "proposedStandardActions": ["run-skbrain-sync", "run-cmdb-reconcile"]
  },
  "knowledge": {
    "namespace": "ops",
    "search_fn": "ops.hybrid_search_ops",
    "retriever": "skos.skbrain.read_api:build_retriever",
    "reader_role": "skbrain_ops_ro",
    "graph": "ops_brain",
    "kinds": ["runbook", "known-error", "postmortem"],
    "kedb": true
  },
  "install": {
    "requires": {
      "capabilities": ["skmem-pg"],
      "packages": { "skcapstone": ">=0.16", "skos": ">=0.3", "skmemory": ">=0.12" }
    },
    "steps": [
      { "kind": "sql_migration", "db": "skmem-pg",
        "script": "skmemory:deploy/skmem-pg/03-ops-namespace.sql",
        "pre_dump": true, "verify": "skmemory:deploy/skmem-pg/verify-ops.sql" },
      { "kind": "db_roles", "db": "skmem-pg",
        "logins": { "skbrain_projector": "skbrain_ops_rw",
                    "skbrain_reader": "skbrain_ops_ro" },
        "password_source": "skvault",
        "vault_entries": { "skbrain_projector": "SKBRAIN_PG_PROJECTOR_PW",
                           "skbrain_reader": "SKBRAIN_PG_READER_PW" },
        "env_drop_in": "~/.config/environment.d/skbrain.conf" },
      { "kind": "content_repo", "name": "skbrain-ops", "dest": "~/clawd/skbrain-ops",
        "private": true, "marker": "CLAUDE.md", "syncthing": true },
      { "kind": "seed", "cmd": ["skoperator", "kedb-seed"] },
      { "kind": "seed", "cmd": ["skcapstone", "cmdb", "seed"] },
      { "kind": "seed", "cmd": ["skbrain", "sync"], "defer_ok": true },
      { "kind": "fleet_objects",
        "objects": ["cronjob/skbrain-sync.json", "cronjob/skbrain-cmdb-reconcile.json"] },
      { "kind": "doctor",
        "checks": ["skbrain:schema", "skbrain:grants", "skbrain:content",
                   "skbrain:projector", "skbrain:kedb", "skbrain:adapter",
                   "skbrain:cron"] }
    ]
  }
}
```

### 2.7 Reserved blocks (not shipped)

The umbrella-shell design 5.2 also sketched `version`, `embed`, `theme`,
`presence`, `notifications`, and `core_modules` blocks. **No shipped manifest
emits any of them today.** They are defined as *optional* in the schema (so a
future manifest that adds them still validates) but are NOT part of the frozen
required surface. Do not add them to a subapp manifest until this standard
promotes them into the required set with a schema-version bump. (The v1.2
`install` and `knowledge` facets in §2.4-§2.5 are different: they are documented,
normative optional facets with a real consumer, not reserved sketches.)

---

## 3. The Dart contract (`skworld_module_api` v0, the UI-facet validator)

This is a **documentation freeze of an interface that already ships**, not a
code move. The package is `skchat-app/packages/skworld_module_api` (abstract
types only; it imports nothing from the shell or from skchat beyond Flutter
widget/theme primitives, so it can be promoted to its own repo when skcode
becomes the second consumer). The whole surface a Grade A module may touch:

```dart
// The UI-facet contract a subapp implements to mount into the shell.
abstract interface class SkworldModule {
  String get id;                                    // must match manifest.id
  ModuleNav get nav;                                // mirrors manifest.nav
  Widget build(BuildContext context, ShellContext? shell);
}

// What the shell provides a MOUNTED module. NULLABLE at the boundary.
abstract interface class ShellContext {
  ThemeData get theme;      // the shell's theme (Sovereign Glass)
  AuthContext get auth;     // audience-scoped identity/token surface
  ShellBus get bus;         // events + navigation back to the shell
}

// The audience-scoped identity a mounted module sees (never a root credential).
abstract interface class AuthContext {
  String get audience;                 // matches manifest.auth.audience
  String? get subjectFqid;             // null until an identity is established
  Set<String> get scopes;              // matches manifest.auth.scopes
  bool hasScope(String scope);
  Future<String?> token();             // short-lived; never persist
}

// The event + navigation bus (transport-agnostic: one contract for the
// in-process Dart bus today and a future postmessage bridge).
abstract interface class ShellBus {
  void navigate(String deeplink);      // skworld://<id>/<path>, cross-module OK
  void emit(ShellEvent event);
  Stream<ShellEvent> get events;
}

// Primary-navigation metadata (mirrors the manifest `nav` block).
class ModuleNav {
  const ModuleNav({required this.label, required this.icon,
                   this.order = 100, this.deeplinkPrefix});
  // label, icon (IconData), order (int), deeplinkPrefix (String?)
}
```

### 3.1 The standalone-nullability rule (the independence contract)

`ShellContext` is **nullable by design**, and that nullability is the entire
standalone signal:

- **`shell == null` means STANDALONE.** The module runs under its own runner
  (for example `apps/skchat_standalone`) with no shell, and MUST fall back to
  its own theme, its own capauth login, and its own router.
- **`shell != null` means MOUNTED.** The module composes into the shell and uses
  the shell's `theme`, `auth`, and `bus`.
- **A first-class subapp MUST behave correctly in both modes.** CI for every
  Grade A module boots it with `shell == null` (the standalone boot gate), and a
  grep gate proves the module's UI package imports only `skworld_module_api`,
  never any shell package. This keeps every subapp independently deployable.

The `ShellBus` is **optional by contract**: a standalone module has none, so
badges, notifications, and cross-module navigation are enhancements, never
load-bearing. `AuthContext.token()` is async because minting may round-trip to
the identity kernel; callers treat the result as short-lived and never persist
it. Authentication (the token) is the shell's job; **authorization stays
downstream** as a `capauth.authz.decide` call in the subapp's backend.

---

## 4. The registry and the signing rule

**The registry.** Each node holds a static, capauth-signed shell registry at
`~/.skcapstone/shell/modules` (`modules.json`): an ordered list of **manifest
locations** — each a **local file** or a `/.well-known/` **URL** — plus the
operator's enable set. The fleet `Operatorapp` registration object and the
shell's registry point at the **same** manifest, so the UI facet and the
operator facet can never diverge unseen.

**The signing rule (mount gate).** Every referenced manifest carries a
**detached capauth signature** (`skworld.module.json.sig`, signed by the
operator-approved manifest key). The shell **refuses to mount any manifest whose
detached capauth signature does not verify** against an operator-approved key,
and refuses any `embed.allowed_origins` (when that reserved block is eventually
used) not covered by the signed manifest. Verification reuses
`fleet/signing.py::verify_payload` semantics — not a reimplementation.

**Discovery posture.** Dynamic discovery (a node advertising its own modules) is
explicitly **deferred**; when it arrives it rides the **same** signature rule.
Until then, registration is the operator adding a signed manifest location to
the node registry. A deployment may still hide modules it does not ship via the
existing node capabilities hint.

---

## 5. Per-repo compliance checklist

A subapp is a **first-class SKWorld module** when:

1. It ships `skworld.module.json` validating against
   [the schema](../reference/skworld-module/skworld.module.schema.json)
   (`schemaVersion: "1.1"`, or `"1.2"` when it also declares a v1.2 facet), with
   **both** required facets (UI + operator).
2. Its daemon serves the manifest unauthenticated at
   `/.well-known/skworld-module.json`, built origin-relative.
3. A **detached capauth signature** exists and verifies before mount (section 4).
4. `operator.conditions` **exactly equals** its Atlas adapter `CONDITIONS`
   (drift-guard test present).
5. Grade A: it implements `SkworldModule` from `skworld_module_api`, imports
   **only** that package (grep gate), and **boots headless with `shell == null`**
   in CI (standalone guarantee).
6. `nav.icon` is a **design-system token name**, never a URL; `deeplinkPrefix`
   matches `skworld://<id>/`.

A manifest is additionally a **pluggable capability pack** when it declares an
`install` facet (§2.4) and, if it ships retrievable knowledge, a `knowledge`
facet (§2.5); it then sets `schemaVersion: "1.2"`, is capauth-signed like any
other manifest (the signature is the trust gate for BOTH the shell mount and the
operator seat's discovery), and its capability is installed by
`skos install <id>` and asserted by the `<id>:*` doctor family it registers.

---

## 6. Related standards

- [`SK_REPO_DOC_STANDARD`](./SK_REPO_DOC_STANDARD.md) — the AI-first, then
  human-readable doc set every subapp repo also ships.
- [`ARCHITECTURE_AND_DATAFLOW_STANDARD`](./ARCHITECTURE_AND_DATAFLOW_STANDARD.md)
  — how the shell/subapp composition is drawn.
- [`UNIFIED_INGRESS_STANDARD`](./UNIFIED_INGRESS_STANDARD.md) — the one public
  `:443` rule the subapp backends sit behind.
- [`VERSION_LIFECYCLE`](./VERSION_LIFECYCLE.md) — how the schema version and the
  operator `contractVersion` move.
