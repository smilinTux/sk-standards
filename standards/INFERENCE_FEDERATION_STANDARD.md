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
3. **Distinguish subscription-BOUND upstreams from API-key upstreams.** Both are
   estate-private, but for different reasons, and only one of them blocks a new
   estate from standing itself up:

   | | Provisioning | Effect on a new estate |
   |---|---|---|
   | **Subscription-bound** | Requires a **human login in that estate**. Cannot be provisioned remotely, and one machine owns the refresh. | **Blocks bootstrap.** The operator must sit down and log in. |
   | **API key** | Copy the key. Not machine-bound. | Trivial. Hand it over and go. |

   Anthropic (via `claude --print` through claude-code-api) and Codex (`codex
   login` on one host, with the credential file synced read-only to others) are
   subscription-bound. OpenRouter and similar are keys.

   This is the line that matters when bootstrapping a peer estate. A plan that
   treats "estate-private" as one category will assume a new estate can be handed
   its inference access remotely, and it cannot: the subscription-bound half needs
   a person in front of a browser, in that estate, before it works at all.
4. **A gateway serving the pool lane SHOULD NOT be the same process serving the
   subscription lane.** Separate processes make rule 1 a deployment property
   rather than a configuration promise, so a mistake in a config file cannot
   expose a key that the process never loaded.

---

## Topology: mesh, because priority is a local decision

The obvious design is one shared pool gateway that every estate points at. Reject
it.

5. **Estates federate inference peer to peer, not through a central pool.** Each
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

6. **Pool members MUST be declared statically in gateway configuration**, and a
   member that is powered off, busy, or unreachable MUST be handled by the
   gateway's health and quarantine layer rather than by removing it from config.

Two reasons, one architectural and one mechanical.

Architecturally, "is this box up right now" is a runtime question and belongs to
the runtime. A health layer already answers it continuously, for every backend,
without anybody editing anything. Encoding it in config means a human or a script
has to know something the gateway is already measuring.

Mechanically, in the **Node `skgateway` implementation specifically**, adding or
removing a backend requires a **full gateway restart**, not a config reload.

`_routerBackends` is a `const` assembled once at module scope, executed at import,
and handed to `createRouter()` there. The SIGHUP path (`_cfgEmitter.on("config-changed", ...)`)
does three things: it `Object.assign`s the fresh config over the snapshot and
rebuilds the two authenticators. It never re-reads `config.backends`, never
rebuilds `_routerBackends`, and never calls `createRouter()` again.

It is worse than "the router is not rebuilt". The router holds a **shallow copy**
of each backend (`{ ...b }`) taken at boot, so even the object identity is severed
from the reloaded config. **And the failure is silent:** a SIGHUP after editing
`backends` leaves the router serving the boot-time set, with no error and no log
line saying it ignored you. That silence is what makes it a hazard rather than an
inconvenience.

*Cited by symbol, not by line.* Three separate readings of this file during
drafting produced three different line numbers, and the file had not changed:
it was byte-identical across every commit involved. Both wrong readings came from
a working tree rather than a commit, one stale and one dirty while an edit was in
flight. **A working tree is not a commit, and a line number does not record which
one it came from.** That is why the rule is to cite by symbol: it survives a
rebase, a dirty tree, a wrong branch, and a deployed copy alike, none of which a
line number survives, and only one of which a careful reader would think to check.

So dynamic membership would bounce the gateway, for every consumer, every time any
contributor's box changed state. A static declaration plus quarantine gives the
same behaviour with no restarts at all.

### Hazard: "skgateway" names four different things

That restart rule is a property of one codebase, not of the name. Verify which
implementation you are reasoning about before applying any statement about
gateway behaviour, because the fleet currently runs this (measured 2026-09-02):

| Endpoint | What it actually is |
|---|---|
| `noroc2027:18780` | The Node repo. This is "skgateway". |
| `chiap01:18790` | The Node repo again, a staged codex instance from a separate checkout. |
| `chiap04:18780` | **`skgateway-chi`**: a single 9KB Python uvicorn app, self-identifying under that name in `/health`, sharing nothing with the Node repo but the word. Its directory **is not a git working tree** on that host, and it binds `127.0.0.1` only, so it is invisible to a tailnet probe and looks "down" rather than loopback-scoped. |
| `chiap01:/opt/skgateway` | The Node repo, clean but detached and behind `main`, with nothing running from it. A deploy trap. |

7. **Any rule about gateway behaviour MUST name the implementation it describes.**
   A statement scoped to "skgateway" is wrong in at least three places in the
   current fleet. A single-file service answering on the same port under the same
   name is the worst case: nothing about the Node implementation's behaviour can
   be assumed of it.

   Stated precisely, because the distinction matters: what was observed is that
   the running host's copy is **not in a git working tree**. That is not the same
   as "nobody manages it". Something upstream may generate or deploy it, and that
   was not checked. The actionable point stands either way: whatever governs that
   file, it is not the Node repository, so no statement about the Node repository
   describes it.

8. **A contributor declares its own admission ceiling**, because only the
   contributor knows the hardware. Ceilings are a property of the serving box (a
   `llama-server --parallel 4` genuinely cannot take a fifth concurrent request),
   not a throttle to be guessed by the consumer.

---

## Authorization

9. **A pool request is an authorization decision like any other.** The gateway is
   a Policy Enforcement Point and MUST run the
   [`SKWORLD_AUTHORIZATION_STANDARD` section 1](./SKWORLD_AUTHORIZATION_STANDARD.md)
   lifecycle: classify route, authenticate, resolve subject from the credential
   only, map to a capability, decide against the one PDP, emit the audit
   obligation. A gateway that accepts a peer's traffic because it arrived on the
   bridge interface has authenticated the *network*, not the *caller*.
10. **Cross-estate inference REQUIRES the peer estates' trust roots to be
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

11. **An aggregator MAY be adopted as a BACKEND behind the estate gateway. It MUST
   NOT replace it.** The estate gateway is the PEP, the sanitizer and the
   admission controller, and those responsibilities are defined by other standards
   here. An aggregator reaches many providers; it is not a policy decision point
   and does not know the estate's authorization model.
12. **An aggregator MUST live on the subscription lane only, never the pool
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

13. **Web-session-replay providers MUST NOT be enabled.** Pasting a
    browser storage-state or cookie header so a gateway can impersonate your
    logged-in session against a consumer web UI breaches those services' terms,
    and the credential at risk is a **real personal account**, not an API key with
    a spending cap. The blast radius of a ban is the human's account, not the
    estate's budget. Aggregators that carry these typically flag them (OmniRoute
    marks each with `subscriptionRisk: true`); that flag is a reason to exclude
    the class, not a disclosure that makes it acceptable.

### Free tiers are paid for in data, so route by data class

14. **Eligibility for a free tier is decided by the DATA CLASS of the request, never
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

15. **Cost-tier fallback laddering** (subscription, then paid API, then cheap,
    then free) is a sound routing pattern and SHOULD be adopted, bounded by
    rule 12: the ladder never crosses into a free tier for a request whose data
    class forbids it.
16. **Per-provider quota tracking with automatic rotation on exhaustion** is the
    feature that makes many small free allowances usable in aggregate. Individually
    each free tier is too small to matter; tracked and rotated, they add up. This
    is the genuinely valuable engineering in an aggregator and is worth
    reimplementing natively.
17. **Ranking free providers by independent model-quality scores** rather than
    treating "free" as one undifferentiated bucket is worth copying. Joining a
    provider catalogue against crowd-sourced ELO scores answers "which free
    provider gives the best model" instead of "which free provider answered
    first", and a free frontier model is worth far more than a free legacy one.
18. **Vendor performance claims MUST be measured locally before being relied
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

19. **Donated capacity SHOULD be recorded**, at minimum as requests served and
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
- [ ] Subscription-bound upstreams are distinguished from API-key ones in any bootstrap plan.
- [ ] Every statement about gateway behaviour names the implementation it describes.
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
