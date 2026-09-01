# ADR-0005: Five operating seats, and gates relaxed by catalog rather than by prompt

**Status:** Accepted
**Date:** 2026-09-01
**Deciders:** Chef, Mero
**Extends:** [`ADR-0002`](./ADR-0002-two-coding-lanes.md)
**Constituent of:** [`AUTONOMY_STANDARD`](../standards/AUTONOMY_STANDARD.md)
**Purpose:** separate the operating roles that had collapsed into one seat, and
record the sanctioned path to running in production without a human prompt on
every action.

## Context

On the night of 2026-08-31 the chi cluster was measured end to end. The board
held 2,603 cards. Only 16.1 percent were `delivered`, meaning done with both a
verdict and an evidence artifact. **56.4 percent reached done carrying no verdict
at all.** Resolving evidence referents against disk rather than trusting the
presence of a link dropped the delivery fraction from 19.2 percent to 10.6
percent: 188 cards cite evidence that does not exist, does not hash match, or is
not a path. The weekly backlog has never once shrunk.

Six independent failures were traced that night. Read them together, because the
pattern is the decision:

| Failure | What was missing |
|---|---|
| One card claimed and released 139 times, re-dispatched every five minutes for sixteen hours after it had actually finished | nobody noticed |
| A worker held a claim 17.4 hours at 00:00:00 CPU with a zero-byte log | the reaper measured session existence, not progress |
| Six pull requests open, none with an assigned reviewer | nobody owns the trunk |
| A signed human authorization lapsed against a fixed 30 minute window | nobody was watching the clock |
| ATLAS has never run, because its freeze store was never provisioned | nobody noticed the prerequisite |
| 56.4 percent of cards done with no verdict | nobody owns delivery quality |

**Every one is "nobody noticed". Not one is "nobody approved."** That is the
finding this ADR is built on, and it points the opposite way from adding gates.

Meanwhile one agent seat, Jarvis, was carrying four jobs at once: fleet dispatch,
the liveness watcher, status reporting, and relaying human decisions. Two were
actively harmful. The watcher reported `workers=0` and `workers=1` against 32
live worker processes, an undercount of roughly 17x, which makes its outage
alerts and its recovery alerts equally uninformative. And two human decisions
travelled to an executing agent as forwarded chat messages, putting an agent
inside the authorization path that
[`ACTION_AUTHORIZATION_STANDARD`](../standards/ACTION_AUTHORIZATION_STANDARD.md)
exists to close.

## Decision

### 1. Five seats, separated

| Seat | Owns | Explicitly does not own |
|---|---|---|
| **Dispatcher** | Rotation, claims, liveness. Board mechanics. | status reporting, reviewer assignment, relaying human decisions |
| **Integrator** (`link`) | The trunk. Assigns independent reviewers, runs the merge queue, enforces the merge gate, decides what lands, owns delivery quality. | dispatch, actuation |
| **Operations** | Apps and infra. Observes, reasons, repairs, under the Atlas Constitution. | the coordination board, which it provably does not read |
| **Overseer** | Convergence and drift. Emits observations, produces briefs. | any actuation whatsoever |
| **Recorder** | Not an agent. A rule: a human decision lands as a signed artifact or an ITIL change record. | being a message forwarded by an agent |

The Dispatcher seat is held by Jarvis, narrowed. The Operations seat is ATLAS.
The Overseer seat is Mero. **The Integrator seat is new, named `link`, and
currently unfilled**, and its absence is the direct cause of two of the six
failures above.

The name is not decoration. Link is the operator who sees where everyone is,
routes them, and gets them in and out, which is the coordinating half of the
seat. The other half is the reason it was chosen over the alternatives: a
**linker** is the build stage that resolves symbols across separately compiled
objects and produces the single final artifact. That is integration in the exact
sense this seat means it. `lock` was rejected despite fitting the gate role,
because the fleet already sends `FILE-LOCK` and `FILE-LOCK-RELEASE` on skmail
constantly and an agent of that name would be ambiguous in the channel it works
in.

The Recorder row is a rule rather than a role on purpose. There is no seat to
appoint; the obligation is that a human decision must be durable and verifiable
at the moment it is made, not reconstructed afterwards from a chat relay.

### 2. Gates are relaxed by catalog edit, never by prompt

Production does not mean a human approves every action. It means every action is
**recorded**, and the human gate is set **per action class** in the ratified
action catalog rather than per action.

[`ACTION_AUTHORIZATION_STANDARD`](../standards/ACTION_AUTHORIZATION_STANDARD.md)
R4 already names this as the intended path: *"The intended path was to relax a
gate after the record proved the action class safe."* Relaxation must be a
reviewed, versioned catalog change citing ledger lineage for that class. It must
not be a code branch, a hidden flag, a caller exception, or a model-selected
path.

The sequencing follows from that and is the whole operating strategy:

1. A new action class starts gated.
2. The ledger accumulates outcomes for it. **This is what recording is for.**
3. When the lineage supports it, one reviewed catalog edit relaxes the class.
4. Every subsequent action in that class produces a full ITIL record and **no
   prompt**.

A class cannot be relaxed before it has lineage, so the record is the
prerequisite for the streamlining rather than a tax on it. Rubber-stamping is
achieved by ratifying the catalog once, not by approving actions quickly.

Two classes are never relaxed, and this is a deliberate floor: anything the
Atlas Constitution Article 2 calls irreversible, and anything touching the
guardrails covered by the Article 3 carve-out.

### 3. Coverage comes from deadlines, not from people

Nothing dies on the vine because a human forgot to look. Every card carries a
completion deadline. A breach emits an observation. Operations raises a change.
The Integrator receives it. A human sees it only on second escalation.

This reuses the machinery already ratified, pointed at **silence** rather than at
actions. The six failures above were all silences: a card nobody re-examined, a
worker nobody could see was inert, PRs nobody assigned, a clock nobody watched, a
prerequisite nobody checked, verdicts nobody required.

### 4. The Overseer never actuates

The Overseer seat measures and reports. It emits
`skoperator.observation/v1` envelopes for the board the way any app emits its
own, and Operations consumes them under its constitution.

`AUTONOMY_STANDARD` invariant 2 already excludes briefs from the actuator's
inputs by category. This ADR makes that structural rather than incidental: the
Overseer has no actuation surface and therefore needs no row in the
actuation-surface registry, no freeze story of its own, and no capability token.

## Consequences

### Positive

- The undercounting watcher and the decision relay both leave the Dispatcher
  seat, so a broken collector can no longer discredit the seat's other outputs.
- The Integrator seat gives PRs, reviewer assignment and delivery quality a
  named owner, which nothing had.
- Production becomes reachable without a prompt on every action, by the route the
  authorization standard already sanctions.
- The Overseer shrinks. Deleting its actuation phase removes an entire parallel
  authority ladder that would have duplicated the Atlas Constitution.

### Constraints

- **Operations cannot start until its freeze store is provisioned in the off
  position.** Measured 2026-09-01 across chiap01, chiap02, chiap03, chiap04,
  chiap08 and noroc2027: the CLI is installed everywhere and there is no
  `objects/_freeze.json` on any host, no agent home, no unit, no timer, no
  process. Under
  [`ACTUATION_READINESS_AND_FREEZE_STANDARD`](../standards/ACTUATION_READINESS_AND_FREEZE_STANDARD.md)
  an absent kill switch means no actuation rather than free actuation, so this is
  failing safe. Provisioning it is a human-only write.
- Catalog relaxation requires lineage, so the first weeks of any new action class
  are gated by construction. That is the cost of the streamlining, paid once per
  class.
- The Integrator seat is unfilled. Naming it `link` does not fill it, and this
  ADR deliberately does not assign it to an existing agent: handing it to
  whoever currently holds the most context is how one seat came to carry four
  jobs in the first place.

### Rejected alternatives

- **Replace the Dispatcher.** Rejected. The seat was not being held badly, it was
  holding four jobs. Replacing the occupant would have carried all four across.
- **Add human gates to raise quality.** Rejected on evidence. All six failures
  were failures to notice, and none was a failure to approve. More gates would
  add latency to the paths that already work while leaving every silence intact.
- **Give the Overseer bounded override authority.** Rejected. Operations already
  holds that chair with a constitution, a freeze, escalation and ITIL. A second
  actuator would violate the one-approval-store invariant.

## Verification

- Six failures, each measured on the live cluster on 2026-08-31 and 2026-09-01,
  with card ids, process ids, CPU times and file hashes recorded in the Overseer
  evidence artifact `docs/evidence/P0-CENSUS-2026-08-31.md` and on the cards
  themselves.
- The watcher undercount was verified by counting live worker processes across
  four hosts against the alert payload in the same minute.
- The freeze-store absence was verified by direct filesystem check on six hosts.

## Related

- [`AUTONOMY_STANDARD`](../standards/AUTONOMY_STANDARD.md)
- [`ACTION_AUTHORIZATION_STANDARD`](../standards/ACTION_AUTHORIZATION_STANDARD.md)
- [`ACTUATION_SURFACE_GOVERNANCE_STANDARD`](../standards/ACTUATION_SURFACE_GOVERNANCE_STANDARD.md)
- [`ACTUATION_READINESS_AND_FREEZE_STANDARD`](../standards/ACTUATION_READINESS_AND_FREEZE_STANDARD.md)
- [`SELF_HEALING_TIERS_STANDARD`](../standards/SELF_HEALING_TIERS_STANDARD.md)
- [`ADR-0002`](./ADR-0002-two-coding-lanes.md)
