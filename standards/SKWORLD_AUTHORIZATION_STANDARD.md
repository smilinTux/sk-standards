# SKWorld Authorization Standard

**Status:** Ecosystem standard for every `sk*` subapp that exposes an
authenticated network surface (skchat, skdashboard, skboard/skcoord, skcode,
skos, skgateway, and future subapps). Companion to
[`SKWORLD_MODULE_CONTRACT_STANDARD`](./SKWORLD_MODULE_CONTRACT_STANDARD.md),
[`CRYPTOGRAPHY_STANDARD`](./CRYPTOGRAPHY_STANDARD.md),
[`IDENTITY_NAMING_STANDARD`](./IDENTITY_NAMING_STANDARD.md),
[`PROVENANCE_AND_MUTATION_STANDARD`](./PROVENANCE_AND_MUTATION_STANDARD.md),
and the
[ITIL operating model](./ITIL_AND_RUNBOOK_OPERATING_MODEL_STANDARD.md).

**Why:** SKWorld has the right kernel, ONE deterministic Policy Decision Point
(`capauth.authz.decide(subject, capability, resource, context)`, deciding from
cryptographic facts only and failing closed), but had no *model* for how each
subapp enforces. Two live incidents on the CR-3 enforce flip proved the gap:
(a) a subject class with no declared, auditable grant set, and (b) an enforce
flip that 403ed real routes because the route map was incomplete AND **shadow
mode structurally cannot see unmapped routes** (it only compares where a
capability is already mapped). "Shadow divergence == 0" is therefore necessary
but never sufficient evidence for enforce-safety. This standard makes coverage,
not soak, the safety criterion.

> **Division of labour with the neighbouring standards.**
> [`IDENTITY_NAMING_STANDARD`](./IDENTITY_NAMING_STANDARD.md) governs **how a
> subject is spelled**; this standard governs **what that subject MAY do** once
> resolved. [`PROVENANCE_AND_MUTATION_STANDARD`](./PROVENANCE_AND_MUTATION_STANDARD.md)
> records **who DID act** after the decision. The three are not
> interchangeable and none of them may re-implement another's job.

---

## 1. One PDP, many thin PEPs

There is exactly one decision point: `capauth.authz.decide`. Every subapp is a
thin **Policy Enforcement Point** that DECIDES NOTHING; it runs the universal
request lifecycle and delegates the allow/deny to the PDP:

1. **Classify the route** (gated / public / self-auth) BEFORE anything else.
2. **Authenticate** (a valid capauth / audience credential), else 401.
3. **Resolve the subject** from the verified credential only, never from request
   input. The subject string MUST be a canonical **fqid** per
   [`IDENTITY_NAMING_STANDARD` section 1](./IDENTITY_NAMING_STANDARD.md#1-canonical-grammar-normative-schema):
   `device:<fingerprint>` for a device seat, `<agent>@<operator>.<org-domain>`
   for an agent, `<name>@<org-domain>` for a sovereign human root. Legacy
   spellings (`operator:<fingerprint>`, a `capauth:`-prefixed wire form) are
   translated by that standard's closed alias table **at ingest or enrollment**
   and never reach this lifecycle.
4. **Map (method, route) to a capability.** In enforce, an unmapped gated route
   is a 403 by construction; the coverage gate (section 3) makes that branch
   provably unreachable for legitimate routes.
5. **Decide** via `decide(subject, capability, resource, context)`. Fail closed
   on any error, unknown capability, or insufficient enrollment mode.
6. **Emit the audit obligation** the PDP returns.

`decide()` is the function
[`IDENTITY_NAMING_STANDARD` section 2.4](./IDENTITY_NAMING_STANDARD.md#2-normative-rules)
keeps pure: it is an **exact matcher over already-canonical strings**. It MUST
NOT lowercase, trim, strip a prefix, or consult an alias table. Normalizing
inside the decision function is how "what got enrolled" and "what gets matched"
drift apart, and that drift fails OPEN as easily as closed.

A non-Python subapp (e.g. skgateway, Node) MUST NOT re-implement the PDP; it
calls a capauth authorization endpoint (`POST /v1/authz/decide`) so there is one
decision point and no drift. The same rule binds a **non-HTTP** authenticated
surface: an MCP tool handler is a PEP too (see
[`ITIL_AND_RUNBOOK_OPERATING_MODEL_STANDARD`](./ITIL_AND_RUNBOOK_OPERATING_MODEL_STANDARD.md),
which names the MCP tool as the enforcement point for the `agentrun.*` and
`change.*` capabilities), and it runs the same six steps with "tool name" in
place of "(method, route)".

## 2. Capability taxonomy

- Names are `<subapp>.<action>` (`skchat.inbox`, `skboard.read`,
  `skdashboard.itil.write`, `skcode.dispatch`).
- Capabilities gate CLASSES of action, not individual routes; many routes map to
  one capability.
- Three sensitivity tiers map to `minimum_mode` (the enrollment trust floor):
  **read = TOFU**, **write = attested**, **act/admin/RCE = verified**.
- Least privilege: a route gets the lowest-tier capability that still protects
  the resource. New subapps mint their own `<subapp>.*` namespace as
  `CapabilityRule` rows in the PDP's `DEFAULT_RULES`.

## 3. Route-coverage discipline (the enforce-safety criterion)

Every authenticated route is exactly one of: **capability-mapped**,
**explicit-public** (on a declared allowlist), or **explicit-self-auth** (on a
declared registry with a per-route verifier + rationale). Nothing implicit.

- A **CI completeness gate** enumerates the subapp's LIVE route table and FAILS
  if any gated route is unclassified. This gate, not shadow soak, is what makes
  an enforce flip provably safe.
- Mapping MUST be **method-aware**: `GET` and `POST` on the same path can be
  different capabilities (read vs write). Suffix-only maps are non-compliant.
- **Shadow mode MUST additionally log unmapped gated routes**, so the structural
  blind spot (a route with no capability) is observable during soak instead of
  only at enforce.
- The coverage gate MUST be a gate that can fail. Per
  [`TESTING_AND_CI_STANDARD` section 6](./TESTING_AND_CI_STANDARD.md), a
  coverage job that is skipped, soft-failed, or `|| true`-swallowed is not
  evidence of coverage, and it is exactly the shape that lets an incomplete
  route map reach an enforce flip while the board reads green.

## 4. Token-minting and self-auth routes

Routes that authenticate differently (audience-token / embed-token mints via a
per-request check, auth/pair bootstrap, guest links, inbound federation) are NOT
capability-gated. They MUST be listed in the subapp's self-auth registry with
their verifier and a one-line rationale, so the coverage gate accepts them
explicitly rather than by omission. A self-auth route still fails closed on a
missing/invalid credential where one is required (e.g. a mint endpoint never
mints for an anonymous caller).

## 5. Subjects and declared grant bundles

Each subject class (device seat, agent fqid, guest) has a DECLARED grant
bundle, minted at enrollment (the `operator_grants.py` pattern: non-expiring,
best-effort, written to the same store the PDP reads). Grants are audited by
literally calling `decide()` for each (subject, capability) pair, not assumed.
Enrollment mode gates the bundle: a capability whose `minimum_mode` exceeds the
subject's enrollment mode is not usable even if the token is present.

**Open gap: the guest subject class has no canonical fqid form.** The
[`IDENTITY_NAMING_STANDARD` section 1](./IDENTITY_NAMING_STANDARD.md#1-canonical-grammar-normative-schema)
grammar admits five entity classes (humans, agents, services, nodes, device
seats) and exactly one prefixed class (`device:`). An invite-scoped guest
matches none of them and the section 1 regex REJECTS a `guest:<invite_id>`
string. Until that standard is amended to define a guest class, a subapp MUST
NOT invent a local guest spelling and store it as a policy-decision subject:
either bind the guest to a real enrolled subject at redemption, or handle the
invite as a **self-auth route** under section 4, where the invite is the
verifier and no PDP subject is minted. This is recorded as an open item, not a
resolved one.

## 6. Rollout rails (per subapp, shadow is necessary but NOT sufficient)

1. Turn the dataplane auth gate ON (authentication only).
2. PDP **shadow** (compute the decision, log divergence + unmapped gated routes,
   return the legacy outcome).
3. **Coverage gate GREEN** (every gated route classified). This is the gate, not
   step 4.
4. Mint + **audit every subject's grant bundle** via `decide()`.
5. Soak: a clean window with zero divergence AND zero unmapped-route logs.
6. **Enforce** (human-hand), first node only, 24h doctor-green, then the rest,
   an ITIL change per node. Watch the `enforce-deny` log; revert = flip the flag
   back to shadow (instant, no data change).

An RCE / write-authority surface (skcode dispatch/inject) is **deny-all by
default** and stays that way until a pre-enable security review has been done
and recorded as an ITIL change. That is the correct posture for the highest
tier, not a bug. The review is the gate; passing it is how such a surface is
legitimately enabled, and any enablement without one is the defect.

## 7. Module-contract integration (proposed `authz` facet, NOT yet in the schema)

**Status: proposed, not ratified.** The shipped manifest schema is **v1.2**
([`SKWORLD_MODULE_CONTRACT_STANDARD`](./SKWORLD_MODULE_CONTRACT_STANDARD.md),
[`reference/skworld-module/skworld.module.schema.json`](../reference/skworld-module/skworld.module.schema.json)),
it declares `additionalProperties: false`, and it has no `authz` block. A
manifest that adds one today **will fail schema validation**. Nothing in this
section is implementable until the schema is bumped.

The proposal: a subapp declares its authorization surface in
`skworld.module.json` via an optional `authz` facet carrying its capability
namespace, the (method, route) to capability map, the public allowlist, and the
self-auth registry. A drift-guard test binds the declaration to the PEP's live
tables (mirroring the operator-facet conditions guard). This would let the shell
and the operator seat verify coverage without reading code. Adopting it
requires a schema-version bump handled under the module contract standard's own
versioning rules, exactly as the v1.1 to v1.2 facet addition was, and this
section MUST be updated to name the ratified version at that time.

## Compliance checklist (per authenticated subapp)

- [ ] PEP runs the section-1 lifecycle; decides nothing itself; fails closed.
- [ ] Subjects are canonical fqids per `IDENTITY_NAMING_STANDARD` section 1; no
      `operator:`-prefixed or `capauth:`-prefixed value reaches `decide()`.
- [ ] `decide()` is a pure exact matcher: no normalization, no alias lookup.
- [ ] Capabilities are `<subapp>.<action>`, tiered read/write/act to TOFU/attested/verified.
- [ ] Every gated route is capability-mapped, explicit-public, or explicit-self-auth.
- [ ] A CI **coverage completeness gate** enumerates live routes and fails on any gap,
      and that gate is proven able to fail (no skip, no soft-fail, no `|| true`).
- [ ] Route mapping is method-aware.
- [ ] Shadow logs unmapped gated routes.
- [ ] Each subject class has a declared grant bundle, audited via `decide()`.
- [ ] No locally-invented guest subject spelling is persisted (section 5).
- [ ] Enforce only after coverage-green + grants-audited + a clean soak; human-hand, reversible.
- [ ] Non-Python subapps, and non-HTTP surfaces such as MCP tool handlers, call the
      capauth decide endpoint, never a ported PDP.

---

## Related standards

- [IDENTITY_NAMING_STANDARD](./IDENTITY_NAMING_STANDARD.md): how a subject is
  spelled. That standard governs the string; this one governs what it may do.
  It also defines the purity constraint on `decide()` (its section 2.4).
- [PROVENANCE_AND_MUTATION_STANDARD](./PROVENANCE_AND_MUTATION_STANDARD.md):
  what happens after the decision. This standard says who MAY act; that one
  records who DID act, and reuses the section 3 route-coverage pattern.
- [SKWORLD_MODULE_CONTRACT_STANDARD](./SKWORLD_MODULE_CONTRACT_STANDARD.md):
  the manifest that would carry the proposed `authz` facet (section 7).
- [TESTING_AND_CI_STANDARD](./TESTING_AND_CI_STANDARD.md): section 6 gate
  integrity, which the coverage gate in section 3 depends on.
- [ITIL_AND_RUNBOOK_OPERATING_MODEL_STANDARD](./ITIL_AND_RUNBOOK_OPERATING_MODEL_STANDARD.md):
  the change record every enforce flip needs, and the MCP-tool-as-PEP framing.

*Design background: the originating design note and the skchat reference
instantiation live outside this repo, in the operator's working docs
(`docs/superpowers/specs/2026-08-06-skworld-authorization-model.md`). It is not
part of `sk-standards` and is not required to apply this standard.*

---

*License: Apache-2.0. Part of [sk-standards](../README.md); the skstacks copies
carry a "canonical home" pointer back here.*
