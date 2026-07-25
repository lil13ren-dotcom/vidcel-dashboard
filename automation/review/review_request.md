# Review Package

Root: `/home/user/vidcel-dashboard`

## Overall: PASS (with skips) (0 passed, 0 failed, 5 skipped)

| Check | Status | Exit code |
|---|---|---|
| Ruff check | SKIPPED | - |
| Ruff format check | SKIPPED | - |
| mypy | SKIPPED | - |
| Alembic check | SKIPPED | - |
| pytest | SKIPPED | - |

## Git status
```
M automation/README.md
 M automation/generate_completion_report.py
 M automation/generate_review_package.py
 M automation/reports/git_diff.md
 M automation/reports/latest_report.json
 M automation/reports/latest_report.md
 M automation/reports/quality_checks.json
 M automation/reports/task_meta.example.json
 M automation/reports/task_meta.json
 M automation/reports/test_results.md
 M automation/review/review_request.md
 M automation/run_pm_pipeline.py
 M automation/tasks/NEXT_TASK_DRAFT.md
?? automation/DECISION_PACKAGE.md
?? automation/examples/
?? automation/generate_decision_package.py
?? automation/review/next_task_draft.md
?? automation/review/review_decision.json
?? automation/review/review_summary.md
?? automation/schemas/
```

### Build — SKIPPED

no package.json in this repo

## Screenshots

No automation/review/screenshots/ directory -- none collected.

## See also
- `automation/reports/git_diff.md` -- full diff
- `automation/reports/test_results.md` -- full output for every check above
- `automation/reports/quality_checks.json` -- machine-readable check results
- `automation/reports/latest_report.md` -- narrative completion report