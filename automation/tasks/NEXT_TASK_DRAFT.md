# Next Task Draft

- **Generated:** 2026-07-25T06:43:26+00:00
- **Status:** DRAFT — not an approved Task ID. Requires explicit human
  approval before Claude Code acts on this. Nothing in this automation
  layer executes this file automatically.

## From previous task: PM-AUTO-03

**Suggested next task (as written in the previous completion report):**

PM-AUTO-04: wire review_decision.json / run_pm_pipeline.py's exit code into an actual GitHub Actions workflow step, so a real CI run gates on PASS/FAIL/BLOCKED automatically.

**Previous task's remaining blockers (for context):**

_(none noted)_

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
