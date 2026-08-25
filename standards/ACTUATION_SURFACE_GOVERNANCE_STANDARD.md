# Actuation Surface Governance Standard

**Status:** RATIFIED. This is constituent S4 of the
[`AUTONOMY_STANDARD`](./AUTONOMY_STANDARD.md). It applies the readiness and
freeze predicate from
[`ACTUATION_READINESS_AND_FREEZE_STANDARD`](./ACTUATION_READINESS_AND_FREEZE_STANDARD.md)
and the approval contract from
[`ACTION_AUTHORIZATION_STANDARD`](./ACTION_AUTHORIZATION_STANDARD.md) to every
surface that can cause a physical, fleet, deployment, or external effect.

**Why:** On 2026-08-25, two MCP surfaces disproved the estate's belief that its
kill switch covered everything that could act. `run_ansible_playbook` invoked a
raw subprocess against arbitrary playbooks and inventories with no freeze,
authorization, classification, or allowlist check. Trustee restart, scale, and
rotate performed their effects before writing an audit record. Both were
reachable from an agent session that held the MCP surface. A freeze that does
not cover every acting surface is a label, not a switch.

---

## 1. Registered or not shipped

Every surface that can change host, fleet, deployment, credential, repository,
or external state MUST have exactly one row in
[`reference/autonomy/actuation-surfaces.json`](../reference/autonomy/actuation-surfaces.json)
before it ships. The row names its owning repository, implementation evidence,
gate symbol, before-effect gate, freeze coverage, authorization object, status,
and reason.

The registry records one of these states:

- `GOVERNED`: its named gate runs before every effect;
- `FENCED`: the effect path is unreachable while a tracked gate is built;
- `UNGOVERNED_KNOWN`: the gap is honestly present and has a retrofit card;
- `REMOVED`: the implementation no longer ships, while its historical row and
  explicit retirement reason remain checked in.

Missing is not a status. Removing a registry row does not prove that its code
was removed. Every id ever registered remains in the validator's append-only
baseline. A retired baseline id carries an explicit reason, and its registry row
remains present with status `REMOVED`. Reusing a retired id for a new surface is
forbidden.

**Incident:** The ansible and trustee effects existed outside the surfaces
believed to be governed. The first registry could have appeared green by simply
deleting those embarrassing rows, so omission itself had to become a checked
failure.

**Check:** `scripts/check_actuation_registry.py` checks row shape, statuses,
retirement reasons, baseline retention, agreement with the umbrella table, and
S4 document wiring. Its self-test deletes a baseline row and proves the gate
fails.

---

## 2. Actuation-capable MCP tools

An MCP tool that can change host, fleet, deployment, or external state MUST run
both gates before acting, in this order:

1. verify actuation readiness and the freeze;
2. verify either an approved change under
   [`ACTION_AUTHORIZATION_STANDARD`](./ACTION_AUTHORIZATION_STANDARD.md), or a
   CapAuth PDP allow where that enforcement path is deployed.

A PDP that is unreachable, unavailable, or unable to identify the caller MUST
deny. An approved change does not waive readiness or freeze. A PDP allow does
not waive an approved change when the action class requires one. The gate MUST
cover every reachable path to the effect, not only the MCP wrapper.

Recording the action after it happens is an audit, not a gate, and does not
satisfy this rule. Audit evidence remains required where the owning standard
requires it, but it cannot repair a missing before-effect decision.

Every actuation-capable MCP tool MUST map to an actuation-surface registry row.
Tool names containing effect verbs such as start, stop, restart, scale, rotate,
execute, apply, or send are detection candidates and require review. A
read-only or check-mode variant is exempt from actuation authorization and
SHOULD exist so dry inspection does not require permission to mutate state.
The exemption applies only when the implementation structurally cannot cause
the effect.

**Incident:** Trustee `_audit` ran only after restart, scale, or rotate. The
ansible tool had no before-effect gate at all. Both patterns let successful
logging be mistaken for authorization.

**Check:** The registry validator can parse supplied MCP source with the Python
standard library AST. A detected effect tool with no matching registry row is a
failure. Its negative fixture adds an unregistered `deployment_apply_hotfix`
tool and proves the registry gate rejects it. Runtime repositories remain
responsible for exercising their actual gate order and refusal behavior.

---

## 3. Current disposition of the incident surfaces

### Removed ansible surface

skcapstone PR 199 removed `run_ansible_playbook`, its implementation module, and
both registration points. The registry preserves `mcp-run-ansible-playbook` as
`REMOVED`; its baseline entry is retired with the merge evidence and a reason.
Removal, not a weaker gate, is the settled disposition.

### Governed trustee lifecycle

skcapstone PR 200 inserted `trustee_actuation.guard` inside the shared trustee
operations path for restart, scale, and rotate. The guard checks readiness and
freeze first, then a verb-scoped CapAuth PDP allow. An unreachable PDP denies.
The implementation deliberately defines its own trustee capability rules at the
`VERIFIED` enrollment tier instead of calling `fleet.operator_http.authorize`
directly. That function hardcodes the operator-plane rule table, and CapAuth
denies unknown capabilities. Reusing it for trustee verbs would deny because
the table did not know the capability, not because the correct trustee policy
made a decision. Following its fail-closed pattern while supplying the right
rules preserves that distinction. Rotate additionally requires an ITIL change
that currently folds to approved. Read-only trustee health, logs, and
deployment listing remain outside the effect gate.

The shipped runtime tests named in section 5 verify those claims. The canonical
registry row remains the concise inventory statement; this section explains
why that row changed.

---

## 4. Machine-readable contract

```actuation-surface-governance-contract
{
  "schema": "skworld.actuation-surface-governance/v1",
  "shipping_rule": "registered_or_not_shipped",
  "statuses": ["GOVERNED", "FENCED", "UNGOVERNED_KNOWN", "REMOVED"],
  "retirement": {
    "row_preserved": true,
    "baseline_reason_required": true,
    "id_reuse_allowed": false
  },
  "mcp_actuation": {
    "effect_domains": ["host", "fleet", "deployment", "external_state"],
    "before_effect": ["actuation_readiness_and_freeze", "approved_change_or_capauth_allow"],
    "pdp_unreachable": "deny",
    "audit_after_effect_is_gate": false,
    "registry_row_required": true,
    "read_only_or_check_mode_exempt": true,
    "read_only_or_check_mode_should_exist": true
  }
}
```

---

## 5. Enforcement and runtime evidence

Repository-local enforcement:

```bash
python3 scripts/check_actuation_registry.py --repo .
python3 scripts/check_actuation_registry.py --self-test
```

Optional read-only MCP source detection:

```bash
python3 scripts/check_actuation_registry.py --repo . \
  --mcp-source /path/to/skcapstone/src/skcapstone/mcp_tools/trustee_tools.py
```

Current skcapstone main proves the two dispositions with focused tests and
source checks:

- absence of `ansible_tools.py` and `run_ansible_playbook` from MCP
  registration after PR 199;
- `test_guard_refuses_unprovisioned`;
- `test_guard_refuses_frozen_even_with_a_grant`;
- `test_guard_refuses_when_capauth_unreachable_never_allows`;
- `test_guard_rotate_requires_change_id_even_when_ready_and_authorized`;
- `test_guard_rotate_refuses_unapproved_change`.

The runtime tests use temporary stores and fakes. They cause no live restart,
scale, rotation, deployment, or external effect.

---

## 6. Compliance checklist

- [ ] Every effect-capable surface has exactly one registry row before shipping.
- [ ] Every retired surface retains its row, id, and explicit retirement reason.
- [ ] Every actuation-capable MCP path checks readiness and freeze before effect.
- [ ] Every actuation-capable MCP path checks an approved change or deployed PDP allow.
- [ ] PDP unavailability denies rather than allowing or skipping the decision.
- [ ] Post-effect audit is never presented as a before-effect gate.
- [ ] Every detected MCP effect tool maps to a registry row.
- [ ] Read-only or check mode is structurally effect-free and preferably available.

---

## Related standards

- [AUTONOMY_STANDARD](./AUTONOMY_STANDARD.md): owns the canonical actuation
  registry and cross-cutting registered-and-gated invariant.
- [ACTUATION_READINESS_AND_FREEZE_STANDARD](./ACTUATION_READINESS_AND_FREEZE_STANDARD.md):
  owns the shared first gate and human-held freeze.
- [ACTION_AUTHORIZATION_STANDARD](./ACTION_AUTHORIZATION_STANDARD.md): owns
  approved-change authorization and dispatch-time reclassification.
- [MCP_TOOL_OWNERSHIP_STANDARD](./MCP_TOOL_OWNERSHIP_STANDARD.md): owns MCP tool
  implementation and delegate boundaries, including the E13 actuation rule.
- [SKWORLD_AUTHORIZATION_STANDARD](./SKWORLD_AUTHORIZATION_STANDARD.md): owns
  the one PDP and thin PEP lifecycle for a deployed CapAuth decision path.

---

*License: Apache-2.0. Part of [sk-standards](../README.md).*
