# Observability & Scheduling Standard

How every `sk*` node runs **scheduled work** so that nothing fails silently and
every input becomes tracked, reportable, actionable work — not a line lost in a
log nobody reads.

The governing principle: **a scheduled job that can fail must be observable, and
an input that needs action must be captured.** An unwrapped cron is a silent
single point of failure; an inbound event with no capture path evaporates into
chat history. Both are defects.

Reference implementation: `skos` — the **`gtd-ingest`** subsystem
([`docs/gtd-ingest-architecture.md`](https://github.com/smilinTux/skos/blob/main/docs/gtd-ingest-architecture.md)
+ [`docs/gtd-ingest-SOP.md`](https://github.com/smilinTux/skos/blob/main/docs/gtd-ingest-SOP.md)) and the
`sk-cron-run` wrapper + `sk-status` reporter; ITIL/email/cron/calendar/telegram are
the reference adapters.

---

## 1. Every scheduled job is wrapped (observability)

A cron / systemd-timer job MUST run under an **observability wrapper** that:

1. appends a structured **run-ledger** record — `{job, host, start, dur_s, exit, ok, tail}` (JSONL);
2. on failure, **captures an actionable item** into the unified GTD store (source=`cron`) **and** fires `sk-alert` (real-time);
3. returns the wrapped command's exit code unchanged.

Reference: `sk-cron-run <job-name> <command…>`. An unwrapped scheduled job is
reviewed like missing error handling. The wrapper is idempotent and adds no
behavior beyond recording + alerting.

## 2. Unified capture — sources are adapters, one sink, one store

External inputs (incidents, email, calendar, chat, cron failures, voice) MUST be
captured through **one `capture()` sink** into **one store**, never bespoke
per-source writers:

- **Port + adapters.** A single capability (`gtd-ingest`) is the port; each source
  is an **adapter**. *Push* adapters call `capture()` on their event; *pull*
  adapters implement `poll()` and are drained by a wrapped job. Adding a source is
  one adapter class — no core changes.
- **Idempotent + deduped.** Every capture carries a stable **`source_ref`**
  (incident id, mail thread id, `chat:msg_id`, `cron:job@date`). The sink dedupes on
  `(source, source_ref)`; re-ingest never duplicates.
- **One store, many sources.** Captures land in the same GTD store with a `source`
  tag; clarify once, organize everywhere. The sink resolves the *canonical* store
  path (never a divergent copy).

## 3. Notify, don't nag — real-time vs. digest

- **Real-time `sk-alert`** only for failures / urgent (crit) events — the exception, not the stream.
- **A daily ops report** (delivered to the operator's channel) rolls up the last 24 h:
  every job's `ok/fail/duration` from the run-ledger, plus surfaced pipeline health.
  Sent **always**, so silence is never ambiguous ("no report" ≠ "all fine").
- Monitored pipelines (ingest, backups, re-embeds, wiki maintenance) become
  first-class report lines by (1) wrapping their job in the observability wrapper and
  (2) adding a `*_status()` reader to the report.

## 4. Self-report is the evidence

The node MUST be able to report its live scheduling/observability state on demand
(`sk-status all` / `<service> status`): recent job outcomes, capture counts,
pipeline health. Per the [TESTING_AND_CI_STANDARD](./TESTING_AND_CI_STANDARD.md)
"tests are evidence" gate — every claim in a report/SOP is checkable from that
command.

## 5. Worker liveness: three signals, and never actuate on absence

A long-running worker that buffers its output until completion emits nothing for
hours. A nine hour run and a nine hour hang are then indistinguishable from
outside. Anything that supervises such workers MUST separate three signals, which
fail independently:

| Signal | Claim | Emitted by | Catches |
|---|---|---|---|
| **Liveness** | the process exists and its supervisor holds it | the wrapper | crash, kill, host loss |
| **Progress** | work is advancing | the agent | deadlock, infinite retry, wedged inference |
| **Disposition** | what the worker believes it is doing, in its own words | the agent | blocked on a human, missing dependency |

Rules:

- **A beat carries a progress token, never a bare pulse.** A pulse proves only
  that the pulse works. The token is monotonic and compared for equality only
  (step, phase ordinal, artifact hash). Unchanged across K beats while beats
  continue is the definition of *stalled*, which is not the same as dead.
- **Label the emitter.** A wrapper beat MUST NOT populate progress. A supervisor
  seeing only wrapper beats knows the process lives and knows nothing about
  advancement, and MUST say so rather than render it as healthy.
- **Self-reported blocked beats inferred blocked.** Give workers a closed
  vocabulary (`RUNNING`, `WAITING_DEPENDENCY`, `BLOCKED_NEEDS_HUMAN`,
  `DEGRADED_RETRYING`) plus a one line reason. A blocked worker states its reason
  in a sentence; no supervisor can infer it correctly from silence.
- **Absence of signal is the alarm.** A scheduler or supervisor that can stop
  without emitting an error needs a dead-man switch, because a stopped timer
  produces no logs, no errors and no alerts.
- **Beat absence MUST NOT actuate.** A missing beat while the unit is alive is a
  *telemetry fault*, never a releasable condition. Any release, reap or
  termination additionally requires **host-local** negative proof (systemd or
  cgroup) plus an exact owner and revision fence. Stated as an invariant to carry
  verbatim: *no lease state is derived from beat evidence alone; beats only
  corroborate preconditioned claim events.*
- **Set timeouts from measured transport latency, not from intuition.** Where
  beats cross hosts over a replicated store, measure p95 first. Measured on the
  chi cluster 2026-09-04: Syncthing chiap04 to chiap01 median 101.4s, p95 292.3s,
  with an observed skipped window over 40 minutes and generations that vanished
  in transit. A 120s cross-host timeout against that transport manufactures false
  deaths as routine behaviour.
- **Distinguish transport-stale from worker-stale**, or evaluate host-local only.
  A classifier that cannot tell them apart is reporting the network as a dead
  worker.
- **Beat interval is at most one third of the staleness threshold**, so one lost
  beat never raises an alarm, and startup grace is a separate budget from running
  grace.
- **Telemetry gets its own bounded channel.** High-frequency beats are state, and
  belong in a self-expiring per-worker record where only the latest value
  matters. Blocking and unblocking are events with history and belong in an
  append-only channel. Mixing them destroys whichever channel humans read.

Reference implementation and the measured evidence behind every number above:
`.skcapstone/docs/WORKER-BEAT-PROTOCOL.md` on the chi cluster.

## 6. Scheduling hygiene

- Jobs are **idempotent** and **deduped** (safe to re-run; a missed run self-heals next tick).
- Retention/verbosity is **config at the top**, not scattered magic numbers.
- Long drains run **fully detached** (`setsid`) so they survive a harness/session reap; a fixed round cap is a backstop, not the exit condition.
- Secrets are **read from existing stores** (keyring / `.env` / vault), never inlined in a job definition.

---

## Compliance line (put in your SOP + README)

> **Observability & Scheduling:** all scheduled jobs wrapped (run-ledger +
> failure→GTD + sk-alert); external inputs captured via the `gtd-ingest` sink
> (`source_ref`-deduped); daily ops report + on-demand `… status`; any
> long-running worker separates liveness, progress and disposition, and never
> actuates on beat absence alone. Conforms to
> [OBSERVABILITY_AND_SCHEDULING_STANDARD](https://github.com/smilinTux/sk-standards/blob/main/standards/OBSERVABILITY_AND_SCHEDULING_STANDARD.md).

Not applicable (`N/A — <reason>`) only for repos with **no scheduled work and no
external inputs** (pure libraries).
