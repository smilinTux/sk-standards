# SKWorld Application Identity: Architecture Assessment and Design

**Status:** ARCHITECTURE REVIEW, NOT NORMATIVE, NOT AN AUTHORIZATION
**Date:** 2026-08-25
**Reviews:** `APPLICATION_IDENTITY_AND_CAPAUTH_KEY_MANAGEMENT_BLUEPRINT.md` (card `b298a763`, uncommitted draft)
**Evidence base:** `EVIDENCE_PACK.md` (four read-only lanes, 2026-08-25) plus direct reads of `sk-standards` at HEAD `2b20639` performed for this review
**Author's conflict note:** `standards/PROVENANCE_AND_MUTATION_STANDARD.md` lists this reviewer as author. One blocking finding below is a defect in that document. It is treated here as a defect to fix, not a position to defend.

This document designs architecture only. Nothing in it authorizes key creation, enrollment, import, export, rotation, revocation, deployment, restart, service changes, provider traffic, protected-data access, or any external action. Every operation named below is a proposal for separately gated human decisions.

**Provenance discipline for this review.** Standards text quoted below was read directly from the canonical checkout (`/home/skuser01/work/sk-standards`, branch main, HEAD `2b20639`) today. Code, key, and coordination-board claims are cited from `EVIDENCE_PACK.md` lanes 1, 3, and 4, which carry their own file and line citations; where this document relies on them it says so. FACT and INFERENCE are labeled at the points where the distinction matters.

---

## 1. Verdict in one paragraph

The blueprint's core call is correct and should be approved in principle: one stable application registration per product and environment, a boundary-derived roster instead of a fixed count, durable keys rare, short-lived attenuated delegation for ordinary workloads. Its three-layer shape (registration, workload identity, credential slot) is the right shape, for reasons given in section 2.2, provided the registration and the credential slot are understood as metadata layers around the one ratified subject grammar, never as new grammar classes. The blueprint has four real defects: it presents six identity classes where the ratified grammar has five, it is silent on a live contradiction between two ratified standards that it stands on simultaneously, it generalizes a keyless-workload model fleet-wide that is built for SKLegal and absent at the fleet's actual front door, and it declines the rotation decision that its own section 1.1 names as a prerequisite. This document makes that decision (section 3), replaces the exact-seven roster with a derived one (section 4: two durable credentials today), separates the incidents from the standards work (section 5), and writes the normative edits (section 6).

---

## 2. Assessment of the blueprint

### 2.1 What is right, and why it is right rather than merely defensible

**The boundary-derived roster.** The exact-seven requirement is a traced category error: card `d0d6063a` (2026-08-21) counted seven HOSTS holding a copy of one leaked private key, and card `34ac09c6` (2026-08-25) converted that host count into a target count of application IDENTITIES, with no dependency link, no ADR, and no occurrence of "seven" anywhere in the standards repo (`EVIDENCE_PACK.md` 4.2, FACT). A roster derived from security boundaries cannot inherit that error, because it derives the number instead of receiving it. This is the blueprint's most valuable move and it should survive review intact.

**Keyless workloads by default.** This is not aspiration. The delegation machinery is real and strict: `capauth/src/capauth/delegated.py` enforces TTL of at most 3600 seconds, depth at most 2, and monotonic attenuation checked at both issuance and verification with no escape path (`EVIDENCE_PACK.md` 3.2, FACT). SKLegal has composed it for production with a Postgres replay backend that rejects the in-memory backend by isinstance check, and its issuer never lets the private key touch application code (gpg-agent or sidecar socket, `EVIDENCE_PACK.md` 3.2 and 3.3, FACT). A recommendation backed by a deployed reference implementation is a different thing from a paper design, and the blueprint should say so more loudly than it does.

**Durable keys as the exception with a recorded justification.** Consistent with the estate's direction of travel (the migration off one shared human-controlled signer, `EVIDENCE_PACK.md` 4.7) and with the external cross-check in blueprint section 17, which is sound.

**Opaque custody references, the failover rule, and the ownership table** (blueprint sections 10, 11) are correct and match defects actually observed in the estate: literal filesystem paths sit today in both `estate.json` fields and the one resolved roster entry's `secret_store_reference` (`EVIDENCE_PACK.md` 1.2, 1.4, FACT), and the observed anti-pattern of copying one private key across hosts and treating the copies as availability (`EVIDENCE_PACK.md` 1.1, FACT) is exactly what section 10.3 prohibits.

### 2.2 The three-layer model is the right shape

The alternative worth taking seriously is a two-layer model: registration plus keyed principals, with no distinct workload-identity layer. It fails on the evidence. In a two-layer model, every runtime boundary that needs a separate policy decision or separate audit attribution must either hold a durable key or disappear from policy and provenance entirely. The estate's own trajectory shows both failure modes: the shared C8D key is what "everything holds the same key" looks like, and SKGateway's caller-supplied `X-Agent-Id` subject is what "attribution without any credential layer" looks like (`EVIDENCE_PACK.md` 1.1, 3.4, FACT). The middle layer, a logical principal that is a real policy subject authenticated by a short-lived delegated capability rather than by holding a key, is precisely the thing `capauth.delegated` plus SKLegal's `PresentedCapability` envelope already implement. The three-layer model is right because layer 2 is implemented fact, and because separating layer 2 from layer 3 is the only way to express the outcome the whole design aims at: N logical identities, K durable credentials, K much smaller than N.

One correction is mandatory before this can become a standard. The ratified grammar has exactly five entity classes (`IDENTITY_NAMING_STANDARD.md` section 1 table, confirmed independently by `SKWORLD_AUTHORIZATION_STANDARD.md`, which says "five entity classes"). The blueprint's section 4 table has six rows under a column headed "Class", splitting Services into "Application service" and "Workload service". Whatever the intent, that table reads as a sixth grammar class, and the ratified precedent for a genuine class gap is explicit: the guest gap in `SKWORLD_AUTHORIZATION_STANDARD.md` says a subapp "MUST NOT invent a local guest spelling and store it as a policy-decision subject" until the naming standard is amended. The fix is presentational but load bearing: application registration is a metadata layer ABOVE the grammar, workloads and applications are both spelled as Services (`sk<name>@<operator>.<org-domain>`) when they are subjects at all, and the capability-ceiling class registry (CapAuth's `identity_class.py`, a separate registry from the grammar, which already has four members that do not map one-to-one onto the five grammar classes) is where a `service` versus `connector` distinction lives. The blueprint's own section 3.2 item 2 calls `connector` a missing "identity class"; under this framing it is a missing CEILING class, and that is the version that should be built (section 6, edit E4).

### 2.3 Where the blueprint over-reaches or stays silent

**Silent on a contradiction it stands on.** `PROVENANCE_AND_MUTATION_STANDARD.md` line 56 defines `actor.id` as "the `capauth_uri` (wire form, `capauth:<agent>@skworld.io`) or the sovereign FQID" (verified directly at HEAD `2b20639`). `IDENTITY_NAMING_STANDARD.md` section 2.1 makes the `capauth:` form a DEPRECATED wire alias that "MUST NOT appear in a policy-decision subject or a device record", and its Related standards block names the exact field: "`actor.id` MUST carry the fqid form defined here, never the deprecated `capauth:` wire alias" (verified directly). Two ratified documents, same field, opposite rules, live in code at `skgateway/src/identity/capauth.mjs:118` (`EVIDENCE_PACK.md` 3.4, FACT). The blueprint cites both standards as its foundation (its section 20) and never flags the conflict. A proposal aiming to become a standard in this estate must not build on a foundation it has not checked for cracks. The fix is a one-line edit and it goes against the provenance standard, because the naming standard's cross-reference already adjudicated the disagreement and the provenance standard simply never received the corresponding edit. As that document's author: this is my defect, ratified eleven days ago, and edit E1 below fixes it.

**Fleet-wide claims for a model that is absent at the front door.** Blueprint sections 6 and 7 read as if the keyless delegated-workload model applies everywhere. It is production-composed for SKLegal and does not exist at SKGateway: the fleet's single non-Python PEP contains no reference to `capauth.delegated` or chain parsing at all, its `subjectFromIdentity()` at `authz_routes.mjs:113-123` never inspects `identity.verified`, its enforcement master flag is off by default, and its PGP verification path cannot succeed on the current build because the `openpgp` package is not installed (`EVIDENCE_PACK.md` 3.3 and 3.4, FACT for the code, INFERENCE that no other verification path exists). The architecture should state its claims with scope: "the model is proven at SKLegal; SKGateway is a named migration target with a named gap", and the gap itself is an incident, not a standards question (section 5).

**A prerequisite named but not sized.** Blueprint section 3.2 item 2 says a new application principal "must not enter permissive unclassified behavior". That understates what the code does. There are two behaviors and the distinction is load bearing: a MALFORMED class assignment fails closed (`identity_class.py:441-444` raising, `authz.py:773-784` denying), but NO assignment, which is the state every `service` or `connector` subject is in because no such ceiling class exists, causes `authz.py:735-745` to skip the ceiling layer entirely, leaving the subject with zero structural ceiling and nothing preventing it holding capabilities that `agent` and `node` are hardcoded to forbid (`EVIDENCE_PACK.md` 3.1, FACT). The danger is not an edge case a new principal might wander into; it is the default state a new principal is born into. Edit E4 closes it, and section 5 sequences it as a hard prerequisite to any enrollment.

**The declined decision.** Blueprint section 1.1 correctly identifies that the naming standard's fingerprint-is-root rule does not permit "a cryptographic identity unchanged through rotation", and then defers the resolution to "a future normative card". For a blueprint whose central object is a registration stable across rotation, that is deferring the load-bearing joint. Section 3 makes the decision.

**Minor.** The blueprint's own "seven logical records" phrasing in section 8 risks laundering the bogus number back in through a side door; section 4 below keeps the derivation and drops the coincidence. Its section 12 manifest is close to right; three field-level corrections are folded into edit E5.

---

## 3. The rotation resolution: Path C, the dated dual-enrollment window

### 3.1 The decision

**Chosen: Path C.** Credential rotation for an enrolled subject is a dated, enumerated dual-enrollment window, modeled exactly on the five-point shape `IDENTITY_NAMING_STANDARD.md` section 2.6 already ratifies for domain-alias migration, with the predecessor named by a `replaces="<fingerprint>"` breadcrumb borrowing the spelling `CRYPTO_AGILITY_STANDARD.md` section 3.1 already uses for suite succession. Path A's registration layer is adopted as part of the architecture regardless (section 2.2), but it is rejected AS the rotation answer. Path D (rotation as a registered provenance verb) is not a competing answer and falls out automatically: enrollment and retirement are mutations of a shared store, so `PROVENANCE_AND_MUTATION_STANDARD` already obliges them to carry SPE envelopes with registered verbs.

The normative text is edit E2 in section 6. The mechanism in brief: by default one fqid binds exactly one key, exactly as today. Rotation creates a second enrollment record binding the SAME fqid to the successor fingerprint, permitted only under an explicit rotation entry that (1) enumerates the one fqid, the predecessor fingerprint, and the successor fingerprint, never inferring succession from UID string equality, (2) carries a removal date in the entry itself, (3) names the migration that re-issues grants and retires the predecessor, (4) makes the successor write-canonical immediately, with the predecessor verify-only for the window, and (5) is recorded in the implementing component's SECURITY.md or SOP. The window closes only by an explicit, SPE-carrying retirement mutation. It never closes by a clock read inside the decision function.

### 3.2 Why this preserves the two things that must not break

**`decide()` stays pure.** The subject presented to `decide()` is resolved from the verified credential's fingerprint through `canonical_subject()` at ingest and enrollment, exactly as `IDENTITY_NAMING_STANDARD` section 2.4 requires. During a window the registry holds two enrollment records; `decide()` remains an exact matcher over already-canonical strings and gains no clock, no alias logic, no lineage traversal. The "dated" property is an operational commitment enforced by a validator that fails when the removal date passes with the predecessor still enrolled (the check for edit E2), not a runtime branch.

**Fingerprint stays root.** The rule exists to stop a string and a key disagreeing. Under Path C nothing ever infers a key from a string: both bindings are explicit enrollment records, each key is its own root, the two principals remain distinguishable in provenance for all time (their SPE signatures carry different keys), and the window is a finite reviewable entry in exactly the sense section 2.5 demands of every alias ("a closed, enumerated table, never an algorithmic rewriter"). What the window sanctions is the temporary condition that one label is bound to two roots, explicitly, with an end date.

### 3.3 Against the strongest alternatives

**Against A (registration outside the grammar is the whole answer; rotation is just retire-and-enroll).** A is the conceptually cleanest position and it costs nothing in grammar edits. It fails on two grounds. First, the ratified standard itself forbids the escape hatch A would force. If the same fqid cannot be re-bound, then a rotated issuer needs a new fqid, which puts a generation marker in the spelling; the naming standard's enrollment checklist is explicit that "status lives on the enrollment record or the policy, never in the local-part or domain" (verified directly at HEAD `2b20639`), and the rejected local/federated suffix split is the standing precedent that lifecycle state never enters the spelling. So under A the fqid must be re-bound atomically, which is a flag-day cutover: every grant, trusted-issuer entry, and gateway binding re-issued in one motion or downtime accepted. Second, and decisive: this estate has already demonstrated, on the record, what happens when the standard is silent about a migration it forces. Section 2.6's own rationale note records that the alias table said REJECTED while a live implementation quietly aliased the shape anyway, "and the divergence went unnoticed because both sides read the same section and drew opposite conclusions". A standard that mandates flag-day rotation will get improvised overlap, unreviewed, exactly there. C puts the overlap where it can be reviewed. INFERENCE, but grounded in a recorded incident of this precise failure mode.

**Against B alone (a lineage breadcrumb, no window).** `replaces=` answers "which key succeeded which" and nothing else. It does not say when the predecessor stops being valid, and a succession record with no end date is precisely what section 2.6 point 2 calls "a second grammar wearing a migration costume". B's spelling survives inside C as the enumeration field; B as the whole answer is the un-dated half of C.

**Against D alone.** An append-only rotation verb makes rotation auditable and answers nothing about what `decide()` does while two fingerprints exist. It is a complement by its own definition, and it is already owed under the provenance standard, so ratifying it as THE answer would be ratifying a tautology.

### 3.4 The incident behind the rule

The C8D Jarvis service key: RSA 4096, created 2026-08-11, no expiry, secret material present on at least two hosts and asserted by the estate's own critical card to have reached seven (`EVIDENCE_PACK.md` 1.1, FACT for two hosts, card-asserted for seven). Every key pair found on the cluster is non-expiring (`EVIDENCE_PACK.md` 1.3, FACT). A fleet where no sanctioned rotation semantics exist is a fleet where keys are never rotated and where the eventual forced replacement of a compromised key has no rails. Thirteen critical cards are stalled behind the roster question that rotation semantics feed (`EVIDENCE_PACK.md` 4.3, FACT). That is the incident. The check is named in edit E2.

---

## 4. The boundary split test, sharpened and applied

### 4.1 The test

Blueprint section 7.3's five criteria are right in substance and too abstract to apply identically by two different people. The sharpened form: one guard question, then five yes/no questions in fixed order. Answer yes ONLY if you can name the concrete artifact that makes it yes (the capability string, the custody location class, the classification label, the signed artifact). If you cannot name it, the answer is no.

**Q0 (guard).** Is the candidate distinct only by process, container, replica, repository, port, queue, or database pool? If yes and it needs no separate policy decision and no separate audit attribution, it is not even a logical identity. Stop: it inherits its parent workload's identity.

Then, a candidate logical identity gets a DURABLE credential if and only if at least one of:

1. **KILL IT ALONE.** Must its authority be revocable without revoking anything else's? Name the scenario in which you would revoke it and leave its siblings running.
2. **IT LEAVES THE HOUSE.** Can it cause external effects: email, filings, calendar writes, provider egress, spend? Name the capability string.
3. **DIFFERENT DRAWER.** Does its secret material live under a different custody class: different host, different account, TPM versus file, different organization? Name the custody class on each side.
4. **DIFFERENT WALL.** Does it handle a higher data classification or sit behind an ethical wall its siblings must not cross? Name the classification or wall.
5. **IT OUTLIVES.** Does it sign artifacts that must verify after the issuer is gone, or must it operate while the application issuer is unavailable? Name the artifact or the availability requirement.

All five no: logical workload identity, keyless, authenticated by short-lived delegated capabilities from the application issuer. Any yes: a durable credential slot, with the yes answer recorded as the justification on the registration record. That recording requirement is what makes the test auditable a year later.

Two people applying this to the same candidate diverge only if they disagree about a nameable fact, which is the kind of disagreement that can be settled. That is the property the one-minute bar actually needs.

### 4.2 Applied on the record

Sources: SKLegal audiences and architecture per `EVIDENCE_PACK.md` 1.4, 1.6, 3.2, 3.3, 3.6 and blueprint sections 3.1 and 8; SKDashboard per blueprint section 3.1 and board card `94cbf19a` (DONE, `EVIDENCE_PACK.md` 4.4).

| Candidate | Q0 | Q1-Q5 | Verdict |
|---|---|---|---|
| SKLegal application authority | passes | Q1 yes (revoking SKLegal issuance must not touch SKDashboard or the gateway), Q5 yes (it is the issuer; its availability requirement is the point) | DURABLE, one per environment |
| SKLegal API workload | passes (separate policy decisions per Tenant and Matter) | all no; it is inside the house, same custody, same wall as the app | keyless logical identity |
| SKLegal model workload | passes | Q2 no on current evidence: model traffic terminates at sovereign inference through the gateway, not provider egress (INFERENCE from estate posture; if a paid external provider is ever in path, Q2 flips and this line is re-run) | keyless logical identity |
| SKLegal tool workload | passes | all no | keyless logical identity |
| SKLegal connector workload | passes | Q2 YES: `action.email.dispatch`, `action.filing.dispatch`, `action.calendar.dispatch`, `action.service.dispatch` are named capability strings in the deployed policy (`EVIDENCE_PACK.md` 3.6, FACT) | keyless TODAY because dispatch is not enabled and policy denies it; DURABLE separate issuer the day dispatch enables. The trigger is the enablement decision, not this document |
| SKLegal context broker | passes | Q1 arguable, but the POSTGRES-PRINCIPAL-SCALING design already answers it with short-lived injected authority and database-owned one-use leases | keyless logical identity; revisit only if custody or availability evidence appears, per blueprint section 19 |
| SKLegal runtime pool | passes | all no, and it is explicitly designed to hold no signing key and to be unable to choose a Principal | keyless, no key ever |
| SKDashboard | separate product, separate release cycle, separate session surface: it is its own REGISTRATION, not an SKLegal workload | Q1 yes (revocable alone), Q3 yes (file-backed deployment credentials in a different custody location, blueprint section 3.1) | DURABLE, one OIDC client or workload credential on the SKDashboard registration |
| SKGateway | its own service subject in the grammar already (`skgateway@...`) | Q3 turns on a custody decision not yet made: whether the gateway authenticates ITSELF to backends and the PDP, or remains a thin PEP forwarding verified subjects. As a thin PEP: all no | NOT durable today; conditional, and the condition is Chef's call (section 7) |

**The roster, with the number.** Across the reviewed SKLegal and SKDashboard surfaces: seven SKLegal logical identity records plus one SKDashboard registration record, and exactly **two durable credentials today**: the SKLegal application issuer and the SKDashboard client credential. Three when external dispatch enables. Four only if the SKGateway custody question resolves toward a self-authenticating gateway. Defense of the number: each durable entry above carries a named yes from the test, each keyless entry survived all five questions, and every line can be re-litigated by disputing a named fact rather than an intuition.

That SKLegal's logical record count happens to be seven is a coincidence of an unrelated derivation and must not be allowed to rescue card `34ac09c6`'s criterion, which demands seven ATTESTED APPLICATION IDENTITIES, a quantity this derivation says is two. The criterion should be amended, not reinterpreted into accidental correctness.

---

## 5. Sequencing: what is an incident, what is a standard, what actually blocks what

The tidy version of this list would be a phase plan. The honest version is three lanes that mostly do not block each other, plus two genuine blocking edges.

### 5.1 Incident lane (does not wait for any standard)

**INC-1: the SKGateway exposure. This is an incident, full stop.** A running process on chiap01, bound to all interfaces on LAN and tailnet, `allow_anonymous: true`, enforcement master flag off so `decide()` is never called for gated routes, subject built from an unverifiable caller-supplied header, and signature verification structurally unable to succeed because `openpgp` is absent from the build (`EVIDENCE_PACK.md` 1.5 and 3.4, FACT). Two honesty notes: whether an unauthenticated request reaches an actual gated route is NOT VERIFIED (only health and config were checked), so step one is that verification; and the app-level flags are the WRONG containment because `require_agent_id` does not reject unverified header identities, so turning it on manufactures false assurance. Real containment is network-scoped (loopback or tailnet ACL) pending a human-gated change. File it through ITIL, today. No standards edit is a prerequisite and no standards edit should wait for it.

**INC-2: the shared C8D key.** Already tracked as CRITICAL on card `d0d6063a`. Containment does not block on the rotation standard: C8D is an AGENT-class key, SKLegal's issuer already refuses it at construction (`FORBIDDEN_ISSUER_FINGERPRINTS`, `EVIDENCE_PACK.md` 3.6, FACT), and the containment moves (stop new grants, resolve which host is custodial, revoke the rest) are incident response. Its eventual full replacement is the first real consumer of edit E2's rotation window, which is a reason to land E2 promptly, not a reason to delay containment.

**INC-3 (small): literal custody paths in public metadata.** `estate.json` fields and the roster entry's `secret_store_reference` hold filesystem paths where opaque handles belong (`EVIDENCE_PACK.md` 1.2, 1.4, FACT). A metadata repair card. It should land before any new manifest schema ships so the new schema is born clean.

### 5.2 Board lane (a decision, not an incident and not a standard)

**G-1: amend card `34ac09c6`.** The exact-seven acceptance criterion is the traced category error, and thirteen critical cards stall behind it. Replace the criterion with "roster derived per the boundary split test, each durable credential carrying its recorded justification", link `d0d6063a` and `34ac09c6` as related, and record the correction as a decision note in `decisions/`. This is the single cheapest high-leverage act in this entire document, it unblocks thirteen cards, and it needs Chef because the card is a human gate.

**G-2: resolve the worktree collision before standards edits.** An uncommitted detached-HEAD diff in worktree `f0c63c2a` edits the same two standards this design extends, while its card shows DONE (`EVIDENCE_PACK.md` 4.5, FACT). Land it or close it before E-series PRs touch those files. Separately, the `b298a763` blueprint draft is itself uncommitted working-tree-only and should be committed to its branch immediately; uncommitted work in a shared checkout is one pull from gone.

### 5.3 Standards lane (ordered by dependency, not by size)

1. **E1** (fix `actor.id` in PROVENANCE) and **E3** (the one-word module-contract fix). No dependencies, one-line-scale, separate small PRs. E1 must precede E6 promotion because a blueprint cannot be promoted while it stands on two documents that contradict each other on a field the blueprint's provenance chain uses.
2. **E4** (ceiling classes for service and connector, unclassified fall-through closed). This is the one standards-plus-code item that HARD-BLOCKS operations: no new service principal may be enrolled anywhere until it lands, because until it lands every such principal is born with zero structural ceiling. It does not block E1, E2, E3, or the incident lane.
3. **E2** (the rotation window in IDENTITY_NAMING). Blocks nothing operational today, but it is the prerequisite the blueprint itself named, INC-2's full remediation consumes it, and E6 cannot promote without it.
4. **E5/E6** (registration standard promoted from the amended blueprint). Blocks on E1, E2, E4, G-1, G-2, and Chef's open decisions in section 7. It does not block the incident lane and must not be allowed to.

The genuine blocking edges, stated plainly: the thirteen cards block on G-1 alone (a decision, available immediately); enrollment of any new principal blocks on E4 and on the roster decision; promotion blocks on E1, E2, E4, and the collisions. Everything else can move in parallel, and the incident lane moves first regardless.

---

## 6. The normative edits

Each edit gives the file, the location, the exact text, the incident behind it, and the check with its negative test, per the CONTRIBUTING.md bar ("A standard states a rule, an incident, and a check. A rule with no incident behind it and no way to check it is an opinion."). All land via the observed governance path: branch off main, local checks (`scripts/docs_check.py`, `scripts/check_fences.py`, `scripts/ci_gate_check.py`), negative-test proof where a gate is touched, PR, Chef merges.

### E1. `standards/PROVENANCE_AND_MUTATION_STANDARD.md`, section 1 envelope table, `actor.id` row

Current text (verified at HEAD `2b20639`):

> The authenticated identity of the writer, from `capauth.resolve_agent_identity()`: the `capauth_uri` (wire form, `capauth:<agent>@skworld.io`) or the sovereign FQID. NEVER free text, NEVER a magic string like `"human"` or `"operator"` typed by a caller.

Replace with:

> The authenticated identity of the writer, from `capauth.resolve_agent_identity()`, carried as the canonical fqid form defined in [IDENTITY_NAMING_STANDARD](./IDENTITY_NAMING_STANDARD.md) §1. The `capauth:` wire form is a DEPRECATED alias per that standard §2.1: the §2.4 validator MUST strip it at ingest and it MUST NOT be stored in this field. NEVER free text, NEVER a magic string like `"human"` or `"operator"` typed by a caller.

And append to the standard's changelog or header notes:

> 2026-08-25: `actor.id` corrected to require the canonical fqid only. The original row permitted the `capauth:` wire form, contradicting IDENTITY_NAMING_STANDARD §2.1 and its Related standards cross-reference, both ratified the same day. The naming standard's rule stands; this row now matches it.

**Incident:** two ratified standards ruling oppositely on one field, live at `skgateway/src/identity/capauth.mjs:118` where a `capauth:` URI is baked into the builtin agent registry (`EVIDENCE_PACK.md` 2.1, 3.4).
**Check:** in each SPE-implementing store's test suite (CardStore first), a negative test: an envelope whose `actor.id` is `capauth:agent-one@example.org` must be stored stripped to `agent-one@example.org` by the §2.4 validator at ingest, and an `actor.id` of free text (`"human"`) must be rejected. The test proves sensitivity by asserting the pre-fix behavior (storing the prefixed form) now fails.

### E1b. Same file, section 1 table: two additive SHOULD rows

The blueprint's reconstruction chain (its section 5) and its own section 6.1 requirement ("audit must record both Jarvis as the actor and the application or workload authority under which the action was accepted") need two fields the envelope genuinely lacks (`EVIDENCE_PACK.md` 2.5, FACT). Additive, so old readers are unaffected, per the standard's own rule that "a new envelope field never breaks an old reader". Add two rows:

> | `actor.authority` | string | SHOULD; MUST when the action is performed under delegated or application-issued authority | The canonical fqid of the authority under which the action was accepted (the application issuer or the delegating principal), distinct from `actor.id`. Resolved from the presented capability chain, NEVER inferred from `actor.id`, NEVER caller-typed. Absent means the actor acted under its own direct enrollment. |
> | `authz.revision` | string | SHOULD; MUST when the action was gated by a versioned policy | Opaque revision identifier of the policy or registry revision the authorization decision was made under (e.g. an `IssuerPolicyStore` revision). Absent means the gating policy was unversioned, which is itself a fact worth recording. |

**Incident:** the deployed SKLegal flat trusted-issuers file carries no revision or status field and does not match the newer versioned model, and it is currently unresolvable which of two authorization surfaces serves live traffic (`EVIDENCE_PACK.md` 3.6). A provenance record that cannot say which policy revision admitted an action cannot support the reconstruction chain the blueprint promises.
**Check:** SPE fixture tests: a record carrying both fields round-trips; a record where `actor.authority` equals a caller-supplied string not present in the verified chain is rejected. Promotion of SHOULD to MUST is a later dated change with its own migration note, per CONTRIBUTING's rule-change row.

### E2. `standards/IDENTITY_NAMING_STANDARD.md`, new section 2.7

Insert after section 2.6, before rule 6:

> ### 2.7 Credential rotation: dated dual-enrollment windows
>
> The fingerprint-is-root rule (§1) means a rotated key is a new root. Lifecycle state never enters the subject spelling (enrollment checklist; §3's rejected suffix split), so rotation MUST NOT mint a generation-suffixed fqid: the successor key is enrolled under the SAME fqid. That creates a temporary condition this standard must govern explicitly rather than leave to improvisation: one label bound to two roots.
>
> By default one fqid binds exactly ONE key, and enrolling a second key under an already-bound fqid is REFUSED. A **rotation entry** MAY permit it if and ONLY if all of:
>
> 1. **Enumerated, never inferred.** The entry names ONE fqid, the predecessor fingerprint, and the successor fingerprint, with the succession spelled `replaces="<predecessor-fingerprint>"` (the same breadcrumb discipline as `CRYPTO_AGILITY_STANDARD` §3.1). No component may infer succession from UID string equality or key metadata.
> 2. **Dated, with a removal date in the entry itself.** An overlap with no end date is a second enrollment regime wearing a migration costume (§2.6, point 2, applied to keys).
> 3. **Paired with a migration.** The entry names the plan or tool that re-issues grants to the successor and retires the predecessor, and that migration completes BEFORE the window closes.
> 4. **Write-canonical from the start.** From the successor's enrollment, ALL new issuance and signing uses the successor. The predecessor is verify-only for the remainder of the window; a predecessor that issues or signs during the window is a violation, not a grace.
> 5. **Recorded where implemented.** The implementing component states the entry, its removal date, and its migration in its own SECURITY.md or SOP.
>
> During the window the two `(fqid, fingerprint)` bindings are DISTINCT principals: provenance signed by each remains distinguishable forever, and a grant intended for both MUST be granted to both explicitly, never merged. `decide()` is unchanged by this section: it remains the pure exact matcher of §2.4, gains no clock, no lineage traversal, and no alias logic. The window closes ONLY by an explicit retirement mutation of the predecessor's enrollment record, carrying a Signed Provenance Envelope with a registered verb (`PROVENANCE_AND_MUTATION_STANDARD` §3). A window whose removal date has passed while the predecessor remains enrolled is a compliance failure that the estate health check MUST report as failing; it does not silently alter any decision.

Also append to the Related standards block:

> - [CRYPTO_AGILITY_STANDARD](./CRYPTO_AGILITY_STANDARD.md): the `replaces=` succession breadcrumb that §2.7 rotation entries reuse for keys.

**Incident:** every key pair found on the cluster is non-expiring; the C8D service key (created 2026-08-11, no expiry) has secret material on multiple hosts and has never rotated because no sanctioned semantics exist; thirteen critical cards stall behind the roster question this feeds (`EVIDENCE_PACK.md` 1.1, 1.3, 4.3). The recorded §2.6 rationale (a live implementation improvising exactly the migration the table was silent about) is the precedent for why silence here produces unreviewed overlap.
**Check:** extend `capauth doctor estate` (working fail-closed precedent at `capauth/src/capauth/cli.py:1884-1982` per `EVIDENCE_PACK.md` 3.7), plus a repo-side validator over committed enrollment metadata (new `scripts/check_rotation_windows.py` wired into the existing CI gates). Negative tests, each proving sensitivity by constructing the violation and observing failure: (a) dual enrollment with no rotation entry is refused; (b) a rotation entry with no removal date is refused; (c) a fixture registry with an expired window and an unretired predecessor fails doctor with a nonzero exit; (d) predecessor issuance during a window is denied.

### E3. `standards/SKWORLD_MODULE_CONTRACT_STANDARD.md`, the facet-separation paragraph (line 65 region)

Current text (verified at HEAD `2b20639`):

> a failed UI pane renders grey with a reason; a failed operator observe must fail *safe* and report healthy

Replace the final clause:

> a failed UI pane renders grey with a reason; a failed operator observe must fail *safe* and report `Unknown`, never healthy

**Incident:** the sentence contradicts the tri-state condition vocabulary (module schema line 127; `ITIL_AND_RUNBOOK_OPERATING_MODEL_STANDARD.md:481`) and the fail-closed rule in `SKWORLD_AUTHORIZATION_STANDARD.md` (`EVIDENCE_PACK.md` 2.7). A sensor that reports healthy when broken masks outages; `Unknown` preserves the intended property (a broken sensor must not trigger remediation) without asserting a falsehood.
**Check:** `scripts/docs_check.py` cross-reference pass; module conformance negative test: a module whose operator observe path is made to fail and which reports `healthy` fails conformance, one reporting `Unknown` passes.

### E4. `standards/SKWORLD_AUTHORIZATION_STANDARD.md`, new rule after the enrollment-mode paragraph (near the guest-gap note, line 120 region), plus the capauth code card it obliges

Insert:

> **Every policy-decision subject MUST resolve to exactly one registered capability-ceiling class, and a subject that resolves to NO registered class MUST be denied exactly as a malformed class assignment is denied.** The ceiling-class registry is CapAuth's, is distinct from the IDENTITY_NAMING_STANDARD §1 grammar classes, and MAY subdivide a grammar class (e.g. `service` and `connector` are two ceiling classes over service-spelled subjects, distinguished on the enrollment record, never in the spelling). A skipped ceiling is not a neutral default: a subject with no ceiling is structurally uncapped and can hold capabilities other classes are hardcoded to forbid. Registry completeness is a checked property: the registry MUST cover every subject kind the deployment enrolls. Migration note: deployments with live unclassified subjects follow a dated migration in the §2.6 shape of IDENTITY_NAMING_STANDARD (enumerate the unclassified subjects, date the flip, classify before the date); the fall-through flips to deny at the recorded date, not silently.

Code obligation (a linked card, not standard text): add `SERVICE` and `CONNECTOR` to `IdentityClassName` and `DEFAULT_CLASSES` with explicit allowed/forbidden capability sets (connector's allowing external-effect capabilities that service's forbids), and change the no-assignment path so it denies instead of skipping the ceiling layer.

**Incident:** `capauth/src/capauth/identity_class.py:102-116` has four members; `resolve_identity_class()` returns None for anything else and `authz.py:735-745` skips the ceiling layer entirely, so the exact subject kinds this whole design creates would be born with zero structural ceiling, while nothing stops them holding `Capability.ALL`, `TOKEN_ISSUE`, or `IDENTITY_SIGN` (`EVIDENCE_PACK.md` 3.1). SKLegal names service and connector as principal types but caps neither (`sklegal_capauth/models.py:51-55`).
**Check:** capauth negative tests: (a) a subject resolving to no ceiling class requesting `IDENTITY_SIGN` is denied with the same failure class as a malformed assignment; (b) a registry-completeness test asserting every enrolled subject kind has a ceiling class. Test (b) fails against today's code, which is the sensitivity proof: it goes green only when the classes land.

### E5. The registration standard: promote the amended blueprint as `standards/APPLICATION_REGISTRATION_STANDARD.md`

Not a full re-draft here; the blueprint, amended per section 2 of this document, is the draft. The four load-bearing normative rules it must state, in rule-incident-check form:

> **R1.** An application registration is METADATA. Its `app_id` is NEVER a policy-decision subject and NEVER enters `decide()`. Anything requiring authorization is one of the IDENTITY_NAMING_STANDARD §1 entity classes, spelled by that grammar.
> *Incident:* the exact-seven roster demanded key-bearing identities to satisfy a count with no boundary behind it (cards `d0d6063a` to `34ac09c6`, unlinked). *Check:* `capauth app lint` rejects any manifest whose `app_id` matches the subject regex or appears in a grants file; negative test: a manifest using its app_id as a grant subject fails lint.
>
> **R2.** The registration record owns the roster: owners (the blueprint's six responsibilities), workload registry, credential slots with public fingerprints, typed opaque custody references, policy and revocation revisions, lineage. Three schema corrections to the blueprint's §12 manifest: `identity_class` takes ceiling-class values per E4; `predecessor_fingerprint` is renamed `replaces` to match E2 and CRYPTO_AGILITY; `credential_reference` is a typed handle from an enumerated scheme union, with anything shaped like a filesystem path REJECTED.
> *Incident:* literal custody paths live today in `estate.json` and the roster entry's `secret_store_reference` (`EVIDENCE_PACK.md` 1.2, 1.4). *Check:* `capauth app lint` scheme-union validation; negative test: a `credential_reference` beginning with `/` or `~` fails.
>
> **R3.** A durable credential is added ONLY by a recorded yes to the section 4.1 split test, with the named artifact written into the registration record. A process, container, replica, repo, port, queue, or pool split is never alone a justification.
> *Incident:* one key copied to seven hosts is what unprincipled credential placement produced. *Check:* `capauth app lint` requires a non-empty `split_justification` naming one of the five criteria on every durable slot; negative test: a durable slot without one fails.
>
> **R4.** Workloads are keyless by default, authenticated by short-lived attenuated delegated capabilities from the application issuer (`capauth.delegated` semantics: bounded TTL, bounded depth, monotonic attenuation, replay-checked with a durable backend in production).
> *Incident:* the in-memory replay backend is documented "never a production default" and SKLegal already enforces the isinstance rejection (`EVIDENCE_PACK.md` 3.2). *Check:* the blueprint §18 negative-control suite, run with synthetic credentials.

Plus the CI-enforced README.md line:

> | [**APPLICATION_REGISTRATION_STANDARD**](./standards/APPLICATION_REGISTRATION_STANDARD.md) | What an application IS in identity terms: one stable registration per product and environment as metadata above the fqid grammar (never a decision subject), the boundary split test that is the only path to a durable credential, keyless workloads by default via short-lived attenuated delegation, credential slots with typed opaque custody references, and the rotation lineage that IDENTITY_NAMING §2.7 governs. |

**Check for the standard as a whole:** the blueprint's §14 tooling, built fail-closed on the `capauth doctor` precedent, with the §18 negative controls as its test suite.

### E6. Blueprint amendments required before E5 promotion

In the `b298a763` draft itself, before it is promoted: (1) rewrite the section 4 table to five grammar classes plus a registration metadata layer, per section 2.2 above; (2) correct section 3.2 item 2 to name `connector` a missing CEILING class, per E4; (3) add the E1 contradiction to section 3.2's gap list with its resolution; (4) scope sections 6 and 7 claims to "proven at SKLegal, migration target at SKGateway" with the gateway gap cited; (5) replace section 8's "seven logical records" framing with the section 4.2 derivation and the explicit statement that the durable count is two.

---

## 7. What stays open (Chef's decisions, not an architect's)

1. **Amend or void card `34ac09c6`'s exact-seven criterion** (G-1). It is a human-gate card; only Chef amends it. Everything in section 4 is input to that decision, not a substitute for it.
2. **SKGateway containment timing and shape** (INC-1). Network-scoping a live service is an operational disruption call.
3. **Whether SKGateway becomes a self-authenticating principal** with its own durable credential, or stays a thin PEP. This is a custody and exposure judgment the split test can inform but not settle, because it turns on how Chef wants the front door to fail.
4. **Enabling external dispatch at all**, which is what triggers the connector issuer. The trigger is the product decision, not this design.
5. **C8D custody resolution** (INC-2): which host, if any, remains custodial, and the remediation schedule. Key operations are human-gated without exception.
6. **Ratification of the amended blueprint** as APPLICATION_REGISTRATION_STANDARD, after the E-series lands and on Chef's own read.

Everything else in this document is either an assessment Chef can overrule or an edit that goes through the normal PR gate where Chef is the merger. Nothing here executes anything.
