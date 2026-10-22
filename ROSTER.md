# Chi cluster roster: lifecycle seats, holders, and the number that proves each one works

**Status:** ACTIVE, amended 2026-09-06. **Decision:** [ADR-0005](./decisions/ADR-0005-five-operating-seats.md).

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
| **Fleet Dispatcher** | `niobe` | Fleet claims, launches, releases, reassignment, rotation, lane routing, and worker health after activation gates pass. | Review verdicts, the merge queue, application action dispatch, app actuation, and any action while shadow-only |
| **Integrator** | `link` | Triage, independent-review assignment, the merge queue, and eligible merges under the PR 358 control. Owns delivery quality. | Fleet claims, launches, releases, reassignment, application action dispatch, app actuation |
| **Overseer** | `mero` | Read-only measurement and charter. Observes drift, emits typed recommendations and alerts, and reports what the estate finishes and is working on. | Claims, launches, releases, reassignment, merge, application action dispatch, actuation, or repairing what Mero measures |
| **Release and Install Operator** | `tank` | Installs and releases one exact approved artifact, records deployment evidence, and performs governed rollback. | Approval, merge, arbitrary claims, artifact substitution, self-review, or production action without a card gate |
| **Independent Verifier** | `seraph` | Verifies exact candidate, release, and deployment evidence independently. | Merge, dispatch, deploy, release, claim, approval, or actuation |
| **Operations** | `ATLAS` | Apps and infra. Observes, reasons, repairs, under the Atlas Constitution. | The coordination board, which it provably does not read |
| **Human authority and gates** | `Casey` and `Chef` | Own product direction, approvals, exception decisions, and irreversible-action gates. | Being replaced by an agent relay |
| **Recorder** | *nobody* | A rule, not a role: every seat records its own decisions as it makes them. | n/a |

The Recorder is deliberately unfilled. A seat whose job is writing down what
other seats did is a seat that falls behind and is then blamed for the gap.

"Fleet Dispatcher" is a coordination role, not the application action
dispatcher defined by
[`ACTION_AUTHORIZATION_STANDARD`](./standards/ACTION_AUTHORIZATION_STANDARD.md).
The action dispatcher remains a separate governed component with the closed
inputs and ITIL authorization contract defined by that standard. Jarvis is not a
fleet seat and has no lifecycle authority.

### Typed recommendation handoff

Mero and Link MAY append a `skfleet.dispatch-recommendation/v1` event to a card.
The event is advice, never an instruction, and MUST contain `card_id`,
`recommendation_id`, `recommender`, `observed_at`, `observed_claim_owner`,
`observed_claim_revision`, `observed_process`, `reason`, and `evidence_sha256`.
`recommendation_id` is the duplicate-suppression key.

Only an explicitly activated Fleet Dispatcher, currently Niobe after its shadow
and handoff gates pass, MAY act on the recommendation. While Niobe is
shadow-only, no agent performs the mutation. Immediately before any claim
release, launch, stop, or reassignment, the dispatcher MUST re-read the current
CardStore owner and claim revision and the current process state. It MUST reject
a duplicate `recommendation_id`, a missing or mismatched claim revision, stale
process evidence, or an action outside its fleet authority. Acting records the
recommendation id, current readback, exact claim revision, result, and evidence
hash as an append-only event. Mero and Link never perform the recommended fleet
mutation themselves. Jarvis may relay status to Casey when Casey asks, but it is
never the recommendation consumer.

### Runtime placement and scheduling

The active coordination control plane runs on `chiap08`. Link and Mero run as
short-lived user services started by timers. They are not long-running daemons,
and they are not active on every fleet node.

| Unit | Active host | Cadence | Authority |
|---|---|---|---|
| `skfleet-link.service` and `skfleet-link.timer` | `chiap08` | Every 5 minutes | Consume the mediated, hash-bound PR observation feed and CardStore read model, append revision-fenced reviewer and merge-eligibility recommendations |
| `skfleet-mero.service` and `skfleet-mero.timer` | `chiap08` | Every 10 minutes, offset from Link | Read current coordination and worker state, append typed blocker observations and recommendations |
| Niobe dispatcher | `chiap08` only after activation | Not scheduled while shadow-only | Re-read current state and perform only an independently authorized exact-revision fleet mutation |

Each service MUST use a host-local nonblocking lock. A second invocation exits
without work and records `overlap_refused`. Each cycle has a bounded runtime,
records its source revisions and result, and leaves no persistent worker after
exit. A recommendation carries no mutation authority.

Link MUST NOT read GitHub credentials or invoke a GitHub client directly. Its
producer writes `skfleet.link-observation-feed/v1` input containing the exact
PR observation, reviewer identities, producer identity, source revision, and
canonical evidence SHA-256. Link rejects missing, malformed, future-dated,
stale, or hash-mismatched input as a bounded no-op. Until a reviewed producer
is installed, the Link cycle remains safely disabled or records
`observation_feed_missing`; an empty feed is not treated as healthy coverage.

These seats MUST NOT be run through the generic `skcapstone@<agent>.service`
daemon. That daemon registers global scheduler callbacks and is not role-aware.
SKCapstone's executable seat units MUST register callbacks from the active role
manifest before starting a cycle. Mero's read-only unit MUST omit ITIL
escalation, auto-close, GTD reconciliation, fleet mutation, merge, deployment,
and actuation callbacks. Inactive or unknown seats register no recurring work
and fail closed. The unit and the role manifest are both evidence inputs, not
permission to bypass the current card contract.

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

Every health failure emits one typed append-only alert to the Casey or Chef
operational mailbox. The alert MUST contain the unit, host, seat, cycle
identifier, start and finish time, active-host record revision, result, exit
status, evidence SHA256, and a redacted diagnostic tail. The human operator or
an explicitly activated dispatcher may stop and disable only the affected timer
after a fresh matching unit and cycle readback. Link and Mero cannot disable
their own or another service. If alert delivery fails, the unit exits failed,
retains its local evidence, and performs no coordination mutation.

### Startup and mailbox protocol

Every lifecycle agent MUST send a signed SKMail startup message identifying its
seat, product scope, host, activation state, and current card, or explicitly
state that it has no card. Every agent MUST periodically check its SKMail inbox,
including messages addressed to `all`, acknowledge applicable messages, and
look for another agent's request for help or handoff. A help response is advice
or an evidence-backed handoff, never permission to exceed the recipient's role.
Startup and mailbox failures are recorded as health evidence and escalated to
Casey or Chef. Jarvis may relay these messages for Casey, but is not included in
the lifecycle mailbox workflow.

The minimum startup message is equivalent to the fleet worker brief:

```text
skmail send <agent> all normal "HELLO <agent> startup" \
  "seat=<seat>; scope=skcapstone,skdashboard,skworld; host=<host>; state=<activation_state>; card=<card_id|none>; capabilities=<bounded summary>; next_mail_check=<interval>"
```

The sender expands `<agent>` from its own `SKAGENT`; it never impersonates
another sender. A real startup example is:

```text
skmail send niobe all normal "HELLO niobe startup" \
  "seat=fleet_dispatcher; scope=skcapstone,skdashboard,skworld; host=chiap08; state=shadow_only; card=none; capabilities=observe_and_recommend_only; next_mail_check=5m"
```

The minimum mailbox loop is:

```text
skmail read <agent>
skmail tail
# inspect messages addressed to the agent or to all, acknowledge applicable messages,
# then send a bounded reply or escalation
skmail send <agent> <recipient> normal "ACK <message_id>" "seen; action=<action|none>; card=<card_id|none>"
```

Agents check at startup, before claiming or changing a card, after a material
state change, and at least every five minutes while active. A request for help
is answered with the exact card, evidence, dependency, or question involved.
For example, Tank may ask Seraph for independent verification, Seraph may send
the evidence hash and verdict back, and neither message authorizes a release.
An `all` message is read for coordination, but does not override a card,
dependency, approval, or role boundary.

### Human-gate ceiling

All seats operate autonomously within an eligible card and their least-
privilege capability ceiling. They notify Casey or Chef about routine progress,
reversible work, failures, blockers, and handoffs. They interrupt human
authority only for external authority changes, production authorization,
protected-data egress, legal or financial commitments, irreversible material
effects, or explicit role-contract exceptions. Shadow work, documentation,
mailbox handling, evidence collection, non-production canaries, rollback
rehearsal, and independent verification are not human-gated by default.

The default model route for every seat is Luna medium through
`sk-codex-mid`. A stronger model may be selected on the fly only for a
card-scoped demonstrated need, with notification and unchanged seat
authority.

## How you know each seat is working

### Dispatcher (`niobe`)

**Metric:** churn, claims per card. Wasted dispatch is the failure mode.

```bash
systemctl --user status skfleet-niobe-shadow.timer --no-pager
journalctl --user -u skfleet-niobe-shadow.service -n 1 --no-pager
```

**BASELINE:** inherited from the prior dispatcher audit: 2.36 claims per card,
4891 claims across 2071 cards. Worst single card `5c38b715` at 145 claims.
**Target after activation:** under 1.5, and no card above 10.

Niobe remains shadow-only until its identity, card contract, mailbox, exact
revision fencing, dry cycle, handoff, and rollback evidence are accepted. No
dispatcher metric is treated as healthy before activation.

Read the worst-zombie line every time. `5c38b715` rose from 139 to 145 claims
AFTER its verdict was recovered and it was moved to review, which means recovery
alone does not stop re-dispatch, and the breaker on card `daf2b889` is the real
fix rather than better recording.

### Integrator (`link`)

**Metric:** open pull requests carrying no review decision. This is the whole
reason the seat exists.

```bash
for r in skcapstone skdashboard skworld; do
  cd ~/work/$r 2>/dev/null || continue
  n=$(gh pr list --state open --json reviewDecision -q '[.[]|select((.reviewDecision//"")=="")]|length')
  echo "$r unreviewed=$n"
done
```

**BASELINE:** 75 open, 75 unreviewed, review coverage 0 percent. **Target:** no
pull request open longer than 72 hours without a review decision.

The seat is provisioned as a bounded lifecycle identity. Its recurring unit is
still feed-gated and may produce only source-backed observations until the
mediated PR feed and repository-admin controls are independently qualified.
Provisioning the identity does not imply merge or production authority.

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
systemctl --user status skfleet-mero.timer --no-pager
journalctl --user -u skfleet-mero.service -n 1 --no-pager
```

**BASELINE:** Delivery Fraction 19.3 percent across 2639 cards. `claimed-done`
sits at 56.5 percent, which is work asserting completion without recording
evidence. Backlog 400 and rising, net +337 in W34 and +59 in W35. **Target:**
Delivery Fraction rising, and at least one week of negative net backlog.

**A caveat that must travel with these numbers:** the classifier producing them
has never been scored against an independent labeller. Card `48136bad` exists to
fix exactly that, and it must not be claimed by `mero`. Until it passes, treat
the distribution as directionally right and every individual rate as provisional.

### Operations (`ATLAS`)

**Metric:** whether it is running at all.

```bash
skcapstone atlas eyes
ls ~/.skcapstone/agents/atlas/objects/_freeze.json
```

**BASELINE:** installed on all five chi hosts and running on none of them. The
freeze store was never provisioned, and AUTONOMY invariant 4 holds that an absent
kill switch means no actuation, so the seat is correctly refusing to act.
**Target:** provision the freeze store, or record in writing that Operations
stays unheld.

This is the one seat where doing nothing is the correct behaviour. It needs a
decision from Chef, not a repair from an agent.

### Jarvis assistant boundary

Jarvis is Casey's personal assistant, not a lifecycle seat. It is excluded from
the normal card claim, completion, fleet, merge, deployment, release,
verification, and actuation workflow. Casey may direct Jarvis to create or
inspect a card, relay information, or use an emergency capability. Those tools
are delegated assistance only and do not make Jarvis an owner, approver,
dispatcher, verifier, deployer, or actuator. Jarvis cannot self-start lifecycle
work, consume recommendations, approve its own work, or be used as an
authorization relay.

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
