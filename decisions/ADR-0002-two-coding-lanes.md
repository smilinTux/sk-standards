# ADR-0002: Two coding lanes with one merge bar

**Status:** Accepted
**Date:** 2026-08-25
**Deciders:** Chef, Lumina
**Extends:** [`ADR-0001`](./ADR-0001-skos-skharness-skcode-layering.md)
**Purpose:** record the accepted two-lane coding decision as shipped, including
the driver and context split, the deterministic router, and the shared gate and
evidence artifacts.

## Context

The estate had two real coding modes with no decision record separating them.
The manual pi pane cluster was the most active orchestrator, but its controller
logic existed only as text inside a live tmux session. The managed skharness
task plane already supplied isolated worktrees, Ralph rounds, an independent
grader, the twin gate, and pull requests. Treating those modes as one system
would either impose autonomous machinery on human-steered work or leak operator
context and interactive assumptions into managed sandboxes.

The context posture also appeared contradictory. The interactive fleet loaded
the full operator ritual, while ADR-0001 required a lean build sandbox. The
contradiction disappears when the two drivers are named: a human-driven session
may carry operator context; an orchestrator-driven task may not.

The manual fleet also used private provenance synonyms rather than the engine's
canonical twin-gate verdict and RunRecord content hash concepts. The evidence
bar needed to be shared even though the drivers must remain different.

## Decision

We retain both coding lanes.

### Lane 1: manual pane cluster

A human drives a versioned session-plane pool controller over guarded Pi tmux
panes. The inherited spawn path enforces profile, deny-all-by-default repository
allowlist, git ref, and session-name guards. Teardown persists transcripts
before stopping windows. Activity authority is observation-only. The human is
the loop, so there are no Ralph rounds or managed autoscale semantics in this
lane.

### Lane 2: managed task plane

The skharness task plane drives the job through isolated worktree, Ralph rounds,
pinned independent grader, twin gate, RunRecord, and pull request. An
ATLAS-dispatched coding job requires the action-authorization contract.
`live_execution` and `automerge_repos` remain operator flags and this decision
does not change them.

### Routing decision

A job uses lane 2 if and only if all three conditions hold:

1. acceptance criteria are executable;
2. no human will steer the session mid-flight;
3. the target repository is enrolled for the managed engine.

Otherwise, it uses lane 1. Exploratory or steered work is lane 1. Taste is not a
routing input.

### Shared and separate properties

Both lanes share the coordination card, the imported twin gate, and the
canonical RunRecord vocabulary. They do not share the driver, confinement,
loop, or context posture. Lane 1 may carry operator context. Lane 2 receives the
lean task brief defined by ADR-0001.

In fleet tooling, `codex` means only the skgateway model identity. Human
interactive terminals and stub adapters are not fleet workers.

## Consequences

### Positive

- Human-steered and managed work no longer inherit each other's authority or
  context assumptions.
- Three booleans determine the route identically for humans and software.
- Both lanes retain one merge bar and one verdict evidence vocabulary.
- The manual controller and Pi harness are versioned, testable, and recoverable.
- ADR-0001's lean sandbox remains intact without forbidding operator context in
  interactive sessions.

### Constraints

- Lane 1 must never become an unversioned live-session controller again.
- Lane 2 must not ingest the operator's full context graph.
- Neither lane may reimplement the twin gate.
- This ADR does not authorize `live_execution`, automerge enrollment, session
  retirement, or any production actuation.

## Verification

- [`CODING_LANES_STANDARD`](../standards/CODING_LANES_STANDARD.md) contains the
  normative five rules and machine-readable contract.
- `scripts/check_coding_lanes_standard.py` validates the routing truth table,
  lane properties, index rows, ADR status, and maintained brief vocabulary.
- Current skharness main test
  `test_guard_2_repo_not_on_allowlist_rejects` exercises the real PiHarness
  allowlist guard and proves refusal occurs before git or tmux.

## Related

- [`ADR-0001`](./ADR-0001-skos-skharness-skcode-layering.md)
- [`CODING_LANES_STANDARD`](../standards/CODING_LANES_STANDARD.md)
- [`AUTOCODE_MERGE_GATE_STANDARD`](../standards/AUTOCODE_MERGE_GATE_STANDARD.md)
- [`AUTONOMY_STANDARD`](../standards/AUTONOMY_STANDARD.md)
