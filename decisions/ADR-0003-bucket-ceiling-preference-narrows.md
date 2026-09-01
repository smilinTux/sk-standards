# ADR-0003: Bucket is the ceiling, preference narrows only

**Status:** Accepted
**Date:** 2026-08-26
**Deciders:** Chef, Lumina
**Extends:** None
**Purpose:** record the routing shape selected before family and cost preference
implementation begins, without defining a routing standard or claiming shipped
behavior.

## Context

Family-scoped model selection was requested so callers could prefer families
such as codex, claude, kimi, or glm, plus a free option, without pinning a
vendor model identifier.

The existing bucket address combines model class and sensitivity. Its grammar
is mirrored byte for byte in skgateway `src/policy/buckets.mjs` and skharness
`src/skharness/autocode/buckets.py`.

## Decision

The bucket remains the ceiling and resolves as it does today. An optional
preference only reorders or filters models within the resolved member set. It
does not reach outside that set. When the preferred family is absent, selection
falls back to cost-ranked selection within the same set rather than widening
the bucket. Preference neither consults nor modifies sensitivity.

Callers name families rather than model identifiers. This keeps model
identifiers swappable beneath the family preference.

Free preference is confined to public sensitivity. The source for this choice
is skgateway `src/policy/sensitivity.mjs`, lines 22 through 30, which records
provider terms verified on 2026-08-15 and states: "Free is not a discount, it
is a different payment method, and the payment is the data."

The cost and trust ladders remain separate. Cost measures cheapness and prefers
free remote service over paid cloud service. Trust measures where data can go
and ranks free remote service worst because the cited providers train on
submitted content. The same source states that both ladders are correct about
different questions and says not to reconcile them.

## Rejected option

The rejected option was a third bucket grammar axis:
`sk-<class>-<sensitivity>-<family>`.

It was rejected for three reasons:

1. The grammar is mirrored byte for byte across skgateway and skharness, so the
   change would require a lockstep two-repository migration with a wire-format
   break between versions.
2. Four classes by three sensitivities by six families produces 72 bucket
   identifiers, most of them permanently empty. `sk-xl-secret` is already empty
   with the current 12 identifiers.
3. Class and sensitivity are constraints, while family is a preference. Putting
   all three questions in one token creates a path for preference to widen a
   safety ceiling.

## Consequences

The bucket grammar stays on its two existing axes. Family and cost preference
remain a separate narrowing layer. A routing standard can describe the behavior
after the related implementation ships with its evidence; this ADR does not do
so and claims no check.
