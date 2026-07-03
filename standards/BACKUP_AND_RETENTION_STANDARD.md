# Backup & Retention Standard

How every `sk*` node backs up **sovereign state** so it survives disk loss,
corruption, or a bad migration — with enough depth to roll back days, weeks,
months, or a year, and without unbounded growth.

The governing principle: **back up what you cannot regenerate; skip what you
can.** A backup that also hauls rebuildable indexes and transient churn is too
heavy to keep on a rotation, which is how operators end up with *one* stale copy
instead of a deep history.

Reference implementation: `skcapstone` — `scripts/skcapstone-gfs-backup.sh` +
[`docs/BACKUP.md`](https://github.com/smilinTux/skcapstone/blob/main/docs/BACKUP.md).

---

## 1. The retention scheme — Grandfather-Father-Son (GFS)

Scheduled backups MUST use a GFS rotation with a pruner, not an ever-growing
pile. The baseline depths (tune per node; keep the four tiers):

| Tier | Keep | Promoted |
| ---- | ---- | -------- |
| **daily** (Son) | 14 | every run |
| **weekly** (Father) | 8 | Sundays |
| **monthly** (Grandfather) | 12 | 1st of month |
| **yearly** | 2 | Jan 1 |

- Each tier is a directory; the daily run writes today's archive, then **copies**
  it up to weekly/monthly/yearly on the promotion boundary.
- A **pruner runs every execution** and keeps the newest N per tier — so
  steady-state size is bounded and predictable (`Σ tier_keep × archive_size`).
- Retention depths are **config at the top of the script**, not scattered magic
  numbers.

## 2. What is backed up vs. skipped

Classify every path as **irreplaceable** (back up) or **rebuildable / transient**
(skip):

| Class | Examples | Action |
| ----- | -------- | ------ |
| Irreplaceable state | flat memory tiers, soul, identity, trust, seeds, config, coordination, journal, key material, song/emotional anchors | **archive** |
| Rebuildable | vector store (Chroma/pgvector), SQLite `index.db` + WAL — reconstruct from the flat source of truth | **skip** (rebuild on restore) |
| Transient | comms queues (inbox/outbox/acks), logs, subconscious/whisper caches, media renders, voices | **skip** |
| Never | venvs, `__pycache__`, `node_modules`, `.stversions`, lock/pid/tmp/sync-conflict files, **the backup dir itself** | **skip** |

Skipping the rebuildable index is the difference between a ~1 GB and a ~80 MB
archive — the small one is what makes a deep rotation affordable. This mirrors
the source-of-truth split in the
[Architecture standard](./ARCHITECTURE_AND_DATAFLOW_STANDARD.md): flat files are
canonical; indexes are derived.

## 3. Integrity, safety, and location

- **Checksums.** Every archive carries a matching `*.sha256` sidecar; restore
  verifies (`sha256sum -c`) **before** unpacking.
- **Disk guard.** The job refuses to run below a free-space floor (e.g. 2 GB)
  and alerts (`sk-alert`) rather than pushing a full disk over the edge. A
  backup must never *cause* the outage it protects against.
- **No self-nesting.** The rotation directory is excluded from its own archive.
- **No symlink escape.** Never follow symlinks out of the backup root; skip
  convenience symlinks so nothing is archived twice.
- **3-2-1 aspiration.** Local rotation is the floor. Where the state is
  high-value, keep at least one copy **off the box** (another host / removable
  mount / sovereign object store). Encrypt off-box copies at rest per the
  [Cryptography standard](./CRYPTOGRAPHY_STANDARD.md).
- **Secrets in backups** follow the same "names/handles, not plaintext values"
  posture as everywhere else — sealed key material stays sealed in the archive.

## 4. Scheduling

- A scheduled backup is a **cron / systemd-timer job**, decoupled from any
  long-running daemon (so it still runs when the daemon is down).
- Pick a **quiet slot distinct** from the housekeeping/prune window.
- **Idempotent install** — the installer greps for the job before adding it, so
  re-running never duplicates the schedule.
- **Log every run** (start / archive path + size / rotation summary) to a
  predictable path.

## 5. Restore is part of the standard

A backup you can't restore is not a backup. The repo's `SOP.md` / backup doc
MUST document the exact restore path, including the **index-rebuild step** for
anything skipped in §2:

```bash
sha256sum -c <archive>.sha256          # verify
tar -xzf <archive> -C /restore/root    # unpack irreplaceable state
<rebuild-index-command>                # e.g. skmemory reindex
```

Backup and [housekeeping](https://github.com/smilinTux/skcapstone/blob/main/docs/HOUSEKEEPING.md)
are inverses: housekeeping **prunes what you never read again**; backup
**preserves what you can never regenerate**. A compliant node runs both.

---

## 6. Per-repo / per-node compliance checklist

- [ ] Scheduled backup on a **GFS rotation** (4 tiers) with a **pruner** — not an
      unbounded pile.
- [ ] Archives the **irreplaceable** state; **excludes** rebuildable indexes +
      transient churn (§2).
- [ ] Per-archive **`.sha256`** integrity sidecar.
- [ ] **Free-space guard** + alert; excludes its own dir; no symlink escape.
- [ ] Retention depths + free-space floor are **config**, not magic numbers.
- [ ] Job is a **cron/timer** (daemon-independent), idempotently installed, and
      **logged**.
- [ ] `SOP.md` documents the **restore path incl. index rebuild** — and it's been
      tested at least once.
- [ ] High-value state has **≥1 off-box copy**, encrypted at rest.
