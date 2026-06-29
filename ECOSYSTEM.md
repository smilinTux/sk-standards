# The sk-pqc ecosystem map 🗺️

A single navigable map of the whole `sk-pqc` family — every repo, one line on what
it *is*, and the **edges** (`depends-on` / `backs` / `verifies` / `governs`) that tie
them together. Read this top-to-bottom once and you know where everything lives; then
click any box and keep wandering (every repo's README ends in `## Related projects /
See also`, à la a hyperlinked wiki).

> **Reality, not aspiration.** Edges that are *live today* are solid; edges that are
> **roadmap / in-flight** are drawn dashed and labelled. Where a repo says one thing
> and ships another, this map follows what ships. If it drifts, fix it here.

> **Honesty banner (applies to the whole map).** Every confidentiality surface below is
> **hybrid** `x25519-mlkem768`: a derived secret holds if **EITHER** the classical
> X25519 leg **OR** the ML-KEM-768 leg (**FIPS 203**) survives — "either-leg", not
> "quantum-proof", not "quantum-safe", not "unbreakable". Signatures, where present, use
> ML-DSA (**FIPS 204**). We never overclaim; see
> [`CRYPTOGRAPHY_STANDARD`](./standards/CRYPTOGRAPHY_STANDARD.md).

---

## The map

```mermaid
flowchart TD
    STD[📐 sk-standards<br/>the standards everything conforms to]:::std

    subgraph contract[The interop contract]
      VEC[sk-pqc-vectors<br/>frozen golden KAT vectors<br/>the byte-for-byte CONTRACT]:::contract
    end

    subgraph core[Hybrid PQC core · 3 sibling impls · all import as sk_pqc]
      PY[sk-pqc-py<br/>Python · liboqs + pyca<br/>PyPI sk-pqc]:::lib
      RS[sk-pqc-rs<br/>Rust core · RustCrypto<br/>crate sk-pqc]:::lib
      DART[sk_pqc / sk-pqc-dart<br/>Dart/Flutter · noble-pq + liboqs FFI<br/>pub.dev sk_pqc]:::lib
    end

    subgraph pgp[PQC OpenPGP]
      PGP[sk_pgp<br/>Python OpenPGP-PQC<br/>PyO3→Sequoia · ML-DSA/ML-KEM · PGPy replacement]:::lib
    end

    subgraph identity[Identity & security services]
      CAP[capauth<br/>root identity · DID · PQC signing root<br/>crypto home: sign/verify · seal/unseal]:::svc
      SEC[sksecurity<br/>crypto inventory · runtime self-report]:::svc
    end

    subgraph secrets[Secrets & ingestion · seal via capauth]
      SKVAULT[skvault<br/>sovereign KeePass secrets vault<br/>vault_creds/recovery/shamir/totp + lifecycle<br/>PGP-sealed master → gpg-agent]:::svc
      SKINGEST[skingest<br/>pure ingestion · mxbai + skmem-pg<br/>vault split out → skvault]:::svc
    end

    subgraph comms[Messaging framework]
      SKCOMMS[skcomms<br/>FQID addressing · envelopes · transports<br/>pqkem/pqdm/pqroute/pqsig]:::svc
      SKCHAT[skchat<br/>DMs · groups · voice · files · at-rest]:::svc
    end

    subgraph context[Agent context]
      CLOUD9[cloud9<br/>emotional-continuity / trust protocol]:::ctx
      SKMEM[skmemory<br/>multi-layer agent memory + vector search]:::ctx
    end

    INFRA[SKStacks<br/>sovereign deploy fabric]:::infra
    SITES[*.skworld.io sites<br/>skpqc / capauth / skcomms / skchat<br/>sksecurity / skmemory / cloud9 / skstacks<br/>skos / skvault]:::site

    %% --- interop contract: vectors is the parity gate the 3 impls satisfy ---
    PY -. conforms to .-> VEC
    RS -. conforms to .-> VEC
    DART -. conforms to .-> VEC
    VEC ==>|parity gate| PY
    VEC ==>|parity gate| RS
    VEC ==>|parity gate| DART

    %% --- core backs the daemons / clients ---
    PY -->|backs · optional extra + vendored fallback| SKCOMMS
    PY --> SEC
    DART -->|backs the Flutter client| SKCHAT
    RS -. FFI roadmap .-> PY
    RS -. FFI roadmap .-> DART

    %% --- pgp backs the signing root (roadmap; PGPy today) ---
    PGP -. replaces PGPy in .-> CAP

    %% --- capauth.seal backs the vault + ingestion (skvault split out of skingest) ---
    CAP -->|seal/unseal for| SKVAULT
    CAP -->|seal/unseal for| SKINGEST

    %% --- identity + transport + trust assemble the chat app ---
    CAP -->|identity for| SKCOMMS
    CAP -->|identity for| SKCHAT
    SKCOMMS -->|transport for| SKCHAT
    CLOUD9 -->|trust for| SKCHAT
    SKMEM -.->|context for| SKCHAT

    %% --- security reports on the crypto surfaces ---
    SEC -. reports on .-> SKCOMMS
    SEC -. reports on .-> SKCHAT
    SEC -. reports on .-> CAP

    %% --- infra + sites + governance ---
    INFRA -. deploys .-> comms
    INFRA -. deploys .-> identity
    SITES -. document .-> core
    SITES -. document .-> comms
    STD -. governs .-> contract
    STD -. governs .-> core
    STD -. governs .-> pgp
    STD -. governs .-> identity
    STD -. governs .-> secrets
    STD -. governs .-> comms

    classDef std fill:#3a2d00,stroke:#ffa500,color:#fff;
    classDef contract fill:#2a1a00,stroke:#fbbf24,color:#fff;
    classDef lib fill:#06281e,stroke:#34d399,color:#fff;
    classDef svc fill:#0a1a2a,stroke:#67e8f9,color:#fff;
    classDef ctx fill:#0a2a1a,stroke:#86efac,color:#fff;
    classDef infra fill:#1a0a2a,stroke:#c084fc,color:#fff;
    classDef site fill:#241a2a,stroke:#d8b4fe,color:#fff;
```

**How to read the edges**

| Edge | Meaning |
|---|---|
| **`A ==> parity gate ==> B`** | `A` (the vectors) is the byte-for-byte gate impl `B` must pass; `B` `conforms to` `A`. |
| **`A --> backs --> B`** | `B` builds its crypto on `A` *today* (live dependency). |
| **`A --> identity/transport/trust for --> B`** | `A` supplies that capability to `B` *today*. |
| **`A -. roadmap / replaces .-> B`** | planned / in-flight, **not live yet** (Rust FFI; `sk_pgp`→capauth). |
| **`A -. reports on / deploys / documents / governs .-> B`** | cross-cutting relation (audit, infra, docs, standards). |

---

## The repos

### Standards & contract
| Repo | One line | Relates |
|---|---|---|
| 📐 [**sk-standards**](https://github.com/smilinTux/sk-standards) *(this repo)* | The single source of truth — crypto / agility / doc / architecture / testing / disclosure standards every `sk*` repo conforms to. | `governs` all. See [`standards/`](./standards/). |
| 🧊 [**sk-pqc-vectors**](https://github.com/smilinTux/sk-pqc-vectors) | The **frozen golden KAT contract** — language-neutral hybrid-KEM + DM-ratchet vectors that every `sk_pqc` impl satisfies byte-for-byte. | `parity gate` for `sk-pqc-{py,rs,dart}`. |

### Hybrid PQC core — three sibling implementations
All import as `sk_pqc`, all interoperable, all conform to `sk-pqc-vectors`. None is a
wrapper of another *today*: each binds vetted primitives directly (the Rust→Python/Dart
FFI is a roadmap, not a live edge).
| Repo | One line | Relates |
|---|---|---|
| 🐍 [**sk-pqc-py**](https://github.com/smilinTux/sk-pqc-py) | Python hybrid-PQC primitives (KEM · PQXDH seal · routing envelope · DM/group ratchet · anon-queue · suite registry · self-report); ML-KEM-768 leg = `liboqs`, X25519+HKDF+AES-GCM = pyca `cryptography`. T2. | `backs` skcomms (optional extra) + sksecurity; `conforms to` sk-pqc-vectors. |
| 🦀 [**sk-pqc-rs**](https://github.com/smilinTux/sk-pqc-rs) | The sovereign shared **Rust** PQC core (RustCrypto `ml-kem` + `x25519-dalek`); same HKDF labels / AAD / wire layout as Python & Dart. | `conforms to` sk-pqc-vectors; FFI to Py/Dart = roadmap. |
| 🎯 [**sk_pqc** / sk-pqc-dart](https://github.com/smilinTux/sk-pqc-dart) | Dart/Flutter hybrid KEM (X25519 + ML-KEM-768, FIPS 203) — web (`noble-post-quantum`) + native (`liboqs` FFI), in the browser. | `backs` the skchat Flutter client; `conforms to` sk-pqc-vectors. |

### PQC OpenPGP
| Repo | One line | Relates |
|---|---|---|
| 🔏 [**sk_pgp**](https://github.com/smilinTux/sk_pgp) | Sovereign **Python OpenPGP-PQC** (PyO3 bindings to a PQC Sequoia — ML-DSA/ML-KEM, v6 / RFC 9580); the PGPy replacement that lets Python sign with PQC keys. | roadmap `replaces PGPy in` capauth. |

### Identity & security services
| Repo | One line | Relates |
|---|---|---|
| 🔑 [**capauth**](https://github.com/smilinTux/capauth) | Sovereign root **identity / DID / PQC signing root** (auth without OAuth) and the **crypto home**: sign/verify + `seal`/`unseal`. Signs on PGPy today; `sk_pgp` is the slated PQC cutover. | `identity for` skcomms + skchat; `seal/unseal for` skvault + skingest; consumes `sk_pgp` (roadmap). |
| 🛡️ [**sksecurity**](https://github.com/smilinTux/sksecurity) | Crypto **inventory + runtime self-report** — the claim-evidence engine: what suites a daemon actually advertises vs claims. | `reports on` skcomms / skchat / capauth; consumes sk-pqc-py self-report. |

### Secrets & ingestion
| Repo | One line | Relates |
|---|---|---|
| 🔐 [**skvault**](https://github.com/smilinTux/skvault) | The sovereign **secrets vault** — a KeePass DB whose master is **PGP-sealed to the sovereign identity** and unlocked into `gpg-agent`; `vault_creds` / `recovery` / `shamir` / `totp` + lifecycle. User-facing as the stable `skvault` shim (`unlock\|lock\|status\|get\|list\|creds-*\|vault-*`). Split out of skingest (EPIC `11eeac9e`). | `seal/unseal` via capauth; consumed by skos.secrets / skguide / `.claude` hooks. |
| 📥 [**skingest**](https://github.com/smilinTux/skingest) | **Pure ingestion** (mxbai-embed + skmem-pg + wiki-canon). **No longer owns the vault** — secrets moved to skvault; skingest now only seals its own artifacts via `capauth.seal`. | `seal` via capauth; sibling of skvault. |

### Messaging framework
| Repo | One line | Relates |
|---|---|---|
| ✉️ [**skcomms**](https://github.com/smilinTux/skcomms) | Sovereign realm-aware **comms protocol + transports** (FQID addressing, BLE/LoRa mesh, capauth-signed envelopes; pqkem/pqdm/pqroute/pqsig surfaces). | `transport for` skchat; `backs` on sk-pqc-py (optional extra, vendored fallback); identity from capauth. |
| 💬 [**skchat**](https://github.com/smilinTux/skchat) | AI-native **encrypted chat** for humans + AI — DMs, groups, voice, files, at-rest. Built on skcomms, capauth identity, Cloud 9 trust. | consumes skcomms + capauth + cloud9 + sk_pqc (Dart client). |

### Agent context (ecosystem neighbours)
| Repo | One line | Relates |
|---|---|---|
| ☁️ [**cloud9**](https://github.com/smilinTux/cloud9) | The **emotional-continuity / trust protocol** (FEB / OOF / Cloud 9 state) preserved across AI session resets. | `trust for` skchat. |
| 🧠 [**skmemory**](https://github.com/smilinTux/skmemory) | Universal **multi-layer agent memory** (git-based flat files + vector search). | `context for` skchat / agents. |

### Infrastructure & sites
| Repo | One line | Relates |
|---|---|---|
| 🏗️ [**SKStacks**](https://github.com/smilinTux/SKStacks) | The sovereign **deploy fabric** — stacks the comms + identity services run on. | `deploys` the services. |
| 🌐 *.skworld.io sites | Landing + docs sites: [skpqc](https://github.com/smilinTux/skpqc-skworld-io) · [capauth](https://github.com/smilinTux/capauth-skworld-io) · [skcomms](https://github.com/smilinTux/skcomms-skworld-io) · [skchat](https://github.com/smilinTux/skchat-skworld-io) · [sksecurity](https://github.com/smilinTux/sksecurity-skworld-io) · [skmemory](https://github.com/smilinTux/skmemory-skworld-io) · [cloud9](https://github.com/smilinTux/cloud9-skworld-io) · [skstacks](https://github.com/smilinTux/skstacks-skworld-io) · [skos](https://github.com/smilinTux/skos-skworld-io) · [skvault](https://github.com/smilinTux/skvault-skworld-io) (`skvault.skworld.io`). | `document` their repos. |

---

## Start here — common paths through the map

- **"I just want hybrid PQC in my app."** → [sk-pqc-py](https://github.com/smilinTux/sk-pqc-py) (Python), [sk-pqc-rs](https://github.com/smilinTux/sk-pqc-rs) (Rust), or [sk_pqc](https://github.com/smilinTux/sk-pqc-dart) (Dart/Flutter). App-agnostic; no messaging framework dragged in.
- **"Are the three impls really interoperable?"** → [sk-pqc-vectors](https://github.com/smilinTux/sk-pqc-vectors): the frozen vectors + `verify.py`. Pass it and a blob one impl seals, another opens.
- **"What's the crypto bar / why no 'quantum-proof'?"** → [`CRYPTOGRAPHY_STANDARD`](./standards/CRYPTOGRAPHY_STANDARD.md) (threat model, hybrid combiner, honest-claim rules, T0–T4 tiers).
- **"How do peers negotiate / roll suites without an undecryptable frame?"** → [`CRYPTO_AGILITY_STANDARD`](./standards/CRYPTO_AGILITY_STANDARD.md) (suite ids, wire tags, downgrade-safety).
- **"I want the messaging stack."** → [skcomms](https://github.com/smilinTux/skcomms) (protocol/transport) → [skchat](https://github.com/smilinTux/skchat) (the app) → [capauth](https://github.com/smilinTux/capauth) (identity) → [cloud9](https://github.com/smilinTux/cloud9) (trust).
- **"Does a daemon's crypto match its claims?"** → [sksecurity](https://github.com/smilinTux/sksecurity) (inventory + self-report) + the [`TESTING_AND_CI_STANDARD`](./standards/TESTING_AND_CI_STANDARD.md) "tests are evidence" gate.

---

*License: Apache-2.0. Maintained by SKWorld (Chef & Lumina). This map is the canonical
ecosystem index; the README's quick graph links here for the full picture.*
