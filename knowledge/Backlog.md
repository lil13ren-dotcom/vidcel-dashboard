# Backlog — PM OS project

Open items surfaced during PM OS work, not yet assigned a Task ID. Per PM OS
rule: nothing here may be implemented without an approved Task ID.

## Resolved

1. ~~Where does the 店舗IT担当 production backend get built?~~ **Resolved by
   PM-003 (2026-07-25).** Decision: it doesn't need a custom backend for the
   initial release — Stripe Payment Link → Google Form → Spreadsheet →
   existing Apps Script is sufficient (see `Decision_Log.md` and
   `Architecture.md`). Custom Cloudflare Worker / Resend / custom Stripe
   backend moved to the PM OS's `07_Parking` sheet, re-evaluate only if
   operational evidence justifies it (see conditions listed there).

## Awaiting project-owner decision

1. **G1-06 — Is the Stripe Payment Link actually live, and does its
   post-payment redirect reach the correct Google Form?** Requires Stripe
   dashboard access this session doesn't have. This is the top blocker on
   Gate 1 ("Ready to Accept First Paying Customer") — see PM OS `04_Gates`.

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
