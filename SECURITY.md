# Security Policy - sk-standards

`sk-standards` is a docs-and-reference repo. It has no runtime, no listener, no
credential, and no key material, so it is **not a crypto component** and declares no
maturity tier or PQC posture of its own. It *governs* the crypto standards rather than
implementing them:
[CRYPTOGRAPHY_STANDARD](./standards/CRYPTOGRAPHY_STANDARD.md),
[CRYPTO_AGILITY_STANDARD](./standards/CRYPTO_AGILITY_STANDARD.md), and
[SECURITY_DISCLOSURE_STANDARD](./standards/SECURITY_DISCLOSURE_STANDARD.md), which is
the process this file implements for itself.

> **It still has a real attack surface, and it is a supply-chain one.** This repo ships
> two reusable GitHub Actions workflows and the Python validators behind them, which
> **other repos execute inside their own CI**, by default at `@main`. A change merged
> here runs in every consumer's next CI job with no action on their part. Read "Threat
> model" before deciding this repo is harmless because it is "just docs".

---

## Threat model

### In scope

| Surface | Why it matters |
|---|---|
| `.github/workflows/docs-check.yml`, `.github/workflows/ci-gate-check.yml` | The two reusable gates. Consumers call them as `uses: smilinTux/sk-standards/.github/workflows/<name>.yml@main`. A malicious or mistaken merge to `main` executes in every consumer's CI on their next run. |
| `scripts/docs_check.py`, `scripts/ci_gate_check.py` | Fetched by those workflows at `standards-ref` (default `main`) and run against the consumer's tree. Same blast radius. `ci-gate-check.yml` additionally runs `pip install pyyaml==6.0.2` in the consumer's runner. |
| `scripts/check_fences.py`, `scripts/audit-service-units.sh` | Run by hand or in CI by whoever adopts them. `audit-service-units.sh` reads a live host through `systemctl`; `ci_gate_check.py sweep` shells out to `gh` and writes a state file under `~/.skcapstone/state/`. |
| `reference/ingress/*` | People **copy these into production ingress**. A weakened `Caddyfile`, `traefik-dynamic.yml`, `cloudflared-config.yml`, or `capauth_gate.py` gate decision would propagate as a real exposure, not a doc bug. The public-by-design prefix list in `capauth_gate.py` is the sharpest edge here. |
| `reference/systemd/*`, `reference/skworld-module/skworld.module.schema.json` | Same copy-paste propagation: a drop-in that disables a restart limiter, or a schema that stops requiring the signature field. |
| The security guidance in `standards/*.md` | An incorrect rule that gets adopted fleet-wide is a vulnerability with a long fuse. Report a materially wrong security instruction the same way you would report code. |

### Known, accepted risks (named rather than hidden)

1. **Tier 3 executes strings from the consumer's own `SOP.md`.** `docs_check.py` runs
   each `docs-evidence` `run:` line with `bash -lc` in the checked-out repo. That is the
   design: the consumer authors those commands. The consequence is that a pull request
   which edits `SOP.md` can execute code in the consumer's CI runner. The reusable
   workflow limits the damage by requesting `permissions: contents: read` and consuming
   **no secrets**, so a fork PR gets an ephemeral runner and a read-only token.
   **Do not call this gate from `pull_request_target`, and do not grant it write
   permissions or secrets.** That combination would turn an author-controlled command
   into a repo-write primitive.
2. **`@main` is an unpinned dependency.** The documented consumer snippet pins the
   floating `main` ref, which is what makes fleet-wide rule changes propagate. If you
   need reproducibility over propagation, pin the `uses:` line to a commit SHA, or pass
   `standards-ref: <sha>`. This is the reason branch protection on `main` here is the
   single highest-value control for this repo.
3. **`ci-gate-check.yml` installs a package into the consumer's runner.**
   `pip install pyyaml==6.0.2` runs in the consumer's CI. The version is pinned, but it
   resolves from PyPI at job time with no hash pin, so a compromised PyPI artifact for
   that exact version would execute there. `docs-check.yml` installs nothing, which is
   why both `docs_check.py` and `check_fences.py` are kept stdlib-only.
4. **Third-party actions are tag-pinned, not SHA-pinned.** `actions/checkout@v4`,
   `actions/setup-python@v5`, and `lycheeverse/lychee-action@v2` follow moving major
   tags. A compromised upstream tag would run here.
5. **The gitleaks binary is downloaded without checksum verification.**
   `secret-scan.yml` pipes a GitHub release tarball straight into `tar -xz -C
   /usr/local/bin`. The version is pinned (`GITLEAKS_VERSION: 8.28.0`) and the transport
   is HTTPS, but there is no signature or hash check on the artifact.

Items 3, 4, and 5 are honest gaps, not mitigations. They are reported here rather than
implied away.

### Out of scope

- **Vulnerabilities in a consumer repo.** If `docs-check` failed to catch something in
  `skchat`, report it to `skchat`. Report it here only if the *gate itself* is wrong.
- **Third-party tools the reference configs configure.** Caddy, Traefik, cloudflared,
  Tailscale, gitleaks, lychee, and the GitHub Actions above are upstream. Report there;
  we will track and bump.
- **The upstream actions and binaries themselves** (see above), beyond our choice of
  how to pin them, which *is* in scope.
- **Theoretical findings with no realisable impact** on a supported configuration.
- **Style, wording, or disagreement with a standard's substance.** That is a pull
  request or an issue, not a vulnerability report.

---

## Secret handling and dependency posture

- **This repo holds no secret.** It provisions none, consumes none, and needs no repo or
  org secret to run its CI. `secret-scan.yml` deliberately runs the gitleaks **binary**
  rather than `gitleaks-action`, which requires a paid license for organization-owned
  repos and exits before scanning a single byte. A fleet repo carried exactly that gate
  for months: permanently red, therefore ignored, and scanning nothing at all.
- **The scan covers the full history**, not just the tip (`fetch-depth: 0`, `gitleaks
  detect --source .`). The history scanned **clean on 2026-08-14**. If it goes red, a
  secret was **added**: rotate it and purge it. Do not weaken the gate to an incremental
  scan.
- **Runtime dependencies: almost none.** `docs_check.py` and `check_fences.py` are
  stdlib-only by design, so the `docs-check` gate cannot fail for the wrong reason on a
  minimal runner. The single exception is `ci_gate_check.py`, which needs PyYAML to
  parse workflow files; `ci-gate-check.yml` pins it as `pyyaml==6.0.2`. There is no
  lockfile, because a one-package pin in one workflow is the whole dependency set.
- **Never inline a live secret in a reference config.** `reference/ingress/*` and
  `reference/systemd/*` are copy-paste templates; a placeholder that looks like a
  credential will end up in someone's production tree.

---

## Supported versions

This repo has **no releases and no tags** (verified 2026-08-14). There is nothing to
backport to.

| Ref | Supported |
|---|---|
| `main` | Yes. Fixes land here, and consumers pinned to `@main` receive them on their next CI run. |
| A pinned commit SHA | No. A pinned consumer is frozen by choice and is **not** patched retroactively. Re-pin to pick up a fix. |

Consistent with
[VERSION_LIFECYCLE](./standards/VERSION_LIFECYCLE.md): the active line always gets
fixes. Here the active line is the only line.

---

## Reporting a vulnerability

**Do not open a public GitHub issue for a security vulnerability.**

- **Primary:** GitHub **private vulnerability reporting** on
  [`smilinTux/sk-standards`](https://github.com/smilinTux/sk-standards) (Security tab,
  "Report a vulnerability"). This keeps the report, the fix, and the advisory in one
  place.
- **Secondary (out of band):** contact the maintainers (smilinTux / SKWorld) via the
  address on the GitHub organization profile, and encrypt sensitive reports to the
  maintainer's sovereign capauth / `sk_pgp` key, whose fingerprint is published on that
  profile. No fingerprint is duplicated inline here, because a stale fingerprint in a
  second place is worse than one canonical copy.

Please include: the file and line, whether the issue is in the gate, a script, a
reference config, or a standard's text, and what a consumer repo would experience.

We aim to **acknowledge within 72 hours**, and to ship a fix or mitigation within 90
days while coordinating a disclosure date. Active exploitation collapses the embargo:
protecting users beats a tidy timeline.

**Safe harbour:** good-faith research conducted under coordinated disclosure will not be
pursued. Credit is given unless you ask otherwise.

### What we especially want to hear about

- A path by which merging to `main` here can obtain **write** access or a **secret** in
  a consumer repo's CI, beyond the read-only, secret-free runner described above.
- A `docs-evidence` command that escapes the runner, or reaches the network or a live
  host, in a way the "hermetic" rule was meant to prevent.
- A reference config in `reference/ingress/` that leaves a surface open which the
  [UNIFIED_INGRESS_STANDARD](./standards/UNIFIED_INGRESS_STANDARD.md) says is gated,
  in particular a public-by-design prefix in `capauth_gate.py` that should not be public.
- A `docs-check` **false green**: a repo that passes the gate while violating the rule
  the gate exists to enforce. A signal that certifies less than it appears to is the
  most dangerous artifact in this ecosystem.
- A standard whose security instruction is materially wrong, such that following it
  creates the exposure it claims to prevent.

---

## Honest-claims note

Per [SK_REPO_DOC_STANDARD section 5](./standards/SK_REPO_DOC_STANDARD.md) and
[SECURITY_DISCLOSURE_STANDARD section 4](./standards/SECURITY_DISCLOSURE_STANDARD.md),
this file claims only what is checkable from the tree:

- "No secrets" is checkable: `grep -rn "secrets\." .github/workflows/` returns nothing,
  and there is no packaging manifest or lockfile in the tree.
- "The gates can fail" is backed by `python3 scripts/docs_check.py --self-test` and
  `python3 scripts/ci_gate_check.py --self-test`, which the respective reusable
  workflows run on every invocation.
- "History clean" is scoped to **2026-08-14**, the date `secret-scan.yml` records, and to
  gitleaks 8.28.0's ruleset. It is not a claim that no secret has ever existed anywhere.
- **Not verified:** whether GitHub private vulnerability reporting is currently toggled
  on for this repo, and whether `main` carries branch protection. Both are repo settings
  invisible from the tree and need an operator with admin access. Given items 1 and 2 in
  "Known, accepted risks", branch protection on `main` is the single highest-value
  control for this repo.
- **Not verified:** `ci_gate_check.py sweep` was not exercised during this pass. Only
  `audit` was run, and it returned clean against this tree on 2026-08-14.

---

**License:** Apache-2.0 (this repo's recorded license, not relicensed).
**Standards:** ISO/IEC 29147 and 30111 (vulnerability disclosure); CVSS v4.0 (severity).
