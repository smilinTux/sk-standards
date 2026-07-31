# SKWorld Module Contract Standard

How every SKWorld subapp declares itself to the platform, so the umbrella shell
can render it and the Atlas operator seat can run it from **one** agreed
contract. This is the **module contract freeze** (`skworld_module_api` v0 +
manifest schema v1.1): one signed manifest per subapp, two facets, one registry
rule.

> One sentence: **a first-class subapp ships ONE capauth-signed
> `skworld.module.json` that declares BOTH a UI facet (how the shell mounts it)
> and an operator facet (how Atlas watches and steers it); a subapp without both
> facets is not first-class.**

**Status:** frozen at schema **v1.1** / `skworld_module_api` **v0**
(card `f60f4e27`, milestone U0). Ratified in the reconciled platform design
2.3 (Chef, 2026-07-30).

**Source of truth:** this standard and its
[JSON Schema](../reference/skworld-module/skworld.module.schema.json). Where a
subapp's manifest builder and this schema disagree, the standard wins (or the
standard is wrong and we fix it here).

**Reference material:**
- Schema: [`reference/skworld-module/skworld.module.schema.json`](../reference/skworld-module/skworld.module.schema.json)
- Documented example (the real shipped skchat manifest): [`reference/skworld-module/skworld.module.example.json`](../reference/skworld-module/skworld.module.example.json)
- Shipped manifest builders cross-checked against this schema: skchat
  (`skchat/src/skchat/skworld_manifest.py`), skcode
  (`skharness/src/skharness/manifest.py`), skdashboard
  (`skcapstone/src/skcapstone/skdashboard_manifest.py`).
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

## 2. The manifest (`skworld.module.json`), schema v1.1

One file per subapp. Public discovery metadata (**no secrets**): the shell reads
it to learn a subapp's entry, nav, and required audience/scopes *before* it has
a token. Served unauthenticated by the subapp's own daemon at
`/.well-known/skworld-module.json`, and also referenced by local file from the
shell registry (section 4). Built origin-relative to the serving request so
`entry`/`health` URLs never hardcode a host or port.

The JSON Schema is
[`reference/skworld-module/skworld.module.schema.json`](../reference/skworld-module/skworld.module.schema.json)
(JSON Schema draft 2020-12, `additionalProperties: false` — the contract is
frozen). The documented example is
[`reference/skworld-module/skworld.module.example.json`](../reference/skworld-module/skworld.module.example.json)
(the real shipped skchat Grade A manifest). Every field below is validated by
that schema against all three shipped manifests.

### 2.1 The UI facet

| Field | Type | Required | Meaning |
|---|---|---|---|
| `schemaVersion` | `"1.1"` | yes | The sk-standards manifest schema version. Frozen at `1.1` (v1 UI shape + the operator block). |
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

### 2.4 Reserved blocks (not shipped)

The umbrella-shell design 5.2 also sketched `version`, `embed`, `theme`,
`presence`, `notifications`, and `core_modules` blocks. **No shipped manifest
emits any of them today.** They are defined as *optional* in the schema (so a
future manifest that adds them still validates) but are NOT part of the frozen
v1.1 required surface. Do not add them to a subapp manifest until this standard
promotes them into the required set with a schema-version bump.

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
   (`schemaVersion: "1.1"`), with **both** facets.
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
