# Decision Log — PM OS project

Append-only. Newest entries at the bottom.

## 2026-07-25 — PM OS built as new spreadsheet, v2 kept as archive

Transformed `店舗IT担当_経営マスタープラン_v2` into a standardized 12-sheet
PM OS (00_Dashboard … 11_AI_Request), delivered as a new workbook
`店舗IT担当_PM_OS_マスタープラン_v3` (uploaded manually by the user due to a
tool size limit on inline Drive upload — see below). v2 untouched, kept as
reference archive. No Apps Script added; formulas/data validation/
conditional formatting only, per explicit instruction.

## 2026-07-25 — Google Drive upload tool size limit

The Drive MCP tool in this session only accepts full inline file content
(base64) for uploads, with no path-reference or chunked-upload option. The
completed v3 workbook (~105KB / ~140K base64 chars) exceeded what could be
reliably transmitted in a single tool call. Decision: hand the file to the
user directly (`SendUserFile`) instead of attempting a partial/risky inline
upload that could leave a corrupted file in Drive. User uploads manually
(drag-and-drop auto-converts xlsx to Sheets).

## 2026-07-25 — PM-001 blocked: repo/spreadsheet mismatch

PM-001 asked to reconcile the PM OS's task list (Gate 0–4, referencing
Cloudflare Worker / Stripe / Resend / E2E) against "the repository." The only
repo in scope at the time (`vidcel-dashboard`) is Vidcel's own ops dashboard
— unrelated tech stack, unrelated business. Rather than fabricate
implementation status against the wrong codebase, stopped and asked the user
which repo actually contains the 店舗IT担当 production code.

## 2026-07-25 — PM-002: production repo search, Gate 1 cannot be marked PASS

Cloned and inspected all 7 repos accessible to this session
(`vidcel-dashboard`, `ai-lead-os`, `vidcel-web`, `vidcel-generation-lab`,
`vidcel-pipeline`, `vidcel-lp`, `vidcel-assets`). Findings (see
`Architecture.md` for the full table):

- No repo contains a Stripe integration (confirmed independently by
  `ai-lead-os/knowledge/BUSINESS_ASSET_INVENTORY.md`, which lists Stripe as
  "not integrated" anywhere yet).
- No repo contains a Resend integration.
- `vidcel-web` contains Cloudflare Worker config (`wrangler.jsonc`) for
  three **demo** sites (restaurant/beauty/clinic) explicitly marked
  "not configured... in this portfolio implementation" — sales assets, not
  the production subscription flow.
- The only real, live system for 店舗IT担当 customer operations is the
  Apps-Script-bound Google Sheet `店舗IT担当_オンボーディング管理_v1`
  (verified trigger/log history), which is not in any git repo.

Decision: per PM-002's explicit instruction, did **not** update the PM OS
(03_MasterTask / 02_Gantt / 04_Gates / 06_Backlog / 07_Parking /
08_DecisionLog) with guessed statuses. Gate 1 (Cloudflare/Worker/Stripe/LP/
AI Chat/E2E all-checked → Release) remains unverifiable as PASS — the
underlying production components do not exist in code yet. This is a
business decision (build vs. reuse vs. re-scope), not something to resolve
by further searching.

## 2026-07-25 — PM-003: initial production architecture confirmed; PM OS corrected

Project owner confirmed the initial production flow: **Stripe Payment Link →
Google Form → Google Spreadsheet → existing Apps Script** (customer
registration, payment confirmation, task generation, customer emails). A
custom Cloudflare Worker, custom Stripe API backend, Resend, a custom
database, a custom admin dashboard, and direct `ai-lead-os` integration are
explicitly **not required** for the initial release.

PM OS corrected accordingly (workbook only; the working onboarding Apps
Script itself was not touched, per instruction):

- `03_MasterTask` / `02_Gantt`: G1-01 (Cloudflare auth), G1-02 (Worker
  deploy), G1-03 (Resend) marked **Obsolete** (new status value added to
  both sheets' dropdowns) rather than deleted, with a note pointing to this
  entry and to `07_Parking`. G1-04 (E2E test) re-scoped to the confirmed
  architecture and moved to In Progress based on real evidence (see below).
  Three new tasks added — G1-06 (Stripe Payment Link + redirect
  verification, **Blocked**: no Stripe dashboard access this session),
  G1-07 (prod/test data separation, **Not Started**: no mechanism exists),
  G1-08 (cancellation/failed-payment procedure documentation, **Not
  Started**: only ad hoc manual edits exist, no written procedure).
- `04_Gates`: the old generic 6-item checklist (Cloudflare/Worker/Stripe/LP/
  AI Chat/E2E) — which assumed the wrong architecture — was removed and
  replaced with **"Gate 1 — Ready to Accept First Paying Customer"**, 15
  evidence-based checks. Status source: `店舗IT担当_オンボーディング管理_v1`'s
  Apps Script `Logs` sheet, read directly (not inferred from documentation).
  Result: **11 Completed, 3 Not Started, 1 Blocked → Gate 1 = Release不可**.
  The Blocked and Not Started items (Stripe Payment Link liveness/redirect,
  prod/test separation, cancellation procedure) are the only things standing
  between this and a real first paying customer.
- `07_Parking`: added the three deferred backend components (custom Worker,
  Resend, custom Stripe backend) with re-evaluation conditions, so they are
  not lost, just correctly deprioritized.
- `06_Backlog`: noted that these components were considered and deferred by
  decision, not simply unaddressed — re-proposing them requires going
  through Backlog again, per the PM OS's own rules.

Recommended next Task ID: **G1-06** (Stripe Payment Link liveness +
redirect verification) — it is the highest-value unblock, requires the
project owner (not Claude Code, which has no Stripe access), and both
Not Started items (G1-07, G1-08) are lower-risk paperwork/process work that
can proceed in parallel or after.
