# Architecture — 店舗IT担当 business, as verified 2026-07-25

**⚠️ 2026-07-25 update (G1-06): the "Confirmed production architecture"
section below (from PM-003) is now disputed.** The project owner stated the
intended post-payment flow is "Stripe Payment Link → Vidcel onboarding page
→ Resend workflow" — not Google Form, and re-involving Resend, which PM-003
had deferred. Not resolved yet; see `Decision_Log.md`'s G1-06 entry and
`Backlog.md` item 0. The evidence below (Apps Script `Logs`) is still
factually accurate for what that system does — it just may not be *the*
production path going forward. Treat the table row for "Customer onboarding"
and the confirmed-architecture diagram as **provisional**, not settled.

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
| Stripe billing | Stripe Payment Link (hosted, no custom integration) | **Confirmed as the intended mechanism (PM-003)** — a custom Stripe API backend is deliberately deferred, see below |
| Resend transactional email | Not used — Apps Script (`GmailApp`) sends confirmation emails instead | **Deliberately deferred (PM-003)** — Apps Script already has working send evidence in `Logs` |
| Cloudflare Worker (production) | Not used for the initial release | **Deliberately deferred (PM-003)** — `wrangler.jsonc` exists only for `vidcel-web`'s 3 demo sites, unrelated to this decision |
| Sales/lead generation tooling | `ai-lead-os` | Real, mature, separate roadmap (Phase A–E sales intelligence). Used by 店舗IT担当's G2 tasks only as a reused tool for lead-list creation/diagnosis — not part of the 店舗IT担当 product itself |
| AI video generation pipeline | `vidcel-generation-lab`, `vidcel-pipeline`, `vidcel-assets` | Unrelated to 店舗IT担当; Vidcel's separate video-production business |
| Internal ops dashboard | `vidcel-dashboard` (this repo) | Unrelated to 店舗IT担当; Vidcel's own ops tracking |

## Repos checked (all 7 accessible to this session)

`vidcel-dashboard`, `ai-lead-os`, `vidcel-web`, `vidcel-generation-lab`,
`vidcel-pipeline`, `vidcel-lp`, `vidcel-assets` — searched for `wrangler.toml`/
`wrangler.json(c)`, `package.json` deps on `stripe`/`resend`, and any
Cloudflare/Stripe/Resend/onboarding-form references. See PM-002 conversation
record for the full per-repo grep output.

## Confirmed production architecture (PM-003, 2026-07-25)

The open question below was resolved by the project owner. The initial
production flow is:

```
Stripe Payment Link
  → Google Form
  → Google Spreadsheet (店舗IT担当_オンボーディング管理_v1)
  → existing Google Apps Script (bound to that spreadsheet)
  → customer registration, payment confirmation, task generation, customer emails
```

Deliberately **not** part of the initial release (see `Backlog.md` and
`08_DecisionLog` in the PM OS for the full reasoning): a custom Cloudflare
Worker, a custom Stripe API backend, Resend, a custom database, a custom
admin dashboard, or direct integration with `ai-lead-os`. All of these are
recorded in the PM OS's `07_Parking` sheet, not deleted — they remain
re-proposable via `06_Backlog` if operational evidence later justifies them.

This was not a guess: the Apps Script's own execution log (`Logs` sheet in
`店舗IT担当_オンボーディング管理_v1`, inspected directly 2026-07-25) shows
real, working evidence for most of the flow — duplicate-customer prevention,
payment-method/status capture, task generation, and confirmation emails all
fired correctly for test customers. What is **not** yet verified: whether
the Stripe Payment Link itself is currently active and redirects correctly
(requires Stripe dashboard access this session doesn't have), and there is
no production/test data separation or documented cancellation procedure yet.
Full per-item status: PM OS `04_Gates`, "Gate 1 — Ready to Accept First
Paying Customer".

## Superseded: original open question (resolved above)

No repo implements the "申込〜決済〜登録〜通知" flow as a custom backend —
and per the decision above, none needs to for the initial release. The
previous framing of this as "which repo should build it" no longer applies;
the answer is "none, by design — the existing Apps Script already does it."
