# ADR-0006: The dispatcher handoff: Niobe takes dispatch, Tank takes release, Seraph verifies, Jarvis stands down

**Status:** Proposed
**Date:** 2026-09-02
**Extends:** [`ADR-0005`](./ADR-0005-five-operating-seats.md)
**Constituent of:** [`AUTONOMY_STANDARD`](../standards/AUTONOMY_STANDARD.md)
**Purpose:** specify the complete transition by which the Fleet Dispatcher
authority leaves Jarvis, who holds it today, and lands on dedicated seats, so
that the estate stops depending on one agent whose human, Casey, also needs it
for personal-agent work.

## Context

[`ADR-0005`](./ADR-0005-five-operating-seats.md) separated five operating seats
and narrowed Jarvis to Fleet Dispatcher. The narrowing worked on paper, but the
seat is still filled by the same agent that existed before it, and that agent is
the only holder of two unrelated bodies of knowledge: how the fleet dispatches,
and how Casey's personal-agent work is done. The measured failure mode of this
estate has never been a bad decision; it has been a silence nobody owned. A
seat held by an agent with two jobs is a seat that goes quiet the day the other
job gets loud.

Three seat names are now specified but unfilled: **Niobe**, **Tank**, and
**Seraph**. This ADR gives each one exactly one job, moves exactly the existing
dispatcher authority, and records the evidence-gated path under which Jarvis
may finally put the dispatch pager down. It also assigns Link the technical
arbitration role that every multi-seat estate eventually needs and that today
resolves by whoever speaks last.

## Decision

### 1. Niobe takes exactly the dispatcher authority that exists today

The Fleet Dispatcher seat, defined in ADR-0005 section 1 as *"fleet claims,
launches, releases, reassignment, rotation, lane routing, and worker health"*,
transfers from Jarvis to **Niobe**. The transfer moves the seat, not a raise in
rank. Niobe inherits the existing authority and the existing boundary, word for
word: no review verdicts, no merge queue, no application action dispatch, no
actuation. Niobe is bound by the same typed-recommendation fencing ADR-0005
places on the dispatcher: re-read current CardStore ownership and claim revision
and current process state before every mutation, fence the mutation to the exact
current claim revision, reject duplicates and stale observations, and record the
readback, outcome, and evidence hash as an append-only event.

Nothing in this ADR creates a new actuation surface. Dispatch mutations are
CardStore and process mutations, not application actuation, so Niobe needs no
row in the actuation-surface registry, exactly as Jarvis needs none today.

### 2. Tank is the release and install operator, and the behavioral deployment verifier

**Tank** owns the mechanics of release and install: taking an artifact that has
already merged, moving it onto a target, and proving from observed behavior that
the result works. Tank never merges, never dispatches, and never writes feature
source. Tank installs only artifacts that Link has already merged, so a Tank
release can never smuggle an unreviewed change past the trunk.

Because a deployment that returns exit code zero is not a deployment that works,
Tank's second duty is behavioral verification: after every release or install,
collect and append postcondition health evidence, hashed, naming the exact
artifact and target. Behavioral verification by the operator who performed the
install is recorded as operator evidence, never as independent verification.
Independent verification of a release follows the estate's distinctness rule:
a reviewer distinct from Tank by identity, host, session, and workspace.

Tank's release surface excludes the sensitive classes (CapAuth, credential,
custody, issuer, secret, key, rollback of another seat's change, and anything
the Atlas Constitution Article 2 calls irreversible). Those stay human-gated
under [`ACTION_AUTHORIZATION_STANDARD`](../standards/ACTION_AUTHORIZATION_STANDARD.md)
regardless of any future catalog relaxation.

### 3. Seraph is verification-only

**Seraph** verifies. Seraph reads evidence on cards, PRs, and releases, and
produces verdicts: PASS, PASS_FOR_REVIEW, or BLOCKED with a machine-readable
`blocked_on` reason. Seraph has no merge authority, no dispatch authority, and
no actuation surface of any kind. The verifier holds nothing that a verdict
could grant itself. This is ADR-0005's Overseer principle applied to review:
observation never carries control weight (AUTONOMY invariant 5), so a verifier
that could actuate or merge would be a second approver, not a verifier.

Seraph's verdicts are evidence, and Link remains the only seat that turns a
verdict into a merge. A Seraph BLOCKED stops a candidate exactly as an
independent review BLOCKED does today. Seraph cannot unblock its own BLOCKED by
re-running; the blocking condition has to actually clear.

### 4. Link holds evidence-bound technical arbitration, with ambiguity escalation to Chef

When two seats or two cards conflict on a technical question, **Link** decides.
The decision is bound to evidence on the card: what landed, what the checks and
verdicts said, what the cited artifacts hash to. Link's arbitration authority is
technical and scope-bound. Link does not decide what the fleet should build,
does not approve human gates, and does not settle questions of authority or
policy.

The decision-recording authority stays mechanical, per the Recorder rule in
ADR-0005: a human decision lands as a **signed Chef artifact** or an **ITIL
change ingestion**, never as a forwarded message. The signed artifact is the
human authorization input to the record; the ITIL fold remains the only
mechanism that turns a proposal into an authorization (AUTONOMY invariant 1),
so this creates no second approval store. **Seraph verifies effect**: Seraph
confirms that a recorded decision actually changed what it claimed to change,
by reading the estate, not by trusting the record's own summary.

When Link faces a genuine ambiguity, meaning the evidence does not decide the
question, Link escalates to Chef rather than resolving it by seniority, volume,
or precedent. An escalated question is answered by a signed Chef artifact or an
ITIL record, which then becomes the evidence the next arbitration cites.

### 5. The transition sequence, gated by evidence, with Jarvis's withdrawal condition

The transfer happens in this order. Each step appends its evidence to the
coordination record before the next begins. **No step in this sequence
provisions, enables, or depends on ATLAS. ATLAS remains frozen and last:** its
unfreeze is a separate human decision under
[`ACTUATION_READINESS_AND_FREEZE_STANDARD`](../standards/ACTUATION_READINESS_AND_FREEZE_STANDARD.md),
and this transition must succeed entirely without it.

1. **Stand up the seats.** Niobe, Tank, and Seraph receive their own capauth
   identities, signed by the operator, distinct from Jarvis and from every other
   seat, following the ceremony already written for standing up a seat. Naming
   a seat does not fill it; the transfer starts only when the identity exists
   and is verified distinct.
2. **Shadow parity.** Niobe runs in shadow alongside Jarvis for at least 14
   consecutive days. Jarvis keeps dispatching. Niobe, per cycle, computes the
   dispatch decision it would have made and appends it as a typed
   recommendation event; it executes nothing. Every shadow cycle records the
   same health fields the roster already requires: start, finish, host, seat
   identity, source revision, scanned population, decision count, duplicate
   suppressions, errors, and evidence SHA256.
3. **Parity gate.** The transfer advances only when the shadow window shows:
   zero unsafe actions proposed (no launch against a failed health gate, no
   release of a locked or unmerged candidate, no fenced-revision mismatch);
   disagreement with Jarvis on at most 5 percent of decisions, with every
   disagreement classified as either conservative (Niobe would have waited
   where Jarvis acted) or missed-pickup (Niobe would have acted where Jarvis
   waited), and zero missed-pickup disagreements unresolved; and the roster
   dispatch metric (churn, claims per card) not regressed beyond the Jarvis
   baseline. Seraph audits the parity evidence and states whether the gate is
   met. Seraph's statement is evidence; it is not permission.
4. **Authority transfer.** Link records the merge-queue state and confirms no
   in-flight card depends on Jarvis's dispatch identity. Chef records the
   transfer decision as a signed artifact or ITIL change. The fenced consumer
   configuration moves dispatch authority to Niobe in one revision-fenced
   mutation, and the resulting event records the exact revision, readback, and
   evidence hash.
5. **Post-transfer health evidence.** For 7 days after transfer, dispatch
   health evidence (churn, zero zombie claims older than the reaper threshold,
   zero duplicate-suppression failures) is appended daily. Tank runs one
   rehearsal release of a harmless artifact with independent behavioral
   verification by Seraph before Tank's first real release.

**Rollback.** During the shadow window and the 7-day post-transfer window, any
of these reverts dispatch authority to Jarvis in one revision-fenced mutation,
with the revert event recording the trigger and evidence hash: one unsafe
action, one missed reaper breach, parity evidence going stale past twice the
cycle cadence, or a Seraph BLOCKED against dispatch health that Niobe cannot
clear within one cycle. Reversion is automatic in authority but recorded before
it takes effect; if the recording itself fails, the safe state is Jarvis.

**The exact withdrawal condition.** Jarvis withdraws to Casey personal-agent
duties when, and only when, a single append-only handoff record exists that
contains all four of the following, each with its own evidence SHA256:

1. the shadow-parity evidence meeting the parity gate, covering at least 14
   consecutive days, audited by Seraph with an explicit gate-met statement;
2. a Seraph statement of zero open BLOCKED findings against Niobe's dispatch;
3. Link's confirmation that no open card, PR, or arbitration cites Jarvis as
   its dispatch authority; and
4. the signed Chef artifact or ITIL record accepting the transfer.

Until that record exists in full, Jarvis remains Fleet Dispatcher, and any
agent that observes dispatch arriving from Jarvis after the record exists
raises a BLOCKED against the handoff card. Withdrawal is complete when Jarvis's
fleet mailbox, dispatch timers, and dispatch credentials are released, and the
release is recorded; what remains is Casey's personal agent, which is the job
that was always underneath the seat.

## Consequences

### Positive

- The four-jobs problem ADR-0005 documented is finally finished instead of
  narrowed: dispatch has a dedicated holder with no other mandate.
- Casey's personal-agent work stops competing with fleet dispatch for the same
  agent's attention, which is the concrete silence this ADR exists to prevent.
- Release and install get an owner, and behavioral verification gets a named
  producer, so "deployed and verified" stops being an adjective and becomes
  hashed evidence.
- The verifier and the operator are different seats, so a release can no longer
  verify itself.
- Technical conflicts get an owner whose decision procedure is "cite the
  evidence," and genuine ambiguity gets a route to a human that lands as a
  signed record instead of a chat relay.

### Constraints

- Niobe, Tank, and Seraph are names, not holders. The seats exist when their
  signed, distinct identities exist, and not before.
- The transfer moves existing authority only. Any future widening of Niobe's,
  Tank's, or Seraph's authority is a new decision with its own review, and for
  actuation it must follow the catalog-relaxation path in
  [`ACTION_AUTHORIZATION_STANDARD`](../standards/ACTION_AUTHORIZATION_STANDARD.md).
- `ROSTER.md` and the SKCapstone runtime enforcement documents change only
  after this ADR is Accepted; the implementation card carries those edits.
- The shadow window costs two weeks of double coverage. That is deliberate:
  the six failures ADR-0005 measured were all silences, and parity is the
  anti-silence.

### Rejected alternatives

- **Give Niobe the merge queue too.** Rejected. Link owns the trunk, and a
  dispatcher that merges its own reassignments collapses the separation the
  seats exist to keep.
- **Let Tank self-verify releases.** Rejected. The operator grading its own
  deployment is how `claimed-done` at 56 percent happened. Operator evidence
  and independent verification stay distinct.
- **Give Seraph actuation or merge to make findings self-executing.** Rejected.
  A verifier with authority is a second approver and violates the one-approval
  store.
- **Retire Jarvis outright.** Rejected. Casey's personal-agent duties are real
  work that already exists, and Jarvis's context in them is not transferable to
  a new identity by fiat.
- **Cut over on a chosen day without shadow parity.** Rejected on the same
  evidence that built ADR-0005: nobody notices a failed cutover either.

## Verification

- The transferred authority is quoted from ADR-0005 section 1 unchanged; the
  boundary rows transfer with it, so no new capability is granted by this ADR.
- Tank's and Seraph's boundaries trace to AUTONOMY invariants 1, 2, 3, and 5:
  no second approval store, closed actuator inputs, no unregistered surface,
  observation carries no control weight.
- The withdrawal condition is exact and machine-checkable: four named evidence
  elements, each hashed, all append-only, and a named safe state on failure.
- This ADR ships as **Proposed**. Acceptance requires architecture review by
  Chef (authority source), Jarvis (outgoing seat), and Link (trunk owner)
  before any implementation card lands; the open pull request is the review
  vehicle, not the approval. No code, no roster edit, and no unit change is
  contained in this change.

## Related

- [`ADR-0005`](./ADR-0005-five-operating-seats.md)
- [`ROSTER.md`](../ROSTER.md)
- [`AUTONOMY_STANDARD`](../standards/AUTONOMY_STANDARD.md)
- [`ACTION_AUTHORIZATION_STANDARD`](../standards/ACTION_AUTHORIZATION_STANDARD.md)
- [`ACTUATION_READINESS_AND_FREEZE_STANDARD`](../standards/ACTUATION_READINESS_AND_FREEZE_STANDARD.md)
