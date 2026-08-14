# Runbook: `ci-gate-health` fired

Operational response for the [TESTING_AND_CI_STANDARD §6.4](../../standards/TESTING_AND_CI_STANDARD.md)
sweep. Job definition: [`ci-gate-health.yaml`](./ci-gate-health.yaml).
Checker: [`scripts/ci_gate_check.py`](../../scripts/ci_gate_check.py).

**This alert is never a page.** It fires at most every 6h, and every finding it
reports has already been true for hours. Nothing here is a 3am action.

## What the exit code means

| Exit | Meaning | Response |
|---|---|---|
| 0 | No new breakage. Known-red carried silently. | None. Nothing is sent. |
| 1 | **NEW** red gate on `main`. | Triage below. |
| 2 | The sweep could not run. | Fix the monitor. A monitor that cannot run is not a green monitor. |

Exit 2 is the one people dismiss. Treat it as seriously as exit 1: while it
persists you have **no** coverage, and the alert channel is quiet for the wrong
reason. It has two known causes: `gh` unauthenticated on the node, and the vendor
clone missing or stale.

```bash
/usr/bin/gh auth status
git -C ~/.skcapstone/vendor/sk-standards log --oneline -1
~/.skenv/bin/python ~/.skcapstone/vendor/sk-standards/scripts/ci_gate_check.py --self-test
```

## Triage for exit 1

Findings are printed one per line, `NEW` marking what just broke.

### 1. Confirm it is live, not stale

The checker already applies the §6.2 timestamp rule, but confirm before acting,
because acting on a stale red wastes the same time twice:

```bash
gh run list --repo smilinTux/<repo> --branch main --limit 5
gh api "repos/smilinTux/<repo>/commits?path=.github/workflows/<file>&per_page=1" \
  --jq '.[0].commit.author.date'
```

Workflow file touched **after** the failing run means someone already fixed it and
it has not re-triggered. Not breakage.

### 2. Classify it

Use the §6.3 table. The classification decides urgency, and the loudest is not the
worst:

- **Tests never ran** (`ModuleNotFoundError` at collection, `Interrupted: N errors
  during collection`). Highest urgency. The job reported that tests ran when none
  did, so every other signal from that repo is currently worthless.
- **Release-path** (a publish job red, or green while nothing uploads). High. Verify
  on the registry, never on the run.
- **Real failure** (an assertion, a non-zero CLI exit). The gate is working. Read it.
- **Lint debt** ("Found N errors"). Low urgency, but it must not sit: it holds the
  gate red permanently, which is the disease.
- **Environment** (`command not found`, platform-only step on the wrong runner).
  Usually a one-line `runner.os` guard.

### 3. Attribute it

```bash
gh run list --repo smilinTux/<repo> --branch main --workflow <name> --limit 4 \
  --json conclusion,displayTitle,createdAt \
  --jq '.[]|"\(.conclusion)  \(.createdAt[11:16])  \(.displayTitle[0:52])"'
```

The last green run and the first red one bracket the cause. If the breaking merge is
someone else's in-flight work, **raise an incident and stop**: they hold the context
for their own failing assertion, and a second person guessing at it is how a
one-line fix becomes an afternoon.

```bash
skcapstone itil incident create -t "<repo> CI red on main: <test>" -s sev3 \
  --service <repo> --by <you> --tag ci --tag red-gate --impact "<evidence>"
```

### 4. Fix or revert, same day

Per §6.1, red on `main` is an incident, not a backlog item. **Fix the pre-existing
break in its own PR**, never folded into a feature branch. If neither fix nor revert
is possible today, disable the gate with a linked card saying why and when it
returns. A deliberately-disabled gate is honest; a permanently-failing one is not.

## After the fix

The next sweep prints `FIXED <repo>/<workflow>` and drops it from state. That line
is the confirmation. Do not close the incident on the merge alone: verify the gate
actually went green on `main`, because a fix that merges is not a fix that worked.

```bash
gh run list --repo smilinTux/<repo> --branch main --workflow <name> --limit 2 \
  --json conclusion,displayTitle
```

## Tuning

- **Repo list** lives in the job's `--repos`. A repo with no completed runs reports
  as `unreachable`, which is informational, not a finding.
- **State** is `~/.skcapstone/state/ci-gate-health.json`. Deleting it makes every
  current red look NEW once. That is the correct way to force a full re-report, and
  the wrong way to silence one.
- **Never** silence a finding by removing its repo from `--repos`. That is the
  disease this standard exists to treat, moved into the config file.
