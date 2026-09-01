# Chi cluster roster: seats, holders, and the number that proves each one works

**Status:** ACTIVE. **Date:** 2026-09-01. **Decision:** [ADR-0005](./decisions/ADR-0005-five-operating-seats.md).

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
| **Dispatcher** | `jarvis` | Fleet dispatch, lane routing, worker health, the rotation. Decides what runs where and when. | The merge queue, review assignment, actuation on apps |
| **Integrator** | `link` | The trunk. Assigns independent reviewers, runs the merge queue, enforces the merge gate, decides what lands. Owns delivery quality. | Dispatch, actuation |
| **Overseer** | `mero` | Measurement and charter. Reports what the estate finishes and what it is actually working on. Read-only by design. | Dispatch, merge, actuation. Mero never repairs what he measures |
| **Operations** | `ATLAS` | Apps and infra. Observes, reasons, repairs, under the Atlas Constitution. | The coordination board, which it provably does not read |
| **Recorder** | *nobody* | A rule, not a role: every seat records its own decisions as it makes them. | n/a |

The Recorder is deliberately unfilled. A seat whose job is writing down what
other seats did is a seat that falls behind and is then blamed for the gap.

## How you know each seat is working

### Dispatcher (`jarvis`)

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

### Integrator (`link`)

**Metric:** open pull requests carrying no review decision. This is the whole
reason the seat exists.

```bash
for r in skcapstone skdashboard sk-standards capauth skgateway sklegal; do
  cd ~/work/$r 2>/dev/null || continue
  n=$(gh pr list --state open --json reviewDecision -q '[.[]|select((.reviewDecision//"")=="")]|length')
  echo "$r unreviewed=$n"
done
```

**BASELINE:** 75 open, 75 unreviewed, review coverage 0 percent. **Target:** no
pull request open longer than 72 hours without a review decision.

The seat is filled by name only. Naming `link` did not fill it, and this roster
says so rather than implying a coverage that does not exist.

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
