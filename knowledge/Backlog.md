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

2. ~~G1-09 (bridge mechanism) — How does the Vidcel onboarding page actually
   deliver data into the existing Google Sheet?~~ **Design resolved by
   G1-06D (2026-07-25).** See `ADD_G1-06D_Onboarding_Data_Bridge.md`: an
   Apps Script Web App calling the existing registration logic directly.
   Rejected: direct Sheets API calls (doesn't solve the trigger problem
   alone) and a Cloudflare Worker proxy (would re-reverse PM-003's Worker
   deferral a third time). **Implementation is G1-12 — now BLOCKED**, see
   item 0a below. Still blocks Gate 1 items 3–4 until built and
   independently validated (no inherited Form evidence, per the ADD).

0a. **⚠️ G1-12 BLOCKED — implementing the Web App endpoint requires
   the real Apps Script source, which was never obtained.** Everything
   documented about `handleFormSubmit` etc. across G1-06 through G1-11 was
   inferred from `Logs` messages and sheet headers, never read from actual
   code — this only became a blocking problem once implementation (not
   design/analysis) was requested. Also: this session has no Apps Script
   deployment/execution access at all, so nothing could be tested even
   with the source. See `CHECKLIST_G1-12_Source_Access.md` for the exact
   files/config needed and the five-phase breakdown (source review →
   implementation → deployment → runtime testing → E2E evidence). No code
   was written. Top blocker on Gate 1 items 3–4, ahead of item 3 (Stripe
   Payment Link verification) in practical urgency since nothing else in
   the onboarding-page work can proceed without it.

   ⚠️ **Naming collision:** `03_MasterTask`'s `G1-09` row (added by G1-06C)
   is this bridge-mechanism task. The task that produced
   `SPEC_G1-09_Onboarding_Data_Model.md` (field set / data model — item 2a
   below) was *also* labeled "G1-09" by the project owner, but is a
   different scope. Flagged, not resolved — the PM OS workbook wasn't in
   scope for either doc-only task. Recommend the owner either renumber one
   (e.g. the field-model task becomes G1-09B) or explicitly merge them
   before either gets a real implementation Task ID.

2a. **G1-09 (data model) — What fields does the onboarding page collect,
   and where do they go?** Specified by the task above:
   `SPEC_G1-09_Onboarding_Data_Model.md`. 18 fields reused as-is from the
   current Form/`Customers` schema, 6 new fields justified by the confirmed
   JP+US Payment Links (Country, Preferred Language, Currency, WhatsApp,
   Time Zone, a Country-conditional Legal Consent Set). Not implemented.
   Surfaced a **live bug**: `00_Dashboard`'s MRR formula assumes ¥2,980 for
   every customer — see item 7 below.

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

7. ~~Live bug: `00_Dashboard`'s MRR formula assumes ¥2,980 for every
   customer.~~ **Full model designed by G1-11 (2026-07-25) — not yet
   implemented, not yet a Task ID.** See
   `SPEC_G1-11_Multicurrency_KPI_Model.md`: 12 formulas affected (not just
   MRR — gross profit, margin %, LTV, CAC all inherit it), plus a second,
   distinct problem where `Cost_Model`'s fixed costs have no currency
   dimension at all. Recommends `Billing Amount` + `Currency` fields (the
   G1-09 spec proposed `Currency` alone, which isn't sufficient by itself —
   closed here), a `GOOGLEFINANCE`-based FX rate (no new vendor), and
   showing both separate per-currency totals and one labeled converted
   total. **Recommended gate: validate with a synthetic USD customer row
   before the first real US customer is onboarded** — independent timing
   from the rest of the onboarding-page work.

8. **Legal consent checkboxes aren't copied from the raw Form response log
   into the processed `Customers` table.** Pre-existing gap, found while
   building the G1-09 data-model spec; unrelated to the multi-market
   question but means the canonical customer record has no consent audit
   trail today.

9. **Legal review needed for non-Japan (starting with US) consent
   requirements** before the Legal Consent Set field in
   `SPEC_G1-09_Onboarding_Data_Model.md` can be finalized. Explicitly not
   something to guess at in an engineering spec.

10. **Does Stripe charge a different fee rate for USD vs. JPY
   transactions?** `Cost_Model!B6` (3.6%) is currently assumed uniform
   across currencies — found while building `SPEC_G1-11_Multicurrency_KPI_Model.md`,
   not verified against Stripe's actual per-currency/region fee schedule.

11. **Tax/accounting treatment of multi-currency revenue** — needs
   accounting/legal input before real USD revenue is used in any reporting
   shown outside the team (investors, tax filings, etc.). Same category as
   item 9; flagged by `SPEC_G1-11`, not assessed there.

12. ~~PM-AUTO-01's pytest/mypy/ruff/npm-build detection is unverified
   against a repo that actually has them configured.~~ **Resolved by
   PM-AUTO-02 (2026-07-25).** Validated against `ai-lead-os`'s real
   pytest/mypy/ruff/Alembic config: all 6 checks (Ruff check, Ruff format
   check, mypy strict, Alembic upgrade+check, pytest+coverage) correctly
   discovered and executed, output matching a manual baseline exactly; a
   deliberately-injected Ruff violation was correctly detected as FAIL
   (no false PASS) and reverted. npm-build detection remains untested
   against a repo with a real `package.json`/build script — `ai-lead-os`
   is a pure Python repo, so this specific sub-path is still only
   smoke-tested against the "no package.json" skip path. See
   `Decision_Log.md`'s PM-AUTO-02 entry.

13. **Confirm folder-structure interpretation for `automation/`.**
   PM-AUTO-01's instructions listed `automation/`, `reports/`, `review/`,
   `tasks/`, `knowledge/` without clear nesting; built as
   `automation/{reports,review,tasks}/` reusing the existing top-level
   `knowledge/` rather than a new `automation/knowledge/`. Flagged in
   `Decision_Log.md` in case a separate nested one (e.g. for automation-run
   logs) was actually intended.

14. **PM-AUTO-03's `risk` field (LOW/MEDIUM/HIGH) doesn't gate anything
   yet.** It's captured in `review_decision.json` and defaults to MEDIUM
   if omitted, but a `HIGH` risk `PASS` is currently treated identically to
   a `LOW` risk `PASS` — no extra approval step, no different exit code.
   Worth a decision on whether e.g. HIGH risk should force a distinct exit
   code or a mandatory `status_override` before the pipeline will report
   PASS, once there's a real case where risk should have changed the
   outcome and didn't.

15. **No actual GitHub Actions workflow consumes
   `run_pm_pipeline.py`'s exit code yet.** PM-AUTO-03 made the exit code
   CI-shaped (0/2/3/1) specifically for this, per its own explicit "must be
   suitable for future GitHub Actions integration" requirement, but no
   `.github/workflows/*.yml` file exists. This is the suggested next task
   (PM-AUTO-04) — see `automation/review/next_task_draft.md`.
