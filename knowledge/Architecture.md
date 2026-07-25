# Architecture — 店舗IT担当 business, as verified 2026-07-25

**⚠️ 2026-07-25 update (G1-06C): the "Confirmed production architecture"
diagram below (from PM-003) is now superseded on the entry point.** Finalized
architecture: **Stripe Payment Link → Vidcel onboarding page (replaces
Google Form) → Google Sheets + existing Apps Script (backend, unchanged)**.
The backend portion of PM-003's decision stands as originally reasoned; only
the entry point changed. The evidence below (Apps Script `Logs`) is still
factually accurate for what the *backend* does — it just doesn't
automatically prove anything about the not-yet-built onboarding page. See
`Decision_Log.md`'s G1-06C entry, and PM OS `04_Gates`/`03_MasterTask`
(new task G1-09) for what's still open: the onboarding-page → Sheet
integration mechanism, and whether Resend has any role in the new page.

Cross-repo inventory produced by PM-002 (repository search for the 店舗IT担当
production implementation). Verified by cloning and inspecting each repo
directly — not inferred from names or memory.

## Where things actually live

| Concern | Location | Status |
|---|---|---|
| PM management (roadmap, tasks, gates, KPI) | Google Sheets `店舗IT担当_PM_OS_マスタープラン_v3` | Live, this is the SSOT |
| Customer onboarding backend | Google Sheets `店舗IT担当_オンボーディング管理_v1` + bound Apps Script | Live and proven (form submit, daily 7am, edit triggers — see `Logs`). **Confirmed as the permanent backend (G1-06C)**; its input is changing from the native Google Form to a new "Vidcel onboarding page" whose data-delivery mechanism isn't decided yet (G1-09) |
| Customer onboarding entry point | "Vidcel onboarding page" (not yet located/built — name only, per G1-06C) | **Not found in any of the 7 repos inventoried by PM-002.** May not exist yet, or may live in a repo/branch not yet in this session's scope |
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

## Confirmed production architecture (PM-003 2026-07-25, entry point updated by G1-06C 2026-07-25)

```
Stripe Payment Link
  → Vidcel onboarding page   ← entry point, replaces the Google Form (G1-06C)
  → Google Spreadsheet (店舗IT担当_オンボーディング管理_v1)   ← integration mechanism TBD, see G1-09
  → existing Google Apps Script (bound to that spreadsheet)   ← backend, unchanged (PM-003)
  → customer registration, payment confirmation, task generation, customer emails
```

The backend (Sheets + Apps Script) is unchanged from PM-003's original
decision. Only the entry point changed. The step from "Vidcel onboarding
page" to "Google Spreadsheet" is **not yet a real, working link**.

**2026-07-25 (G1-06D): that link now has a recommended design.** See
[`ADD_G1-06D_Onboarding_Data_Bridge.md`](./ADD_G1-06D_Onboarding_Data_Bridge.md)
for the full Architecture Decision Document. Summary: an Apps Script
**Web App** (`doPost`) added to the *same* script project already bound to
the spreadsheet, calling the existing registration logic directly (not via
the Form-only `onFormSubmit` trigger, which cannot be invoked by any
non-Form data source — this is a hard technical constraint, not a
preference). Rejected: direct Google Sheets API calls and a Cloudflare
Worker proxy (the latter would re-reverse PM-003's Worker-deferral decision
for the third time — see the G1-06 conflict entry in `Decision_Log.md`).
**Nothing has been implemented** — the ADD is a recommendation pending
its own authorization and Task ID (see the ADD's §6 for the itemized
follow-up work). Until then, this diagram remains the *target*, not
something functioning end-to-end.

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

## Architecture Decision Documents & Specifications

- [`ADD_G1-06D_Onboarding_Data_Bridge.md`](./ADD_G1-06D_Onboarding_Data_Bridge.md)
  — how the Vidcel Onboarding Page delivers data to the existing spreadsheet/
  Apps Script backend. Recommends an Apps Script Web App. Not implemented.
- [`SPEC_G1-09_Onboarding_Data_Model.md`](./SPEC_G1-09_Onboarding_Data_Model.md)
  — the onboarding field set itself: 18 reused fields (verified against the
  live Form/`Customers` schema) + 6 new fields (Country, Preferred Language,
  Currency, WhatsApp, Time Zone, Legal Consent Set), justified by the
  confirmed JP + US Stripe Payment Links (G1-06). **Surfaces a real,
  already-live bug**: `00_Dashboard`'s MRR formula assumes every customer
  pays ¥2,980 — a USD customer would silently corrupt that figure today.
  Not implemented; see the spec's §4 for the recommended build order.
- [`SPEC_G1-11_Multicurrency_KPI_Model.md`](./SPEC_G1-11_Multicurrency_KPI_Model.md)
  — full KPI impact analysis for the MRR bug above: **12 formulas across
  `00_Dashboard`/`Cost_Model`/`05_KPI`** are affected (not just the one MRR
  cell — the same single-currency assumption propagates into gross profit,
  margin %, LTV, and CAC). Proposes `Currency` + `Billing Amount` fields, a
  `GOOGLEFINANCE`-based FX reference (no new vendor/credential), and
  recommends showing **both** separate per-currency totals and one clearly-
  labeled converted consolidated figure rather than picking one. Not
  implemented — formulas are unchanged.

## Superseded: original open question (resolved above)

No repo implements the "申込〜決済〜登録〜通知" flow as a custom backend —
and per the decision above, none needs to for the initial release. The
previous framing of this as "which repo should build it" no longer applies;
the answer is "none, by design — the existing Apps Script already does it."
