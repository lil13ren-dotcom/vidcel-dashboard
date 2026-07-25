# Architecture — 店舗IT担当 business, as verified 2026-07-25

Cross-repo inventory produced by PM-002 (repository search for the 店舗IT担当
production implementation). Verified by cloning and inspecting each repo
directly — not inferred from names or memory.

## Where things actually live

| Concern | Location | Status |
|---|---|---|
| PM management (roadmap, tasks, gates, KPI) | Google Sheets `店舗IT担当_PM_OS_マスタープラン_v3` | Live, this is the SSOT |
| Customer onboarding / task automation | Google Sheets `店舗IT担当_オンボーディング管理_v1` + bound Apps Script | Live — real trigger/log history exists (form submit, daily 7am, edit triggers) |
| Marketing LP | `vidcel-web` (`apps/lp`), deployed to Vercel (`vidcel-lp.vercel.app`) | Live but **frozen** (not migrated to Cloudflare) |
| Duplicate/earlier LP | `vidcel-lp` (standalone repo) | Appears to mirror `apps/lp`; not the deploy target of record |
| Per-industry demo sites | `vidcel-web` (`apps/restaurant`, `apps/beauty`, `apps/clinic`) | Built, `wrangler.jsonc` present but explicitly **not configured for production** (no custom domain, no external services) — sales-demo assets, not the customer-facing subscription product |
| Stripe subscription billing | **Not found in any repo** | Not integrated anywhere in code (confirmed via `ai-lead-os/knowledge/BUSINESS_ASSET_INVENTORY.md`: "None yet — not integrated into AI Lead OS", and zero hits across all 7 repos) |
| Resend transactional email | **Not found in any repo** | Same — not integrated anywhere |
| Cloudflare Worker (production) | **Not found** | `wrangler.jsonc` exists only for the 3 demo sites above, undeployed |
| Sales/lead generation tooling | `ai-lead-os` | Real, mature, separate roadmap (Phase A–E sales intelligence). Used by 店舗IT担当's G2 tasks only as a reused tool for lead-list creation/diagnosis — not part of the 店舗IT担当 product itself |
| AI video generation pipeline | `vidcel-generation-lab`, `vidcel-pipeline`, `vidcel-assets` | Unrelated to 店舗IT担当; Vidcel's separate video-production business |
| Internal ops dashboard | `vidcel-dashboard` (this repo) | Unrelated to 店舗IT担当; Vidcel's own ops tracking |

## Repos checked (all 7 accessible to this session)

`vidcel-dashboard`, `ai-lead-os`, `vidcel-web`, `vidcel-generation-lab`,
`vidcel-pipeline`, `vidcel-lp`, `vidcel-assets` — searched for `wrangler.toml`/
`wrangler.json(c)`, `package.json` deps on `stripe`/`resend`, and any
Cloudflare/Stripe/Resend/onboarding-form references. See PM-002 conversation
record for the full per-repo grep output.

## Open question (blocks Gate 1)

No repo currently implements the "申込〜決済〜登録〜通知" (application →
payment → registration → notification) flow the PM OS's Gate 1 requires.
Whether this should be built as a new Cloudflare Worker (possibly reusing
`vidcel-web`'s per-vertical demo sites as a base) or via another path is an
open decision for the project owner — see `Backlog.md`.
