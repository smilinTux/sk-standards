# SKStacks — Cryptography Standard (quantum-resistance goal)

**Status:** Going-forward ecosystem standard. The bar **new** SK components should
target; existing components migrate under epic `PQC-MIGRATION` (coord `e1d6ba2a`).
**Master plan / source of truth:** [skchat `docs/quantum-resistance-architecture.md`](https://github.com/smilinTux/skchat/blob/main/docs/quantum-resistance-architecture.md).
**Standards anchor:** FIPS 203 (ML-KEM), FIPS 204 (ML-DSA), FIPS 205 (SLH-DSA); NIST CSWP 39 (crypto-agility); RFC 9580 + draft-ietf-openpgp-pqc-17.

---

## Why this exists

The urgent threat is **Harvest-Now-Decrypt-Later (HNDL)**: an adversary records
ciphertext **today** and decrypts it once a cryptographically-relevant quantum
computer (CRQC) exists — plausibly the **early-to-mid 2030s**. By
**Mosca's Inequality** (`data-shelf-life + migration-time > years-to-CRQC`), our
longest-lived secrets are *already* past the threshold. We do **not** justify
urgency with "Q-Day is imminent" — that is not credible. We act on **confidentiality
key exchange first**, signatures later, because signatures are not retroactively
breakable.

This standard makes **crypto-agility** — the ability to swap primitives without a
flag-day — the primary architectural requirement. Per NIST CSWP 39, swap-ability is
worth more than any single parameter choice.

---

## The standard (what new components MUST target)

### 1. Symmetric / hashing — already quantum-acceptable (the floor)

- **AES-256-GCM minimum** for bulk encryption. Never AES-128 in new code (verify it
  does not sneak into DTLS-SRTP profiles either). Grover only halves AES-256 to
  ~128-bit — **safe**. No fear-based AES messaging.
- **SHA-256 / SHA-384, HKDF-SHA256, scrypt** for hashing/KDF — Grover-only, fine.

### 2. Key exchange / KEM — hybrid post-quantum (the HNDL fix)

- **Target: hybrid X25519 + ML-KEM-768 (FIPS 203).** The **-768 tier** is the
  internet default (matches TLS `X25519MLKEM768` and Signal PQXDH).
- **Universal combiner (never deviate):**
  ```
  shared_key = HKDF-SHA256( X25519_ss || ML-KEM-768_ss, info = "<context-label>" )
  ```
  Concatenate-then-KDF. **Never XOR, never replace** classical with PQ. Secure if
  *either* primitive holds.
- Reserve **ML-KEM-1024** only for a sovereign root (where size/perf is irrelevant
  and blast radius is catastrophic).

### 3. Signatures — hybrid post-quantum (deferrable, Phase 2)

- **Target: ML-DSA-65 + Ed25519 hybrid** (FIPS 204), either-or verify during
  transition. **SLH-DSA-SHAKE-256** (FIPS 205, hash-only) for a rarely-rotated
  sovereign root. Keep classical keys **additive/reversible** — never remove them
  while interop is in flux.

### 4. Crypto-agility — MANDATORY for new components

> **Full pattern: [CRYPTO_AGILITY_STANDARD](./CRYPTO_AGILITY_STANDARD.md)** — self-describing
> wire tags, capability-advertisement + downgrade-safety, how to register and roll to the
> *next* KEM/signature without a flag-day, and the named anti-patterns. The bullets here
> are the summary.

- **Machine-readable suite id on every crypto container** (envelope, key, ciphertext).
  Example: `sig_suite="mldsa65-ed25519-v2"`, `kem_suite="x25519-mlkem768-v2"`,
  `epoch=N`. Algorithm choice is **config-driven, never hard-coded**.
- **Suite registry** (`suite_id → {kem, sig, kdf, aead, params}`) — policy/mechanism
  separation. The next migration becomes a registry entry + a negotiation, not a flag-day.
- **One backend abstraction** (a `CryptoBackend`-style ABC) routing all
  sign/verify/encrypt/decrypt — so hybrid + classical can coexist during rollout.
- **Downgrade protection:** PQ material is optional until **both** peers advertise
  support via a **signed** capability flag (never an unauthenticated header), then
  **locks in for the session.**

### 5. Self-report (claim evidence) — MANDATORY

- A component MUST be able to report, **per live channel**, the negotiated
  KEM / signature / cipher and **hybrid-vs-classical**, citing FIPS 203/204/205
  (e.g. extend `sksecurity status` / `skcapstone doctor`). **This is what makes
  every claim evidence-backed rather than asserted.**

---

## Honest-claim rules (ecosystem-wide)

Every external quantum-resistance claim MUST cite **the surface + the FIPS number +
hybrid-vs-classical**, backed by the self-report. **No claim without evidence.**

**Forbidden words / claims:**

- ❌ "quantum-proof" / "unbreakable" / "quantum-safe encryption" — say
  **"quantum-resistant"** or **"post-quantum,"** never "-proof."
- ❌ "end-to-end quantum-resistant" while any leg is classical (CF→origin, tailnet
  handshake, LiveKit DTLS, PGPy-signed payloads). **Scope every claim to the exact surface.**
- ❌ "PQC" when only signatures migrated — that does nothing for HNDL.
- ❌ "CNSA 2.0 compliant" — we use the **-768 hybrid tier**, not the CNSA level-5
  ceiling (ML-KEM-1024 / ML-DSA-87). CNSA 2.0 is an *aspirational reference bar*, not a claim.
- ❌ "FIPS 206 / Falcon" — draft-stage; not claimable yet.
- ❌ Implying **AES-256 is "broken" by quantum** — it is not.

---

## Maturity tiers (self-assessment for any component)

| Tier | Meaning |
|---|---|
| **T0 — Classical** | Asymmetric crypto is classical (X25519/Ed25519/RSA). Symmetric is AES-256/SHA-2. Most components today. |
| **T1 — Agile** | Suite-ids on all containers + suite registry + backend ABC + self-report. No new algorithms yet. (Phase 0.) |
| **T2 — Hybrid KEM** | Key exchange / key-wrap / at-rest use `HKDF(X25519 ‖ MLKEM768)`. HNDL neutralised. (Phase 1.) |
| **T3 — Hybrid sig** | Signatures use ML-DSA-65 + Ed25519 (additive); root has an SLH-DSA option. (Phase 2.) |
| **T4 — Transport closed** | Edge-to-origin TLS hybrid (OpenSSL 3.5+); residual classical legs (tailnet/media) documented. (Phase 3.) |

**Minimal viable PQ posture = T1 + T2** (Phase 0 + 1). That unlocks the real claim
and neutralises HNDL on everything we own.

---

## The browser / Flutter PQC constraint (know this before you ship a web client)

- **WebCrypto has NO PQC API in any browser (2026).** A PWA cannot get app-layer
  ML-KEM from the platform.
- **Native (Flutter/desktop): solved** via FFI to liboqs (`oqs` / `mlkem_native`) —
  but ship the native binary **per-platform in CI**.
- **Web: not solved by the platform** — options are WASM-liboqs (own the audit risk),
  pure-Dart/JS (more audit risk), or server-side KEM with a **disclosed**
  reduced-assurance web leg. **No web client may claim it is E2E PQ.**

---

## Reference: per-component crypto views

| Component | Crypto doc | Owns surfaces |
|---|---|---|
| **skchat** | `docs/crypto-architecture.md` | group-key distribution, 1:1 DM, at-rest store |
| **skcomms** | `docs/crypto-architecture.md` | SignedEnvelope sig, envelope payload wrap |
| **capauth** | `docs/CRYPTO_SPEC.md` + quantum-resistance section | root identity, DID/challenge sig, OpenPGP composites |
| **sksecurity** | `docs/QUANTUM_RESISTANCE.md` | crypto inventory + runtime self-report (claim evidence) |

**Epic:** `PQC-MIGRATION` (coord `e1d6ba2a`), tag `quantum-resistance` — runs
alongside the comms-suite epic, side-tabbable.

---

## Appendix — primitive cheat-sheet

- **KEM:** ML-KEM-768 (FIPS 203) — pk ~1184 B, ct ~1088 B, ~33× X25519. ML-KEM-1024 only for the root.
- **Sig:** ML-DSA-65 (FIPS 204) — pk ~1952 B, sig ~3309 B, ~50× Ed25519. SLH-DSA (FIPS 205) — hash-only, large/slow, **root-of-trust only**.
- **Symmetric (keep):** AES-256-GCM, SHA-256/384, HKDF, scrypt — Grover-only, quantum-acceptable.
- **Hybrid combiner (always):** `HKDF-SHA256( X25519_ss ‖ MLKEM768_ss, info=context )`. Never XOR, never pure-PQ.
