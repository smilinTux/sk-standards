# Provenance & Mutation Standard (the Signed Provenance Envelope)

**Status:** proposed
**Date:** 2026-08-14
**Author:** Fable (claude-fable-5)
**Extends:** [CRYPTOGRAPHY_STANDARD](./CRYPTOGRAPHY_STANDARD.md), [CRYPTO_AGILITY_STANDARD](./CRYPTO_AGILITY_STANDARD.md), [SKWORLD_AUTHORIZATION_STANDARD](./SKWORLD_AUTHORIZATION_STANDARD.md), [OBSERVABILITY_AND_SCHEDULING_STANDARD](./OBSERVABILITY_AND_SCHEDULING_STANDARD.md)

---

How every `sk*` store accepts a mutation: wrapped in one **Signed Provenance
Envelope (SPE)**, appended to an immutable log, and reversible. Full design +
the incident forensics: skcapstone
`docs/specs/2026-08-14-signed-provenance-envelope-arch.md`.

---

## The thesis

> **Fast requires reversible. Reversible requires attributable.**

We run fast, we break things, we iterate. That posture is only survivable when
every mutation can be mapped back to who did it, from what state, and undone
with one more event. Provenance in SKWorld exists to **empower agents to
self-correct**, never to name and shame. Chef's words, verbatim: *"there should
always be a good provenance trail of identity ownership so we can map back
quickly, that's the whole point of our keys"* and *"it's not to name n shame
but to empower."*

The inverse is the defect: a store where `done` is a one-way door, where the
actor is free text or absent, where a mutation can hit the wrong target because
nothing validated it, is a store where a single bad grep is unrecoverable. Two
live incidents on 2026-08-13 (a GTD substring match that closed an unrelated
item with no undo path, and a 16x operator-seat crash loop that silently
dropped human escalations) both reduce to the same five holes: loose
identifier matching, no target validation before mutating, no blast-radius
isolation, no attribution, no undo. This standard closes all five with one
mechanism.

**Scope.** Every store that accepts mutations from more than one process,
agent, or human: the coord CardStore, the fleet object store, the unified GTD
store, the ITIL event store, and any future shared store. Pure per-process
caches and derived indexes (rebuildable from a compliant store) are out of
scope.

---

## 1. The envelope (SPE): normative schema

Every mutation record MUST carry, embedded in the store's own native record
(never a sidecar file), the following envelope:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `spe` | string | MUST | Envelope wire-format version tag, currently `"spe1"`. Same discipline as `pqdm1:`/`pqdr1` in [CRYPTO_AGILITY_STANDARD](./CRYPTO_AGILITY_STANDARD.md) §1: the tag is the format version; never redefine it, mint `spe2` instead. |
| `actor.id` | string | MUST | The authenticated identity of the writer, from `capauth.resolve_agent_identity()`: the `capauth_uri` (wire form, `capauth:<agent>@skworld.io`) or the sovereign FQID. NEVER free text, NEVER a magic string like `"human"` or `"operator"` typed by a caller. |
| `actor.role` | string | MUST | One of the fleet writer roles (`operator`, `agent`, `scheduler`, `controller`, `human`), aligned with `skcapstone/src/skcapstone/fleet/store.py:24-42` (`Writer`). |
| `actor.node` | string | MUST | Hostname of the writing process. |
| `actor.session` | string | SHOULD | Session identifier (Claude session id, run id, tty). Lets a self-correcting agent find its OWN recent mutations fast. |
| `ts` | string | MUST | RFC 3339 UTC timestamp. |
| `action` | string | MUST | A verb from the store's REGISTERED action set (see §3). An unregistered verb is rejected, not folded. |
| `target` | object | MUST | `{store, kind, id}`. The writer MUST have resolved the target to an exact id and validated it exists in the store's catalog BEFORE emitting the event (§4). |
| `prior` | string | SHOULD | Reference to the state the writer observed before mutating: the last event id/seq it folded, or a content hash of the prior state. This is the stale-plan binding (unified-consent-plane §3.2): a mutation against a state that no longer exists is detectable. |
| `sig.suite_id` | string | MUST when signed | Self-describing signature suite id from the `skcomms.crypto_suites` registry (`ed25519-v1`, `mldsa65-ed25519-v2`, ...). A signature with no suite id is the "hardcoded primitive" anti-pattern (CRYPTO_AGILITY §4) and is non-compliant. |
| `sig.value` | string / null | MUST (slot) | Detached signature over the canonical bytes of the record with the `sig.value` slot blanked, exactly the `canonical_bytes` construction in `skcapstone/src/skcapstone/fleet/signing.py:31-42`. `null` is a legal value in `off`/`permissive` modes; the SLOT itself is mandatory from day one so enforcement is a flip, not a migration. |

Rules:

- **The envelope embeds in the native record.** A CardStore event line gains
  these keys; the fleet `writer` block IS this envelope; a GTD journal line
  carries it. No parallel provenance store, ever.
- **Actor is resolved, never asserted.** The writing code calls
  `capauth.resolve_agent_identity()` (the one canonical resolver, capauth epic
  `2b264064`) at write time. A caller-supplied actor string is input to
  logging, never to the envelope.
- **Version is explicit and additive.** Old records without an envelope still
  load (they classify as `pre-spe`, §5); a new envelope field never breaks an
  old reader.

## 2. The append-only mutation log: MANDATORY

A compliant store never mutates state in place as its record of truth:

1. **Immutable creation + append-only events.** The reference shape is the
   CardStore: a write-once core (`O_CREAT|O_EXCL`, skcoord
   `src/skcoord/card_store.py:204-223`) plus per-writer append-only JSONL event
   logs (`cards/<id>/events/<agent>@<host>.jsonl`, `card_store.py:225-249`,
   flock-guarded, per-writer `seq`). Per-writer files are what make the log
   Syncthing-merge-safe: concurrent appends on different nodes never conflict.
2. **State is a pure fold.** Current status is DERIVED by folding the event
   stream in deterministic `(ts, writer, seq)` order (`card_store.py:291-413`),
   never stored as a mutable field that a writer edits. A stored status field
   that writers overwrite is last-writer-wins and unattributable.
3. **One store lock, every writer.** All load-modify-save cycles on shared flat
   files serialize on the store's single advisory lock (the GTD reference:
   `flock(LOCK_EX)` on `.gtd.lock`, skcapstone
   `src/skcapstone/mcp_tools/gtd_tools.py:92-113`) and write each file
   atomically (temp + fsync + `os.replace`, `gtd_tools.py:115-143`). A writer
   that bypasses the lock or writes with a bare `write_text` is non-compliant
   however small it is.
4. **Cross-file moves are write-then-delete.** When an item must move between
   files, land it in the destination FIRST, then remove it from the source, so
   a crash between the two saves duplicates (self-healing) instead of losing
   (skos `src/skos/gtd_ingest.py:345-354` is the reference; skcapstone
   `gtd_tools.py:720-754` `gtd done` is the counter-example this rule exists
   to kill).

## 3. The reversal rule: every destructive verb ships its inverse

Undo falls out of append-only for free: **undo is one more event that reverses
the fold**, exactly like the CardStore's existing `reopen` action
(`card_store.py:407`) reverses `complete`/`archive`.

- Every verb in a store's registered action set that removes, completes,
  archives, or otherwise takes an item out of the working set MUST have a
  registered inverse verb that puts it back **under the same id**. Recovery
  that requires recapturing under a new id breaks the provenance chain and is
  a defect, not a workaround.
- **Archive is a state, not an exit.** An archived item remains in the store's
  lookup universe: findable by id, reopenable, and deduped. A store where the
  archive participates in dedupe but not in lookup has two disagreeing
  universes (§6, anti-pattern 2).
- The inverse verb carries its own SPE and a `prior` ref to the event it
  reverses, so the timeline reads: did X, undid X, both attributed. The
  original event is never edited or deleted. History is append-only in both
  directions.

## 4. Target validation before mutation: MANDATORY

A mutation is emitted only after the writer has:

1. **Resolved the target to an exact id.** Substring/grep matching is a
   DISCOVERY tool, never a targeting tool. A flow that pipes a text match
   straight into a destructive verb (the 2026-08-13 incident: one ambiguous
   token matched both a person's name and an unrelated organization) is
   non-compliant; the destructive call takes ids,
   and anything that fans one query out to N destructive calls MUST confirm
   each target individually (or run in a dry-run-then-confirm shape).
2. **Validated the target against the store's catalog.** Validating the ACTION
   while trusting the OBJECT is a named anti-pattern: the operator seat
   validated proposals' actions against the app catalog but never the object
   name (`skcapstone/src/skcapstone/operator_seat/plan.py:26-46`), so an
   LLM-guessed object name crash-looped the seat 16 times at
   `operator_seat/fleet_adapter.py:172-173`. Both halves of `(action, target)`
   are validated, and an invalid target is a per-item refusal (parked,
   reported), never an uncaught raise that aborts the batch.
3. **Recorded what it saw** in `prior`, so a concurrent change is detectable
   at fold/verify time instead of silently overwritten.

## 5. Signature + verification rules

- **Construction.** Detached signature over canonical JSON bytes with the
  signature slot blanked and keys sorted, per
  `fleet/signing.py::canonical_bytes` (`signing.py:31-42`). The signature
  covers the whole record including `ts` and any generation counter, so
  replaying an old signed record over a newer one verifies as invalid.
- **Suite agility.** The suite is named by `sig.suite_id` from the
  `crypto_suites` registry and rolls per CRYPTO_AGILITY §3 (new suite = new
  id + `replaces=` breadcrumb + dual-stack window). No store hardcodes a
  primitive.
- **Trust roster stays local.** Verification keys come from the LOCAL capauth
  home (own key + `fleet-trust/*.asc`, `signing.py:112-131`), never from the
  synced tree the signatures protect. The roster must not be writable by the
  thing it authenticates.
- **Three verification classes, three modes.** A record verifies as
  `verified`, `unsigned` (a null slot), `invalid` (a bad signature), or
  classifies as `pre-spe` (predates the envelope). Rollout is
  `off -> permissive -> enforce` per store (the `SKFLEET_SIGNING` pattern,
  `signing.py:21-28`): permissive signs and counts, enforce refuses to ACT on
  `unsigned`/`invalid` while never destroying data or stopping running
  services. Historical `pre-spe` records are grandfathered read-only and are
  NEVER backfilled with synthetic envelopes: fabricating attribution is worse
  than admitting its absence.
- **The honest-claim gate applies to provenance.** Documentation, docstrings,
  and self-reports MUST NOT describe a record as "signed", "verified", or
  "auditable" unless a wired verify path enforces it. The live
  counter-example: `fleet_act`'s docstring claims it records "a SIGNED entry"
  (`operator_seat/fleet_adapter.py:156-157`) while the writer's `signature` is
  `null` on disk (verified live on `objects/service/skgateway.json`). Same
  rule as the crypto honest-claim gate: say what is enforced, not what is
  intended.

## 6. Named anti-patterns (do not ship these)

| # | Anti-pattern | Live example (all real, 2026-08-13/14) | The fix |
|---|---|---|---|
| 1 | **Destructive two-file move** (delete-before-write) | `gtd done` removes from the source list (`gtd_tools.py:735`, saved at `:200`) BEFORE appending to archive (`:743`); a crash between the saves loses the item. The sibling sink got it right (`gtd_ingest.py:345-354`). | Write-then-delete ordering (§2.4) + an event log so the item's history survives any file outcome. |
| 2 | **Write-universe / lookup-universe mismatch** | GTD dedupe scans archive (`_seen_refs`, `gtd_tools.py:149-166`) but lookup does not (`_find_item_across_lists` iterates `_GTD_LISTS` only, `:184-191`, `:20-26`); `move` can PUSH into archive (`_DESTINATION_MAP`, `:34-41`) but nothing can find or reopen there. Three modules disagree on whether archive is in the store at all (`agent_run.py:62-71` and `skos/adapters/order.py:78-88` include it). | ONE file-set constant per store, shared by every reader and writer; archive in the lookup universe (§3). |
| 3 | **Unlocked writer** | `skcapstone gtd capture` inlines `_load_list`/`_save_list` with no store lock and no dedupe (`cli/gtd.py:46-61`); skos `mail.py::_save` is a bare `write_text`, unlocked AND non-atomic (`mail.py:169-170`), and archives items itself (`:453-460`). | Every writer goes through the store's locked, atomic sink. No inline shortcuts. |
| 4 | **Unsigned actor claim** (free-text identity) | GTD has ZERO actor fields anywhere (grep for `resolve_agent_identity` over `gtd_tools.py`, `cli/gtd.py`, `skos/gtd_ingest.py`: zero hits); `fleet_act` hardcodes `"by": "atlas"` (`fleet_adapter.py:178`); CAB votes take free-text `agent`. | `actor.id` from `capauth.resolve_agent_identity()` at write time (§1), signed when the mode is on. |
| 5 | **The "SIGNED" overclaim** | `fleet_act` docstring vs the `signature: null` on disk (§5). | Honest-claim gate: the word appears only where a verifier enforces it. |
| 6 | **One-way door** (no inverse verb) | `gtd done` has no `reopen`; the 2026-08-13 recovery required hand-reading `archive.json` and recapturing under a NEW id, breaking the chain. | Every destructive verb registers its inverse (§3). |
| 7 | **Grep-and-mutate** | a `gtd inbox \| grep -iE "..."` topic filter fed directly into `gtd done`; one ambiguous token matched two unrelated items, closed 541ms apart. | Discovery and targeting are separate steps; destructive calls take validated ids (§4.1). |
| 8 | **Validate-the-action, trust-the-object** | `plan.plan_actions` checks the action against the catalog, never the object (`plan.py:26-46`); the proposer feeds the LLM app labels (`proposer.py:79-83`) and the guess reaches `fleet_act` unvalidated, raising at `fleet_adapter.py:172-173`. | Validate both halves of `(action, target)`; invalid target = per-item park + report, never a batch-aborting raise (§4.2). |

## 7. Per-store status (honest, as of 2026-08-14)

The three stores do the SAME job at three maturity levels. This table is the
gap analysis the epic closes; re-verify it when adopting.

| Requirement | coord CardStore | fleet object store | unified GTD |
|---|---|---|---|
| Append-only event log (§2.1) | YES: per-writer JSONL, flock, seq (`card_store.py:225-249`) | PARTIAL: `operatorActions` appended inside the spec (`fleet_adapter.py:175-186`); spec itself is versioned by generation | **NO**: flat lists mutated in place |
| Write-once creation (§2.1) | YES: `O_EXCL` core (`card_store.py:204-223`) | n/a (declared-state model) | NO |
| State = pure fold (§2.2) | YES: status only in fold (`:291-413`) | n/a: spec IS desired state | **NO**: `status` is a stored mutable field |
| Inverse verbs (§3) | YES: `reopen` (`:407`) | PARTIAL: reversible-actions catalog exists; no reversing event convention | **NO**: none; `done` is one-way |
| Lookup universe = write universe (§3) | YES | YES | **NO**: anti-pattern 2 |
| Lock discipline, all writers (§2.3) | YES | YES (`atomic_write_text`) | PARTIAL: shared `.gtd.lock` on main paths, two unlocked writers (anti-pattern 3) |
| Target validation (§4) | PARTIAL: fold rejects invalid transitions | **NO**: object name unvalidated (anti-pattern 8) | **NO** |
| Actor envelope (§1) | PARTIAL: `writer`+`node`+`seq` per event, but writer is an unresolved agent string | PARTIAL: `Writer(role, node, identity, agent_seat)` block on every spec | **NO**: zero actor fields |
| Signature + suite id (§5) | NO | SLOT + full machinery shipped, mode `off`, no `suite_id` (`signing.py`, `SKFLEET_SIGNING`); live `signature: null` | NO |
| Honest claims (§5) | YES | **NO**: the "SIGNED" overclaim | n/a (claims nothing) |
| Schema | pydantic `Card` (`skcoord/src/skcoord/card.py:50-72`) | dataclass `Writer` + spec conventions | **NO**: no model anywhere; two divergent item constructors (`gtd_tools.py:220-238` vs `gtd_ingest.py:251-266`, the latter flattening arbitrary `meta` keys onto the item); enums are bare module constants (`gtd_tools.py:28-49`); three naming axes for five files |

Evidence the un-enveloped store is already incoherent: of 5188 archived GTD
items, 3867 carry `archived_at` but only 1321 carry `completed_at`; the
majority was written by ad-hoc scripts no one can now identify. That is the
world this standard ends.

## 8. Compliance checklist (per store-owning repo)

- [ ] Every mutation record embeds the §1 envelope (`spe`, `actor.*`, `ts`,
      `action`, `target`, `sig` slot); `actor.id` comes from
      `capauth.resolve_agent_identity()`, never caller input.
- [ ] Mutations are append-only events; current state is a deterministic fold;
      no writer edits a stored status field.
- [ ] Event logs are per-writer files (Syncthing-merge-safe), flock-guarded,
      with a per-writer `seq`.
- [ ] Every destructive verb has a registered inverse that restores under the
      SAME id; archive is in the lookup universe.
- [ ] All writers share one store lock + atomic per-file writes; cross-file
      moves are write-then-delete; zero inline/unlocked writers (grep for
      bypasses in CI).
- [ ] Destructive entry points take validated ids; `(action, target)` both
      validated; invalid target = per-item refusal, never a batch abort.
- [ ] Signatures are detached over blanked-slot canonical bytes with a
      registry `suite_id`; roster local; rollout off -> permissive -> enforce;
      `pre-spe` records grandfathered, never backfilled.
- [ ] No §6 anti-pattern present; no doc or docstring claims "signed"/
      "verified" beyond what a wired verifier enforces.
- [ ] A CI completeness gate enumerates the store's write entry points and
      fails on any writer that does not produce a valid envelope (the
      route-coverage pattern from [SKWORLD_AUTHORIZATION_STANDARD](./SKWORLD_AUTHORIZATION_STANDARD.md) §3:
      a soak shows you mapped paths behaving; only enumeration shows you
      UNMAPPED paths existing).
- [ ] `doctor` reports envelope coverage (verified / unsigned / invalid /
      pre-spe counts) per store, so the claim "this store is attributable" is
      checkable on demand.

## Related standards

- [CRYPTOGRAPHY_STANDARD](./CRYPTOGRAPHY_STANDARD.md): which signature
  primitives, and the honest-claim rules §5 inherits.
- [CRYPTO_AGILITY_STANDARD](./CRYPTO_AGILITY_STANDARD.md): suite ids, wire
  tags, capability advertisement, and the roll-to-next mechanism the `sig`
  block rides on.
- [SKWORLD_AUTHORIZATION_STANDARD](./SKWORLD_AUTHORIZATION_STANDARD.md):
  who MAY act (the PDP). This standard records who DID act. The consent plane
  (`skcapstone/docs/specs/2026-08-13-unified-consent-plane-arch.md`) is the
  bridge: its `consent.granted` events are SPE-bearing events in these same
  stores.
- [OBSERVABILITY_AND_SCHEDULING_STANDARD](./OBSERVABILITY_AND_SCHEDULING_STANDARD.md):
  a failed mutation surfaces (run-ledger + failure-to-GTD + sk-alert), never
  silently skips the park.
- [TESTING_AND_CI_STANDARD](./TESTING_AND_CI_STANDARD.md): the completeness
  gate and "tests are evidence" for every checklist claim.

---

*License: Apache-2.0. Part of [sk-standards](../README.md); the skstacks copies
carry a "canonical home" pointer back here.*
