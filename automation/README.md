# PM Automation Layer (PM-AUTO-01)

Reduces manual copy-paste between the PM (ChatGPT/human) and Claude Code by
standardizing completion reports, auto-collecting review material, and
drafting the next task. **This is not autonomous development.** Nothing
here writes product code, touches Stripe, touches the production Apps
Script, or approves its own next step. Every implementation still requires
explicit human approval, per PM OS rule ("No implementation without Task
ID").

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
HALT. Print reason.    generate_review_package.py --> review/review_request.md
Exit code 2.                  |
Human review required.        v
                        generate_next_task.py --> tasks/NEXT_TASK_DRAFT.md
                               |
                               v
                        Human (or ChatGPT PM) reviews review_request.md,
                        returns PASS / FAIL / BLOCKED, and explicitly
                        approves (or rewrites) NEXT_TASK_DRAFT.md before
                        it becomes a real Task ID. This automation layer
                        never does that step itself.
```

`run_pm_pipeline.py` runs all three stages in order and stops itself the
moment a stop-flag appears — this is the "Task Runner" in the architecture
diagram.

## Folder structure

```
automation/
  README.md                       this file
  generate_completion_report.py   stage 1
  generate_review_package.py      stage 2 (skipped on auto-stop)
  generate_next_task.py           stage 3 (skipped on auto-stop)
  run_pm_pipeline.py              orchestrator
  reports/
    task_meta.json                 input you write per task (overwritten/committed
                                    each run — history lives in git log, not in
                                    accumulated files)
    task_meta.example.json         schema reference, always committed
    latest_report.md               output — human-readable
    latest_report.json             output — machine-readable
    git_diff.md                    output — from the review stage
    test_results.md                output — pytest/mypy/ruff, from the review stage
  review/
    review_request.md              output — the review package
    screenshots/                   optional — drop images here before running;
                                    they'll be listed (never generated) in the package
  tasks/
    NEXT_TASK_DRAFT.md              output — draft only, never auto-approved
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
   not just uncommitted changes.
3. If it halts (exit code 2), the reason is printed and in
   `latest_report.md` — resolve it like any other PM OS blocker (see
   `knowledge/Decision_Log.md`'s pattern for prior blockers, e.g. G1-12) and
   don't just remove the flag to make the pipeline continue.
4. If it completes (exit code 0), hand `automation/review/review_request.md`
   to the PM (ChatGPT or a human) for PASS / FAIL / BLOCKED.
5. On PASS, review `automation/tasks/NEXT_TASK_DRAFT.md`, edit it as
   needed, assign it a real Task ID, and get explicit approval before it
   goes to Claude Code. The draft is intentionally not polished enough to
   send as-is — it's a starting point built from whatever the previous
   report's `suggested_next_task` said, plus open Backlog items.

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
- Does not decide PASS/FAIL/BLOCKED — that's the PM's call, human or
  ChatGPT, reading `review_request.md`.
- Does not approve or execute `NEXT_TASK_DRAFT.md` — that requires an
  explicit human action outside this tooling.
- Does not install any dependency. pytest/mypy/ruff/npm are only invoked
  if already present in the environment *and* configured in the repo;
  otherwise each is reported as skipped, not silently ignored.

## Remaining manual steps

- Writing `task_meta.json`'s narrative fields (objective, risks, evidence,
  suggested next task) — this is deliberately not automated; it's the
  actual PM judgment.
- Reading `review_request.md` and deciding PASS/FAIL/BLOCKED.
- Reviewing and approving (or rewriting) `NEXT_TASK_DRAFT.md` before it
  becomes a real Task ID.
- Dropping screenshots into `automation/review/screenshots/` before running,
  if visual evidence is relevant — nothing captures them automatically.

## Not yet validated

This was smoke-tested only against `vidcel-dashboard` itself, which has no
pytest/mypy/ruff/npm build configured — so the "tool found and actually ran
it" path is unverified, only the "tool not configured, correctly skipped"
path is. `ai-lead-os` (this account's Python project with real pytest/
mypy/ruff config, per its `pyproject.toml`) would be a good next real-world
test — see `automation/tasks/NEXT_TASK_DRAFT.md`.
