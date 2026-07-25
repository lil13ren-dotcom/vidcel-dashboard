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
