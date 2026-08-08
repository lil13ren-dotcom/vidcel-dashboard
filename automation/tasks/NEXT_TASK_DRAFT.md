# Next Task Draft

- **Generated:** 2026-07-25T07:35:06+00:00
- **Status:** DRAFT — not an approved Task ID. Requires explicit human
  approval before Claude Code acts on this. Nothing in this automation
  layer executes this file automatically.

## From previous task: PM-AUTO-04A

**Suggested next task (as written in the previous completion report):**

Project owner reviews and decides whether to merge PR #1. If merged: dispatch the four validation scenarios for real (fixtures already committed under automation/tests/fixtures/) and close out PM-AUTO-04's runtime-evidence gap. If not merged: formally accept local/static validation as sufficient, or close PR #1.

**Previous task's remaining blockers (for context):**

PR #1 (https://github.com/lil13ren-dotcom/vidcel-dashboard/pull/1) is open as a draft, per explicit instruction not to merge it. Merging main-branch changes requires the project owner's explicit approval, which is outside this task's scope. Until merged, workflow_dispatch remains unregistered and PM-AUTO-04's real-runtime-evidence gap (see its own remaining_blockers, still tracked in Backlog.md item 16) stays open.

## Open Backlog items (best-effort extract from knowledge/Backlog.md)

_Text-parsed from Backlog.md's 'Awaiting project-owner decision' section — not authoritative. Read the actual file for full context before picking one._

- Does the Vidcel onboarding page use Resend for anything?
- Where does the "Vidcel onboarding page" itself live?
- G1-06 — Is the Stripe Payment Link actually live?
- `vidcel-lp` vs. `vidcel-web/apps/lp` — which is the repo of record?
- Tax/accounting treatment of multi-currency revenue
- Confirm folder-structure interpretation for `automation/`.

## Human review checklist before approving this as a real task

- [ ] Does the suggested next task actually match current priorities?
- [ ] Does it require a PRODUCTION_CHANGE / PAYMENT_CHANGE / SECRET_REQUIRED /
      DEPLOYMENT_REQUIRED / ARCHITECTURE_CHANGE / LEGAL_DECISION step? If so,
      make sure that's explicit in the task instructions, not implied.
- [ ] Assign a real Task ID before handing this to Claude Code.
