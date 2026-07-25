# Next Task Draft

- **Generated:** 2026-07-25T06:43:26+00:00
- **Derived from:** PM-AUTO-03 (status: PASS)
- **Status:** DRAFT — not an approved Task ID. Requires explicit human
  approval before Claude Code acts on this. Nothing in this automation
  layer executes this file automatically.

## Title
PM-AUTO-04

## Objective
PM-AUTO-04: wire review_decision.json / run_pm_pipeline.py's exit code into an actual GitHub Actions workflow step, so a real CI run gates on PASS/FAIL/BLOCKED automatically.

## Scope
Not yet scoped by this automation — PM to define based on the objective above and current Backlog/Gate priorities.

## Deliverables
TBD — to be defined when this draft is turned into a real Task ID.

## Validation requirements
TBD — define alongside deliverables.

## Stop conditions
Halt and require human approval before proceeding if any of these apply:
- BLOCKED
- EVIDENCE_MISSING
- PRODUCTION_CHANGE
- ARCHITECTURE_CHANGE
- PAYMENT_CHANGE
- LEGAL_DECISION
- SECRET_REQUIRED
- DEPLOYMENT_REQUIRED
