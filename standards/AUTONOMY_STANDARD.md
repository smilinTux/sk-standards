# SKWorld Autonomy Standard

**Status:** FRAMEWORK, ACCRETING. Created as a placeholder under the accretion
model: each constituent standard lands as its own PR with its own check and
updates this document. **A row marked PENDING is an intention, not a rule.**
Companion to [`ITIL_AND_RUNBOOK_OPERATING_MODEL_STANDARD`](./ITIL_AND_RUNBOOK_OPERATING_MODEL_STANDARD.md),
[`SKWORLD_AUTHORIZATION_STANDARD`](./SKWORLD_AUTHORIZATION_STANDARD.md),
[`PROVENANCE_AND_MUTATION_STANDARD`](./PROVENANCE_AND_MUTATION_STANDARD.md),
and [`MCP_TOOL_OWNERSHIP_STANDARD`](./MCP_TOOL_OWNERSHIP_STANDARD.md).

**Why:** Every other standard in this repo governs a **noun**. Repos and their
docs, crypto suites, service units, backups, module manifests, identity strings,
provenance envelopes, MCP tool names, authorization decisions, ingress topology:
each owns a thing and says how that thing is built, named, signed, checked, or
retired. Nothing in the set governs a **verb**. Nothing says what must be true
before the estate *acts*.

That gap had two live consequences on 2026-08-25, both found by direct read:

1. **Approval caused nothing.** `skoperator decide --approve` wrote a record and
   stopped. `decisions.py` says of itself that it "performs no actuation, only
   file-backed record I/O; it is not a guardrail", and no code anywhere re-read a
   resolved decision. Every escalated proposal was a dead end at the park stage.
2. **The kill switch did not cover everything that can act.** The ansible MCP
   tool ran playbooks against arbitrary inventories as a raw subprocess with no
   freeze check, no authorization check, and no allowlist. The trustee lifecycle
   tools recorded their actions only *after* performing them. Neither had any
   relationship to the freeze, and the freeze itself reported "active" on a host
   where its file had never existed.

A freeze that does not cover every surface is a label, not a switch. This
standard is the estate's first verb stratum, and its job is to make coverage a
checked property instead of a prose belief.

---

## 1. The invariants

These hold across the whole autonomy layer. Each is detailed by the constituent
standard named beside it. Until that constituent lands, the invariant states the
intended rule and is marked PENDING in section 3.

1. **One approval store.** The ITIL change record's fold is the only mechanism
   that turns a proposal into an authorization. No other store's "approved" field
   authorizes anything. *[ACTION_AUTHORIZATION]*
2. **The actuator's only inputs** are the action ledger, the ITIL change fold,
   the freeze and readiness state, and the ratified action catalog. Proposals,
   briefs, model output, chat, and activity streams are never actuation inputs.
   *[ACTION_AUTHORIZATION]*
3. **Registered and gated, or not shipped.** Every surface that can cause
   physical, fleet, or external effect appears in the actuation-surface registry
   (section 2) with a named gate, and the freeze covers it or its row states in
   writing why not. *[ACTUATION_SURFACE_GOVERNANCE]*
4. **Provisioned before active.** Actuation requires an explicitly provisioned
   freeze store in the off position. An absent kill switch means no actuation,
   not free actuation. *[ACTUATION_READINESS_AND_FREEZE]*
5. **Observation never carries control weight.** Worker and agent activity
   streams are evidence; authority is pinned to observation at the schema level.
   *[AUTOCODE_MERGE_GATE]*
6. **Machine-written code merges only through the twin gate**, called by import
   from every merge path, never reimplemented. *[AUTOCODE_MERGE_GATE]*
7. **A human, and only a human, holds the freeze.** Already enforced in code
   (`fleet/store.py` refuses unless the writer is a human operator and not the
   agent seat: "the AI must not be able to unfreeze itself"). Restated here so
   the invariant survives refactors. *[ACTUATION_READINESS_AND_FREEZE]*

---

## 2. The actuation-surface registry

**Machine-readable copy:** [`reference/autonomy/actuation-surfaces.json`](../reference/autonomy/actuation-surfaces.json).
**Checked by:** `scripts/check_actuation_registry.py`.

The registry is the kill-switch coverage proof. It ships with the two ungoverned
surfaces **honestly listed**, because a standard that is green on day one by
omission is worse than no standard. An `UNGOVERNED_KNOWN` row with a tracked
retrofit card is honest and passes. A **missing** row is the lie this registry
exists to catch, and the check's `BASELINE_SURFACES` set exists so that deleting
an embarrassing row fails the build rather than fixing it.

| Surface | Gate today | Freeze coverage | Status |
|---|---|---|---|
| fleet converge heal | per-node actuate opt-in, restartPolicy, backoff; signature when `SKFLEET_SIGNING` is enforce | yes | GOVERNED (mechanical tier) |
| operator actuator honor | freeze check, honor allowlist, classification, execute flag | yes | GOVERNED (unreachable pending the dispatcher) |
| operator HTTP actions | capauth end to end, fails closed | yes | GOVERNED (feature-gated off) |
| run_ansible_playbook (MCP) | none | none | UNGOVERNED_KNOWN, retrofit tracked |
| trustee restart, scale, rotate (MCP) | audit after the fact only | none | UNGOVERNED_KNOWN, retrofit tracked |
| skharness merge (twin gate) | twin gate by import, protected manifest, automerge list empty | n/a, governed by its own operator flags | GOVERNED |

**The mechanical tier is deliberate.** Converge's thirty-second
restart-on-unhealthy pass, bounded by `restartPolicy` and a per-node opt-in,
sits below the action contract on purpose. A thermostat is not a decision-maker,
and routing it through change management would flood the change log and teach
people to ignore it. It still owes the freeze and the readiness predicate.

**Audit is not a gate.** A surface that records what it did after doing it has an
audit trail, not an authorization. Rows are graded on what runs *before* the
effect.

**Cross-repo scope.** This repo ships documents, not the code the registry cites.
The check verifies what is verifiable here: well-formedness, agreement between
this table and the JSON, baseline coverage, and retrofit tracking. Resolving a
named gate symbol in its own repo belongs to that repo's gate, per
[`TESTING_AND_CI_STANDARD`](./TESTING_AND_CI_STANDARD.md). A check that claims
more than it verifies is worse than one that states its own edge.

---

## 3. Constituent standards

| Standard | Owns | Status |
|---|---|---|
| [ACTUATION_READINESS_AND_FREEZE](./ACTUATION_READINESS_AND_FREEZE_STANDARD.md) | the readiness predicate, the provisioning ceremony, tri-state status, the freeze coverage rule | RATIFIED |
| ACTION_AUTHORIZATION | the ITIL fold as the authorization object, the ledger as evidence and queue, the dispatcher as sole consumer, re-classification at dispatch | PENDING |
| ACTUATION_SURFACE_GOVERNANCE | the registered-or-not-shipped rule and the MCP actuation-tool amendment | PENDING |
| [AUTOCODE_MERGE_GATE](./AUTOCODE_MERGE_GATE_STANDARD.md) | the twin gate as the sole merge bar for machine-authored change, the grader pin, the protected floor, RunRecord at the verdict boundary | RATIFIED |
| CODING_LANES | the two lane contracts, the three-predicate router, the context-posture split | PENDING |
| SELF_HEALING_TIERS | the three live healers with explicit scope bounds and what none of them may ever touch | PENDING |

**Accretion rule.** This document is never edited to say more than the landed
constituents justify. Each constituent's PR flips its own row and any registry
statuses it changes, and nothing else.

---

## Related standards

- [ITIL_AND_RUNBOOK_OPERATING_MODEL_STANDARD](./ITIL_AND_RUNBOOK_OPERATING_MODEL_STANDARD.md):
  owns change management. Invariant 1 is a sharpening of that document, not a
  replacement for it.
- [SKWORLD_AUTHORIZATION_STANDARD](./SKWORLD_AUTHORIZATION_STANDARD.md): one PDP,
  many thin PEPs. An actuation gate is a PEP; that standard decides who may call.
- [PROVENANCE_AND_MUTATION_STANDARD](./PROVENANCE_AND_MUTATION_STANDARD.md):
  an approval whose approver is a caller-typed literal is not an approval.
  Approver identity follows that standard's resolved-actor rule.
- [MCP_TOOL_OWNERSHIP_STANDARD](./MCP_TOOL_OWNERSHIP_STANDARD.md): an
  actuation-capable MCP tool is registered here and owned there.

---

*License: Apache-2.0. Part of [sk-standards](../README.md).*
