# Inference Federation Standard

**Status:** Ecosystem standard for every estate running an inference gateway.
Companion to [`SITE_AND_HOST_NAMING_STANDARD`](./SITE_AND_HOST_NAMING_STANDARD.md)
(which defines estates and bridge nodes),
[`SKWORLD_AUTHORIZATION_STANDARD`](./SKWORLD_AUTHORIZATION_STANDARD.md),
and [`OBSERVABILITY_AND_SCHEDULING_STANDARD`](./OBSERVABILITY_AND_SCHEDULING_STANDARD.md).

**Why:** Estates want to pool spare GPU capacity. They emphatically do not want to
pool their credit cards. Those two facts pull in opposite directions through the
same piece of software, because one gateway process holds both the donated local
models and the paid API keys. Without a rule, the natural implementation quietly
lets one estate's subscription fund everyone's usage, with no per-estate
accounting and no way to notice. This standard fixes the separation, and says how
capacity is pooled without also pooling spend, trust, or blast radius.

---

## The two lanes

Every estate's gateway carries two kinds of upstream, and they are governed
differently. This is the whole standard in one table; everything below is
consequence.

| | **Subscription lane** | **Pool lane** |
|---|---|---|
| What | Paid third-party APIs | Donated local inference |
| Examples | OpenAI, Anthropic, z.ai | A member's idle GPU box |
| Credentials | Paid keys live here | **None, ever** |
| Scope | Estate-private | Federated across estates |
| Billed to | The estate that holds the key | Nobody |
| Failure mode if confused | One estate silently funds everyone | Wasted cycles, nothing more |

1. **The pool lane MUST hold no paid API credentials.** Not a key, not a token,
   not a credentials file, not an inherited environment variable. A gateway
   reachable by a peer estate and holding a paid key means that peer can spend
   money that is not theirs, invisibly, with no per-estate accounting and no
   receipt. This is
   [`SITE_AND_HOST_NAMING_STANDARD` rule 24](./SITE_AND_HOST_NAMING_STANDARD.md)
   (shared names are fine, shared credentials never) applied to the one place it
   costs real money.
2. **Subscriptions stay on the estate-local gateway**, where the billing
   relationship already lives. An estate's paid capacity is never a pool
   contribution. If an estate wants to donate paid capacity, it donates the
   *output* through some deliberate mechanism, never by exposing the key.
3. **A gateway serving the pool lane SHOULD NOT be the same process serving the
   subscription lane.** Separate processes make rule 1 a deployment property
   rather than a configuration promise, so a mistake in a config file cannot
   expose a key that the process never loaded.

---

## Topology: mesh, because priority is a local decision

The obvious design is one shared pool gateway that every estate points at. Reject
it.

4. **Estates federate inference peer to peer, not through a central pool.** Each
   estate's gateway adds each peer's gateway as an upstream. The peer's gateway
   **is** its bridge node under
   [`SITE_AND_HOST_NAMING_STANDARD` rules 16 to 19](./SITE_AND_HOST_NAMING_STANDARD.md):
   user-owned, enumerated in the registry, carrying one application-layer exchange
   (inference) and no general reachability.

**The decisive reason is that routing preference is a local policy decision.** An
estate almost always wants to exhaust its own GPU before spending a peer's. Under
a central pool that ordering is set by whoever runs the pool. Under a mesh each
estate keeps its own:

```
  chef's gateway      priority 1   own GPU
                      priority 2   cakjr bridge
                      priority 3   greg bridge

  greg's gateway      priority 1   own GPU
                      priority 2   chef bridge      different order,
                      priority 3   cakjr bridge     same pool
```

Three secondary reasons: no single estate hosts and powers everyone else's
coordination point, there is no single point of failure for the whole community,
and it introduces no new concept because the bridge-node rules already cover the
transport.

The cost is `N-1` upstreams per estate rather than one. At three estates that is
two entries in a config file.

---

## Membership is static; availability is runtime

The instinct for a voluntary pool is dynamic registration: a box joins when it is
idle and leaves when its owner starts gaming. Resist it.

5. **Pool members MUST be declared statically in gateway configuration**, and a
   member that is powered off, busy, or unreachable MUST be handled by the
   gateway's health and quarantine layer rather than by removing it from config.

Two reasons, one architectural and one mechanical.

Architecturally, "is this box up right now" is a runtime question and belongs to
the runtime. A health layer already answers it continuously, for every backend,
without anybody editing anything. Encoding it in config means a human or a script
has to know something the gateway is already measuring.

Mechanically, in the reference implementation adding or removing a backend
requires a **full gateway restart**, not a config reload: the router's backend map
is built once at startup and the reload path refreshes only the config snapshot.
So dynamic membership would bounce the gateway, for every consumer, every time any
contributor's box changed state. A static declaration plus quarantine gives the
same behaviour with no restarts at all.

6. **A contributor declares its own admission ceiling**, because only the
   contributor knows the hardware. Ceilings are a property of the serving box (a
   `llama-server --parallel 4` genuinely cannot take a fifth concurrent request),
   not a throttle to be guessed by the consumer.

---

## Authorization

7. **A pool request is an authorization decision like any other.** The gateway is
   a Policy Enforcement Point and MUST run the
   [`SKWORLD_AUTHORIZATION_STANDARD` section 1](./SKWORLD_AUTHORIZATION_STANDARD.md)
   lifecycle: classify route, authenticate, resolve subject from the credential
   only, map to a capability, decide against the one PDP, emit the audit
   obligation. A gateway that accepts a peer's traffic because it arrived on the
   bridge interface has authenticated the *network*, not the *caller*.
8. **Cross-estate inference REQUIRES the peer estates' trust roots to be
   established first.** Until each estate has its own PGP primary key and a
   resolvable operator segment, a cross-estate capability grant has nothing to
   verify against. This is a hard ordering constraint: the pool cannot ship
   before the trust roots do.

---

## Third-party aggregators and the three kinds of "free"

Projects like OmniRoute (MIT, TypeScript, a standalone service fronting hundreds
of providers) are attractive for reach and for cost features an estate gateway may
not have. The MIT licence means the good ideas can be taken directly, with
attribution, which is usually the better move than adopting the whole service.

9. **An aggregator MAY be adopted as a BACKEND behind the estate gateway. It MUST
   NOT replace it.** The estate gateway is the PEP, the sanitizer and the
   admission controller, and those responsibilities are defined by other standards
   here. An aggregator reaches many providers; it is not a policy decision point
   and does not know the estate's authorization model.
10. **An aggregator MUST live on the subscription lane only, never the pool
    lane.** It exists to reach third-party APIs, precisely the traffic rule 1
    keeps away from peers. Estate-local also keeps its blast radius inside one
    estate.

### "Free" is three different things, and only two are allowed

A catalogue advertising "150+ free providers" is aggregating three categories with
nothing in common but the price. They MUST be treated separately.

| Class | What it is | Disposition |
|---|---|---|
| No-auth endpoints | Genuinely open, no credential | **Allowed**, subject to data class below |
| Free tiers | A real account's free allowance (OAuth or API key) | **Allowed**, subject to data class below |
| Web-session replay | Your logged-in browser cookie replayed against a consumer web UI | **Forbidden** |

11. **Web-session-replay providers MUST NOT be enabled.** Pasting a
    browser storage-state or cookie header so a gateway can impersonate your
    logged-in session against a consumer web UI breaches those services' terms,
    and the credential at risk is a **real personal account**, not an API key with
    a spending cap. The blast radius of a ban is the human's account, not the
    estate's budget. Aggregators that carry these typically flag them (OmniRoute
    marks each with `subscriptionRisk: true`); that flag is a reason to exclude
    the class, not a disclosure that makes it acceptable.

### Free tiers are paid for in data, so route by data class

12. **Eligibility for a free tier is decided by the DATA CLASS of the request, never
    by cost.** Free tiers are generally free because the provider reserves the
    right to train on submitted content. For an ecosystem whose entire thesis is
    sovereign memory and private state, routing the wrong content through one
    inverts the point of the estate.

    | May use free tiers | MUST NOT |
    |---|---|
    | Already-public corpus text | Agent memory, soul files, journals |
    | Throwaway classification and triage | Client work and anything under an engagement |
    | Public-document summarisation | Personal data about the operator or third parties |
    | Non-sensitive scratch generation | Anything covered by a confidentiality obligation |

    A gateway that routes purely on cost or availability **will** eventually send
    private state to a free tier, because nothing in a cost-ranked router knows
    what the payload is. The data class MUST therefore be carried on the request
    and enforced at the gateway, not left to the caller's discretion.

### What is worth taking

13. **Cost-tier fallback laddering** (subscription, then paid API, then cheap,
    then free) is a sound routing pattern and SHOULD be adopted, bounded by
    rule 12: the ladder never crosses into a free tier for a request whose data
    class forbids it.
14. **Per-provider quota tracking with automatic rotation on exhaustion** is the
    feature that makes many small free allowances usable in aggregate. Individually
    each free tier is too small to matter; tracked and rotated, they add up. This
    is the genuinely valuable engineering in an aggregator and is worth
    reimplementing natively.
15. **Ranking free providers by independent model-quality scores** rather than
    treating "free" as one undifferentiated bucket is worth copying. Joining a
    provider catalogue against crowd-sourced ELO scores answers "which free
    provider gives the best model" instead of "which free provider answered
    first", and a free frontier model is worth far more than a free legacy one.
16. **Vendor performance claims MUST be measured locally before being relied
    upon.** Compression ratios and cost savings are the vendor's numbers on the
    vendor's workloads. This is the
    [`TESTING_AND_CI_STANDARD`](./TESTING_AND_CI_STANDARD.md) "tests are evidence
    for claims" rule applied to a dependency's marketing.

**Supply-chain note.** A fast-moving upstream in the inference request path is a
real risk: high release cadence, a large dependency surface, and youth all argue
for confining it to one lane in one estate, where a bad release degrades that
estate's third-party access and touches nothing federated. That confinement is
what makes adopting it a bounded decision. Reimplementing a good idea natively
(rules 13 to 15) carries no such risk at all, which is usually the better trade.

---

## Accounting

17. **Donated capacity SHOULD be recorded**, at minimum as requests served and
    tokens produced per contributing estate, through the existing SKJoule ledger
    rather than a parallel store.

This is deliberately a SHOULD, not a MUST. At three estates an informal pool works
and instrumentation is overhead. But a pool with no record of who contributed
versus who consumed has exactly one long-run failure mode, and it is not technical:
one member quietly carries everyone until they stop. The record is what makes that
visible early enough to talk about, so it is worth adding before it is needed
rather than after somebody is annoyed.

---

## Compliance checklist

- [ ] No paid credential is reachable from any pool-lane gateway.
- [ ] Subscription and pool lanes are separate processes, or the exception is written down.
- [ ] Each estate's gateway sets its own upstream priority order.
- [ ] Pool members are declared statically; availability is left to health and quarantine.
- [ ] Each contributor set its own admission ceiling from its actual hardware.
- [ ] Cross-estate requests are authorized against the PDP, not accepted on network position.
- [ ] Peer trust roots exist before any cross-estate inference is enabled.
- [ ] Any third-party aggregator is a backend, on the subscription lane, with its claims measured locally.
- [ ] No web-session-replay provider is enabled anywhere.
- [ ] Every request carries a data class, and free-tier eligibility is enforced from it at the gateway.
- [ ] No cost-ranked fallback can route private state to a free tier.
