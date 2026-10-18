# FWE Agent Operating Standard

**Status:** Binding for every agent (Claude, Codex, Jarvis, Pi, and any later seat)
that touches the FWE matter pipeline. Architecture lives in
[`FWE_MATTER_DOCUMENT_GENERATION_STANDARD`](./FWE_MATTER_DOCUMENT_GENERATION_STANDARD.md);
URLs and commands live in [`FWE_ONBOARDING_QUICKREF`](./FWE_ONBOARDING_QUICKREF.md).
Decisions D1 to D5 below were made by Chef on 2026-10-18.

**Why:** On 2026-10-17 an agent working for Casey built a parallel offline publishing
process because nothing told it that Windmill and the stage-machine worker existed. In
the same session it merged four PRs into `main`, rolled worker images (one with no PR),
and edited and rearranged live matters and the Team Folder in place. A worker pin on
`main` drifted from the image that was live. Nobody was malicious; the agent had
credentials, a goal and no map. Rules written for a human who "would just know" do not
bind an agent, so these are written to be read cold and followed literally.

---

## 1. Product rules (binding, from Casey's session of 2026-10-17)

1. The original FWE course examples are the reference. **Never invent wording or forms.**
   When the source does not show the full form, **HOLD** instead of guessing, and ask.
2. FWE-only. The saved 2011 candidate forms are comparison evidence, not templates.
   UCC1Ad, UCC3 and the no-trespass sign stay on HOLD. The 17 held branches stay held.
3. Replace a file only after verification, and **archive the original first**.
4. Signature blocks omit the ZIP where the source says so. Plain address blocks. Exact
   presentment text, no added brackets.
5. Missing input means HOLD with **no document body**. A changed fact cancels earlier
   approval.
6. Every draft gets supervised review against the source, the facts and the real DOCX
   and PDF. An AI review is not a human or legal review. **Nothing is mailed without a
   person's sign-off.**
7. Work lives in Nextcloud. A case counts as **delivered only after a fresh download
   matches its hash.**
8. No reboot and no service stop without saved work and an owner's approval.

---

## 2. Decisions D1 to D5

| Id | Decision | What it means for you |
|---|---|---|
| D1 | No agent merges to `main`, rolls images, or writes into Nextcloud `Matters/` directly. Everything goes through PRs reviewed by another lane and through Windmill flows. Approvals happen in Windmill | Section 3 and section 4 |
| D2 | One named person approves per matter: Casey (Authentik `mrarchitect`, Windmill `caseyjr@kobez.net`) or Chef (`chefboyrdave2.1`, `chefboyrdave2.1@gmail.com`), signed in through SSO | An agent is never the approver; "approved by agent" is not a state |
| D3 | Practice and study material moves to the documented top-level `Matters/Library/`. In progress (2026-10-18) | Do not create new top-level folders in `Matters/`; put study material under `Library/` |
| D4 | For now use the existing example matters FWE-2026-0004 to 0008. Real and sample matters come later through `Matters/Intake/FWE/` | Do not invent new matter numbers to test with |
| D5 | Credential rotation happens at a quiet moment and values go to skvault. The coordinator does this | Do not rotate, and do not paste values anywhere |

---

## 3. The only allowed write paths

| You want to change | Allowed path | Not allowed |
|---|---|---|
| Matter content in `Matters/<id>/` | Request the worker through a Windmill flow (`f/fwe/inquiry`, `f/fwe/advance`), or drop a request in `Matters/Intake/FWE/` | Any direct WebDAV or `occ` write, scripts that compose and publish packages, editing a generated file in place |
| Worker behavior, flows, corpus, templates | A branch in your own git worktree, a PR on skgit, **reviewed by a different lane** than the author | Pushing to `main`, merging your own PR, reviewing your own PR |
| What runs on NAM | Build the image on NAM, push to skreg, put the new **tag and digest** in `deploy/fwe/stack.yml` through a reviewed PR, then `docker stack deploy` from the manager | `docker service update --image` by hand, a tag-only reference, deploying the file from an unmerged branch |
| Templates in `Matters/Templates/FWE/` | Edit in hammerTime; the scheduled publish copies it (in progress, 2026-10-18) | Editing the Nextcloud copy. The repo is the source of truth |
| Study material | `Matters/Library/` | New top-level folders in `Matters/` |

The Windmill flow is the write path for matter content because it is the only path
that goes through step checks, replay keys, labels, mailing checklists and calendar
reminders.

---

## 4. Never

1. Never write directly into `Matters/` (D1). The worker is the only writer of matter
   folders. Reading is fine.
2. Never merge or deploy your own work. Open the PR, report it, stop.
3. Never invent a form, a clause, or a wording. HOLD and ask (section 1, rules 1 and 5).
4. Never call `/v1/responses` for GLM. It EOL-gates the model. Use chat completions.
   Keep to one GLM agent at a time.
5. Never reboot a host or stop a shared service without saved work and an owner's
   approval.
6. Never change the Team Folder mount name `Matters` or the intake path
   `Matters/Intake/FWE`. The worker breaks.
7. Never edit or "improve" an example matter in place. Re-run it through the flow; the
   original is archived by the pipeline, not by hand.
8. Never print, log, commit or paste a secret value, including the Windmill token, the
   worker token, the Nextcloud password and the Authentik client secret.
9. Never deploy `deploy/fwe/stack.yml` under the `skflow-prod` stack name, and never
   redeploy the shared Windmill stack from FWE work.
10. Never treat a green test run as proof until you know whether the private fonts and
    the border image were present. Without them 113 tests error and 6 render tests skip
    silently.
11. Never use em or en dashes in code comments, docs, commits, generated text or
    calendar text. The worker strips them from new drafts; do not add them back.
12. Never build a second process. If you need a gate the worker lacks, write it into
    the worker (PR) or the Windmill flow (PR), not beside them.

---

## 5. How to start a new matter

Two supported ways. Both end at the same worker.

1. **Intake.** Put the scan (PDF, PNG or JPEG) in `Matters/Intake/FWE/` and, next to
   it, a sidecar named `<same-name>.request.json`. The worker acts only on the sidecar;
   a bill dropped alone is never processed and the worker never guesses a process.

   ```json
   {
     "corpus_id": "freedom-with-equity",
     "process_id": "inquiry-candidate",
     "source_path": "Matters/Intake/FWE/<scan-name>.pdf",
     "matter_id": "FWE-2026-NNNN-<slug>",
     "facts": {"provider": "...", "due_date": "YYYY-MM-DD"},
     "calendar_owners": ["chefboyrdave2.1", "mrarch"]
   }
   ```

   `f/fwe/poll-intake` picks it up every minute. Check the highest `NNNN` for the year
   in `Matters/` and `Matters/Closed/` first. The matter id pattern is
   `FWE-YYYY-NNNN-<slug>` (slug: lowercase letters, digits, hyphens, up to 48).
   Required facts for the inquiry, acceptance and dishonor processes are listed in
   `deploy/fwe/README.md` ("Indexed candidate generation").
2. **Windmill form.** The "New FWE matter" form in workspace `fwe` lets a person start
   a matter with no agent. In progress (2026-10-18).

Do not set `"demo": true` on real matters. Missing facts produce `needs-information`
with the field list in `Audit/status.json`; supply them with the same matter id.

---

## 6. Approvals and release

- Generation produces a **candidate** draft, visibly marked. Generation, a typography
  check or an AI review never clears candidate status.
- A release decision belongs to **one named person per matter** (D2), signed in to
  Windmill through Authentik SSO so the approval carries a real name. The Windmill
  approval step is **in progress (2026-10-18)**; until it is deployed, release is
  recorded by that person in the matter, and no agent substitutes for them.
- A changed fact (any fact an earlier step used) returns 409 and cancels earlier
  approval. Re-approval is required.
- After the person approves: correct labels for the step, mailing by the chosen
  `mail_method` (certificate of mailing PS Form 3665 by default, or certified PS 3800
  and 3811), scan proof into `Mailing/`, then `/advance` to the next stage. Never infer
  mailing from generation.

---

## 7. Working discipline

1. **Own worktree, own branch.** Never switch the branch of, or edit files in, a shared
   checkout (the hammerTime checkout on chiap08 is an OneDrive mount with uncommitted
   edits owned by someone else).
2. **Commit before verify.** Commit as soon as the code is written and a fast check
   passes, push the branch to skgit, and only then run the long test suite. Amend or add
   a follow-up commit afterwards. A lane is not done until the work is a commit on a
   pushed branch with a PR. Uncommitted work is not saved work.
3. **Commit trailer** names the agent that did the work. Never add a co-author line you
   cannot evidence.
4. **Verify by a different path than you wrote.** Wrote a file: download it again and
   hash it. Wrote a calendar event: read it back over CalDAV. Pinned an image: compare
   the digest from `docker service inspect`. A tool that exits 0 is not evidence.
5. **Report with evidence:** commit SHAs, PR numbers, exact test counts (passed,
   failed, skipped), whether the private assets were present, job ids of Windmill runs,
   and what you did not verify. Under 700 words.
6. **Clean up** worktrees, temp files and background processes you started.
7. **Read shared state before touching it:** the skmail thread, `git log`, the Windmill
   run list, `docker service ls`.

---

## 8. Where credentials live

Names only; values are never written in any repo or report.

| What | Where |
|---|---|
| Windmill API deploy token (workspace `fwe`, expires 2026-11-16) | Handed to a lane in a `0600` file by the coordinator; stored in skvault. Never print it |
| Worker bearer token | Windmill secret variable `f/fwe/worker_token`; Swarm secret `skflow_fwe_worker_token_v1` |
| Nextcloud `svc-fwe` password | Swarm secret `skflow_nextcloud_password_v1`, mounted at `/run/secrets/nextcloud_password` in the worker |
| Qdrant API key | Swarm secret `skfwe_vector_api_key_v1` |
| Authentik `skflow-windmill` client secret | skvault, coordinator only |
| `GOG_KEYRING_PASSWORD` and other estate secrets | skvault |

If you need a value you do not have, ask the coordinator. If you find a value exposed in
output or a file, say so in your report and do not repeat it.

---

## 9. Checks

| Rule | How to check |
|---|---|
| Nothing wrote to `Matters/` outside the worker | The worker issues only `MKCOL`, `PUT`, `GET`, `PROPFIND`. Walk the matter tree (PROPFIND) and compare every file's hash and modification time against its manifest; a file with no manifest entry, or a changed hash, was written outside the worker |
| Every file matches its manifest | Download and sha256 against `generation-manifest.json` |
| Deployed image equals reviewed pin | `docker service inspect` digest equals `deploy/fwe/stack.yml` on `main` |
| No unreviewed merge | skgit PR list: every merged FWE PR has a reviewer who is not its author |
| No dashes in new output | `test_new_output_dashes.py`; CI that makes a missing asset fail is in progress (2026-10-18) |

---

## Related standards

- [FWE_MATTER_DOCUMENT_GENERATION_STANDARD](./FWE_MATTER_DOCUMENT_GENERATION_STANDARD.md): the system these rules protect.
- [FWE_ONBOARDING_QUICKREF](./FWE_ONBOARDING_QUICKREF.md): URLs, paths and commands.
- [AUTONOMY_STANDARD](./AUTONOMY_STANDARD.md): machine-written code merges only through the twin gate; a human holds the freeze.
- [CODING_LANES_STANDARD](./CODING_LANES_STANDARD.md): one merge bar across coding lanes.
- [PROVENANCE_AND_MUTATION_STANDARD](./PROVENANCE_AND_MUTATION_STANDARD.md): fast requires reversible; reversible requires attributable.
- [ACTION_AUTHORIZATION_STANDARD](./ACTION_AUTHORIZATION_STANDARD.md): approval is a separate store from the log of what happened.
