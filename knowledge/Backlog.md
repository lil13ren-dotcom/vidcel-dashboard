# Backlog — PM OS project

Open items surfaced during PM OS work, not yet assigned a Task ID. Per PM OS
rule: nothing here may be implemented without an approved Task ID.

## Resolved (but see reopened item below)

1. ~~Where does the 店舗IT担当 production backend get built?~~ **Resolved by
   PM-003 (2026-07-25)** as: no custom backend needed, Stripe Payment Link →
   Google Form → Spreadsheet → existing Apps Script is sufficient. **Partially
   reopened by G1-06 (2026-07-25)** — see the first item below. The Cloudflare
   Worker / custom Stripe backend parts of this decision are unaffected.

## Resolved (2026-07-25, G1-06C)

0. ~~Conflict: does the production flow use Google Form + Apps Script, or
   Resend?~~ **Resolved by G1-06C.** The entry point is the **Vidcel
   onboarding page** (replacing the bare Google Form); the backend stays
   **Google Sheets + existing Apps Script, unchanged**. This confirms
   PM-003's original reasoning for deferring Resend as *the backend* still
   holds. **Not fully resolved:** G1-06C never mentions Resend at all, so
   whether Resend plays any role in the new onboarding page itself (e.g. its
   own confirmation email) is still an open question — see item 0 below.

## Awaiting project-owner decision

0. **Does the Vidcel onboarding page use Resend for anything?** G1-06
   said the intended flow was "...→ Resend workflow"; G1-06C finalized the
   entry point/backend split but didn't mention Resend at all. Not urgent —
   doesn't block G1-09 (which only needs the page → Sheet mechanism) — but
   should be clarified before the onboarding page is built, not after.

1. **Where does the "Vidcel onboarding page" itself live?** Not found in any
   of the 7 repos inventoried by PM-002 (`vidcel-dashboard`, `ai-lead-os`,
   `vidcel-web`, `vidcel-generation-lab`, `vidcel-pipeline`, `vidcel-lp`,
   `vidcel-assets`). It may not be built yet, or may live somewhere outside
   this session's scope. Worth confirming before G1-09 is scoped in detail —
   no point designing the Sheet-integration mechanism against a page that
   doesn't exist yet.

2. ~~G1-09 — How does the Vidcel onboarding page actually deliver data into
   the existing Google Sheet?~~ **Design recommended by G1-06D (2026-07-25)
   — not yet implemented, not yet a Task ID.** See
   `ADD_G1-06D_Onboarding_Data_Bridge.md`: an Apps Script Web App calling
   the existing registration logic directly. Rejected: direct Sheets API
   calls (doesn't solve the trigger problem alone) and a Cloudflare Worker
   proxy (would re-reverse PM-003's Worker deferral a third time). Six
   follow-up implementation items are listed in the ADD's §6 and still need
   Task IDs, starting with decoupling the registration logic from
   `onFormSubmit`. Still blocks Gate 1 items 3–4 until built and
   independently validated (no inherited Form evidence, per the ADD).

3. **G1-06 — Is the Stripe Payment Link actually live?** Owner confirmed a
   JP and a US Payment Link exist; still unverified: active status, product
   name, price, live vs. test mode, the actual URLs, redirect configuration
   (now pointing at the onboarding page, not a Google Form), LP-CTA/Payment-
   Link URL match, and full payment→onboarding E2E. Top blocker on Gate 1.

4. **G1-07 — How should production customer data be separated from test
   data** in `店舗IT担当_オンボーディング管理_v1`? Currently there is no
   mechanism; test rows appear to have been manually deleted from the same
   live tables. Needs a decision (separate tab, flag column, naming
   convention) before real customers are onboarded.

5. **G1-08 — Cancellation / failed-payment procedure needs to be written
   down.** The mechanism works (`handleEdit` on the Customers sheet, per
   `Logs`), but there is no documented procedure for staff to follow.

6. **`vidcel-lp` vs. `vidcel-web/apps/lp` — which is the repo of record?**
   Both exist with near-identical `package.json`. `vidcel-web`'s README
   says `apps/lp` deploys to `vidcel-lp.vercel.app` (frozen). Unclear
   whether standalone `vidcel-lp` is stale/superseded or actively
   maintained separately. Not urgent, but worth resolving before any LP
   work is scoped as a Task ID.
