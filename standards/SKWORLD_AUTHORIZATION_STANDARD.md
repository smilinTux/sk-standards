# SKWorld Authorization Standard

**Status:** Ecosystem standard for every `sk*` subapp that exposes an
authenticated network surface (skchat, skdashboard, skboard/skcoord, skcode,
skos, skgateway, and future subapps). Companion to
[`SKWORLD_MODULE_CONTRACT_STANDARD`](./SKWORLD_MODULE_CONTRACT_STANDARD.md),
[`CRYPTOGRAPHY_STANDARD`](./CRYPTOGRAPHY_STANDARD.md), and the ITIL operating
model. Full design + the skchat reference instantiation:
`docs/superpowers/specs/2026-08-06-skworld-authorization-model.md`.

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

---

## 1. One PDP, many thin PEPs

There is exactly one decision point: `capauth.authz.decide`. Every subapp is a
thin **Policy Enforcement Point** that DECIDES NOTHING; it runs the universal
request lifecycle and delegates the allow/deny to the PDP:

1. **Classify the route** (gated / public / self-auth) BEFORE anything else.
2. **Authenticate** (a valid capauth / audience credential), else 401.
3. **Resolve the subject** from the verified credential only, never from request
   input (`operator:<device_fp>`, `<agent>@<operator>.<realm>`, `guest:<invite_id>`).
4. **Map (method, route) to a capability.** In enforce, an unmapped gated route
   is a 403 by construction; the coverage gate (section 3) makes that branch
   provably unreachable for legitimate routes.
5. **Decide** via `decide(subject, capability, resource, context)`. Fail closed
   on any error, unknown capability, or insufficient enrollment mode.
6. **Emit the audit obligation** the PDP returns.

A non-Python subapp (e.g. skgateway, Node) MUST NOT re-implement the PDP; it
calls a capauth authorization endpoint (`POST /v1/authz/decide`) so there is one
decision point and no drift.

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

## 4. Token-minting and self-auth routes

Routes that authenticate differently (audience-token / embed-token mints via a
per-request check, auth/pair bootstrap, guest links, inbound federation) are NOT
capability-gated. They MUST be listed in the subapp's self-auth registry with
their verifier and a one-line rationale, so the coverage gate accepts them
explicitly rather than by omission. A self-auth route still fails closed on a
missing/invalid credential where one is required (e.g. a mint endpoint never
mints for an anonymous caller).

## 5. Subjects and declared grant bundles

Each subject class (operator device, agent FQID, guest) has a DECLARED grant
bundle, minted at enrollment (the `operator_grants.py` pattern: non-expiring,
best-effort, written to the same store the PDP reads). Grants are audited by
literally calling `decide()` for each (subject, capability) pair, not assumed.
Enrollment mode gates the bundle: a capability whose `minimum_mode` exceeds the
subject's enrollment mode is not usable even if the token is present.

## 6. Rollout rails (per subapp, shadow is necessary but NOT sufficient)

1. Turn the dataplane auth gate ON (authentication only).
2. PDP **shadow** (compute the decision, log divergence + unmapped gated routes,
   return the legacy outcome).
3. **Coverage gate GREEN** (every gated route classified). This is the gate, not
   step 4.
4. Mint + **audit every subject's grant bundle** via `decide()`.
5. Soak: a clean window with zero divergence AND zero unmapped-route logs.
6. **Enforce** (Chef-hand), `.158` first, 24h doctor-green, then `.41`, ITIL
   change per node. Watch the `enforce-deny` log; revert = flip the flag back to
   shadow (instant, no data change).

An RCE / write-authority surface (skcode dispatch/inject) stays **deny-all by
default** until a pre-enable security review, that is the correct posture for the
highest tier, not a bug.

## 7. Module-contract integration (optional `authz` facet, contract v1.3)

A subapp MAY declare its authorization surface in `skworld.module.json` via an
`authz` facet: its capability namespace, the (method, route) -> capability map,
the public allowlist, and the self-auth registry. A drift-guard test binds the
declaration to the PEP's live tables (mirroring the operator-facet conditions
guard). This lets the shell and the operator seat verify coverage without
reading code. See the module contract standard for the facet schema (v1.3).

## Compliance checklist (per authenticated subapp)

- [ ] PEP runs the section-1 lifecycle; decides nothing itself; fails closed.
- [ ] Capabilities are `<subapp>.<action>`, tiered read/write/act -> TOFU/attested/verified.
- [ ] Every gated route is capability-mapped, explicit-public, or explicit-self-auth.
- [ ] A CI **coverage completeness gate** enumerates live routes and fails on any gap.
- [ ] Route mapping is method-aware.
- [ ] Shadow logs unmapped gated routes.
- [ ] Each subject class has a declared grant bundle, audited via `decide()`.
- [ ] Enforce only after coverage-green + grants-audited + a clean soak; Chef-hand, reversible.
- [ ] Non-Python subapps call the capauth decide endpoint, never a ported PDP.
