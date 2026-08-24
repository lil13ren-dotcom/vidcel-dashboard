# Review Summary — PM-AUTO-03-EXAMPLE-BLOCKED

- **Generated:** 2026-07-25T06:37:58+00:00
- **Status:** BLOCKED
- **Risk:** HIGH

## Objective
Example fixture demonstrating a BLOCKED decision package: an auto-stop flag is present, so the pipeline halts before running quality checks.

## Files changed
- `automation/examples/blocked/next_task_draft.md`
- `automation/examples/blocked/review_decision.json`
- `automation/examples/blocked/review_summary.md`
- `automation/examples/blocked/task_meta.json`
- `automation/examples/fail/task_meta.json`
- `automation/examples/pass/next_task_draft.md`
- `automation/examples/pass/review_decision.json`
- `automation/examples/pass/review_summary.md`
- `automation/examples/pass/task_meta.json`
- `automation/generate_completion_report.py`
- `automation/generate_decision_package.py`
- `automation/generate_review_package.py`
- `automation/reports/git_diff.md`
- `automation/reports/latest_report.json`
- `automation/reports/latest_report.md`
- `automation/reports/quality_checks.json`
- `automation/reports/task_meta.example.json`
- `automation/reports/test_results.md`
- `automation/review/next_task_draft.md`
- `automation/review/review_decision.json`
- `automation/review/review_request.md`
- `automation/review/review_summary.md`
- `automation/run_pm_pipeline.py`
- `automation/schemas/review_decision.schema.json`
- `automation/tasks/NEXT_TASK_DRAFT.md`

## Tests executed
_(none listed)_

## Results
Not run -- pipeline halts on the auto-stop flag before the quality-check stage.

## Risks
Would require a real secret/credential to proceed.

## Remaining blockers
Needs a production API key that this session does not have access to.

## Evidence summary
None yet -- blocked before any implementation work started.

## Recommendation
BLOCKED — do not proceed. Resolve the blocker(s) on PM-AUTO-03-EXAMPLE-BLOCKED listed below before any further action.
