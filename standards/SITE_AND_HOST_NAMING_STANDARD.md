# Site and Host Naming Standard

**Status:** Ecosystem standard for every SKWorld physical site and the hosts in it.
Companion to [`IDENTITY_NAMING_STANDARD`](./IDENTITY_NAMING_STANDARD.md),
[`PROVENANCE_AND_MUTATION_STANDARD`](./PROVENANCE_AND_MUTATION_STANDARD.md),
and [`ITIL_AND_RUNBOOK_OPERATING_MODEL_STANDARD`](./ITIL_AND_RUNBOOK_OPERATING_MODEL_STANDARD.md).

**Why:** SKWorld hostnames encoded geography (`nor`, `chi`) and then an increment
(`chi2`). Geography is the one property of a site most likely to change and least
likely to matter, and an increment is not a name at all: the moment you have
`chi2` you are one purchase away from `chi3`, and nothing in the estate says what
any of them are for. A site prefix appears in every hostname, mount path, CMDB CI
id, Syncthing device name and runbook in the fleet, so it is high-traffic
vocabulary that should carry meaning. This standard fixes the vocabulary and,
more importantly, fixes the rule that a site's **name** and a site's **addresses**
are separate things that change on separate schedules.

---

## Scope boundary: this is not the identity standard

[`IDENTITY_NAMING_STANDARD`](./IDENTITY_NAMING_STANDARD.md) governs the **fqid**
grammar for subjects of an authorization decision, where a node is
`<host>@<operator>.<org-domain>` and only when the node must itself be a policy
subject. That is the identity layer.

This standard governs the **hostname** that appears in the `<host>` position, plus
the site vocabulary above it. The two compose and do not compete:

```
  IDENTITY_NAMING_STANDARD    zioap01@chef.skworld.io
                              ^^^^^^^
  THIS STANDARD ------------- zioap01
                              zio  ap  01
                              site role index
```

A change here never changes an fqid's grammar. A change there never renames a host.

---

## The rule

1. **A site name MUST answer "what is this place" before "where is it."** Geography
   MAY appear in a site's metadata. It MUST NOT be the site's name.
2. **Site codes are drawn from one closed, enumerated vocabulary** held in the site
   registry. Codes are exactly three ASCII-lowercase characters, occupying the
   site slot of `<site:3><role:2><index:4>`.
3. **A site code MUST be claimed in the registry before first use.** Claiming is
   what stops two sites racing for a prefix, and what stops a code being spent on
   something trivial.
4. **A site's NAME and its ADDRESSES change on separate schedules.** Renaming a
   site is a registry edit. Renaming its hosts is a per-node migration that MAY
   never happen. These MUST NOT be coupled into a flag day.
5. **Every rendering surface resolves through the registry**, never through a
   hardcoded prefix: docs, dashboards, CMDB views, ITIL records, coord cards.
6. **A new site is born named.** Hardware that has never booted has no legacy, so
   it MUST receive a conforming hostname from first boot. There is no cost to
   doing this correctly and a compounding cost to deferring it.
7. **Third-party and client-tenant hosts MUST stay outside the vocabulary.** The
   boundary between the estate and someone else's is a security boundary and
   belongs in the hostname where an operator will actually see it.

### Anti-pattern: the incrementing site

`<name>2` is the failure this standard exists to prevent. An increment tells you a
site is the second one and nothing else: not its role, not its trust posture, not
whether it may hold the only copy of something. If a proposed site code is an
existing code plus a digit, the naming has not been done yet.

---

## Federation: the vocabulary is estate-local, and the suffix carries the difference

SKCapstone is deployed by more than one operator. **Every estate will have its own
Zion.** That is correct and expected, not a collision, in the same way that every
company has a `prod` and every organisation has a `postmaster`. A site code names a
*role within an estate*; it was never a globally unique identifier and MUST NOT be
treated as one.

The design goal this serves is **identical internal structure across every estate**.
An operator who drops onto a peer's infrastructure to help should meet the same
nomenclature they already know, with only the estate differing. That portability is
the entire point, and it is why the home site is `zio` everywhere rather than a name
each operator invents.

### Site codes are estate-local

The disambiguation problem is already solved one layer up, and this standard
deliberately does not solve it a second time.

8. **A site code is unique within ONE estate, never globally.** Two federated
   estates both using `zio` are both correct.
9. **A site code MUST NOT change when an estate federates.** This inherits
   [`IDENTITY_NAMING_STANDARD` rule 6](./IDENTITY_NAMING_STANDARD.md): sovereign
   versus federated is a policy attribute, never a suffix, and no spelling encodes
   deployment status. Respelling a site on promotion (`zio` becoming `zio-local`
   or `zio.skworld`) re-proposes the local/federated split that standard's §3
   already overruled. Do not reintroduce it here.
10. **Cross-estate reference MUST use the fqid form**, where the existing
    `<operator>.<org-domain>` segment carries the estate:

    ```
    zioap01@chef.skworld.io      our Zion node 01
    zioap01@greg.example.org     Greg's Zion node 01, identical hostname
            ^^^^^^^^^^^^^^^^     the operator segment is the discriminator
    ```

    The hostname is bare and identical in both. The operator segment is the only
    discriminator, which is why it must never be omitted in a cross-estate
    reference.

11. **Never mint a local site code for a peer's infrastructure.** A peer's hosts
    belong to the peer's registry and are referenced by their fqid. Assigning one
    of our codes to someone else's node manufactures exactly the ambiguity this
    section exists to prevent, and it asserts an authority over their naming that
    we do not have.

### The estate belongs in the suffix, not in the hostname

A hostname is **bare**: `zioap01`, `ziooc2027`. It carries no estate marker, and it
is spelled identically in every estate. The estate lives in the **domain suffix**,
which is where every naming system has always put it: `casey@cakjr.skworld.io`, not
`cakjr-casey@...`; `web01.acme.com`, not `acme-web01`.

The fqid already does this. `zioap01@cakjr.skworld.io` states the estate once, in
the operator segment. Repeating it in the hostname is pure duplication, and inside
an estate (where every host belongs to that estate) an estate prefix carries
exactly zero information on every host you will ever type.

```
  hostname   zioap01                      bare, identical everywhere
  FQDN       zioap01.<tailnet>.ts.net     suffix supplies the estate
  fqid       zioap01@cakjr.skworld.io     estate stated once, here
```

12. **Hostnames MUST NOT encode the estate.** No prefix, no suffix, no marker of
    any kind. `cakjr-zioap01` and `zioap01-cakjr` are both wrong: they duplicate
    what the domain already says, and the latter additionally *looks* like a
    domain suffix while being un-strippable by any resolver or search path.
13. **The estate is carried by the resolution suffix**, and short names resolve
    inside an estate through the search domain, which is ordinary DNS practice
    and already in use in this fleet.
14. **Everything is identical across estates.**
    A runbook that says `ssh zioap01` is literally correct in every estate. That
    is the strongest form of the portability this standard exists to provide, and
    an estate marker in the hostname would have weakened it.

### Why this does not collide, on Tailscale specifically

The obvious objection is that two estates both naming a host `zioap01` collide in
MagicDNS. They do **not**, provided the tailnet boundary matches the estate
boundary, because Tailscale already enforces exactly the suffix rule above:

> Recipients cannot access machines by using their short name. Shared devices use
> the format `<hostname>.<tailnet-name>.ts.net`

So a device shared from another tailnet is *only* reachable by its full name. The
short name is scoped to its own tailnet by construction. Two estates on two
tailnets can both hold a `zioap01` forever.

15. **An estate SHOULD own its own resolution namespace** (its own tailnet, DNS
    zone, or equivalent). This is not a naming preference: it is what makes the
    bare hostname unambiguous. The alternative, several estates sharing one
    namespace, forces the first registrant to win the bare name and the rest to be
    silently renamed by the resolver, which is a naming standard being overruled
    by DNS.

**Verified constraints (Tailscale, checked 2026-09-02).** Device sharing is
available on all plans including the free tier, and the free Personal plan carries
up to 6 users, unlimited user devices, and 50 tagged resources per tailnet, so
splitting one estate-shared tailnet into per-estate tailnets increases the tagged
allowance rather than consuming it.

**Unverified and load-bearing:** shares are accepted by *users*, and a shared
machine is documented as visible only to the recipient user rather than to their
whole tailnet, while most nodes in this fleet are tag-owned rather than
user-owned. Whether a tagged node can reach a machine shared to a user is **not
answered by the documentation and MUST be tested before any migration depends on
it.** Recorded here as an open dependency rather than an assumption.

### Bridge nodes: how estates reach each other without merging

Rule 15 says an estate should own its resolution namespace. That is only usable
advice if there is an answer to "then how do two estates talk," so the answer is
here. It is deliberately narrow, and the narrowness is the point.

**There is no bulk mechanism, and you do not want one.** Tailscale shares devices
one at a time, with no batch or whole-tailnet option, and the tailnet-level
alternative (inviting a user into your tailnet) is not federation at all: the
invited user becomes a member with default access to everything, both estates
collapse into one namespace, and the bare-hostname rule breaks. Shared machines
also do not advertise subnet routes, so "share one router, expose the LAN" is
closed off too.

Read as a constraint that is a naming problem, this looks bad. Read as an
architecture, it is the correct default: **a peer estate should never have been
able to enumerate your whole fleet.**

16. **Estates federate through designated BRIDGE NODES, never as a full mesh.**
    Each estate exposes a small, enumerated set of nodes (normally one) to a given
    peer. Everything else in the estate is unreachable from outside it, by
    construction rather than by policy.
17. **A bridge node MUST be user-owned, not tag-owned.** Device shares are accepted
    by users and a shared machine is documented as visible to the recipient *user*
    rather than to their whole tailnet, so a tag-owned node is the wrong thing on
    both ends of a share. Keeping bridges user-owned and everything else tagged
    means cross-estate traffic is user-owned-bridge to user-owned-bridge, and the
    question of whether a tagged node can reach a user-shared machine never has to
    be answered.
18. **A bridge is an APPLICATION-layer bridge, not a network route.** Because a
    shared machine cannot advertise subnets, a bridge carries a specific,
    enumerated exchange (a sync folder, a mailbox, a signed message queue), never
    general reachability into the estate behind it. This is the same conclusion
    the fleet reached independently: a narrow shared folder between rings rather
    than merged state trees.
19. **The bridge set MUST be enumerated in the registry.** It is the estate's
    entire federation surface, so it is exactly the thing that should be reviewable
    in one place, and a bridge that exists but is not written down is an
    unaudited hole.

**Cost, so it is not a surprise.** Pairwise bridging is `N(N-1)` one-time shares
for `N` estates: six for three estates, done once. That is the whole ongoing
burden, and it does not grow with the number of machines in an estate, only with
the number of estates. An estate can add fifty nodes without a single new share.

```
  chef  <-> cakjr      2 shares
  chef  <-> greg       2 shares
  cakjr <-> greg       2 shares
  ------------------------------
  6 shares, one time, for any fleet size
```

### Estate identity: a subdomain of one org is the default, and it costs nothing

An estate needs a globally unique label. It does **not** need a registered domain
of its own, and buying one is usually the wrong first move.

Per [`IDENTITY_NAMING_STANDARD`](./IDENTITY_NAMING_STANDARD.md), **the PGP
primary-key fingerprint is the root identity and the subject string is a bound
label.** The domain is a name, not an address. It never has to resolve for identity
to work. So an estate whose operator holds its own primary key is sovereign
regardless of whose domain its label sits under. Revoke the label tomorrow and the
key is untouched; only the spelling would have to move.

20. **The DEFAULT is an operator segment under a shared org-domain**, which is the
    existing grammar with no new concept bolted on:

    ```
      zioap01@cakjr.skworld.io
              ^^^^^ ^^^^^^^^^^
              operator  org-domain     (the estate, stated once)
    ```

    Note this composes with the human apex form unchanged: the operator is a
    person's estate (`cakjr.skworld.io`), while that person as a sovereign root
    stays at the apex with no operator segment at all.

21. **A subdomain delegation MUST be documented as permanent and non-revocable.**
    This is the whole cost of the default, and it must be paid explicitly rather
    than assumed. An estate label that the parent-domain holder can reclaim is a
    label that can force a rename, and a forced rename breaks every stored
    reference. Write the commitment down; do not leave it to goodwill.
22. **An estate MAY move to its own org-domain at any time**, and this is a
    supported migration rather than a rupture: it goes through
    [`IDENTITY_NAMING_STANDARD` §2.6](./IDENTITY_NAMING_STANDARD.md), which
    already defines dated, enumerated, removable aliases. Because that path
    exists, choosing a subdomain today forecloses nothing.

**Make it resolve anyway.** Identity does not require it, but a resolvable estate
domain gives the ecosystem's `/.well-known` discovery patterns somewhere to live
(the module registry in
[`SKWORLD_MODULE_CONTRACT_STANDARD`](./SKWORLD_MODULE_CONTRACT_STANDARD.md) already
accepts either a local file or a `/.well-known` URL). Cheap now, useful later.

### Shared account names, estate-scoped secrets

The portability principle applies to operator accounts the same way it applies to
hostnames, and it stops in exactly the same place.

23. **An ops or admin account name MAY be identical across estates** (the fleet
    currently uses `skuser01`). That is the same win as identical hostname
    structure: an operator helping on a peer's box reaches for a name they already
    know.
24. **Credentials MUST NOT be.** Passwords, SSH private keys, and any key material
    are **per estate**, never shared and never derived from a common secret. A
    shared account name is a convenience; a shared credential would make the
    estate boundary decorative, since one compromise would cross every estate at
    once. The estates are already run this way and this rule records it rather
    than changing it.

**Out of scope, deliberately.** *How* those per-estate secrets are generated,
stored, rotated and recovered is a credential-management question, not a naming
question, and it is not settled here. This standard fixes only the invariant:
**identical spelling, isolated secrets.**

### Human-readable form when two estates are in the room

When context does not already fix the estate, qualify with the org-domain rather
than inventing a new name: **"Zion (skworld.io)"**, never `zio2`. This is the email
convention, and it is load-bearing for the same reason: nobody has ever needed
globally unique mailbox names, because the domain does that work.

### Registry requirement

A registry file MUST declare the estate it describes, so a peer's registry
obtained through federation or sync is never folded into ours:

```yaml
estate: skworld.io      # REQUIRED. Whose sites this file describes.
schema_version: 1
sites:
  zion:
    code: zio
```

A resolver that reads two registries MUST key sites by `(estate, code)`. Keying by
`code` alone is the bug this requirement exists to prevent.

---

## The vocabulary

SKWorld sites are named for cities of *The Matrix*. The scheme was chosen because
it is closed enough to enumerate, deep enough that the estate will not exhaust it,
and because the source material already distinguishes places by role rather than
by coordinates, which is exactly the distinction rule 1 asks for.

### `zio` is assigned, everything else is chosen

| Code | Site | Role | Assignment |
|---|---|---|---|
| `zio` | Zion | Home. Control plane, memory of record, the agent homes. | **Reserved and automatic.** Every estate's first site is Zion. |

**Zion is not a choice.** It is the reserved role code for an estate's control
plane, the way `root` and `localhost` are reserved words rather than names anyone
picks. Assigning it automatically buys three things: a new operator makes no naming
decision on the day they know least about their own topology, a shared runbook can
say "run this on Zion" and be correct in every estate, and "their Zion" becomes
unambiguous shorthand for "their control plane."

In the lore Zion is the last free human city: not the biggest site in the story and
not the fastest, the one that must not fall. That is a control plane.

**Every other code is chosen**, and only when an estate grows a site that Zion is
not. An estate with one site uses `zio` and nothing else. As of adoption, no SKWorld
estate has a second site, so the rest of the vocabulary below is reserved and unused.
That is the correct state: codes are claimed when a site exists to claim them, never
in advance of one.

### Reserved codes

Reserved codes carry an intended meaning. Claiming one for a different purpose
requires editing this table, which is the point: it makes a semantic drift into a
reviewed change rather than an accident.

| Code | Site | Reserved for | Why it fits |
|---|---|---|---|
| `zer` | Zero One | An estate's standing compute pool: GPU hosts, inference backends, workers | The machine city of the Second Renaissance. Endless industry, no ceremony. The right name for capacity that does work and holds no authority. |
| `ion` | IO | An estate's second city: a distinct site that is not the control plane | In *Resurrections*, IO is the city humans built **after** Zion and explicitly not a rebuild of it. The lore's own word for "the next site," which is the thing an incrementing name fails to say. |
| `meg` | Mega City | Rented, hosted or cloud infrastructure | Mega City *is* the simulation. Anything on someone else's metal is inside the Matrix, so the hostname states the sovereignty boundary without a lookup. |
| `mob` | Mobil Ave | Edge, transit, DMZ, relay | The station between worlds. Somewhere you pass through and never live, which is the correct semantics for a host that only forwards. |
| `src` | The Source | A future core or primary of record | The machine mainframe. Deliberately expensive to spend. |
| `syn` | Synthient | Allied hardware **we operate**, e.g. donated or loaned capacity that is not ours but that we run | The machines that took the human side. Scoped deliberately: a federated PEER's own sites are named in the peer's registry and referenced by fqid (see Federation, rule 11), never given one of our codes. |
| `tem` | The Temple | Unassigned | Held. |

`meg` is the one that does real work. Labelling rented infrastructure "Mega City"
means every hosted node announces its own trust posture in its own name. For an
estate built on sovereignty that is a governance signal, not a joke, and it costs
nothing to read.

---

## Role codes

The two-character role slot is orthogonal to the site slot and is not renamed by
this standard.

| Code | Meaning | Evidence |
|---|---|---|
| `pv` | Proxmox VE hypervisor | **Confirmed.** `norpv1200` runs kernel `6.8.4-3-pve`. |
| `oc` | Control node | **Partial.** The CMDB carries `role: control` for `noroc2027`. The expansion of the letters is not recorded anywhere. |
| `ap` | Application node | **Inferred** from usage. Not confirmed. |
| `wk` | Workstation | **Inferred.** `chiwk11-wsl` and `chiwk13-wsl` are WSL, so Windows workstations. |

`oc`, `ap` and `wk` are marked inferred deliberately. Nothing in the estate records
their expansions, so they are written here as observation and MUST NOT be quoted as
fact until an owner confirms them. Recording the difference between what is
verified and what is assumed is itself the
[`PROVENANCE_AND_MUTATION_STANDARD`](./PROVENANCE_AND_MUTATION_STANDARD.md)
honest-claim posture applied to documentation.

---

## Migration: alias first, rename optionally, never a flag day

A site prefix is load-bearing far beyond hostnames. In the SKWorld estate at
adoption time, `chi` appeared in roughly 890 files under `~/.skcapstone` alone,
plus systemd drop-ins and a `/mnt/chi-*` mount tree. A hard rename additionally
means re-authenticating every Tailscale hostname and re-pairing the Syncthing
rings.

The decisive constraint is the CMDB. **CI ids are keys, not labels**, so renaming
`ci-host-chiap08` is a delete plus a create, which discards the event log that
`cmdb show` folds to produce current state. A rename does not move a CI's history,
it destroys it. That alone disqualifies bulk renaming as a default.

Therefore:

1. **New sites take conforming hostnames immediately** (rule 6).
2. **Existing sites get a registry alias.** `legacy_prefix` makes both spellings
   resolve, so every human-facing surface shows the correct name on day one while
   every address keeps working.
3. **Host renames happen per node, on their own schedule, or never.** A host that
   is never renamed is not out of compliance. Its site is still resolvable, which
   is the only property this standard actually requires.

A migration that requires the whole fleet to move at once will not be done, and a
standard that requires it will be ignored. Aliasing is what makes this adoptable.

---

## The registry

The registry is the single source of truth for site identity. It holds sites and
their node membership by hostname. It is **not** a parallel inventory: per-host
facts stay in the CMDB, and a host's site is derivable from its prefix.

Reference implementation: `~/.skcapstone/sites.yaml`, distributed to every node by
the existing Syncthing folder rather than by a separate mechanism.

```yaml
sites:
  zion:
    code: zio
    display: Zion
    legacy_prefix: nor
    status: active
    nodes: [noroc2027, norap1001]
  io:
    code: ion
    display: IO
    legacy_prefix: null
    status: building
    nodes: []

reserved:
  megacity:
    code: meg
    intended_for: rented / hosted / cloud
```

Resolution MUST accept both the current code and the legacy prefix:

```python
def site_of(hostname, sites):
    """Resolve a hostname to its site by current code or legacy prefix."""
    for key, s in sites.items():
        for prefix in (s["code"], s.get("legacy_prefix")):
            if prefix and hostname.startswith(prefix):
                return key, s["display"]
    return None, hostname
```

---

## Compliance checklist

- [ ] Every site in the estate has a registry entry with a claimed three-character code.
- [ ] No site code is another code plus a digit.
- [ ] Every site that was renamed carries a `legacy_prefix`, and both spellings resolve.
- [ ] New hardware received a conforming hostname before joining Tailscale, Syncthing or the CMDB.
- [ ] No CMDB CI was renamed in order to adopt this standard.
- [ ] Client-tenant and third-party hosts are outside the vocabulary.
- [ ] Role-code meanings are stated as confirmed or inferred, never blurred.
- [ ] The registry declares its `estate`, and any resolver reading more than one keys sites by `(estate, code)`.
- [ ] No site was respelled to indicate federation status.
- [ ] No local code has been minted for a peer's infrastructure.
- [ ] No hostname encodes the estate, as a prefix or a suffix.
- [ ] Hostnames are spelled identically across estates.
- [ ] Each estate owns its own resolution namespace, or the shared-namespace risk is accepted in writing.
- [ ] No code was claimed for a site that does not exist yet.
- [ ] Each estate's operator segment matches `[a-z0-9]{2,12}` and contains no hyphen.
- [ ] Any subdomain delegation is documented as permanent and non-revocable.
- [ ] Ops account names may be shared; no credential is.
- [ ] Every estate's bridge set is enumerated in its registry.
- [ ] Every bridge node is user-owned, not tag-owned.
- [ ] No bridge grants general reachability into the estate behind it.
