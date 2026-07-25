# GitHub Actions Integration (PM-AUTO-04)

`.github/workflows/pm-pipeline.yml` runs the existing PM automation
pipeline (PM-AUTO-01/02/03) inside GitHub Actions, preserving its exit-code
contract, uploading every generated artifact, and never executing anything
it produces. This document covers the workflow's triggers, inputs, the
PASS/BLOCKED/FAIL/ERROR policy, security posture, and how to run it.

## Triggers

**`workflow_dispatch` only.** No `push` or `pull_request` trigger is
configured, deliberately: there is not yet a convention for which
`task_meta.json` a given push/PR corresponds to, and guessing one would
risk a misleading PASS/FAIL badge on unrelated changes. Adding an
automatic trigger is a reasonable future task once that convention exists
(see Backlog.md) — not something to bolt on speculatively here.

## Inputs

| Input | Default | Meaning |
|---|---|---|
| `task_meta_path` | `automation/reports/task_meta.json` | Path to the `task_meta.json` to run, relative to the repo root. |
| `target_root` | `.` | Path to the repo to run quality checks against, relative to the repo root. **Must resolve inside the checked-out workspace** — this workflow checks out only this repository, so it cannot point at a separate repository (e.g. `ai-lead-os`) the way a local `--root` run can. |
| `artifact_retention_days` | `14` | Days to retain the uploaded artifact bundle (0-90). |

Both path inputs are free text from whoever dispatches the workflow and
are never trusted directly. `automation/validate_ci_inputs.py` resolves
each against `$GITHUB_WORKSPACE` and rejects anything that escapes it
(`..` traversal, an absolute path outside the workspace) or doesn't exist
as the expected type, before either value is used as an argument to
anything else. Inputs are passed to the pipeline as literal argv strings
(never interpolated into a shell string or `eval`'d), so even an input
that somehow got past validation could not be executed as a command.

## Exit-code contract (unchanged from PM-AUTO-03)

| Exit code | Meaning |
|---|---|
| 0 | PASS |
| 2 | BLOCKED |
| 3 | FAIL |
| 1 | Invalid `task_meta.json`, or (in this workflow) any earlier infrastructure failure such as failed input validation |

The workflow's own job outcome is derived from this without reinterpreting
it: the "Run PM pipeline" step captures the pipeline's real exit code into
a step output (`continue-on-error: true`, so a non-zero pipeline exit
doesn't fail the job at that point), and a final "Enforce PASS-only
success" step is the *only* step whose failure fails the job.

## Chosen policy: BLOCKED must not appear as PASS

The task requires BLOCKED to be "clearly shown" and to "must NOT appear as
PASS," and asks for the chosen policy to be documented. **GitHub Actions
has no native "neutral" conclusion for a workflow job** (unlike some older
CI systems with a neutral/inconclusive state) — a job is either green
(success) or red (failure/cancelled). Given that binary choice, the policy
here is:

- **PASS (exit 0) → job succeeds** (green).
- **BLOCKED (exit 2), FAIL (exit 3), and ERROR (exit 1 / infra failure) →
  job fails** (red).

This means BLOCKED and FAIL both show as a failing check, which is the
conservative, correct choice given the constraint: a BLOCKED task
genuinely has not been completed and must not read as "done." The
*distinction* between BLOCKED, FAIL, and ERROR is carried entirely by the
job summary (`$GITHUB_STEP_SUMMARY`) and the uploaded
`review_decision.json` — a human reading the run must open the summary to
tell them apart, but can never mistake any of them for PASS from the
badge/checkmark alone.

## Never fabricates a decision

`automation/ci_summary.py` cross-checks the pipeline's exit code against
`review_decision.json`'s own `status` field rather than trusting either
alone. If they disagree, or `review_decision.json` is missing or
malformed, the result is classified **ERROR**, not guessed in either
direction. It also does not display `review_decision.json` / `quality_checks.json`
/ `latest_report.json`'s *content* when classified as ERROR, because in
that case those files may be stale leftovers from a previous run (they are
tracked in git, so a fresh checkout can start with old committed copies)
rather than something the current run actually produced — showing their
fields under an ERROR header would misleadingly look like real data about
this run. This was caught and fixed during this task's own local dry-run
(see `knowledge/Decision_Log.md`'s PM-AUTO-04 entry) before any workflow
run was attempted.

## Artifacts

Every run — PASS, BLOCKED, FAIL, or ERROR — uploads a fixed, explicit list
of files (never a directory wildcard) under a single `pm-pipeline-artifacts`
bundle:

```
automation/reports/latest_report.md
automation/reports/latest_report.json
automation/review/review_summary.md
automation/review/review_decision.json
automation/reports/quality_checks.json
automation/review/next_task_draft.md
automation/tasks/NEXT_TASK_DRAFT.md
automation/reports/git_diff.md
automation/reports/test_results.md
automation/reports/pipeline_run.log   (full stdout/stderr of the pipeline run -- diagnostics)
```

`if-no-files-found: ignore` — files that were never generated (e.g.
`quality_checks.json` on a BLOCKED run, or everything on an ERROR run that
never reached the pipeline) are simply absent from the bundle, not an
upload failure. Nothing outside this list is ever included, so no
secrets/credentials/unrelated repo files can be swept in by accident.
`next_task_draft.md` and `NEXT_TASK_DRAFT.md` are uploaded as drafts only —
this workflow never reads, executes, or acts on their content.

## GitHub Actions Summary

`ci_summary.py` writes a structured table to `$GITHUB_STEP_SUMMARY`:
status (with PASS/BLOCKED/FAIL/ERROR emoji), task ID, exit code, risk,
blocked flag, next task, `requires_human_approval` (always `true`),
the classification reason, and quality-check pass/fail/skip counts with
any failing check names. It always states that human approval is required
and that `next_task_draft.md` is never auto-executed.

## Security

```yaml
permissions:
  contents: read
```

at the workflow level — no write access to contents, PRs, issues, or
anything else. The workflow does not push commits, merge PRs, comment on
issues, deploy anything, or expose any secret (it does not reference
`secrets.*` at all). Actions are pinned to major version tags
(`actions/checkout@v4`, `actions/setup-python@v5`,
`actions/upload-artifact@v4`) rather than unpinned `@main`/`@latest` —
per the task's "stable major versions **or** immutable SHAs," major-version
pinning was chosen over SHA-pinning for readability/maintainability, since
both options were explicitly offered.

## Tests

`automation/tests/test_ci_helpers.py` (stdlib `unittest`, no new runtime
dependency) covers: exit-code classification (including the exit-code /
decision-status mismatch case and the stale-data-suppression regression
above), path validation (traversal, absolute escape, wrong file/dir type,
empty input), summary generation for each status, missing/malformed
`review_decision.json`, missing `quality_checks.json`, and a static shape
check of the workflow YAML itself (triggers, permissions, `if: always()`
on the summary/upload/gate steps, no broad artifact globs, pinned actions).
Run locally:

```
python3 -m unittest discover -s automation/tests -v
```

## Usage (workflow_dispatch examples)

Via the GitHub UI: Actions → PM Pipeline → Run workflow, then fill in the
three inputs (or leave defaults for a PASS run against this repo itself).

Via `gh`:

```
gh workflow run pm-pipeline.yml --ref <branch> \
  -f task_meta_path=automation/reports/task_meta.json \
  -f target_root=. \
  -f artifact_retention_days=14
```

Validation fixtures committed for exercising each path directly:
`automation/tests/fixtures/ci_pass_task_meta.json`,
`ci_blocked_task_meta.json`, `ci_fail_task_meta.json` (see each file's own
`objective`/`test_results` fields for what it's testing and why). There is
no fixture for the ERROR scenario — dispatch with an invalid
`target_root` (e.g. `../../../etc`) to exercise it.

## Limitations

- `target_root` can only ever point inside this single repo's checkout —
  validating against a repo with real Python tooling (as PM-AUTO-02 did
  locally against `ai-lead-os`) is not reproducible in this workflow
  without adding cross-repo checkout (needs a PAT with access to that
  repo, out of scope here).
- The FAIL scenario fixture uses `status_override: "FAIL"` rather than a
  real failing quality check, for the same reason — this repo has no
  configured Python tooling for a real check to fail against. The FAIL
  *handling* logic (exit code 3, job fails, `next_task` becomes
  `REWORK-<task_id>`, artifacts still uploaded) is exercised faithfully;
  a genuine tool failure was already validated locally in PM-AUTO-02/03.
- No `push`/`pull_request` trigger yet — manual dispatch only (see
  Triggers above).
- `risk` still doesn't gate anything (inherited limitation from
  PM-AUTO-03), including in CI.
