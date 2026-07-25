# Backlog — PM OS project

Open items surfaced during PM OS work, not yet assigned a Task ID. Per PM OS
rule: nothing here may be implemented without an approved Task ID.

## Awaiting project-owner decision

1. **Where does the 店舗IT担当 production backend (Stripe + Resend +
   Cloudflare Worker, "申込〜決済〜登録〜通知" E2E) actually get built?**
   Surfaced by PM-002 (2026-07-25). Options observed, not recommended:
   - Extend one of `vidcel-web`'s existing demo apps (`apps/restaurant`,
     `apps/beauty`, `apps/clinic`) into the real product, adding Stripe/
     Resend and wiring up `wrangler deploy` for real.
   - Build a new, separate Worker specifically for the subscription/
     onboarding flow, decoupled from the sales-demo sites.
   - Keep relying on the Google Forms + Apps Script system currently in
     production (`店舗IT担当_オンボーディング管理_v1`) and treat Stripe/
     Resend integration as a later automation upgrade rather than a
     blocking Gate 1 requirement.
   Blocks: PM-001 (reconcile PM OS with actual implementation), Gate 1
   PASS/FAIL determination.

2. **`vidcel-lp` vs. `vidcel-web/apps/lp` — which is the repo of record?**
   Both exist with near-identical `package.json`. `vidcel-web`'s README
   says `apps/lp` deploys to `vidcel-lp.vercel.app` (frozen). Unclear
   whether standalone `vidcel-lp` is stale/superseded or actively
   maintained separately. Not urgent, but worth resolving before any LP
   work is scoped as a Task ID.
