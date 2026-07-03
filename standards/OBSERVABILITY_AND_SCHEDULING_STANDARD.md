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

## 5. Scheduling hygiene

- Jobs are **idempotent** and **deduped** (safe to re-run; a missed run self-heals next tick).
- Retention/verbosity is **config at the top**, not scattered magic numbers.
- Long drains run **fully detached** (`setsid`) so they survive a harness/session reap; a fixed round cap is a backstop, not the exit condition.
- Secrets are **read from existing stores** (keyring / `.env` / vault), never inlined in a job definition.

---

## Compliance line (put in your SOP + README)

> **Observability & Scheduling:** all scheduled jobs wrapped (run-ledger +
> failure→GTD + sk-alert); external inputs captured via the `gtd-ingest` sink
> (`source_ref`-deduped); daily ops report + on-demand `… status`. Conforms to
> [OBSERVABILITY_AND_SCHEDULING_STANDARD](https://github.com/smilinTux/sk-standards/blob/main/standards/OBSERVABILITY_AND_SCHEDULING_STANDARD.md).

Not applicable (`N/A — <reason>`) only for repos with **no scheduled work and no
external inputs** (pure libraries).
