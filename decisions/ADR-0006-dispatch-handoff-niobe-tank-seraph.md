# ADR-0006: The dispatcher handoff: Niobe takes dispatch, Tank takes release, Seraph verifies, Jarvis stands down

**Status:** Accepted and active
**Date:** 2026-09-09
**Acceptance evidence:** Casey decision card `c4e7a9b2`; implementation card
`20a637fe`
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

### 5. Active lifecycle contract and Jarvis withdrawal

Casey accepted the direct bounded transfer on card `c4e7a9b2`, replacing the
proposed fourteen-day transition gate. The accepted path preserves the same
role boundaries, exact-revision fencing, rollback, and evidence requirements
without adding a redundant human wait to routine lifecycle work.

Niobe holds recurring dispatcher authority on chiap08. Tank and Seraph are
card-scoped, and ATLAS is active for bounded presence plus separately
authorized operations. Card `20a637fe` records the source implementation.

**Rollback.** A verified unsafe dispatcher action, reaper breach, stale health
evidence, or uncleared Seraph BLOCKED disables Niobe's live timer, preserves
receipts, and restores the shadow timer. Rollback does not silently transfer
another seat's authority.

Jarvis is outside recurring lifecycle scheduling and serves as Casey's
personal assistant. Jarvis retains
emergency card, fleet, merge, deployment, release, verification, and actuation
tools only for explicit Casey-directed assistance. Tool availability is not
ownership or authorization and cannot bypass another seat, a current card, a
capability check, or an exact-revision gate.

### 6. Presence, mail, beats, and safe retirement

Link, Mero, Seraph, Niobe, Tank, and ATLAS have distinct identities and SKMail
write access. Each sends one startup hello to `all` per host boot and polls its
own mailbox view, including direct and `all` traffic, on every bounded cycle.
Each looks for help, handoff, dependency, and reviewer-conflict messages. Mail
never grants authority and is never acknowledged automatically.

Each seat emits bounded health evidence. Recurring services are one-shots with
host-local nonblocking overlap protection, a maximum five-minute runtime, and
immutable receipts. Abandonment requires exact proof that the prior boot ID,
PID, and process start generation is no longer live. Retirement leaves no
persistent child and preserves evidence. Tank and ATLAS presence cycles do not
claim work. Niobe atomically claims and launches exact `seat-tank` and
`seat-atlas` cards under their own identities.

All six seats are scoped to SKCapstone, SKDashboard, and SKWorld on chiap08 and
default to `sk-codex-mid`. Routine catalog-authorized actions are notify-only.
Human interruption is reserved for an explicit catalog human class,
protected-data egress, external authority, legal or financial commitment,
irreversible material effect, or a requested role-contract exception.

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
- `ROSTER.md` and the SKCapstone runtime enforcement documents are aligned by
  implementation card `20a637fe`.
- Bounded activation preserves fail-closed health, exact-revision fencing, and
  rollback evidence without a routine human wait.

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
- Jarvis exclusion is machine-checkable in the lifecycle profile and recurring
  unit set, while emergency tools remain explicitly Casey-directed.
- Acceptance is recorded by Casey decision card `c4e7a9b2`. Source changes,
  tests, exact evidence, and independent review are carried by implementation
  card `20a637fe`.

## Related

- [`ADR-0005`](./ADR-0005-five-operating-seats.md)
- [`ROSTER.md`](../ROSTER.md)
- [`AUTONOMY_STANDARD`](../standards/AUTONOMY_STANDARD.md)
- [`ACTION_AUTHORIZATION_STANDARD`](../standards/ACTION_AUTHORIZATION_STANDARD.md)
- [`ACTUATION_READINESS_AND_FREEZE_STANDARD`](../standards/ACTUATION_READINESS_AND_FREEZE_STANDARD.md)
