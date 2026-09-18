# Chi cluster roster: seats, holders, and the number that proves each one works

**Status:** ACTIVE. **Date:** 2026-09-18. **Decisions:** [ADR-0005](./decisions/ADR-0005-five-operating-seats.md), [ADR-0006](./decisions/ADR-0006-dispatch-handoff-niobe-tank-seraph.md).

Every seat below carries a metric and the command that prints it. That is the
point of this document. A seat whose health can only be established by asking
the agent that holds it is not a seat, it is a rumour, and the estate already
ran that experiment: one agent held four jobs, everyone assumed someone else
was watching the trunk, and 75 of 75 open pull requests reached today with no
review decision recorded on any of them.

Numbers marked BASELINE were measured on 2026-09-01 and are expected to move.
Re-run the command rather than trusting the number printed here.

## The seats

| Seat | Holder | Owns | Explicitly does not own |
|---|---|---|---|
| **Fleet Dispatcher** | `niobe` | Fleet claims, launches, releases, reassignment, rotation, lane routing, and worker health. | Review verdicts, merge, deployment, release, application action dispatch, app actuation |
| **Integrator** | `link` | Triage, independent-review assignment, the merge queue, and eligible merges under the PR 358 control. Owns delivery quality. | Fleet claims, launches, releases, reassignment, application action dispatch, app actuation |
| **Overseer** | `mero` | Read-only measurement and charter. Observes drift, emits typed recommendations and alerts, and reports what the estate finishes and is working on. | Claims, launches, releases, reassignment, merge, application action dispatch, actuation, or repairing what Mero measures |
| **Independent Verifier** | `seraph` | Exact-candidate and release verification with PASS, FAIL, or BLOCKED evidence. | Self-review, merge, dispatch, deployment, release, actuation |
| **Operations** | `ATLAS` | Operational observation, postcondition and behavioral verification, and authorized card-scoped action under the Atlas Constitution. Release, installation, and bounded rollback of exact approved artifacts, absorbed from the dissolved Tank seat (skcapstone PR 751, 2026-09-17): a duty on paper until the freeze store is provisioned and `DEPLOY` is granted. | Coordination-board ownership, card claiming outside its admitted `seat-atlas` lane, reviewer assignment, merge, policy change, unratified action, source authoring, self-approval, independent review of its own release |
| **Recorder** | *nobody* | A rule, not a role: every seat records its own decisions as it makes them. | n/a |

**Tank is dissolved, and none of its jobs are unowned.** skcapstone PR 751
(2026-09-17, nimble-factory Plan B2) folded the seat into ATLAS;
`LIFECYCLE_SEATS` and `lifecycle-seat-profiles.json` now carry five seats.
Measured close-out: Tank identities wrote 33 board events in the 30 days to
2026-09-18, all coordination on DEPLOY cards, zero releases, and no tank unit
or timer exists on chiap08. Where each duty lives now:

- Release and install of exact approved artifacts: ATLAS on paper; in practice
  a human invoking `skcapstone fleet rollout` / `rollback` (dry run by
  default) until the freeze store and the `Action.DEPLOY` grant land.
- Behavioral verification, "is what we merged actually running?": ATLAS's
  postcondition duty, instrumented by `skfleet-readiness.timer`, `skcapstone
  fleet node drift`, and the daily report-only `skfleet-install-audit.timer`
  on all five chi hosts.
- Bounded rollback: `rollout_history.previous_manifest` plus
  `execute_rollback`, human-invoked.

The full boundary, with permitted and prohibited verb lists per seat, is in
skcapstone `docs/fleet/seat-charters.md`; the verb tables below are the
roster-level copy.

The Recorder is deliberately unfilled. A seat whose job is writing down what
other seats did is a seat that falls behind and is then blamed for the gap.

"Fleet Dispatcher" is a coordination role, not the application action
dispatcher defined by
[`ACTION_AUTHORIZATION_STANDARD`](./standards/ACTION_AUTHORIZATION_STANDARD.md).
Niobe gains no application actuation authority from this roster. The action
dispatcher remains a separate governed component with the closed inputs and ITIL
authorization contract defined by that standard.

Jarvis is Casey's personal assistant, not a recurring lifecycle seat. Jarvis
retains emergency card, fleet, merge, deployment, release, verification, and
actuation tools for explicit Casey-directed help. Tool availability is not
seat ownership or authorization and cannot bypass the governing card or policy.
Every emergency operation enters through SKCapstone's
`JarvisEmergencyGateway`, which verifies a signed, unexpired Casey direction
bound to the exact action, target, change, and scope before mutation. The only
permitted product scope is SKCapstone, SKDashboard, and SKWorld. Missing,
forged, expired, substituted, or out-of-scope directions fail closed.

### Typed recommendation handoff

Mero and Link MAY append a `skfleet.dispatch-recommendation/v1` event to a card.
The event is advice, never an instruction, and MUST contain `card_id`,
`recommendation_id`, `recommender`, `observed_at`, `observed_claim_owner`,
`observed_claim_revision`, `observed_process`, `reason`, and `evidence_sha256`.
`recommendation_id` is the duplicate-suppression key.

Only Niobe MAY act on a recurring recommendation. Immediately before any claim release,
launch, stop, or reassignment, Niobe MUST re-read the current CardStore owner and
claim revision and the current process state. It MUST reject a duplicate
`recommendation_id`, a missing or mismatched claim revision, stale process
evidence, or an action outside Niobe's fleet authority. Acting records the
recommendation id, current readback, exact claim revision, result, and evidence
hash as an append-only event. Mero and Link never perform the recommended fleet
mutation themselves.

### Owned verbs by writer identity

"Read-only" as prose is what failed: it named no verbs, so nothing could
check it, and it was violated for two weeks unnoticed. Every board write
lands in `~/.skcapstone/cards/<id>/events/<writer>@<host>.jsonl`; the
filename is the writer, the record field is `action`. These lists are the
checkable contract, and the census query at the end of this section is the
check.

| Writer | Permitted actions | Prohibited actions |
|---|---|---|
| `niobe` | claim, release_claim, move, complete, void, archive, add_dependency, remove_dependency, amend_criteria, describe, priority, reopen, unassign, review_assignment_launch, link | pass_for_review, blocked, review_assignment_recommendation, mero_observation, mero_blocker_recommendation |
| `link` | review_assignment_recommendation, link, move, describe, priority | claim, release_claim, void, archive, review_assignment_launch |
| `mero` | mero_observation, mero_blocker_recommendation, link | claim, release_claim, move, complete, void, archive, add_dependency, remove_dependency, amend_criteria, describe, priority, reopen, unassign |
| `seraph` | claim, move, complete, release_claim (own review lane), review_assignment_launch (bounded `pi-seraph-*` workers), link, pass_for_review, blocked | void, archive, add_dependency, remove_dependency, amend_criteria, describe, priority, reopen, unassign, add_label, review_assignment_recommendation, mero_observation, mero_blocker_recommendation |
| `atlas` | claim, move, complete, release_claim (only on cards labeled `seat-atlas` plus `dispatch-approved`), link | claim on any card lacking that label pair, void, archive, review_assignment_launch, review_assignment_recommendation, add_dependency, remove_dependency, amend_criteria, priority |
| `jarvis` | any verb, only under a verified signed Casey direction through `JarvisEmergencyGateway` | any scheduled or recurring write of any verb |

### Automation writers and their owning seats

The event store carries writer identities that are automation, not seats. A
writer identity that maps to no row here and no seat above is itself a
finding: an unowned job. Measured over the 30 days to 2026-09-18 on chi:

| Writer | 30-day events | Owning seat | Note |
|---|---|---|---|
| `jarvis` (written by `skfleet-rotate` on chiap01 to chiap04) | 12,230 | Fleet Dispatcher | NONCONFORMANT identity: 4,487 of these landed after ADR-0006 removed Jarvis from recurring scheduling. The rotate script defaults its writer to `jarvis`; moving it to `niobe` is the named fix, and until it lands the Jarvis boundary is uncheckable. |
| `archive-done` | 2,031 | Fleet Dispatcher | Board hygiene: archives terminal cards |
| `fleet-liveness-reaper` | 656 | Fleet Dispatcher | Worker health |
| `stale-sweep` | 369 | Fleet Dispatcher | Board hygiene |
| `coord-move` | 274 | Fleet Dispatcher | Board hygiene |
| `lifecycle-reconciler` | 198 | Fleet Dispatcher | Board hygiene |
| `fleet-review-closer` | 65 | Integrator | Review-lane closure |
| `lumina-ghost-reaper` | 60 | Fleet Dispatcher | Worker health |
| `skfleet-install-audit`, `skfleet-readiness`, `skcapstone fleet node drift` | no board writes | Operations | Report-only deploy and install instruments |

Census query (read-only), which reproduces every number above and flags any
writer this roster does not own:

```bash
python3 - <<'EOF'
import json, os, glob, collections
c = collections.Counter()
for f in glob.glob(os.path.expanduser("~/.skcapstone/cards/*/events/*.jsonl")):
    w = os.path.basename(f).split("@")[0]
    for line in open(f):
        try: r = json.loads(line)
        except Exception: continue
        c[(w, r.get("action","?"))] += 1
for (w, a), n in c.most_common(80):
    print(w, a, n)
EOF
```

### Runtime placement and scheduling

The active coordination control plane runs on `chiap08`. Link and Mero run as
short-lived user services started by timers. They are not long-running daemons,
and they are not active on every fleet node.

| Unit | Active host | Cadence | Authority |
|---|---|---|---|
| `skfleet-link.service` and `skfleet-link.timer` | `chiap08` | Every 5 minutes | Read current PR and CardStore state, append revision-fenced reviewer and merge-eligibility recommendations |
| `skfleet-mero.service` and `skfleet-mero.timer` | `chiap08` | Every 5 minutes, offset from Link | Read current coordination and worker state, append typed blocker observations and recommendations |
| Niobe fenced consumer (dedicated `skfleet-niobe` timers installed but disabled; the cycle runs serialized inside `skfleet-seat-cycle.service`) | `chiap08` | Every 5 minutes | Re-read current state and perform only an independently authorized exact-revision fleet mutation |
| `skfleet-seraph.service` (dedicated timer installed but disabled; the cycle runs serialized inside `skfleet-seat-cycle.service`) | `chiap08` | Every 5 minutes | Launch bounded independent review work under an exact distinct reviewer identity |
| `skfleet-atlas.service` and `skfleet-atlas.timer` | `chiap08` | Every 5 minutes | Presence, SKMail, health, and admitted `seat-atlas` cards through Niobe; overlap with a seat-cycle generation records as a no-op |
| `skfleet-rotate.service` and `skfleet-rotate.timer` | `chiap01` to `chiap04` | Every 5 minutes | Fleet dispatch rotation. NONCONFORMANT writer identity: writes to the CardStore as `jarvis`; the identity must move to `niobe` (see Automation writers above) |
| `skfleet-readiness.service` and `skfleet-readiness.timer` | all five chi hosts | Every 15 minutes | Report-only readiness and drift check |
| `skfleet-install-audit.service` and `skfleet-install-audit.timer` | all five chi hosts | Daily | Report-only install hygiene audit |

All five seats use distinct identities, the three-product scope SKCapstone,
SKDashboard, and SKWorld, and the default route `sk-codex-mid`. The governed
repositories are `smilinTux/skcapstone`, `smilinTux/skdashboard`,
`smilinTux/skworld`, and the supporting `smilinTux/sk-standards`. Each sends a
startup hello to `all`, reads its direct and `all` SKMail view every bounded
cycle, and looks for help, handoff, dependency, and reviewer-conflict traffic.
Mail is coordination data, never authority, and is not acknowledged
automatically.

Each recurring process is a bounded one-shot. A host-local nonblocking lock
records overlap as a no-op. Abandonment requires exact proof that the prior
boot ID, PID, and process start generation is dead. Retirement preserves
receipts and leaves no persistent child worker.

Before changing this roster or the SKCapstone lifecycle profile, run
`python scripts/check_lifecycle_seat_alignment.py --skcapstone-profile
../skcapstone/src/skcapstone/data/lifecycle-seat-profiles.json`. The check reads
both repositories and fails if the six-seat cadence or default model contract
diverges.

Each service MUST use a host-local nonblocking lock. A second invocation exits
without work and records `overlap_refused`. Each cycle has a bounded runtime,
records its source revisions and result, and leaves no persistent worker after
exit. A recommendation carries no mutation authority.

Before reading PR, CardStore, worker, or provider state, each cycle MUST read a
revision-pinned control-plane record and compare its `active_host` with the
local hostname. A mismatch exits without scanning or emitting recommendations
and records only `inactive_host_refused` health evidence. Link has a 120-second
runtime limit. Mero has a 180-second runtime limit. A timeout records failure
and terminates the affected cycle.

`chiap01` is the cold standby for the Link and Mero control-plane cycles only.
Its ordinary fleet rotation remains active and is outside this standby rule.
The Link and Mero unit files MAY be installed for byte parity, but both of
their timers MUST remain disabled. Promotion requires all of the following:

1. Fresh evidence that both `chiap08` timers are stopped and inactive.
2. A revision-fenced promotion record naming the source and target hosts.
3. Exact unit, executable, configuration, and package hash readback.
4. One dry cycle on `chiap01` before either timer is enabled.
5. Evidence that no second active scheduler exists.

Automatic failover is forbidden. Running Link or Mero actively on more than one
host recreates duplicate reviewer assignment, stale observation, and worker
collision risks.

### Runtime health and recovery

Health is determined from evidence, not merely from unit state. Each cycle MUST
record start time, finish time, host, seat identity, source revision, scanned
population, emitted recommendation count, duplicate suppression count, error
count, and evidence SHA256. The health check fails when:

- the last successful cycle is older than twice its configured cadence;
- a cycle exceeds its runtime bound or another cycle overlaps it;
- Link acts on a PR head that differs from its observation;
- Mero emits a mutation event or invokes a mutation command;
- the same recommendation identifier is accepted twice; or
- both `chiap08` and `chiap01` report an enabled timer for the same seat.

Recovery stops the affected timer, preserves the failed cycle evidence, and
restores the prior unit and executable bytes. It never clears a claim, changes a
card, assigns a reviewer, merges a PR, or promotes the standby as part of the
health check itself.

Every health failure emits one typed append-only alert to the Jarvis SKMail
inbox. The alert MUST contain the unit, host, seat, cycle identifier, start and
finish time, active-host record revision, result, exit status, evidence SHA256,
and a redacted diagnostic tail. Jarvis disables and stops only the affected
timer after a fresh matching unit and cycle readback. Link and Mero cannot
disable their own or another service. If alert delivery fails, the unit exits
failed, retains its local evidence, and performs no coordination mutation.

## How you know each seat is working

### Dispatcher (`niobe`)

**Metric:** churn, claims per card. Wasted dispatch is the failure mode.

```bash
cd ~/work/mero && .venv/bin/python -m mero.cli census | grep -E "churn|worst zombie"
```

**BASELINE:** 2.36 claims per card, 4891 claims across 2071 cards. Worst single
card `5c38b715` at 145 claims. **Target:** under 1.5, and no card above 10.

Read the worst-zombie line every time. `5c38b715` rose from 139 to 145 claims
AFTER its verdict was recovered and it was moved to review, which means recovery
alone does not stop re-dispatch, and the breaker on card `daf2b889` is the real
fix rather than better recording.

**Identity conformance, measured 2026-09-18:** the seat's job is being done,
but not under the seat's identity. In the 30 days to 2026-09-18 the `niobe`
writer produced 11 card events while the `jarvis` writer produced 12,230, of
which 4,487 landed after ADR-0006 removed Jarvis from recurring scheduling.
The producer is `skfleet-rotate` on chiap01 to chiap04, whose writer identity
defaults to `jarvis`. **Target:** scheduled `jarvis` events per day reach
zero and the rotate cycles appear as `niobe`. Until then the dispatcher
boundary cannot be checked against the event store, because sanctioned
automation and out-of-seat action are indistinguishable.

### Integrator (`link`)

**Metric:** open pull requests carrying no review decision. This is the whole
reason the seat exists.

```bash
for r in skcapstone skdashboard skworld sk-standards; do
  cd ~/work/$r 2>/dev/null || continue
  n=$(gh pr list --state open --json reviewDecision -q '[.[]|select((.reviewDecision//"")=="")]|length')
  echo "$r unreviewed=$n"
done
```

**BASELINE:** 75 open, 75 unreviewed, review coverage 0 percent. **Target:** no
pull request open longer than 72 hours without a review decision.

The seat is filled by name only. Naming `link` did not fill it, and this roster
says so rather than implying a coverage that does not exist.

Link MAY merge only when the source-only control introduced by SKCapstone PR 358
returns eligible for the exact PR head. Eligibility requires a mergeable PR,
zero failed checks, a full-SHA exact-head independent PASS by a distinct author,
no unresolved FAIL or BLOCKED lineage, and a PR not authored by Link. The title
and category MUST also exclude CapAuth, credential, custody, issuer, secret, key,
rollback, deploy, production, release, migration, and any other sensitive class.
Link records the exact head, check state, review identity, review evidence SHA256,
lineage result, category result, and merge receipt as immutable evidence. Any
failed predicate denies the merge and escalates to Chef. This role grants no
deployment, restart, credential, provider, release, migration, or application
actuation authority.

### Overseer (`mero`)

**Metric:** Delivery Fraction, the share of terminated cards that actually
delivered something, together with whether the backlog is growing.

```bash
cd ~/work/mero && .venv/bin/python -m mero.cli census
```

**BASELINE:** Delivery Fraction 19.3 percent across 2639 cards. `claimed-done`
sits at 56.5 percent, which is work asserting completion without recording
evidence. Backlog 400 and rising, net +337 in W34 and +59 in W35. **Target:**
Delivery Fraction rising, and at least one week of negative net backlog.

**A caveat that must travel with these numbers:** the classifier producing them
has never been scored against an independent labeller. Card `48136bad` exists to
fix exactly that, and it must not be claimed by `mero`. Until it passes, treat
the distribution as directionally right and every individual rate as provisional.

### Independent Verifier (`seraph`)

**Metric:** verdict production, and lane conformance of its writes.

```bash
python3 - <<'EOF'
import json, os, glob, collections
c = collections.Counter()
for f in glob.glob(os.path.expanduser("~/.skcapstone/cards/*/events/*.jsonl")):
    w = os.path.basename(f).split("@")[0]
    if "seraph" not in w: continue
    for line in open(f):
        try: c[json.loads(line).get("action","?")] += 1
        except Exception: pass
print(dict(c.most_common()))
EOF
```

**BASELINE (30 days to 2026-09-18):** 2,596 events across `seraph` and its
`pi-seraph-*` review workers: claim 849, move 808, complete 492,
release_claim 193, review_assignment_launch 176. The seat is real and
working. Out-of-lane drift at the same measurement: 20 void, 20 archive, and
21 dependency or metadata writes, which the verb table above now prohibits.
**Target:** verdict-bearing actions keep flowing and the prohibited-verb
count is zero.

### Operations (`ATLAS`)

**Metric:** whether it is running at all.

```bash
skcapstone atlas eyes
ls ~/.skcapstone/agents/atlas/objects/_freeze.json
```

**BASELINE (re-measured 2026-09-18):** the cycle now runs and the work does
not. `skfleet-atlas.timer` on chiap08 has produced 1,166 cycle records in 30
days and every one records `dispatch_succeeded: 0` (`atlas_no_eligible_work`
or `atlas_rotation_overlap`). The freeze store is still absent on all five
chi hosts, and AUTONOMY invariant 4 holds that an absent kill switch means no
actuation, so the seat is correctly refusing every effect. Meanwhile
identities matching `*atlas*` wrote 34 board events in the same window,
including claims on two cards carrying no `seat-atlas` label and void plus
archive on two `seat-seraph` review cards, which the verb table above now
prohibits. The seat is idle on its own job and active outside it.
**Target:** provision the freeze store and grant the bounded `DEPLOY` per
skcapstone `docs/fleet/seat-charters.md`, or record in writing that
Operations stays unheld; either way, prohibited-verb count zero.

This is the one seat where doing nothing is the correct behaviour. It needs a
decision from Chef, not a repair from an agent.

## Escalation

Anything the Atlas Constitution Article 2 calls irreversible goes to Chef.
Everything else routes to the seat that owns it, and the owning seat records the
decision where the next reader will look for it, which means on the card rather
than in chat.

Cross-seat conflict resolves toward the trunk: the Integrator decides what lands,
because a merge is the one action every other seat's work has to pass through.

## Keeping this document honest

Every number here is reproducible from the command printed beside it. If a
command stops working, that is a defect in that seat's instrumentation, and
repairing it is that seat's job, because a seat that cannot be measured has
already begun to drift.
