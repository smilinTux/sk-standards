# ADR-0004: bucket is the ceiling, preference narrows only

**Status:** Accepted
**Date:** 2026-08-27
**Deciders:** Chef, Lumina
**Extends:** [`ADR-0002`](./ADR-0002-two-coding-lanes.md), [`IDENTITY_NAMING_STANDARD`](../standards/IDENTITY_NAMING_STANDARD.md) (rejected-option precedent)
**Purpose:** record the routing-layer decision that family is a preference, not a third bucket axis, and enforce the constraint that a bucket is the absolute ceiling that preference can never exceed.

## Context

Chef requested family-scoped buckets (codex L/M/S, claude, kimi, glm, plus a free tier) so the orchestrator can pick a close enough model while staying relatively white-labeled. The question was whether to add a third axis to the bucket grammar or implement a preference layer.

The existing bucket grammar is `sk-<class>-<sensitivity>`, implemented byte-for-byte in two places:

- `skgateway/src/policy/buckets.mjs`: the gateway's bucket resolver
- `skharness/src/skharness/autocode/buckets.py`: the sending-side validation

Any grammar change is a lockstep two-repo wire-format break that requires coordinated releases. More fundamentally, adding a third axis conflates two different kinds of constraints:

- `model_class` and `sensitivity` are CONSTRAINTS that determine eligibility
- `family` is a PREFERENCE that orders or filters within eligible members

Constraining and preferring are different operations. A constraint narrows the allowed set. A preference orders what remains but must never widen the set. If the preferred family is absent, a preference must fall back rather than reach outside the ceiling.

## Decision

### Rejected option: third grammar axis

**Rejected:** `sk-<class>-<sensitivity>-<family>`

**Reasons rejected:**

1. **Wire-format lockstep.** The bucket grammar is byte-for-byte mirrored in `skgateway/policy/buckets.mjs` and `skharness/autocode/buckets.py`. Changing it from two axes to three is a lockstep two-repo wire-format break that requires coordinated releases and creates a backward-compatibility cliff.

2. **Permanently empty buckets.** The combinatorics are 4 classes × 3 sensitivities × 6 families = 72 bucket ids. The current 12-bucket design already has `sk-xl-secret` empty at 12. Adding a third axis multiplies the empty-bucket problem: most of those 72 ids would never be populated because `sk-xl-secret-codex` is a request we will never route and `sk-s-public-kimi` is redundant with `sk-s-public`.

3. **Conflates constraint with preference.** Class and sensitivity are CONSTRAINTS (a model MUST meet the floor and MUST NOT exceed the trust zone). Family is a PREFERENCE (we would LIKE this model family if it exists). Putting all three in one token treats them identically, which is wrong: a constraint that fails should produce a 503, but a preference that fails should fall back to cost-ranked selection within the ceiling. Three questions in one token is three separate rules wearing one mask, and that is how enforcement erodes.

### Accepted decision: bucket is the ceiling, preference narrows only

The bucket remains `sk-<class>-<sensitivity>` and resolves exactly as today. The bucket is the absolute ceiling on both capability and trust. An optional preference layer reorders or filters WITHIN the resolved member set and can never reach outside it.

**Core rules:**

1. **Bucket is the ceiling.** `resolveBucket()` admits only models that meet the `model_class` floor and the `sensitivity` trust zone ceiling. Nothing that happens later can add a model that failed this gate.

2. **Preference operates within members only.** A preference parameter (e.g., `family: claude`) is applied AFTER `resolveBucket()` returns. It may reorder or filter the members list, but it must never add models that were not already admitted.

3. **No widening on fallback.** If the preferred family has zero members in the bucket, the preference falls back to cost-ranked selection among the admitted members. It does NOT widen the bucket or relax the ceiling to include a member of the preferred family that failed the floor or ceiling check.

4. **Sensitivity is never consulted by preference.** The preference layer never reads or modifies the job's sensitivity. Sensitivity determines the ceiling via `resolveZoneCeiling()` in `sensitivity.mjs`, and that ceiling is final. Preference only cares about family membership among already-eligible models.

5. **Free is constrained, not just labelled.** From `sensitivity.mjs`:

   > Free is not a discount, it is a different payment method, and the payment is the data. Verified 2026-08-15 from provider terms, nvidia, openrouter and opencode all train on submitted content, while Anthropic's commercial terms prohibit training on Customer Content.

   Therefore, `prefer: free` is legal ONLY at `sensitivity: public`. It is never legal at `internal` or `secret`, regardless of whether a free-tier model exists in the bucket. The free tier is not a cost preference; it is a trust-zone decision.

6. **Two ladders stay separate.** The cost ladder (`local < free-remote < paid-cloud`) measures cheapness. The trust ladder (`SOVEREIGN_LOCAL < PAID_CONTRACTUAL < FREE_REMOTE`) measures where data may go. Both are correct about different questions and both stay. From `sensitivity.mjs`:

   > Both ladders are correct about different questions and both stay. Do not "reconcile" them.

   Preference may use cost as a tiebreaker, but it must never use cost to override trust.

7. **Callers name families, not model ids.** The preference parameter accepts a family identifier (e.g., `claude`, `codex`, `kimi`, `glm`), not a specific model id like `claude-3.5-sonnet`. This keeps model ids swappable and prevents callers from pinning a vendor SKU. The orchestrator decides which specific id within the family to use, based on current cost and availability.

## Consequences

### Positive

- No wire-format break. The bucket grammar stays stable across `skgateway` and `skharness`.
- No bucket explosion. 12 buckets instead of 72, all of which are actually useful.
- Constraints and preferences are clearly separated. The bucket layer handles constraints (capability floor, trust zone ceiling). A separate preference layer handles soft selection (family affinity, cost ordering).
- Free-tier safety is explicit. `prefer: free` is gated to `sensitivity: public` by design, not by accident.
- The two-ladder separation is codified. Cost and trust are independent axes, and no code path "reconciles" them.

### Constraints

- Preference must never add a model that `resolveBucket()` rejected. The preference input is the `members` array that `resolveBucket()` returns, never the full catalog.
- `prefer: free` at `sensitivity: internal` or `secret` is a validation error, not a fallback. The caller must either change sensitivity to `public` or remove the free preference.
- Family names are a bounded enum, not free text. Only recognized families are accepted; an unknown family is a validation error, not a silent no-op.
- Model ids are never accepted as preferences. This prevents SKU pinning and keeps the orchestration layer in control of specific model selection.

## Related

- [`ADR-0002`](./ADR-0002-two-coding-lanes.md) (two coding lanes, shared routing layer)
- [`IDENTITY_NAMING_STANDARD`](../standards/IDENTITY_NAMING_STANDARD.md) (rejected-option precedent: recording what was overruled and why)
- `skgateway/src/policy/buckets.mjs` (bucket resolver, ceiling enforcement)
- `skgateway/src/policy/sensitivity.mjs` (trust zone ceilings, free-tier constraint)
- `skharness/src/skharness/autocode/buckets.py` (sending-side bucket validation)

