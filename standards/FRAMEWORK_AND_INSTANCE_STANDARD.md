# Framework and Instance Standard (CANONICAL)

> One sentence: **a framework knows how, an instance knows where.** Every reusable SK* system that runs
> on more than one estate ships as one public framework plus one private instance repo per estate, and
> nothing estate-specific ever lands in the framework.

Related: [`SK_REPO_DOC_STANDARD`](./SK_REPO_DOC_STANDARD.md) (what each repo's docs contain),
[`DOCS_FRESHNESS_STANDARD`](./DOCS_FRESHNESS_STANDARD.md) (the docs gate both sides run),
[`ITIL_AND_RUNBOOK_OPERATING_MODEL_STANDARD`](./ITIL_AND_RUNBOOK_OPERATING_MODEL_STANDARD.md) (the ops canon
is an instance under this standard), [`VERSION_LIFECYCLE`](./VERSION_LIFECYCLE.md) (release tags).

Systems that follow it today: skstacks (`<estate>-prod` instances), skrsi (`skrsi-config-<estate>`),
skbrain (`skbrain-ops-<estate>`).

---

## 0. Definitions

- **Estate:** one operator's whole sovereign install (its nodes, services, agents and people). Estates share
  source code through public git only, never state, files or credentials.
- **Framework:** the public repo that holds mechanism: code, schemas, validators, templates, docs.
- **Instance:** the private repo, one per estate, that holds that estate's facts: names, numbers,
  configuration, content.

## 1. The golden rule (MUST)

If another operator running a different estate would want the change, it goes in the framework. If it names a
node, host, address, domain, person, client, estate or a number measured on one estate, it goes in the instance.
When both are true the change is split: the mechanism to the framework, the values to the instance.

## 2. The framework (MUST)

1. Public, Apache-2.0 unless the owner records otherwise, with the full `SK_REPO_DOC_STANDARD` doc set.
2. Released as annotated tags (`<name>-vX.Y.Z`). Instances pin tags, never branches.
3. Ships a generated, public **instance template** (`<name>-config-template` or `<name>-ops-template`) built
   from a fixture inside the framework by a script. The template is never hand-edited, and its fixture uses a
   fake estate (`example`).
4. Runs a **scrub check** in CI on every PR and before every tag: no IP addresses, no non-example domains, no
   home or mount paths, no tailnet addresses, no em or en dashes, plus an operator denylist (node, person and
   estate names) supplied from outside the repo. A release run without the denylist fails closed.
5. Owns the schema of the instance config file and validates it (unknown fields fail).

## 3. The instance (MUST)

1. Private. One per estate, never one per node or per service. Name `<name>-<estate>` or `<name>-config-<estate>`.
2. Hosted on the estate's own forge where the estate has one. Where it does not, it may be hosted on another
   estate's forge only behind team-scoped access (section 5), and its SECURITY.md says so.
3. Pins the framework as a git submodule at `framework/`, checked out at a release tag, and records the same tag in
   its config file. A doctor or CI check fails when the installed version, the config and the submodule disagree.
4. Holds no framework code. A fix found in an instance is upstreamed to the framework, then the pin is bumped.
5. Upgrades are a PR that bumps the submodule and the config together; CI runs the NEW framework's checks against
   the instance before merge. Roll estates one at a time.
6. Protected default branch: no direct push, at least one approval from an identity other than the author.

## 4. Lessons that apply to more than one estate

A lesson learned in one estate that applies to others is written, scrubbed, into the framework docs by PR. It is
never copied into another estate's instance. Instances link to the framework lesson.

## 5. The estate wall on a shared forge (MUST)

- Agents and bots get access through per-estate teams scoped to that estate's repos. No agent or bot identity is a
  member of an org-wide owner team.
- No credential of one estate (tokens, SSH keys, passwords) is stored on another estate's hosts. A host that needs
  forge access uses its own estate's identity.
- A service projects or indexes only its own estate's instance, on its own estate's nodes.

## 6. Compliance checklist

- [ ] Framework is public, tagged, has a generated template and a fail-closed scrub check.
- [ ] Each estate has exactly one private instance, pinning a tag as `framework/`, config validated by the framework.
- [ ] Version agreement (installed = config = submodule) is checked.
- [ ] Default branches are protected with a second-identity approval.
- [ ] Forge access is per-estate team scoped; no agent is an org owner; no cross-estate credentials.

## 7. What this standard does not claim

It does not say which forge to use, and it does not make two estates on one forge as strong a wall as two forges.
Access control is the wall in that case; backups of a shared forge hold both estates.
