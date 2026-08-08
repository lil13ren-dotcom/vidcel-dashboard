# Review Summary — PM-AUTO-03-EXAMPLE-FAIL

- **Generated:** 2026-07-25T06:41:07+00:00
- **Status:** FAIL
- **Risk:** MEDIUM

## Objective
Example fixture demonstrating a FAIL decision package: no auto-stop flags, but a quality check (Ruff) failed.

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
- automation/generate_review_package.py --root /workspace/ai-lead-os (with a deliberately-injected throwaway Ruff violation)

## Results
Ruff check FAILed (unused imports/variable in a throwaway scratch file); all other checks still PASSed.

## Risks
None -- the failing file was a throwaway scratch fixture, reverted immediately after this example was captured.

## Remaining blockers
_(none noted)_

## Evidence summary
See review_decision.json, review_summary.md, and the referenced automation/reports/quality_checks.json for this run.

## Recommendation
FAIL — do not proceed. Rework required on PM-AUTO-03-EXAMPLE-FAIL; see next_task_draft.md for scope.
