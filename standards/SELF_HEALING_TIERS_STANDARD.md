# Self-Healing Tiers Standard

**Status:** RATIFIED. This is constituent S7 of the
[`AUTONOMY_STANDARD`](./AUTONOMY_STANDARD.md). It bounds the three self-healing
systems currently shipped by skcapstone and states how each relates to
[`ACTUATION_READINESS_AND_FREEZE_STANDARD`](./ACTUATION_READINESS_AND_FREEZE_STANDARD.md),
[`ACTION_AUTHORIZATION_STANDARD`](./ACTION_AUTHORIZATION_STANDARD.md), and the
protected floor in
[`AUTOCODE_MERGE_GATE_STANDARD`](./AUTOCODE_MERGE_GATE_STANDARD.md).

**Why:** On 2026-08-25, three autonomous repair mechanisms were live or shipped
without any standard naming their ceilings. The per-agent `SelfHealingDoctor`
was wired into the daemon on a five-minute cadence and could mutate a live
agent's home and process state. Fleet converge could restart systemd units on a
thirty-second cadence. `ErrorQueue` could replay failed calls. Without explicit
scope bounds, nobody could distinguish a conservative repair from a healer
rewriting the gate that constrained it.

---

## 1. Tier 1: per-agent SelfHealingDoctor

`SelfHealingDoctor` is a local maintenance tier. Its scope is exactly one
agent's own home directory, supplied at construction, and that daemon's own
consciousness-loop process state. The daemon wires it at startup and its healing
component waits 300 seconds between runs.

The executable repair classes on current skcapstone main are exactly:

1. create missing required subdirectories under that one home: `identity`,
   `memory`, `trust`, `security`, `sync`, `config`, `soul`, and `logs`;
2. rebuild that home's `memory/index.json` from JSON entries under its memory
   layers;
3. create that home's missing `sync/sync-manifest.json` with the shipped default;
4. re-probe the running consciousness bridge's configured LLM backends;
5. restart the same process's dead inotify observer.

Profile freshness is reporting only. A stale profile produces a warning and an
informational result; it is not rewritten.

The module docstring also names fallback switching, corrupt-config reset, and
dead-worker restart. Current executable check methods do not implement those
repairs. They are documentation drift, not shipped authority, and this standard
does not grant them. Adding any repair class requires a reviewed amendment to
this contract and a test proving its boundary.

### Readiness relationship

This tier does not require actuation readiness for the five listed local
repairs. It is deliberately below the action contract because its entire effect
is confined to one agent's own home or process and it cannot select a different
host, fleet object, deployment, external target, or remedy. If a future repair
crosses that boundary, it leaves this tier and MUST pass the applicable
readiness, freeze, authorization, and registry gates before effect.

**Incident:** The doctor was repairing a live agent every five minutes with no
ratified ceiling. Its prose described more repair classes than its code
implemented, making a docstring an unsafe candidate source of authority.

**Check:** Current skcapstone tests create only temporary agent homes and verify
home-directory creation, memory-index rebuild, sync-manifest creation, backend
re-probe behavior, and inotify restart. The S7 validator pins the exact shipped
repair list and rejects additions not ratified here.

---

## 2. Tier 2: fleet converge mechanical healing

`fleet/converge.py::_heal` is a node-local mechanical tier. It may start or
restart exactly one systemd unit named by one locally placed service spec on
that node. It does not diagnose a novel remedy, stop a running unit because of
manifest disagreement, change placement, rewrite a service spec, or act on
another node.

A heal is eligible only when all of these are true:

1. the canonical `store.check_actuation_gate` says the freeze store is
   provisioned and not frozen;
2. the node spec has the per-node `actuate` opt-in;
3. the service spec is readable, valid, not paused, and has
   `restartPolicy == "on-failure"`;
4. the unit is failed, inactive, or missing;
5. signature and profile enforcement gates, when enabled, allow it;
6. exponential backoff allows another attempt and the crash-loop ceiling has
   not stopped healing.

The pass cadence is 30 seconds. The unit boundary and backoff make this a
thermostat, not a decision-maker.

### Readiness relationship

Converge MUST pass actuation readiness and freeze before every start or restart.
It is deliberately below the ITIL action-authorization contract after that
precondition. Routing each bounded restart through change management would
flood the change log and train operators to ignore it. The exemption is only
for this exact mechanical start-or-restart behavior. A different remedy,
service-spec edit, placement change, cross-node action, or external effect is
not converge healing and requires the normal action contract.

**Incident:** Before the readiness predicate landed, a missing freeze store was
read as not frozen, so mechanical healing could have been active on an estate
whose kill switch had never been provisioned.

**Check:** Current skcapstone tests prove frozen and unprovisioned nodes execute
zero systemd verbs, absent opt-in is report-only, pause blocks healing, unreadable
specs are no-ops, retry waits obey exponential backoff, and crash-loop attempts
stop at the bounded ceiling.

---

## 3. Tier 3: ErrorQueue bounded replay

`ErrorQueue` is a replay tier, not a diagnosis tier. It persists the original
operation type, payload, and failure. On retry it passes the same `ErrorEntry`
to an injected handler. The handler MUST replay that original operation and
MUST NOT use queue presence to select a different target, parameter set, or
remedy. The queue itself does not choose any of those things, but current code
does not verify handler identity or semantics.

The default retry budget is exactly three failed retries. Delay is exponential:
`BASE_BACKOFF_SECONDS * 2**attempt`. Success resolves the same entry. Failure
increments its retry count. At the budget, the entry becomes `exhausted` and no
later retry is attempted.

### Authority and readiness relationship

The queue itself does not cause the original effect and does not mint
readiness, authorization, or a capability. It therefore has no independent
actuation-readiness check. A retry inherits the original call's authority
requirements, not a stale allow verdict. The injected handler MUST revalidate
all current gates required by the operation, including readiness, freeze,
approved-change, capability, expiry, and target scope where applicable, before
replaying an effect. A queued payload is evidence of a failed request, never an
authorization to execute it later.

Current `ErrorQueue.retry` calls the injected handler with the same entry but
does not itself validate readiness or authorization. This standard records that
implementation edge honestly. Conformance for an effectful retry belongs at the
handler boundary; a handler that trusts queue presence as authority violates
this standard.

**Incident:** A generic replay queue can look harmless because it chooses no new
remedy, while still replaying an effect after its original grant, freeze state,
or target scope has changed.

**Check:** Current skcapstone tests prove the same entry reaches the handler,
failed attempts increment, three failures exhaust, exhausted entries do not run,
and backoff timestamps increase. Consumer tests MUST prove each effectful
handler revalidates its own current gates.

---

## 4. The universal never-touch rule

No healer in any tier may modify, replace, delete, regenerate, chmod, relink, or
repair any of these targets:

1. its own gate, scope definition, retry budget, backoff, or enforcement code;
2. the freeze file or the code that reads, provisions, or enforces it;
3. the protected-manifest file;
4. any path in the S5 protected-manifest hard-coded floor, including every
   detector, merge choke point, fleet-store, plane-file, rubric, guard-module,
   and coverage-configuration class protected there.

This prohibition applies even when the target appears corrupt, absent, stale,
or responsible for the healer's failure. The healer reports and escalates the
condition. It never repairs the mechanism that limits its own authority.

The S5 floor is append-only. This standard follows the current floor by class;
it does not copy a path list that could drift. A path newly added to that floor
is immediately forbidden to all healers.

**Incident:** The current implementations happen not to target their own gates
or the protected floor, but no prior standard made that safety property survive
a future repair-class addition.

**Check:** `scripts/check_self_healing_tiers_standard.py` validates the contract
and can probe a proposed repair target. Its negative controls prove that a
healer targeting `own_gate` or `protected_manifest_floor` is rejected.

---

## 5. Machine-readable contract

```self-healing-tiers-contract
{
  "schema": "skworld.self-healing-tiers/v1",
  "global_forbidden": ["own_gate", "freeze_file", "protected_manifest", "protected_manifest_floor"],
  "exact_forbidden_paths": ["scripts/check_self_healing_tiers_standard.py", "src/skharness/autocode/protected.py"],
  "protected_floor_classes": ["detector", "merge_choke_point", "fleet_store", "plane_files", "rubric", "guard_modules", "coverage_configuration"],
  "healers": {
    "self_healing_doctor": {
      "tier": "local_agent_maintenance",
      "scope": "one_agent_own_home_and_process",
      "cadence_seconds": 300,
      "repairs": ["create_required_home_dirs", "rebuild_memory_index", "create_default_sync_manifest", "reprobe_llm_backends", "restart_inotify_observer"],
      "report_only": ["profile_freshness"],
      "readiness": "not_required_for_exact_bounded_local_repairs",
      "action_contract": "below_contract_while_scope_remains_local"
    },
    "fleet_converge": {
      "tier": "node_mechanical",
      "scope": "one_locally_placed_systemd_unit_per_node",
      "cadence_seconds": 30,
      "repairs": ["start_unit", "restart_failed_unit"],
      "requires": ["actuation_ready_and_not_frozen", "node_actuate_opt_in", "restart_policy_on_failure", "exponential_backoff"],
      "action_contract": "below_itil_contract_for_bounded_mechanical_restart"
    },
    "error_queue": {
      "tier": "bounded_same_call_replay",
      "scope": "same_error_entry_to_injected_handler",
      "handler_must_replay_original_call": true,
      "max_retries": 3,
      "backoff": "exponential",
      "diagnoses": false,
      "chooses_different_remedy": false,
      "mints_authority": false,
      "handler_revalidates_current_gates": true
    }
  }
}
```

Every healer inherits `global_forbidden`. No healer-specific field may weaken
or override it.

---

## 6. Enforcement

```bash
python3 scripts/check_self_healing_tiers_standard.py --repo .
python3 scripts/check_self_healing_tiers_standard.py --self-test
```

Explicit target probes fail closed:

```bash
python3 scripts/check_self_healing_tiers_standard.py --repo . \
  --probe-repair self_healing_doctor:scripts/check_self_healing_tiers_standard.py
python3 scripts/check_self_healing_tiers_standard.py --repo . \
  --probe-repair fleet_converge:src/skharness/autocode/protected.py
```

---

## 7. Compliance checklist

- [ ] SelfHealingDoctor repairs only the five executable classes listed here.
- [ ] Docstring-only repair claims are not treated as shipped authority.
- [ ] Converge passes readiness and freeze, opt-in, policy, and backoff gates.
- [ ] Converge touches only one locally placed unit with start or restart.
- [ ] ErrorQueue replays the same entry at most three times under exponential backoff.
- [ ] Every effectful retry handler revalidates current authority and readiness.
- [ ] No healer touches its own gate, the freeze, the manifest, or the S5 floor.
- [ ] A healer encountering a forbidden target reports and escalates without repair.

---

## Related standards

- [AUTONOMY_STANDARD](./AUTONOMY_STANDARD.md): owns the cross-cutting autonomy
  framework and constituent status.
- [ACTUATION_READINESS_AND_FREEZE_STANDARD](./ACTUATION_READINESS_AND_FREEZE_STANDARD.md):
  owns converge's readiness and freeze precondition.
- [ACTION_AUTHORIZATION_STANDARD](./ACTION_AUTHORIZATION_STANDARD.md): owns the
  action contract used when a repair crosses its bounded tier.
- [AUTOCODE_MERGE_GATE_STANDARD](./AUTOCODE_MERGE_GATE_STANDARD.md): owns the
  append-only protected floor no healer may touch.
- [ACTUATION_SURFACE_GOVERNANCE_STANDARD](./ACTUATION_SURFACE_GOVERNANCE_STANDARD.md):
  owns registration when a future repair becomes an actuation surface.

---

*License: Apache-2.0. Part of [sk-standards](../README.md).*
