# SKWorld Autonomy Layer: Architecture

**Status:** ARCHITECTURE REVIEW, NOT NORMATIVE, NOT AN AUTHORIZATION
**Date:** 2026-08-25
**Scope:** autocoding (skharness, the pi fleet), self-healing (ATLAS, skoperator, converge, per-agent doctor), and the standards that govern both
**Evidence base:** `EVIDENCE_PACK_2.md` (two read-only recon lanes, 2026-08-25) plus direct reads performed today of `skcapstone` at `45a00b3` (main), `skcoord` at `ea33490` (main), `skharness` at `388aeed` (main), and `sk-standards` at `2e0bf5b` (main), all under `/home/skuser01/work/` on chiap08
**Companion:** `ARCHITECTURE.md` (the identity layer, same date). Its E1 to E6 edits are merged; this document's edit series continues at E7.

This document designs architecture only. Nothing in it authorizes enrollment, key operations, deployment, restart, scale, rotation, playbook execution, merge, actuation of any kind, or any external action. Every operation named below is a proposal for separately gated human decisions. Chef's four binding decisions (recorded at the end of `EVIDENCE_PACK_2.md`) are treated as constraints, not suggestions; where this reviewer disagrees, the design still builds what was asked and the disagreement is filed in section 8.

**Provenance discipline.** Claims cite file and line. Where the claim comes from a direct read performed today it says so or cites the local checkout path; where it relies on `EVIDENCE_PACK_2.md` it cites the pack's section. FACT and INFERENCE are labeled at the points where the distinction matters.

---

## 1. Verdict in one paragraph

This estate has built, with unusual discipline, every stage of a governed autonomy loop except the one that connects them. Detection is owned redundantly and well. Diagnosis, classification, actuation, verification, and record-keeping each exist as real, tested, mostly pure modules. What does not exist is the joint: no code path leads from "a human approved this" to "the fleet did this" (`decisions.py:1-7` says of itself that it is not a guardrail, and nothing downstream re-reads a resolved decision, `EVIDENCE_PACK_2.md` B.5, FACT). Meanwhile two actuation surfaces (`run_ansible_playbook` and the trustee tools) act with no gate at all, the freeze covers neither of them, and the freeze itself is un-provisioned rather than off by intent. The design below adds exactly one new load-bearing module (a dispatcher that consumes approved ITIL changes and nothing else), demotes one existing store (the operator decisions inbox becomes a projection over ITIL, because ITIL's CAB fold is already the only approval mechanism on the estate that authenticates its approver), retrofits the two stray surfaces with the same guard, flips the freeze from absent-means-active to present-and-off-means-active for actuation only, gives the manual coding fleet the real contract it is currently improvising inside a live session, and lands all of it as small standards accreting into an umbrella whose job is a checkable coverage registry, not a table of contents.

---

## 2. The assessment

### 2.1 Genuinely well built: leave alone, or merely wire up

These pieces are load bearing. They should not be refactored in the course of this work, and several of them are the reason the design in section 3 can be small.

| Piece | Where | Why it is load bearing |
|---|---|---|
| **Dual-lane observation with a hard conflict error** | `operator_seat/eyes.py:79-115, 174-281` (pack B.2) | Observes every app twice (out-of-process CLI and in-process adapter) and treats disagreement as `LaneConflictError`, never averaged, never silently preferred. This is the correct epistemics for a system that will one day act on what it sees. Leave it exactly as it is. |
| **The grader capability pin** | `skharness` `grader_pin.py:134` (pack A.3.8) | `GRADER_CAPABILITY_CLASS = "m"` regardless of what is graded: a card cannot choose the model that grades it. Closes self-grading leniency structurally, not procedurally. |
| **The four anti-gaming coverage checks** | `skharness` `ci.py:163-270` (pack A.3.6) | Deletes pre-existing reports, checks exit code, requires report mtime to postdate the run, refuses to certify 1.0 when the diff touches source the report never mentions. This is what a check that expects to be gamed looks like. |
| **The fail-closed protected manifest** | `skharness` `autocode/protected.py` (pack A.4) | Missing, unreadable, unsigned, or empty manifest protects everything, and a hard-coded floor always protects the merge choke point, the fleet store, the freeze file, the rubric, and the detector itself. The floor list is the right list. |
| **The twin gate, called by import from both paths** | `engineering.py:63-74`, imported by both the Ralph loop and `ratify.py` (pack A.3.9) | `score==5 AND promise AND ci green AND coverage floor`, and the two merge paths call the exact same function so they cannot drift. Section 4 makes this the shared merge bar for BOTH coding lanes; nothing about it changes. |
| **The action ledger** | `operator_seat/action_ledger.py`, read in full today | Append-only, hash-chained (`:333-377`), fsynced, signature-capable (`capauth-pgp-v1`, `:360-364`), with a derived terminal-state set (`:58-60`), a deduplicating identity that already includes `authorization_ref` (`:132-143`), and occurrence semantics that distinguish a recurring condition from a still-open one (`:231-277`). This is a finished authorization-evidence substrate. Section 3 gives it a consumer; it needs no redesign. |
| **The policy classifier** | `operator_seat/policy.py:26-67`, read in full today | Pure function, no I/O. Irreversibility forces MAJOR two independent ways (`:50-53`), freeze actions force EMERGENCY, the ratified standard catalog is a closed frozenset (`:12-19`), and auto-approval additionally requires a rollback plan and operator authorship. Correct and complete for its job. |
| **The freeze toggle's human-only rule** | `fleet/store.py:362-378`, read today | `set_frozen` raises unless the writer is a human operator and not the agent seat: "the AI must not be able to unfreeze itself." Keep verbatim. |
| **ITIL's CAB fold** | `skcoord/src/skcoord/itil.py`, surveyed today | Event-sourced, pure fold; CAB-major convention (`:85-102`); a dated provenance boundary before which unprovenanced approvals are honored as historical and after which votes must carry authenticated provenance (`:295-346`); no-self-approval enforced in the fold itself (`:422-424`, `:1290-1302`); `deploy_mode` defaults to `"confirm"` (`:1172`) and the AI can never satisfy the human-approval requirement (`:1266`). This is the only approval mechanism on the estate that authenticates its approver. Section 3 makes it THE authorization object for exactly that reason. |
| **The loop's actuation discipline** | `operator_seat/loop.py:233-245, 320-460`, read today | Freeze first ("Freeze wins, always, and first", `:233`), per-proposal isolation so one bad proposal cannot suppress the escalations a human was owed, `performed=True` proof required, postcondition re-observation required when a ledger is wired (`:168-190`), failure paths park a decision and record FAILED/ESCALATED with the ITIL correlation preserved even across an exception (`act_dispatch.py:141-150`). |
| **Interactive spawn guards and teardown** | skharness `harnesses/claude_code.py:867+` (pack A.7) | Four fail-closed guards (profile, repo allowlist empty-means-deny, ref format, name regex), transcript persisted before the window stops. Lane 1 in section 4 is built on this, not beside it. |
| **Worker text can never carry control weight** | skharness `activity.py:188-189` (pack A.7) | `authority` hard-pinned to `"observation"`. This single line is the reason a prompt-injected worker cannot escalate through the activity stream. It becomes a normative rule in E11 so nobody relaxes it casually. |

Two smaller things worth explicit praise because they are easy to lose in a refactor: the no-op guard that bails after two consecutive empty diffs (`engineering.py:637-661`, pack A.3.5), and `resolve_occurrence`'s per-episode memoization contract, whose docstring documents its own degenerate misuse (`action_ledger.py:253-263`).

### 2.2 Built and switched off: wire up, do not rebuild

- The autocode engine end to end, behind `live_execution=false` and `automerge_repos=[]` (pack A.2). Both flags are Chef's to flip and this document does not propose flipping either. What it proposes (section 4) is making the flags' eventual flip safe by unifying provenance first.
- `fleet/operator_http.py`, the one actuation surface that enforces capauth end to end and fails closed, gated off by default (pack B.8.e). It is the precedent E10 points the stray surfaces at.
- The signing plane (`SKFLEET_SIGNING`, default off; pack A.4, B.7.B): real when enforced, nominal today.
- `skoperator.{service,timer}` unit files exist in-repo, hard-coded report-only, never installed (pack B.3). Installing the report-only timer is an epic, not a design problem.
- `fault_injection_drill.py` exists in the operator seat and already consumes the decisions store; it becomes the verification harness for Epic 3.

### 2.3 Missing, at the level of a joint rather than a component

1. **The approved-decision consumer.** `skoperator decide --approve` terminates in a JSON file (`decisions.py`, `cli.py:260-273`). Nothing reads it back. Under Chef's decision 1 (detect, diagnose, propose is the ceiling), this handoff IS the autonomy architecture, and it does not exist. Section 3.
2. **Governance over `run_ansible_playbook` and the trustee tools.** Direct grep today: `mcp_tools/ansible_tools.py` contains no occurrence of freeze, capauth, or authorization of any kind; `trustee_ops.py` likewise, its only safeguard the after-the-fact `_audit` (`trustee_ops.py:58-66`). FACT. Both are exposed as MCP tools to any agent session (this session's own tool roster includes both, FACT). Section 3.5.
3. **Freeze provisioning semantics.** No `_freeze.json` exists; `is_frozen` returns False on a missing file and fails closed only on a corrupt one (`fleet/store.py:347-359`, read today). The estate is safe because a timer was never installed, which is safety by accident. Section 3.6.
4. **A real contract for the live coding fleet.** The pool controller for the pi fleet exists only as text typed into a live session (pack A.5, FACT), and the fleet's provenance vocabulary ("review-verdict PASS", "content-addressed manifest bundle") matches nothing in the engine (pack A.6, FACT). Section 4.
5. **An unauthenticated approver.** `decide_cmd` resolves every decision with the literal string `by="human"` (`operator_seat/cli.py:271`, read today). `PROVENANCE_AND_MUTATION_STANDARD` bans exactly this: never a magic string like "human" typed by a caller. The approval record that the whole autonomy ceiling hangs on is currently free text. This finding, more than any abstract argument, is why section 3 puts authorization in ITIL, whose votes are provenance-bound, rather than teaching the decisions store to authorize.
6. **One stale docstring worth a card, not a standard:** `loop.py:41` still says app observes "fail safe (reports healthy when the app is unreachable)" while the code beneath it and the just-merged E3 standard say Unknown, never healthy (`loop.py` exception path comment: "a probe failure is Unknown, never healthy/crash"). Code-comment drift; fix in Epic 3's repo touch.

---

## 3. The action contract

### 3.1 The shape of the joint

Chef's decision 1 fixes the autonomy ceiling at detect, diagnose, propose. Everything below the ceiling already exists. The joint to design is a durable object that carries a proposed action from detection through approval to actuation to verification, that both ATLAS and a human can write to, and that the actuator reads as its ONLY input.

The estate has three candidate objects, and the right answer is to assign each the role it already claims for itself:

**The ITIL change record is the AUTHORIZATION object.** It is the only store whose approval event authenticates the approver: the CAB fold binds approval to authenticated human roles behind a dated provenance boundary (`skcoord/itil.py:295-346`), enforces no-self-approval inside the fold (`:1290-1302`), and structurally prevents the AI from satisfying a human-approval requirement (`:1266`). The honor path already creates a change before actuating (`act_dispatch.py:104-119`). Nothing new needs to be invented here; the change record only needs to be READ at the moment of actuation instead of merely written on the way past.

**The action ledger lineage is the EVIDENCE, and it is also the actuator's queue.** Its own docstring is correct and stays correct: "operational evidence, not an authorization mechanism" (`action_ledger.py:1-6`). But evidence with a complete lifecycle state machine is exactly the right thing for an actuator to iterate over: an intent in PROPOSED state is the durable, hash-chained, deduplicating representation of "something wants to happen", and the PROPOSED to AUTHORIZED transition (`:46`) is the exact place a gate belongs. The ledger does not authorize; it RECORDS that authorization was verified, with the verification's inputs in the event detail. The distinction is who is allowed to append AUTHORIZED, and on what evidence.

**The decisions store is a PROJECTION, and stops pretending otherwise.** `decisions.py` parks options and records a human's resolution; it authenticates nothing and consumes nothing. Under this design it remains the human-facing inbox (park, list, notify) but its resolution becomes write-through: approving a decision submits a provenance-bound CAB vote on the linked ITIL change, and it is THAT vote, folded by ITIL, that authorizes. A decisions record with no linked change authorizes nothing, and the CLI says so instead of printing success. The magic string `by="human"` dies in the same change, because the CAB vote path already demands authenticated provenance.

### 3.2 The dispatcher: the one new module

One new module, `operator_seat/dispatch.py` (name illustrative), with one job: it is the only code on the estate that turns an approval into an actuation. Per pass (invoked from `loop._run_once` after the propose stage, and available standalone as `skoperator honor-pending`):

1. **Refuse unless actuation-ready** (section 3.6): freeze store provisioned, freeze off, execution explicitly enabled. Freeze wins first, exactly as `loop.py:233` already does.
2. **Enumerate ledger intents whose current state is PROPOSED** and whose intent core carries an `itil_change_id` (or whose `authorization_ref` resolves to one). Intents with neither are invisible to the dispatcher forever, by design.
3. **For each, independently re-read the ITIL change fold.** The change must fold to approved: a human CAB approval for anything `requires_human`, or standard/auto-normal auto-approval for the ratified catalog. The dispatcher trusts the fold, never the proposal's claim about itself, and never the decisions store.
4. **Re-classify at dispatch time.** Run `policy.classify_change` again on the intent's action metadata against the CURRENT ratified catalog. If the classification has hardened since proposal (an action left the standard catalog, a blast radius was reclassified), the dispatcher refuses and escalates rather than honoring a stale approval. The intent's `catalog_generation` binding (`action_ledger.py:101`) already exists for exactly this comparison.
5. **Append AUTHORIZED** with the change id, the fold's approval provenance, and the re-classification result in the event detail; then EXECUTING; then route through `act_dispatch.route_action` to the honor adapters, requiring the `performed=True` proof; then the existing `_verify_postcondition` re-observation; then VERIFIED, or FAILED with the existing rollback and escalation paths.

Two properties fall out for free. First, the auto lane and the human lane converge: today's auto path (loop lines 385-400, which appends AUTHORIZED on its own say-so for auto-dispositioned proposals) is re-pointed through the same dispatcher step, where "standard change, auto-approved by the fold" is simply the fastest kind of approved change. One code path, two speeds. Second, Chef's "the gate may be relaxed per-action later once the record proves itself" becomes a data change, not a code change: relaxing an action is moving it into the ratified standard catalog (a reviewed, versioned, eventually signed artifact), and the record that justifies the move is the ledger's own lineage history for that action.

**What the actuator is allowed to read, exhaustively:** the ledger intent core and its event stream, the ITIL change fold, the freeze and readiness state, the ratified action catalog and adapter registry, and the live observation needed for postcondition verification. **What it must never read as input:** proposals, briefs, brain output, chat, activity streams (authority: observation, always), or the decisions store. Anything the brain wants to happen must become a ledger intent bound to an ITIL change, or it does not happen.

### 3.3 Who writes what

| Actor | May write |
|---|---|
| ATLAS (brain, proposer) | ledger OBSERVED, DIAGNOSED, PROPOSED; ITIL change proposal (draft, `deploy_mode="confirm"`); decision park |
| Human | CAB vote (provenance-bound); decision resolution (which write-through becomes a CAB vote); freeze toggle (exclusively, `store.py:362-378`) |
| Dispatcher (only) | ledger AUTHORIZED, EXECUTING, VERIFIED, FAILED, ROLLED_BACK, ESCALATED |
| Actuation adapters | nothing durable except through the dispatcher's events and ITIL updates; physical effects only |

The ledger's optional signing (`require_signatures`, `capauth-pgp-v1`) is the eventual enforcement that the dispatcher's events really came from the dispatcher's key; it ships off, flips on when the signing plane does. The design does not depend on it, but it is the reason the ledger was the right queue: the substrate for signed authorization evidence already exists.

### 3.4 The vocabulary is already right

Nothing in this section invents a state, a class, or a verb. The lifecycle states are `action_ledger.py:29-40` verbatim. The change classes are `policy.py` verbatim. The approval semantics are ITIL's fold verbatim. The design is a consumer, three refusals, and a demotion. That is the correct size for a joint: if this section had needed a new schema, that would have been evidence the existing pieces were wrong, and they are not.

### 3.5 Every actuation surface, routed or fenced

The estate's five actuation surfaces (pack B.8), disposed one by one:

**(a) `fleet/converge.py` `_heal`** stays a mechanical tier BELOW the contract, deliberately. A thirty-second restart-on-unhealthy pass under backoff, bounded by `restartPolicy == "on-failure"` and per-node `actuate` opt-in, is a thermostat, not a decision-maker, and forcing it through ITIL would either flood the change log or teach people to ignore it. Two amendments only: it honors the readiness rule of 3.6 (a node with no provisioned freeze store does not heal), and its healing events are mirrored into the ledger as single-event VERIFIED-class records for the coverage story (evidence, not gate). Its signing check stays as is and hardens when `SKFLEET_SIGNING` flips.

**(b) `actuator.honor` plus `act_dispatch`** becomes reachable only through the dispatcher. It already refuses when frozen (`actuator.py:35-36`); it gains the readiness check. The known bypass (it runs in the operator-loop process and never passes converge's signature check, pack B.8.b) is closed by the same signing-plane flip that hardens (a); until then the dispatcher's own gate is the control.

**(c) `run_ansible_playbook`** is fenced first, governed second. Immediately (Epic 4): check runs (`--check`) remain available; any live run refuses unless (1) actuation-ready and not frozen, (2) the playbook path resolves inside a versioned, allowlisted playbook root (empty allowlist means deny-all, the estate's established idiom), and (3) the caller supplies an ITIL change id whose fold is approved and whose scope names the playbook. That is the full section 3.2 contract applied at a coarser grain, without waiting for ATLAS to learn ansible as an adapter. If nobody can name a current consumer of live runs, the sharper fence is to ship it check-only and let demand argue for the gate; that choice is Chef's (section 8).

**(d) Trustee restart/scale/rotate** get the same guard helper: refuse when not actuation-ready or frozen; require a capauth PDP allow when `SKOPERATOR_HTTP`-style enforcement is available, per the `operator_http.py` precedent (fail closed if capauth is unreachable); and `trustee_rotate`, being a credential operation, additionally requires an approved ITIL change (rotation is never routine). The `_audit` stays, correctly demoted in everyone's mind from safeguard to record.

**(e) `fleet/operator_http.py`** is already the reference implementation of the gate and needs nothing except eventually being turned on.

The rule that generalizes this, and that the umbrella standard states as an invariant with a registry behind it (section 5, E7): **an actuation surface is either registered and gated, or it does not ship.** Audit-after-the-fact is a record, not a gate, and the freeze must cover every registered surface or the registry entry says in writing why not.

### 3.6 The freeze asymmetry: an opinion

Current semantics (`fleet/store.py:347-359`, FACT): corrupt file fails closed, missing file returns not-frozen. The instinct to call that backwards should be resisted in one direction and honored in the other.

Resisted: missing-must-mean-frozen would make the freeze a switch that anyone able to delete a file can flip, and a kill switch that defaults to on is not a switch, it is an outage. `is_frozen`'s read semantics should not change.

Honored: the real defect is that the current code cannot distinguish "the freeze store is provisioned and the switch is off" from "nobody ever set this estate up", and `skoperator status` renders both as "active (freeze off)" (`cli.py:277-281`, FACT, confirmed live in pack B.3). The fix is a separate predicate, not a change to the switch: **`actuation_ready(paths)` is true only when `_freeze.json` exists, parses, and was written by the human-only `set_frozen` path.** Every actuation surface in 3.5 requires `actuation_ready() and not is_frozen()`. Provisioning an estate for actuation therefore includes a human explicitly writing the freeze file in its off position, which is the moment the kill switch is proven to exist before anything it governs can run. `skoperator status` grows a third word: frozen, active, or UNPROVISIONED. The migration cost is one deliberate provisioning step per actuate-mode node, which is exactly the ceremony a kill switch deserves. Safety stops being an accident and becomes a precondition.

---

## 4. The two coding lanes

Chef's decision 2 wants both lanes, and they are not the same system. The design principle: **share the artifacts, never the driver.**

### 4.1 Lane 1: the manual pane cluster

What exists today: a "three-lane-pool-controller" pi session polling the coord board and sibling processes, whose controller logic is inline text typed into its own live session, registered on the board but existing nowhere on disk (pack A.5, FACT). This is simultaneously proof the lane is wanted, proof it works, and the strongest possible argument for a contract: the estate's most active coding orchestrator currently cannot be reviewed, cannot be restarted, and vanishes with its tmux server.

The contract: a versioned pool controller in skharness's session plane (beside, not inside, the task-plane engine), driving tmux directly: one session, one window, N pi panes, with spawn / scale / drain / destroy verbs. Its rules:

- **Spawns go through the guarded spawn path** (`harnesses/claude_code.py:867+` guards: profile, repo allowlist, ref format, name regex), never bare `tmux new-session` with env vars improvised per wave. The allowlist stays deny-all-by-default; enabling a repo for lane 1 is a config change a human makes.
- **One worktree per task**, the convention the fleet already follows (pack A.5).
- **Teardown persists transcripts first**, the discipline the session plane already has; a drained pane is never a bare kill.
- **Every pane emits activity events** with `authority` pinned to observation (`activity.py:188-189`). The controller reads the board and the activity stream; workers' text never instructs the controller.
- **The human is the loop.** No Ralph rounds, no autoscale ceiling logic, no Docker confinement requirement: the operator watching the panes is the confinement, which is precisely why this lane exists. `pi --approve` under a human's eyes is a power tool, not an autonomy risk, PROVIDED its output cannot merge on its own say-so, which is the next rule.
- **Merges still pass the twin gate.** Lane 1 output lands as a PR, and ratification goes through the one-shot `ratify()` path that calls the same `twin_gate_passed()` by import (pack A.3.9). The lane shares the bar, not the loop.

One flag needs a decision recorded rather than inherited: the fleet's bootstrap loads the full soul ritual and sets an autonomous-by-default env (`load-sk-agent-context.sh`, pack A.5), while ADR-0001 prescribes a lean sandbox with no operator context for engine workers. These are compatible only because they are different lanes: lane 1 panes are interactive agents a human drives and may legitimately carry context; lane 2 workers are sandboxed and must not. The lanes standard (E12) states that split explicitly so the fleet's current practice stops looking like a violation of ADR-0001 and becomes a documented property of lane 1.

### 4.2 Lane 2: the managed flow

A job handed to skharness: claim, worktree, Ralph loop with fresh sessions per round, independent grader under the capability pin, twin gate, PR, and, only for repos on the (currently empty) automerge list, merge. Nothing in this lane needs design; it needs three integrations:

- **ATLAS as a client, not an owner.** When ATLAS diagnoses something whose remedy is code (a failing unit whose fix is a config PR, a recurring condition whose fix is a patch), the proposal's action is `dispatch_coding_job`, classified by `policy.classify_change` like any action, authorized through section 3's contract, and the dispatcher's actuation is a call that files the card and lets skharness run it. The autonomy ceiling holds: the engine builds and opens a PR; `automerge_repos=[]` means a human merges. ATLAS never edits code itself and never merges.
- **`live_execution` and `automerge_repos` stay Chef's flags.** This document deliberately designs nothing that requires either to flip.
- **The run record becomes real.** `run_record.py` defines a content-addressed `RunRecord` with a canonical hash and a versioned schema, and by its own docstring no production writer imports it (pack A.6, FACT). Epic 7 wires the writer at the twin-gate boundary: every job that reaches a verdict, in either lane, writes one.

### 4.3 What is shared, and what is deliberately not

**Shared, byte-identical, by import where possible:**
1. **The card.** A coord card with executable acceptance criteria is the unit of work in both lanes; the fleet's TDD documents already follow this shape (pack A.5).
2. **The twin gate.** One function, two callers, already true; E11 makes it normative so it survives refactors.
3. **The provenance vocabulary.** The fleet's invented terms map onto engine mechanisms and the invented terms retire: "review-verdict PASS" IS the twin-gate verdict; "content-addressed manifest bundle" IS the `RunRecord` content hash. One vocabulary, defined where the code is, used by both lanes' briefs. The arena subsystem's content-addressing stays "proposed" status and is not on this path (pack A.9).

**Deliberately not shared:** the driver (human versus orchestrator), the confinement (eyes versus Docker with restricted egress), the loop (none versus Ralph), the context posture (full ritual versus lean sandbox), and the governance object (a lane 1 session is a human's tool and its actions are the human's; a lane 2 job dispatched by ATLAS is an actuation and rides the section 3 contract).

### 4.4 The routing rule, made decidable

A job goes to **lane 2** if and only if all three hold:

1. It is expressed as a card whose acceptance criteria are executable (tests, CI verdict, coverage floor), so the twin gate can judge it without a human's taste.
2. No human will type into the session mid-flight. The moment steering is intended, it is lane 1.
3. The target repo is enrolled for the engine (worktree-able, CI wired for `external_ci_verdict`, coverage instrumented for the four checks).

Fail any one and it is lane 1 (or it is not ready to be a job at all, which is a card-quality problem, not a routing problem). The rule is three predicates a dispatcher or a human can evaluate identically; taste never enters. Corollary, stated so nobody re-litigates it per job: exploratory work, spike work, and "look at this with me" are lane 1 by rule 2 forever, no matter how good the engine gets.

### 4.5 The word "codex", disambiguated once

Three unrelated things answer to "codex" on this estate (pack A.5): a stub adapter in the engine that raises on use, two long-running interactive CLI processes on chiap04 launched with sandbox bypass flags and a home-directory cwd, and a model identity routed through skgateway (`sk-codex`). The lanes standard names the model identity as the only sanctioned meaning in fleet tooling. The chiap04 sessions are a human's interactive terminals, out of scope for lane rules, but their bypass flags and non-worktree cwd are worth Chef's eyes (section 8); the stub adapter either gets a real backend someday or keeps raising, and either is fine.

---

## 5. The standards architecture, with the meta lens

### 5.1 The shape of the eighteen

Read as a set (all eighteen listed from the canonical checkout today), the estate's standards have a distinctive and mostly excellent shape:

- **They govern nouns.** Repos and their docs, crypto suites, service units, backups, module manifests, identity strings, provenance envelopes, MCP tool names, authorization decisions, ingress topology. Each standard owns a THING and states how that thing is built, named, signed, checked, or retired.
- **The strong ones are incident-driven and gate-backed**, exactly as CONTRIBUTING demands: SERVICE_UNIT carries the 47,187-restart incident and a validator script; DOCS_FRESHNESS carries the gitleaks-scanned-zero-bytes incident and the docs-check gate; AUTHORIZATION carries two live enforce-flip incidents and a route-coverage CI gate. The older aspirational ones (ARCHITECTURE_AND_DATAFLOW, SK_REPO_DOC) predate that bar and are checklist-shaped, which is acceptable drift, not rot.
- **The README table is already a de facto umbrella**: a CI-enforced one-row-per-standard index with real summaries. Any new umbrella that is merely a better table would duplicate it.

What is missing at the level of the SET, and visible only from this altitude: **there is no standard that governs a verb.** Nothing in the set says what must be true before the estate ACTS: who may authorize an action, what an actuation surface owes the kill switch, what a machine-written change owes the merge bar. ITIL_AND_RUNBOOK comes closest but governs the record-keeping of change, not the actuation surfaces themselves; it draws the operator loop and its own drift register admits where the diagram and the code part ways. The autonomy layer is not the nineteenth noun; it is the estate's first verb stratum, and that is why it deserves the umbrella treatment Chef asked for rather than one more standalone document.

A second set-level observation: the set has no dependency discipline. Standards cross-reference informally, and the identity work (E1) has already shown two ratified documents ruling oppositely on one field for eleven days. The umbrella below carries a small invariants section precisely because cross-cutting rules currently have nowhere to live except inside one document that the others may contradict.

### 5.2 The umbrella verdict: right, on one condition

Chef's decision 3 (small standards, each independently landable with a real check and a failing negative test, accreting into one framework standard created FIRST as a placeholder) is the right mechanism, on one condition: **the umbrella must own something checkable that no small standard can own, or it converges to a second README table and should not exist.**

It can own exactly two such things:

1. **The actuation-surface registry.** A machine-readable enumeration (in `reference/`, beside the standard) of every surface on the estate that can cause physical or fleet effect: converge heal, actuator honor, ansible tool, trustee tools, operator HTTP, engine merge, and any future entrant. Each row: surface, gate, freeze coverage, authorization object, status (governed / fenced / ungoverned-known). Its check, `scripts/check_actuation_registry.py`, fails when a registered surface's named gate symbol does not exist in the code, and fails when a repo declares an actuation capability (module-contract `proposedStandardActions`, MCP tools matching a declared actuation pattern) absent from the registry. Its negative test: a fixture registry missing a fixture surface fails. This is the kill-switch coverage proof, and it is the direct answer to finding 2: a freeze that does not cover everything that can act is a label, and the registry is how coverage stops being a prose claim.
2. **The cross-cutting invariants**, each one sentence, each pointing at the small standard that details it: one approval store; the actuator reads only the ledger and the fold; every surface registered and gated or not shipped; freeze provisioned before actuation; observation authority never carries control; machine-written code merges only through the twin gate.

The placeholder is created first (E7) containing the invariants (marked which are aspirational until their small standard lands), the empty registry with today's five surfaces honestly marked (two of them ungoverned-known, which makes the umbrella true on day one rather than green by omission), and a status table of the small standards. Each small standard's PR updates its umbrella row and flips registry statuses. The umbrella is never edited to say more than the landed smalls justify: CONTRIBUTING's "green on day one" applies, and an honest UNGOVERNED row is green; a missing row is the lie.

### 5.3 The small standards, in landing order

| # | Standard | Owns | Depends on |
|---|---|---|---|
| S1 | `AUTONOMY_STANDARD` (umbrella placeholder) | invariants, registry, accretion status | nothing |
| S2 | `ACTUATION_READINESS_AND_FREEZE` | `actuation_ready`, provisioning ceremony, tri-state status, freeze coverage rule | S1 (a registry row per rule) |
| S3 | `ACTION_AUTHORIZATION` | the section 3 contract: ITIL fold as the authorization object, ledger as evidence and queue, dispatcher as sole consumer, decisions store demoted, re-classification at dispatch | S1; code lands with Epic 3 |
| S4 | `ACTUATION_SURFACE_GOVERNANCE` | the registered-or-not-shipped rule, the MCP actuation-tool amendment (E13), the ansible and trustee retrofits as its worked examples | S1, S2 (uses the readiness predicate) |
| S5 | `AUTOCODE_MERGE_GATE` | twin gate as the sole merge bar for machine-authored change, by import; grader pin; protected-manifest floor; RunRecord at the verdict boundary; observation-only authority | S1 |
| S6 | `CODING_LANES` | lane contracts, the three-predicate router, the context-posture split, the vocabulary unification; paired with ADR-0002 recording the two-lane decision | S1, S5 |
| S7 | `SELF_HEALING_TIERS` | the three live healers (per-agent doctor, converge, error queue) with explicit scope bounds: what each may touch, what none may ever touch (its own gate, the freeze, protected-floor files), and their relationship to readiness | S1, S2 |

S2 through S5 are independent of each other and can land in any order or in parallel; S6 needs S5's gate language; S7 needs S2's readiness predicate. Every one carries its incident from the evidence pack and a check with a negative test (section 7). ITIL_AND_RUNBOOK gets one amendment (E8) rather than a new sibling, because the one-approval-store rule is a sharpening of a document that already owns change management, and its drift register is the honest place to record that the operator-loop diagram now includes the dispatcher.

---

## 6. Epics and sprints

Each epic states a machine-verifiable outcome. These become coord cards; acceptance criteria are the outcomes verbatim.

### Epic 1: SKGateway containment carryover (Chef decision 4, approved)

Install `openpgp` so signature verification can succeed on the current build; make `subjectFromIdentity` check `identity.verified` before yielding a subject. Not a tailnet rebind. Model access stays up throughout (deploy is a restart of an already-running service; the health condition `UpstreamServing` is the canary).
**Outcome:** a test proving a request presenting an unverified identity yields no subject where before it yielded one (the failing negative test that today's code fails); a fixture-signed request verifies end to end; `skgateway` operator conditions stay green across the deploy window.
**Blocks:** nothing. **Blocked by:** nothing. This is deliberately first because it is approved, small, and independent.

### Epic 2: Freeze provisioning and readiness

`actuation_ready()` in `fleet/store.py`; provisioning ceremony (human-written `_freeze.json` in off position via the existing human-only `set_frozen`); tri-state `skoperator status`; readiness checks added to `actuator.honor`, `converge._heal`, and the guard helper Epic 4 consumes; install `skoperator.timer` in its shipped report-only form on the pilot node.
**Outcome:** negative tests: absent freeze file refuses actuation with reason `unprovisioned`; corrupt file refuses with reason `frozen`; status renders three distinct states; timer active and its unit drift-clean per `schedule-doctor`.
**Blocks:** Epics 3, 4, 6's spawn-side checks. **Blocked by:** nothing.

### Epic 3: The dispatcher (the action contract)

`operator_seat/dispatch.py` per section 3.2; `decide` write-through to a provenance-bound CAB vote (retiring `by="human"`); auto path re-pointed through the dispatcher; `skoperator honor-pending`; the loop.py:41 docstring fix rides along.
**Outcome:** `fault_injection_drill` extended to the full arc with a capture runner (no real systemd): a MAJOR proposal parks, a simulated human CAB-approves, the dispatcher appends AUTHORIZED with the change id and provenance in detail, the captured actuation fires, postcondition verifies, lineage reads OBSERVED through VERIFIED. Negative tests: an unapproved change never actuates; a decisions-store-only approval (no linked change) never actuates and the CLI names the reason; a stale `catalog_generation` refuses and escalates.
**Blocks:** any future per-action gate relaxation (which is now a catalog change). **Blocked by:** Epic 2 (readiness predicate).

### Epic 4: Fence the strays

`run_ansible_playbook`: check-mode free; live runs require readiness, non-frozen, allowlisted playbook root (empty means deny-all), approved change id. Trustee tools: readiness plus freeze; PDP allow where enforcement is available, fail closed if capauth unreachable, per the `operator_http.py` precedent; `trustee_rotate` additionally requires an approved change. Registry rows flip from ungoverned-known to governed.
**Outcome:** negative tests per surface: live ansible run with no change id refuses; playbook outside the root refuses; trustee restart under freeze refuses; rotate without an approved change refuses; `check_actuation_registry.py` green with both rows governed.
**Blocks:** nothing. **Blocked by:** Epic 2 (shared guard helper). Runs parallel to Epic 3.

### Epic 5: Standards accretion

S1 placeholder first, then S2 through S7 as individual PRs per section 5.3, each with its check and failing negative test, each updating the umbrella. Includes `scripts/check_actuation_registry.py` and its wiring into the repo's CI gates.
**Outcome:** every landed standard passes `docs_check.py` and `ci_gate_check.py`; every check demonstrates a red state on its negative fixture; umbrella status table matches landed reality; README table rows (CI-enforced) present.
**Blocks:** nothing operationally (per the identity review's precedent: incidents and code never wait on standards). **Blocked by:** nothing; S3's text is best written against Epic 3's landed code but may land before it marked with its code obligation open.

### Epic 6: Lane 1 pool controller

The versioned session-plane pool controller per section 4.1: spawn/scale/drain/destroy over guarded spawn, transcript-first teardown, activity emission, board polling. The inline-typed controller retires: its session is drained and its board registration is superseded by the versioned controller's.
**Outcome:** controller exists in skharness with tests; a drill run spawns two pi panes against a fixture repo on the allowlist, drains one, destroys the pool, and every transcript persists; spawning against a repo not on the allowlist refuses (the existing guard, now exercised by the controller's test); a board query shows the versioned controller registered and the inline one gone.
**Blocks:** Epic 7's lane 1 half. **Blocked by:** Epic 2 only for the freeze-awareness nicety; can start in parallel at risk.

### Epic 7: Provenance unification

The `RunRecord` writer wired at the twin-gate verdict boundary for both lanes; lane 1 merges routed through `ratify()`; fleet brief templates rewritten to the engine vocabulary (twin-gate verdict, RunRecord content hash), retiring "review-verdict PASS" and "content-addressed manifest bundle".
**Outcome:** every job reaching a verdict in a drill (one lane 2 dry run, one lane 1 ratify) writes a schema-valid RunRecord whose content hash verifies; a grep of the maintained brief templates finds zero occurrences of the two retired phrases; `ratify()` and the Ralph loop still resolve to the same `twin_gate_passed` function object (an identity assertion in tests, making pack A.3.9's import-level guarantee permanent).
**Blocks:** any future consideration of `automerge_repos` entries (Chef's flip becomes evidence-backed). **Blocked by:** Epic 6 for the lane 1 half; the writer itself has no dependency.

### Sprints

- **Sprint 1 (all parallel):** Epic 1, Epic 2, Epic 5's S1 placeholder plus S2. Three different repos, no shared files.
- **Sprint 2:** Epic 3 and Epic 4 in parallel (both consume Epic 2's helper; they touch different files); Epic 5's S3 and S4 land alongside their code.
- **Sprint 3:** Epic 6 and Epic 7's writer half in parallel; then Epic 7's lane 1 half; Epic 5's S5 through S7 close out the umbrella.

Genuinely sequential edges, and only these: Epic 2 before 3 and 4 (shared readiness helper); Epic 6 before Epic 7's lane 1 ratify routing; S1 before every other small standard (they update it). Everything else is parallelism a fleet can exploit, and each epic's outcome is checkable by a machine that never saw this document.

---

## 7. Normative edits

Format per the landed E-series: file, location, actual text, incident, check with what its negative test proves. All land via the observed governance path: branch, local checks (`scripts/docs_check.py`, `scripts/check_fences.py`, `scripts/ci_gate_check.py`), PR, Chef merges. Numbering continues from the identity series (E1 to E6, merged).

### E7. New file: `standards/AUTONOMY_STANDARD.md` (the umbrella, created first as a placeholder)

Initial full content (the placeholder that accretes):

> # SKWorld Autonomy Standard
>
> **Status:** FRAMEWORK, ACCRETING. Created as a placeholder per the accretion model: each constituent standard lands as its own PR with its own check and updates this document. A row marked PENDING is an intention, not a rule.
>
> ## 1. The invariants
>
> These hold across the whole autonomy layer. Each is detailed by the constituent standard named beside it.
>
> 1. **One approval store.** The ITIL change record's fold is the only mechanism that turns a proposal into an authorization. No other store's "approved" field authorizes anything. [ACTION_AUTHORIZATION, PENDING]
> 2. **The actuator's only inputs** are the action ledger, the ITIL change fold, the freeze and readiness state, and the ratified action catalog. Proposals, briefs, model output, chat, and activity streams are never actuation inputs. [ACTION_AUTHORIZATION, PENDING]
> 3. **Registered and gated, or not shipped.** Every surface that can cause physical, fleet, or external effect appears in the actuation-surface registry (section 2) with a named gate, and the freeze covers it or its row states in writing why not. [ACTUATION_SURFACE_GOVERNANCE, PENDING]
> 4. **Provisioned before active.** Actuation requires an explicitly provisioned freeze store in the off position. An absent kill switch means no actuation, not free actuation. [ACTUATION_READINESS_AND_FREEZE, PENDING]
> 5. **Observation never carries control weight.** Worker and agent activity streams are evidence; authority is pinned to observation at the schema level. [AUTOCODE_MERGE_GATE, PENDING]
> 6. **Machine-written code merges only through the twin gate**, called by import from every merge path. [AUTOCODE_MERGE_GATE, PENDING]
> 7. **A human, and only a human, holds the freeze.** Already enforced in code; restated here so the invariant survives refactors. [ACTUATION_READINESS_AND_FREEZE, PENDING]
>
> ## 2. The actuation-surface registry
>
> Machine-readable copy: `reference/autonomy/actuation-surfaces.json`. Checked by `scripts/check_actuation_registry.py`: the build fails when a row's named gate symbol is absent from the cited code, or when a declared actuation capability exists with no row.
>
> | Surface | Gate today | Freeze coverage | Status |
> |---|---|---|---|
> | fleet converge heal | actuate opt-in, restartPolicy, backoff; signing when enforced | yes | GOVERNED (mechanical tier) |
> | operator actuator honor | freeze check, honor allowlist, classification, execute flag | yes | GOVERNED (unreachable pending dispatcher) |
> | operator HTTP actions | capauth end to end, fail closed | yes | GOVERNED (feature-gated off) |
> | run_ansible_playbook (MCP) | none | none | UNGOVERNED, KNOWN. Retrofit tracked. |
> | trustee restart/scale/rotate (MCP) | audit after the fact only | none | UNGOVERNED, KNOWN. Retrofit tracked. |
> | skharness merge (twin gate) | twin gate, protected manifest, automerge list empty | n/a (governed by its own flags) | GOVERNED |
>
> ## 3. Constituent standards
>
> | Standard | Status |
> |---|---|
> | ACTUATION_READINESS_AND_FREEZE | PENDING |
> | ACTION_AUTHORIZATION | PENDING |
> | ACTUATION_SURFACE_GOVERNANCE | PENDING |
> | AUTOCODE_MERGE_GATE | PENDING |
> | CODING_LANES | PENDING |
> | SELF_HEALING_TIERS | PENDING |

**Incident:** two live actuation surfaces with no gate and no freeze relationship (`mcp_tools/ansible_tools.py`, no authorization reference of any kind; `trustee_ops.py`, audit-after only: direct grep 2026-08-25, FACT), while the estate's kill switch reported "active (freeze off)" on a host where the freeze file has never existed (pack B.3, FACT). Coverage was a prose belief; two counterexamples were live.
**Check:** `scripts/check_actuation_registry.py` as described, wired into the repo CI gates. **Negative test proves:** a fixture registry omitting a fixture surface that declares an actuation capability fails the build; today's registry passes only because the two ungoverned rows are honestly present, so DELETING an ungoverned row (the tempting way to go green) also fails.

### E8. `standards/ITIL_AND_RUNBOOK_OPERATING_MODEL_STANDARD.md`, operator-seat section, new rule after the observe-classify-propose-act loop description

Insert:

> **The one approval store.** For any operator-seat action above the mechanical tier, authorization is the ITIL change record's fold and nothing else. A parked decision record is a projection for the human's inbox: resolving it MUST write through to a provenance-bound CAB vote on the linked change, and a decision with no linked change resolves to nothing. No actuator may read the decisions store as an input. An approval whose approver is a caller-typed literal (for example the string `human`) is not an approval; approver identity follows PROVENANCE_AND_MUTATION_STANDARD's resolved-actor rule. The transition from an approved fold to a physical act is performed by exactly one dispatcher, which re-reads the fold and re-classifies the action against the current ratified catalog at dispatch time; a classification that has hardened since proposal refuses and escalates rather than honoring a stale approval.

And add a drift-register row noting the operator-loop diagram gains the dispatcher between the CAB fold and actuation.

**Incident:** `skoperator decide --approve` wrote a record and stopped; no code re-read an approved decision, so every escalated proposal was a dead end at the park stage (`decisions.py:1-7`, grep of consumers, pack B.5, FACT), and the resolution it did write carried the hardcoded approver string `human` (`operator_seat/cli.py:271`, direct read, FACT), the exact magic string the provenance standard bans.
**Check:** operator-seat test suite: the dispatcher refuses an intent whose linked change is unapproved even when a decisions record beside it says approved. **Negative test proves:** the pre-fix behavior (a decisions-store approval treated as sufficient) now fails; and a `resolve()` invocation carrying a bare literal approver with no provenance is rejected.

### E9. New file: `standards/ACTION_AUTHORIZATION_STANDARD.md` (constituent S3)

Not a full draft here; the four load-bearing rules in rule-incident-check form:

> **R1.** A proposed action becomes durable as an action-ledger intent (schema `skcapstone.atlas.action-intent/v1`) at proposal time. The ledger is evidence and queue, never authorization: the AUTHORIZED event may be appended only by the dispatcher, only after re-reading an approved ITIL fold, and the event detail MUST carry the change id, the fold's approval provenance, and the dispatch-time classification.
> *Incident:* approval caused no action; the lifecycle's PROPOSED to AUTHORIZED edge existed in the schema (`action_ledger.py:46`) with no code entitled to traverse it on a human's behalf. *Check:* ledger tests: AUTHORIZED appended by any actor other than the dispatcher identity, or without a change id in detail, is rejected when signatures are required. *Negative test proves:* a hand-forged AUTHORIZED event without fold evidence fails validation.
>
> **R2.** The dispatcher's input set is closed: ledger, fold, freeze and readiness, ratified catalog, and postcondition observation. Model output and activity streams are structurally excluded.
> *Incident:* the live fleet's controller logic existed only inside a model session (pack A.5); had actuation been wired, the entity deciding was un-reviewable text. *Check:* an import-boundary test: the dispatcher module imports neither the brain nor any adapter's propose path. *Negative test proves:* adding such an import fails the boundary test.
>
> **R3.** Re-classification at dispatch: `policy.classify_change` runs again at dispatch time against the current catalog; `catalog_generation` mismatch or a hardened class refuses and escalates.
> *Incident:* the ledger's identity already binds `catalog_generation` (`action_ledger.py:101,138`) precisely because an approval against catalog N must not actuate under catalog N+1; nothing enforced it. *Check:* a fixture where an action leaves the standard catalog between approval and dispatch. *Negative test proves:* the stale approval actuating (today's would-be behavior) now fails.
>
> **R4.** Relaxing the human gate for an action class is a catalog change (a reviewed, versioned edit to the ratified standard catalog), never a code branch, and the change's justification cites the ledger lineage record for that action class.
> *Incident:* Chef's decision 1 anticipates per-action relaxation "once the record proves itself"; without this rule the relaxation path would be an if-statement. *Check:* the catalog is a versioned artifact whose edits require the citation field. *Negative test proves:* a catalog edit without a lineage citation fails the catalog validator.

### E10. New file: `standards/ACTUATION_READINESS_AND_FREEZE_STANDARD.md` (constituent S2)

Core rules:

> **R1.** `is_frozen` read semantics are unchanged: corrupt fails closed, absent reads not-frozen. The kill switch defaults off and cannot be flipped by deleting a file.
> **R2.** Actuation additionally requires `actuation_ready`: the freeze store exists, parses, and was provisioned through the human-only toggle path. Absent means UNPROVISIONED, and an unprovisioned estate refuses all actuation with that reason. Provisioning is a deliberate human ceremony: the kill switch is proven to exist before anything it governs runs.
> **R3.** Status surfaces are tri-state: frozen, active, unprovisioned. Rendering unprovisioned as active is a violation.
> **R4.** Every registered actuation surface checks readiness and freeze before acting. Audit after the fact is a record, not a gate.

**Incident:** `skoperator status` reported "active (freeze off)" on a host with no freeze file, and nothing actuated only because a timer was never installed (pack B.3, FACT): safe by accident.
**Check:** store tests plus a doctor check. **Negative tests prove:** (a) absent file refuses actuation with reason unprovisioned (fails against today's `honor`, which would pass the freeze check); (b) corrupt file refuses with reason frozen; (c) a status rendering that collapses unprovisioned into active fails the CLI test.

### E11. New file: `standards/AUTOCODE_MERGE_GATE_STANDARD.md` (constituent S5)

Core rules:

> **R1.** Machine-authored change merges only through `twin_gate_passed`, and every merge path binds to it by import, never by reimplementation. An identity assertion in tests keeps the Ralph loop and `ratify()` resolving to the same function object.
> **R2.** The grader capability class is pinned; a card cannot choose the model that grades it.
> **R3.** The protected manifest fails closed, and the hard-coded floor (detector, merge choke point, fleet store, plane files, rubric, guard modules, coverage config) may only grow.
> **R4.** Diff coverage certification carries the four anti-gaming checks; removing any one is a standards violation, not a refactor.
> **R5.** Activity-stream authority is pinned to observation at the schema level; no consumer may treat worker text as control input.
> **R6.** Every job reaching a verdict writes a content-addressed RunRecord at the twin-gate boundary, both lanes.

**Incident:** the live fleet coined its own provenance vocabulary matching nothing in the engine, and the engine's RunRecord had no production writer (pack A.6, FACT): two coding populations, one merge bar, zero shared evidence format.
**Check:** the import-identity test (R1), a floor-monotonicity test (R3), a coverage-checks presence test (R4), and a RunRecord round-trip on a dry-run verdict (R6). **Negative tests prove:** a second gate implementation fails R1's identity assertion; deleting a floor entry fails R3; a verdict with no RunRecord fails R6's drill.

### E12. New file: `standards/CODING_LANES_STANDARD.md` (constituent S6), paired with `decisions/ADR-0002-two-coding-lanes.md`

The ADR records Chef's decision 2 verbatim as the decision, with the pack A.5 observation as context. The standard's core rules:

> **R1.** Lane 1 (manual pane cluster): a versioned pool controller drives guarded spawns (profile, repo allowlist deny-all by default, ref format, name regex) as tmux panes; teardown persists transcripts first; panes emit observation-authority activity; the human is the loop. Orchestration logic typed into a live session is not a controller; a controller exists in a repo or it does not exist.
> **R2.** Lane 2 (managed): the skharness task plane, ATLAS-dispatched jobs riding the action-authorization contract; `live_execution` and `automerge_repos` are operator flags outside this standard's gift.
> **R3.** Routing is the three-predicate test (executable acceptance, no mid-flight human typing, enrolled repo): all three means lane 2, else lane 1. Exploratory and steered work is lane 1 by predicate 2, permanently.
> **R4.** Shared by import or by schema: the coord card, the twin gate, the RunRecord vocabulary. Deliberately unshared: driver, confinement, loop, context posture. Lane 1 panes MAY carry operator context; lane 2 workers run the lean sandbox per ADR-0001. This split is the resolution of the bootstrap-versus-ADR-0001 tension, not a violation of it.
> **R5.** "codex" in fleet tooling refers only to the gateway model identity; interactive sessions and stub adapters are not fleet components.

**Incident:** the estate's most active coding orchestrator existed only as text in a live session, registered on the board with no artifact on disk (pack A.5, FACT), and its briefs used a provenance vocabulary with zero literal matches in the engine or SOP (pack A.6, FACT).
**Check:** the Epic 6 drill (spawn, drain, destroy, transcripts persist, disallowed repo refused) plus the Epic 7 vocabulary grep over maintained brief templates. **Negative tests prove:** a spawn against an un-allowlisted repo refuses (guard exercised, not assumed); a brief template reintroducing a retired phrase fails the grep gate.

### E13. `standards/MCP_TOOL_OWNERSHIP_STANDARD.md`, new rule after the domain-assignment rule

Insert:

> **Actuation-capable tools.** An MCP tool that can change host, fleet, deployment, or external state (start, stop, restart, scale, rotate, execute, apply, send) MUST, before acting: verify actuation readiness and the freeze, and verify authorization per ACTION_AUTHORIZATION (an approved change reference, or a capauth PDP allow where enforcement is deployed, failing closed when the PDP is unreachable). Recording the action afterward is an audit, not a gate, and does not satisfy this rule. Every such tool appears in the AUTONOMY_STANDARD actuation-surface registry. A read-only or check-mode variant of the same tool is exempt and SHOULD exist so that dry inspection never requires an authorization.

**Incident:** `run_ansible_playbook` ran playbooks against arbitrary inventories as a raw subprocess with no check of any kind, and the trustee restart/scale/rotate tools' only safeguard wrote the audit after the action (`ansible_tools.py`, `trustee_ops.py:58-66`, direct grep today and pack B.8.c-d, FACT), both reachable from any agent session holding the MCP surface.
**Check:** the registry completeness gate (E7) plus per-tool negative tests. **Negative tests prove:** a live ansible invocation with no change reference refuses (fails against today's code, the sensitivity proof); a trustee restart under freeze refuses; a new MCP tool matching the actuation verb pattern with no registry row fails the registry gate.

### E14. `README.md`, standards table: one CI-enforced row per new standard

One row each for AUTONOMY_STANDARD and its six constituents as they land, in the established summary style. (Text per-row at PR time; listed here so the accretion PRs budget for it, since the docs gate will demand it.)

---

## 8. Open decisions (Chef's, not an architect's)

1. **Fence or govern `run_ansible_playbook`.** Section 3.5(c) designs the gate; the sharper option is shipping it check-only until a live-run consumer is named. If no one can name one, removal is honest. Your call on which.
2. **Converge's tier.** This design keeps mechanical restart-on-unhealthy below the action contract (thermostat, not decision-maker), with readiness and freeze as its only new gates. If you want EVERY physical act behind ITIL, say so and Epic 3 grows a converge adapter; the cost is change-log noise and a slower reflex.
3. **The provisioning flip's blast radius.** Requiring a provisioned freeze file will halt converge healing on any node already in actuate mode until its file is written. The migration is one ceremony per node; you own the order and timing.
4. **The chiap04 codex sessions.** Two long-running interactive sessions with sandbox bypass flags and a home-directory cwd (pack A.5, FACT). They are yours and out of scope for lane rules; whether they continue in that shape is a judgment only you can make.
5. **When the report-only `skoperator.timer` goes on, and on which node first.** Epic 2 makes it installable; turning on even observation is an operational presence you should place deliberately.
6. **The decisions store's end state.** This design demotes it to a projection with write-through. The further step, retiring it entirely once notify surfaces read ITIL directly, is a UX call about how you like your inbox.
7. **`live_execution` and `automerge_repos`** remain untouched by everything above, by design. The first repo ever to enter the automerge list is the single most consequential autonomy decision on this estate, and nothing in this document pre-empts it. Epic 7's RunRecord trail is built so that when you consider it, you decide from evidence.
8. **A registered objection, per instructions.** None of your four decisions is wrong in this reviewer's judgment. The nearest thing to a disagreement: the umbrella standard is only worth having if it owns the registry check (section 5.2); if the accretion ends with the registry cut for scope, the umbrella should be cut with it and the README table left to do its job.

Everything else in this document is either an assessment you can overrule or an edit that goes through the normal PR gate where you are the merger. Nothing here executes anything.
