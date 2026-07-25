# Next Task Draft

- **Generated:** 2026-07-25T07:20:47+00:00
- **Derived from:** PM-AUTO-04 (status: BLOCKED)
- **Status:** DRAFT — not an approved Task ID. Requires explicit human
  approval before Claude Code acts on this. Nothing in this automation
  layer executes this file automatically.

## Title
UNBLOCK: PM-AUTO-04

## Objective
Resolve the blocker(s) preventing PM-AUTO-04 from completing.

## Scope
Real GitHub Actions runtime evidence for all 4 scenarios could not be obtained in this session. Cause: workflow_dispatch only recognizes a workflow once its YAML file exists on the repository's default branch (main) -- dispatching automation/../.github/workflows/pm-pipeline.yml against this feature branch returned 404, and it does not appear in the repo's registered workflow list. This session's branch policy explicitly prohibits pushing to a different branch (including main) without explicit permission, and the user, when asked, chose the BLOCKED fallback over merging to main or a temporary push-trigger workaround. To unblock: either (a) merge .github/workflows/pm-pipeline.yml to main (a normal PR, not a force-push or anything destructive) so workflow_dispatch can register and dispatch it, or (b) accept local/static validation as sufficient and formally close this out without live-run evidence.

## Deliverables
Whatever removes the blocker(s) in Scope. Do not resume PM-AUTO-04 until this is done.

## Validation requirements
Re-run PM-AUTO-04's original validation once unblocked.

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
