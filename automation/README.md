# PM Automation Layer (PM-AUTO-01 / 02 / 03 / 04)

Reduces manual copy-paste between the PM (ChatGPT/human) and Claude Code by
standardizing completion reports, auto-collecting review material, and
drafting the next task. **This is not autonomous development.** Nothing
here writes product code, touches Stripe, touches the production Apps
Script, or approves its own next step. Every implementation still requires
explicit human approval, per PM OS rule ("No implementation without Task
ID"). Runs both locally (`run_pm_pipeline.py`) and in GitHub Actions via
`.github/workflows/pm-pipeline.yml` — see
[`CI_INTEGRATION.md`](./CI_INTEGRATION.md) for the workflow's triggers,
inputs, exit-code policy, and security posture.

## Flow

```
Claude Code finishes a task
        |
        v
automation/reports/task_meta.json   (Claude/human fills in the narrative fields)
        |
        v
generate_completion_report.py  -->  reports/latest_report.{md,json}
        |
        v
  any auto-stop flag present?
   /                        \
 yes                         no
  |                           |
  v                           v
generate_decision_       generate_review_package.py --> review/review_request.md,
package.py                                              reports/quality_checks.json
(status: BLOCKED)               |
  |                             v
  v                      generate_decision_package.py --> review/review_decision.json,
HALT. Exit code 2.       review/review_summary.md, review/next_task_draft.md
Human review required.   (status: PASS or FAIL)
                                 |
                                 v
                          generate_next_task.py --> tasks/NEXT_TASK_DRAFT.md
                          (freeform, Backlog-aware -- separate from the
                           deterministic next_task_draft.md above)
                                 |
                                 v
                          Human (or ChatGPT PM) reads review_decision.json
                          (or review_summary.md), returns PASS / FAIL / BLOCKED,
                          and explicitly approves (or rewrites) a next task
                          before it becomes a real Task ID. This automation
                          layer never does that step itself.
```

`run_pm_pipeline.py` runs every stage in order and stops itself the moment
a stop-flag appears — this is the "Task Runner" in the architecture diagram.
Its own exit code mirrors the decision (0 = PASS, 2 = BLOCKED, 3 = FAIL, 1 =
invalid `task_meta.json`), so it's directly usable as a CI gate. See
[`DECISION_PACKAGE.md`](./DECISION_PACKAGE.md) for the full design of the
structured decision layer (PM-AUTO-03) — status/risk derivation rules, the
JSON schema, and worked examples.

## Folder structure

```
automation/
  README.md                       this file
  DECISION_PACKAGE.md             design doc for the structured decision layer (PM-AUTO-03)
  generate_completion_report.py   stage 1
  generate_review_package.py      stage 2a (skipped on auto-stop) -- quality checks
  generate_decision_package.py    stage 2b -- deterministic PASS/FAIL/BLOCKED decision
  generate_next_task.py           stage 3 (skipped on auto-stop) -- freeform, Backlog-aware
  run_pm_pipeline.py              orchestrator
  schemas/
    review_decision.schema.json    JSON Schema (draft-07) for review_decision.json
  examples/
    pass/, fail/, blocked/          real, generated example decision packages, each with
                                     the task_meta.json fixture that produced it
  reports/
    task_meta.json                 input you write per task (overwritten/committed
                                    each run — history lives in git log, not in
                                    accumulated files)
    task_meta.example.json         schema reference, always committed
    latest_report.md               output — human-readable
    latest_report.json             output — machine-readable
    git_diff.md                    output — from the review stage
    test_results.md                output — Ruff/mypy/Alembic/pytest, from the review stage
    quality_checks.json            output — machine-readable per-check status/exit code,
                                    from the review stage
  review/
    review_request.md              output — the quality-check review package (stage 2a)
    review_decision.json           output — fixed-schema PASS/FAIL/BLOCKED decision (stage 2b)
    review_summary.md              output — human-readable summary (stage 2b)
    next_task_draft.md             output — structured, status-driven next-task draft (stage 2b)
    screenshots/                   optional — drop images here before running;
                                    they'll be listed (never generated) in the package
  tasks/
    NEXT_TASK_DRAFT.md              output — freeform, Backlog-aware draft (stage 3), never auto-approved
```

The project's existing top-level `knowledge/` folder (`Decision_Log.md`,
`Architecture.md`, `Backlog.md`, `README.md`, plus `ADD_*`/`SPEC_*`/
`CHECKLIST_*` docs) is **not** duplicated under `automation/` — the
next-task generator reads `knowledge/Backlog.md` directly from its real
location for context.

## How to use

1. After finishing a task, fill in `automation/reports/task_meta.json`
   (copy `task_meta.example.json` as a starting point). This is the one
   manual step nothing can automate — the narrative judgment (risks,
   evidence, what's blocked, what's next) has to come from whoever did the
   work.
2. Run the pipeline:
   ```
   python3 automation/run_pm_pipeline.py automation/reports/task_meta.json
   ```
   Optionally add `--base origin/main` to also diff against a base branch,
   not just uncommitted changes. Optionally add `--root /path/to/other/repo`
   to run the quality checks (Ruff/mypy/pytest/Alembic) against a different
   repo than this one — the report/review output still lands under this
   repo's `automation/`. Quality-check discovery reads the target repo's own
   `pyproject.toml`/`alembic.ini`, so this works against any repo without
   per-repo hardcoding.
3. If it halts (exit code 2), `automation/review/review_decision.json` still
   has `status: "BLOCKED"` and a `reason` — resolve it like any other PM OS
   blocker (see `knowledge/Decision_Log.md`'s pattern for prior blockers,
   e.g. G1-12) and don't just remove the flag to make the pipeline continue.
4. Otherwise, hand `automation/review/review_decision.json` (or the
   human-readable `review_summary.md`) to the PM (ChatGPT or a human) for
   PASS / FAIL / BLOCKED. Exit code 3 means the decision is already FAIL —
   see `automation/review/next_task_draft.md`, which will be titled
   `REWORK: <task_id>`. `review/review_request.md` has the full per-check
   detail (commands, exit codes, captured output) behind the decision.
5. On PASS, review `automation/review/next_task_draft.md` (structured,
   status-aware) and/or `automation/tasks/NEXT_TASK_DRAFT.md` (freeform,
   Backlog-aware), edit as needed, assign a real Task ID, and get explicit
   approval before it goes to Claude Code. Neither draft is polished enough
   to send as-is.

## Example workflow

```
$ python3 automation/run_pm_pipeline.py automation/reports/task_meta.json
Wrote automation/reports/latest_report.md
Wrote automation/reports/latest_report.json
Wrote automation/review/review_request.md
Wrote automation/reports/git_diff.md
Wrote automation/reports/test_results.md
Wrote automation/tasks/NEXT_TASK_DRAFT.md
============================================================
Pipeline complete. Nothing was auto-approved or auto-implemented.
Next: a human (or ChatGPT PM) reviews automation/review/review_request.md,
returns PASS / FAIL / BLOCKED, and explicitly approves
automation/tasks/NEXT_TASK_DRAFT.md (or a rewritten version of it) before
it becomes a real Task ID for Claude Code.
============================================================
```

This exact run was performed as a smoke test while building this
automation layer — real output, not illustrative. See the generated files
themselves (committed as of this task) for what they actually contain.

## Auto Stop Rules

The pipeline halts before generating the review package or next-task draft
if `task_meta.json`'s `flags` array contains any of:

`BLOCKED`, `EVIDENCE_MISSING`, `PRODUCTION_CHANGE`, `ARCHITECTURE_CHANGE`,
`PAYMENT_CHANGE`, `LEGAL_DECISION`, `SECRET_REQUIRED`, `DEPLOYMENT_REQUIRED`

These are set **explicitly and honestly** by whoever fills in
`task_meta.json` — there is no text-scanning/keyword-guessing of the risks/
blockers prose to auto-detect them (that would be unreliable in both
directions: false negatives on real risks worded differently, false
positives on the word appearing in an unrelated sentence). If a flag
applies, put it in the `flags` array.

## Auto Continue Categories

The pipeline runs through to a next-task draft without stopping when
`category` is one of: `Documentation`, `Tests`, `Refactoring`, `Lint`,
`Formatting`, `Knowledge updates`, `PM OS updates`, `Task generation`.
`Implementation` is accepted but doesn't get special treatment — the
`flags` array is what actually gates anything risky, not the category
label. A category doesn't override a flag: if `flags` is non-empty, the
pipeline halts regardless of what `category` says.

## What this does NOT do (by design)

- Does not write, edit, or deploy product code.
- Does not touch Stripe, the production Apps Script, or Google Sheets.
- Does not decide anything a human should decide — `review_decision.json`'s
  `status`/`risk` are *derived and reported*, not a substitute for the PM
  actually reading `review_summary.md`/`review_request.md` and choosing
  what happens next. `requires_human_approval` is always `true`.
- Does not approve or execute `next_task_draft.md` / `NEXT_TASK_DRAFT.md` —
  that requires an explicit human action outside this tooling.
- Does not install any dependency. pytest/mypy/ruff/npm are only invoked
  if already present in the environment *and* configured in the repo;
  otherwise each is reported as skipped, not silently ignored.
- Does not parse free-form prose (risks/blockers/evidence text) to decide
  status or risk — see `DECISION_PACKAGE.md` for exactly which fields are
  explicit input versus derived.

## Remaining manual steps

- Writing `task_meta.json`'s narrative fields (objective, risks, evidence,
  suggested next task) and its explicit `risk`/`next_task_id` fields — this
  is deliberately not automated; it's the actual PM judgment.
- Reading `review_decision.json`/`review_summary.md` and deciding what
  happens next (the automation reports PASS/FAIL/BLOCKED, it doesn't act
  on it).
- Reviewing and approving (or rewriting) `next_task_draft.md` or
  `NEXT_TASK_DRAFT.md` before either becomes a real Task ID.
- Dropping screenshots into `automation/review/screenshots/` before running,
  if visual evidence is relevant — nothing captures them automatically.

## Validated (PM-AUTO-02, 2026-07-25)

The "tool found and actually ran it" path — not just "tool not configured,
correctly skipped" — is now verified against `ai-lead-os`'s real pytest/
mypy/ruff/Alembic config via `--root`: all 6 checks (Ruff check, Ruff
format check, mypy strict, Alembic upgrade+check, pytest+coverage) were
discovered and executed for real, with output matching a manually-run
baseline exactly (see `knowledge/Decision_Log.md`'s PM-AUTO-02 entry for
the full evidence). A deliberately-injected Ruff violation was also
correctly detected and reported as a failure (no false PASS), then
reverted. **Still not validated:** npm-build detection against a repo
with a real `package.json`/build script — `ai-lead-os` is pure Python, so
only the "no package.json, correctly skipped" path has been exercised for
that check specifically.

## Validated (PM-AUTO-03, 2026-07-25)

All three decision-package scenarios were run for real and validated
against the JSON Schema (see `automation/examples/{pass,fail,blocked}/`):
a clean run (no flags, no failing checks) → `status: PASS`; a run with
`flags: ["SECRET_REQUIRED"]` → `status: BLOCKED`, quality checks and the
freeform next-task generator correctly skipped, `review_decision.json`
still generated with `requires_human_approval: true`; a run against
`ai-lead-os` with a deliberately-injected, reverted Ruff violation →
`status: FAIL`, `next_task: "REWORK-<task_id>"`. Full evidence in
`knowledge/Decision_Log.md`'s PM-AUTO-03 entry.
