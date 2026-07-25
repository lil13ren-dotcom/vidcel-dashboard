# Next Task Draft

- **Generated:** 2026-07-25T07:35:06+00:00
- **Derived from:** PM-AUTO-04A (status: PASS)
- **Status:** DRAFT — not an approved Task ID. Requires explicit human
  approval before Claude Code acts on this. Nothing in this automation
  layer executes this file automatically.

## Title
(unassigned — human to pick a Task ID)

## Objective
Project owner reviews and decides whether to merge PR #1. If merged: dispatch the four validation scenarios for real (fixtures already committed under automation/tests/fixtures/) and close out PM-AUTO-04's runtime-evidence gap. If not merged: formally accept local/static validation as sufficient, or close PR #1.

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
