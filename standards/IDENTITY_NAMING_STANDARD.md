# Identity Naming Standard (the fqid Grammar)

**Status:** ACTIVE (ratified 2026-08-14, card `b11144cd`)
**Date:** 2026-08-14
**Author:** Claude, session agent (epic `9e6d548f`)
**Ratified by:** Chef, via the architecture review that overruled the proposed local/federated split (see §3)
**Extends:** [PROVENANCE_AND_MUTATION_STANDARD](./PROVENANCE_AND_MUTATION_STANDARD.md) `actor.id`, `SKWORLD_AUTHORIZATION_STANDARD` subject matching

---

One grammar for every subject string a policy decision, a device record, or a
capability token ever matches on: the **fqid** (fully-qualified identity).
Every enrollment, every signature, every `actor.id` conforms to it, and
nothing downstream re-derives or re-normalizes it.

---

## The thesis

> **A subject is a spelling. Authorization matches spellings exactly. A
> grammar with more than one legal spelling per identity is a grammar that
> silently stops authorizing.**

The root cause this standard closes: an authorization decision function that
matches subjects by exact lowercased string is only as sound as its input
grammar is narrow. An internal audit of a live `sk*` deployment found device
and agent identities enrolled under several different subject shapes side by
side, some carrying a deprecated wire-protocol prefix, some missing a domain
suffix entirely, one built around a device fingerprint with no fixed prefix at
all. Every shape mismatch surfaces the same way: a fail-closed
"unknown subject, no enrolled device" deny that reads like a configuration
error rather than what it actually is, a naming defect. This standard defines
the one spelling every subject MUST use, so that "enrolled" and "matches" mean
the same thing everywhere.

---

## 1. Canonical grammar: normative schema

The subject is an email-shaped, ASCII, lowercase string, OR the one permitted
prefixed exception for device seats (row 5). The PGP primary-key fingerprint
is the ROOT identity; the subject string is a label BOUND to that key as a key
UID. **When the string and the key disagree, the key wins and enrollment is
refused.** A subject string with no bound key, or bound to a key other than
the one presenting it, is not a naming-format problem and this standard does
not relax it.

| Entity class | Canonical form | Example (placeholder operator) | Notes |
|---|---|---|---|
| Humans (sovereign roots) | `<name>@<org-domain>`, at the apex | `owner@example.org` | No operator segment. The apex sovereign root. |
| Agents (all: flagship and swarm alike) | `<agent>@<operator>.<org-domain>` | `agent-one@operator-a.example.org` | One shape for every agent tier; there is no separate swarm-vs-flagship grammar. |
| Services | `sk<name>@<operator>.<org-domain>` | `skgateway@operator-a.example.org` | The `sk` prefix keeps the local-part namespace disjoint from agents, so a service can never collide with an agent that happens to share its bare name. |
| Nodes | `<host>@<operator>.<org-domain>` | `host-1@operator-a.example.org` | ONLY when a node itself must be a policy-decision subject (e.g. a host-scoped capability grant). Otherwise a node stays a metadata field (`actor.node` in `PROVENANCE_AND_MUTATION_STANDARD` §1) and is never promoted to a subject of its own. |
| Device seats | `device:<fingerprint>` | `device:0a1b2c3d4e5f6789` | The ONE permitted prefixed class. Replaces every legacy `operator:<fp>` shape (§2.5). |

**Regex**, applied AFTER mandatory lowercasing and ASCII-only enforcement
(§2.2):

```
^(device:[0-9a-f]{16,64}|[a-z0-9][a-z0-9-]{0,62}@(?:[a-z0-9][a-z0-9-]{0,62}\.)*example\.org)$
```

The `example.org` tail is this document's placeholder (RFC 2606 reserves it
for exactly this purpose). A deploying operator substitutes its own
registered apex domain and the grammar generalizes unchanged: the tail is a
single fixed literal per deployment, never a wildcard, never operator-chosen
per subject.

---

## 2. Normative rules

1. **fqid is canonical.** The email-shaped form in §1 is the ONLY form a
   policy-decision subject or a device record MAY store. Any secondary URI
   form (e.g. a `capauth:` scheme wrapping the same local-part) is a
   DEPRECATED wire alias. It MUST NOT appear in a policy-decision subject or
   a device record, and the prefix MUST be stripped by the §2.4 validator
   before the value is ever stored or compared. Migration off the deprecated
   form follows the same dual-stack-window discipline as
   `CRYPTO_AGILITY_STANDARD` §3: legacy shapes are accepted at ingest,
   translated through the closed alias table (§2.5), and stored canonically;
   nothing downstream ever sees the deprecated shape again.

2. **ASCII only. Non-ASCII input is REJECTED, never folded.** Unicode
   normalization (NFKC or similar) at a security boundary is itself the
   attack surface: two visually identical strings that normalize to the same
   ASCII value are exactly the homograph and confusable-character attack
   this rule exists to close. Rejecting an out-of-grammar identity is safe
   (the enrollment fails loudly and the operator picks an ASCII label);
   folding it in is not, because folding hides the substitution instead of
   refusing it.

3. **Reject trailing dots and empty labels.** A domain of the form
   `operator..example.org` or `operator.example.org.` (trailing dot) MUST be
   refused by the same validator, not silently squashed. An empty label is
   evidence of a malformed caller, not a spelling variant to normalize past.

4. **Normalization happens in exactly ONE validator.** A single function
   (the canonical normalizer for the deployment, referred to below as
   `canonical_subject()`) performs lowercasing, ASCII enforcement, and regex
   validation, and it is called at exactly two points: ingest (when a record
   is first written) and enrollment (when a key UID is bound). It is NEVER
   called inside the authorization decision function. The decision function
   stays a pure exact matcher over already-canonical strings, with no
   normalization logic of its own, so that "what got enrolled" and "what
   gets matched" can never drift apart by a code path that normalizes
   differently in the two places.

5. **Any alias mapping MUST be a closed, enumerated table, never an
   algorithmic rewriter.** A finite table is auditable: every legacy shape it
   accepts, and what it becomes, is readable in one sitting and covered by a
   test per row. An open-ended normalization function is not auditable in
   the same way, because its behavior on the NEXT unseen shape is a property
   of the algorithm, not a property anyone reviewed. Illustrative example
   (not the literal enrolled table of any deployment):

   | Legacy shape seen at ingest | Canonical result | Disposition |
   |---|---|---|
   | `operator:<fingerprint>` | `device:<fingerprint>` | Aliased: prefix rewritten, value preserved. |
   | `capauth:<subject>` (deprecated wire form) | `<subject>` | Aliased: prefix stripped per §2.1, nothing else changes. |
   | `<name>@<operator>` (no TLD, domain suffix missing) | `<name>@<operator>.<org-domain>` | Aliased ONLY under a section 2.6 migration entry: one enumerated domain, dated, with a removal date. Absent such an entry: REJECTED, not aliased. A missing domain is not a spelling variant of a valid identity. |

### 2.6 Migration aliases: dated, enumerated, and removable

An alias table row exists to move a deployment OFF a legacy shape, not to bless
it. Section 2.5's first two rows are permanent translations of retired
*prefixes*, where the identity is unambiguous and nothing is lost. A missing
*domain* is different: it is genuinely ambiguous in general, which is why the
default is rejection.

But a deployment that already stored thousands of records under the legacy shape
cannot reject its way out in one step: flipping to rejection makes every stored
record unresolvable at once. That is a migration, and this standard should say
how to run one rather than leaving each component to improvise.

A **migration alias** MAY collapse a missing domain if and ONLY if all of:

1. **Enumerated, never inferred.** The alias names ONE literal legacy domain and
   its one canonical result. No pattern, no "add the org TLD" heuristic. The next
   unseen shape must not be silently repaired. This keeps the auditability
   property section 2.5 exists to protect.
2. **Dated, with a removal date in the entry itself.** An alias with no end date
   is a second grammar wearing a migration costume.
3. **Paired with a migration.** The entry names the tool that rewrites stored
   records to canonical form, and that migration runs BEFORE the alias is removed.
4. **Write-canonical from the start.** New records are written canonically
   immediately. The alias only resolves what is already on disk; it never
   sanctions minting a new subject in the legacy shape.
5. **Recorded where it is implemented.** The implementing component states the
   entry, its removal date, and its migration tool in its own SECURITY.md or SOP,
   so the exception is visible to the people it affects.

An alias satisfying all five is compliant. One that does not is a second grammar,
and section 2.5 rejects it.

> **Why this was added (2026-08-16).** The table said REJECTED while a live
> implementation aliased exactly this shape for one operator domain, and the
> divergence went unnoticed because both sides read the same section and drew
> opposite conclusions. The implementation was right about the need and wrong to
> do it unilaterally; the table was right about the default and silent about
> migration. This section closes that gap in the direction the standard already
> takes twice above: a finite, reviewable table entry.

6. **Sovereign-versus-federated is a POLICY attribute, never a suffix.** No
   subject spelling encodes deployment status. See §3 for why a suffix-based
   split (`.local` vs. federated) was proposed and rejected, so it is not
   re-proposed against a slightly different token next time.

---

## 3. Rejected alternative: the local/federated suffix split

An earlier proposal in the same design review suggested giving sovereign
(non-federated) identities a distinct suffix, e.g. a `.local` tier separate
from the federated `<org-domain>` tier. It was overruled, on the following
grounds, which are recorded here so the same proposal does not recur against
a differently-spelled suffix:

1. **An identity must never change spelling when its deployment status
   changes.** Authorization matches subjects by exact lowercased string
   (§2.4). Promoting an identity from sovereign to federated under a
   two-form scheme means every device record and every capability token that
   already reference the old spelling silently stop matching the moment the
   promotion happens. A two-form scheme builds that failure mode in
   permanently; there is no version of it that does not eventually strand a
   live record.

2. **The operator tier already provides the isolation the local tier was
   for.** `agent-one@operator-a.example.org` cannot collide with
   `agent-one@operator-b.example.org`. A second tier for "this identity is
   not federated yet" adds no isolation the operator segment does not
   already give.

3. **`.local` is mDNS-reserved (RFC 6762), and this ecosystem ships an mDNS
   discovery backend**, so a `.local`-suffixed identity tier collides with a
   protocol the stack already speaks. Compounding it, existing tooling
   already treats a `.local`-suffixed placeholder as the marker for a FAKE
   identity to be banned outright. Overloading `.local` to mean both "fake,
   ban this" and "real, sovereign, keep this" in the same codebase is a
   standing trap, independent of which literal suffix string is chosen.

4. **Keying a tier to a product or deployment-mode name ages badly.** A
   suffix tied to today's product boundary (or today's notion of "not yet
   federated") has to be renamed or reinterpreted the moment that boundary
   is decomposed or the deployment topology changes, and a renamed suffix is
   exactly the spelling-change problem in reason 1, just with an extra step.

Sovereign-versus-federated remains fully expressible: as a field on the
enrollment record, or as an authorization-policy attribute keyed by the
already-canonical fqid, never as a second grammar.

---

## 4. Compliance checklist (per store or service that resolves subjects)

- [ ] Every stored subject matches the §1 regex exactly; no store persists a
      `capauth:`-prefixed or otherwise non-canonical value.
- [ ] Lowercasing, ASCII enforcement, and regex validation happen in exactly
      one shared validator, called at ingest and at enrollment, never inside
      the decision function (§2.4).
- [ ] The decision function is a pure exact matcher: no lowercasing, no
      trimming, no alias lookup inside it.
- [ ] Any accepted legacy shape is translated through a closed, enumerated,
      tested alias table (§2.5); no algorithmic or heuristic rewriter exists
      anywhere in the resolution path.
- [ ] Non-ASCII input is rejected with a clear error at ingest/enrollment;
      grep the codebase for any Unicode-normalization call (NFKC/NFC/etc.)
      touching a subject string and confirm it does not exist.
- [ ] No subject encodes sovereign-versus-federated status in its spelling;
      that status lives on the enrollment record or the policy, never in the
      local-part or domain.
- [ ] The key UID binding is checked at enrollment: a subject string with no
      bound key, or bound to a different key than the one presenting it, is
      refused regardless of whether the string itself matches the grammar.

---

## Related standards

- [PROVENANCE_AND_MUTATION_STANDARD](./PROVENANCE_AND_MUTATION_STANDARD.md):
  `actor.id` MUST carry the fqid form defined here, never the deprecated
  `capauth:` wire alias, never free text.
- `SKWORLD_AUTHORIZATION_STANDARD`: the decision function this standard keeps
  pure (§2.4); that standard governs who MAY act once the subject is
  resolved, this one governs how the subject is spelled.
- [CRYPTO_AGILITY_STANDARD](./CRYPTO_AGILITY_STANDARD.md): the dual-stack
  migration discipline (§2.1) that legacy-alias retirement follows.

---

*License: Apache-2.0. Part of [sk-standards](../README.md); the skstacks copies
carry a "canonical home" pointer back here.*
