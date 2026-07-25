# Backlog — PM OS project

Open items surfaced during PM OS work, not yet assigned a Task ID. Per PM OS
rule: nothing here may be implemented without an approved Task ID.

## Resolved (but see reopened item below)

1. ~~Where does the 店舗IT担当 production backend get built?~~ **Resolved by
   PM-003 (2026-07-25)** as: no custom backend needed, Stripe Payment Link →
   Google Form → Spreadsheet → existing Apps Script is sufficient. **Partially
   reopened by G1-06 (2026-07-25)** — see the first item below. The Cloudflare
   Worker / custom Stripe backend parts of this decision are unaffected.

## Awaiting project-owner decision

0. **⚠️ Conflict: does the production flow use Google Form + Apps Script, or
   Resend?** PM-003 deferred Resend as unnecessary, citing the Apps Script's
   proven email-sending evidence. G1-06 then stated the *intended* flow is
   "Stripe Payment Link → Vidcel onboarding page → Resend workflow" (Resend
   confirmed incomplete) — no Google Form. These can't both be the production
   plan as stated. Needs the owner to clarify: is Resend replacing the
   Apps Script system, or additive to it (e.g. different purpose)? See
   `Decision_Log.md`'s 2026-07-25 G1-06 entry for the two readings
   considered. Left unresolved deliberately — out of scope for G1-06's
   "update documentation only" instruction.

1. **G1-06 — Is the Stripe Payment Link actually live, and where does its
   post-payment redirect actually go?** Owner confirmed a JP and a US Payment
   Link exist; still unverified: active status, product name, price, live vs.
   test mode, the actual URLs, redirect configuration, LP-CTA/Payment-Link
   URL match, and full payment→onboarding E2E. Blocked on item 0 above for
   the redirect target specifically. Top blocker on Gate 1 — see PM OS
   `04_Gates`.

2. **G1-07 — How should production customer data be separated from test
   data** in `店舗IT担当_オンボーディング管理_v1`? Currently there is no
   mechanism; test rows appear to have been manually deleted from the same
   live tables. Needs a decision (separate tab, flag column, naming
   convention) before real customers are onboarded.

3. **G1-08 — Cancellation / failed-payment procedure needs to be written
   down.** The mechanism works (`handleEdit` on the Customers sheet, per
   `Logs`), but there is no documented procedure for staff to follow.

4. **`vidcel-lp` vs. `vidcel-web/apps/lp` — which is the repo of record?**
   Both exist with near-identical `package.json`. `vidcel-web`'s README
   says `apps/lp` deploys to `vidcel-lp.vercel.app` (frozen). Unclear
   whether standalone `vidcel-lp` is stale/superseded or actively
   maintained separately. Not urgent, but worth resolving before any LP
   work is scoped as a Task ID.
