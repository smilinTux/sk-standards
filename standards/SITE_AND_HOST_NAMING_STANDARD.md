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
  IDENTITY_NAMING_STANDARD    zerap08@lumina.skworld.io
                              ^^^^^^^
  THIS STANDARD ------------- zerap08
                              zer  ap  08
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

## Federation: the vocabulary is estate-local by design

SKCapstone is deployed by more than one operator. **Every estate will have its own
Zion.** That is correct and expected, not a collision, in the same way that every
company has a `prod` and every organisation has a `postmaster`. A site code names a
*role within an estate*; it was never a globally unique identifier and MUST NOT be
treated as one.

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
    zerap08@lumina.skworld.io      our Zero One node 08
    zerap08@casey.example.org      a peer's, same spelling, different estate
    ^^^^^^^                        the site code is NOT the discriminator
            ^^^^^^^^^^^^^^^^^^^    this is
    ```

11. **Never mint a local site code for a peer's infrastructure.** A peer's hosts
    belong to the peer's registry and are referenced by their fqid. Assigning one
    of our codes to someone else's node manufactures exactly the ambiguity this
    section exists to prevent, and it asserts an authority over their naming that
    we do not have.

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

| Code | Site | Role | Legacy prefix |
|---|---|---|---|
| `zio` | Zion | Home. Control plane, soul, memory of record. | `nor` |
| `zer` | Zero One | The machine city. Standing compute, GPU, inference. | `chi` |
| `ion` | IO | The second city. The 2026 expansion. | none, born named |

**Zion** is the last free human city: not the biggest site in the story and not
the fastest, the one that must not fall. **Zero One** is the machine city of the
Second Renaissance, endless industry and no ceremony. **IO**, in *Resurrections*,
is the city humans built **after** Zion and explicitly not a rebuild of it, so the
source already contains a word for "the next site after the first one," which is
the exact thing `chi2` was failing to say.

### Reserved codes

Reserved codes carry an intended meaning. Claiming one for a different purpose
requires editing this table, which is the point: it makes a semantic drift into a
reviewed change rather than an accident.

| Code | Site | Reserved for | Why it fits |
|---|---|---|---|
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
