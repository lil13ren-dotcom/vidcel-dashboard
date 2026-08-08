# G1-12 Blocker: Source Code & Environment Acquisition Checklist

- **Task ID:** G1-12
- **Date:** 2026-07-25
- **Status:** BLOCKED — this document exists to unblock it, not to implement
  anything. No code was written for G1-12. No production code should be
  written based on guessed function signatures or inferred internal logic.

## Why this exists

G1-12 ("Apps Script Web App Endpoint") asked for an actual implementation.
Two capability gaps make that impossible to do honestly right now:

1. **No access to the actual bound Apps Script source code.** Everything
   documented so far about `handleFormSubmit`, `generateInitialTasks`,
   `sendApplicationReceivedEmail`, `sendPaymentConfirmedEmail`,
   `handleEdit`, `refreshToday`, `receiveAiInquiry`, `setupAll`,
   `installTriggers`, `notifyError`, and `ensureBankPlaceholderSettings`
   was **inferred from the `Logs` sheet's message strings and the
   spreadsheet's column headers** (`Customers`, `Tasks`, `Today`,
   `Settings`) — not from reading the actual code. A Drive search for the
   bound script (`mimeType = 'application/vnd.google-apps.script'`,
   `fullText contains 'handleFormSubmit'`) found only two unrelated
   standalone script projects (a Gantt-chart backup script and a Google
   Places API scraper) — the actual bound script wasn't returned by either
   query.
2. **No Apps Script deployment/execution environment.** This session has
   Google Drive-level tools only (search/read/create files) — no Apps
   Script API access. A Web App cannot actually be deployed or given a
   real URL, and no code can be executed to produce genuine test evidence.

**Explicit instruction being followed:** the existing Google Form's
execution evidence (in `Logs`) must **not** be treated as evidence for the
new `doPost` endpoint — they are different integrations and each needs its
own validation once built.

## Checklist — what's needed before implementation can resume

### A. Source code

- [ ] The Apps Script project's `.gs`/`.js` file(s) bound to
  `店舗IT担当_オンボーディング管理_v1` — full contents, not excerpts.
  Specifically need to see the real implementations of (at minimum):
  `handleFormSubmit`, `generateInitialTasks`, `sendApplicationReceivedEmail`,
  `sendPaymentConfirmedEmail`, `handleEdit`, `refreshToday`,
  `receiveAiInquiry`, `notifyError`.
- [ ] `appsscript.json` (the project manifest) — timezone, OAuth scopes,
  runtime version (`V8` vs. Rhino), any existing `webapp` config block.
- [ ] Any existing Web App deployment already present (check the
  Deployments panel in the Apps Script editor) — a deployment ID, current
  access level ("Anyone" / "Anyone with Google account" / restricted), and
  execution identity ("Execute as: me" vs. "as the user accessing").

**How to get it** (owner action — no tool in this session can pull it
directly):
- Open the spreadsheet → Extensions → Apps Script, and either paste each
  file's contents directly into the conversation, or share the script
  project itself (its own Drive-visible ID, distinct from the
  spreadsheet's ID) with read access this session's Google account can
  reach.
- Alternative: use Google's `clasp` CLI locally to `clasp pull` the
  project to a local folder, then share those files.

### B. Trigger configuration

- [ ] Exact list of installable triggers currently configured (Apps Script
  editor → Triggers panel, or `installTriggers`'s actual code once seen).
  `Logs` confirms three exist ("フォーム送信時 / 編集時 / 毎日7時") but not
  their exact handler function names, execution identity, or failure
  notification settings.

### C. Script configuration / properties

- [ ] Full list of Script Properties actually read by the code (e.g.
  `NOTIFY_EMAIL` is confirmed **unset**, per a `WARN` log entry — need to
  know what else exists: sheet/tab name constants, any Stripe-related
  config, thresholds, etc.).

### D. Environment for implementation, deployment, and testing

- [ ] A decision on how this session (or the owner) will actually deploy
  and test a new Web App — either:
  - the owner runs a full deploy/test loop manually and reports results
    back (slower, but requires no new tooling), or
  - an Apps Script API-capable tool/connector is added to this session
    (would need to be provisioned, similar to how GitHub/Drive access was
    added earlier in this project) — **not currently available**.
- [ ] Whichever approach: **testing must not run against the live
  production spreadsheet.** A copy (per PM OS Gate 1 item 13 / Backlog
  item on prod/test separation, G1-07) or a dedicated test spreadsheet is
  needed so validation runs don't risk real customer data.

## Phase separation (explicit, per instruction — none of these may be
merged or assumed complete because an earlier one is)

| Phase | What it is | Status | Can start when |
|---|---|---|---|
| 1. Source code review | Read and understand the actual `.gs` files, trigger config, script properties (checklist A–C above) | **Blocked** | Checklist A–C items are provided |
| 2. Implementation | Write the `doPost` handler + any required refactor (e.g. decoupling registration logic from `onFormSubmit`, per `ADD_G1-06D`) | Not started | Phase 1 is complete |
| 3. Deployment | Publish as a Web App — new deployment, stable URL, execution identity and access level configured | Not started | Phase 2 is complete, and checklist D's environment decision is made |
| 4. Runtime testing | Invoke the deployed endpoint with test payloads (valid, missing field, invalid email, duplicate) against a **non-production** spreadsheet copy, observe actual results | Not started | Phase 3 is complete |
| 5. E2E evidence | Full flow evidence once the onboarding page (G1-09/`ADD_G1-06D`) exists too: payment → page → endpoint → sheet → existing Apps Script logic → task generation → email, independently validated | Not started | Phase 4 is complete, onboarding page exists |

Each phase gets its own Task ID once it actually starts — none are
pre-assigned here, since the scope of phases 2–5 depends on what phase 1
finds. A design document or code draft existing (`ADD_G1-06D`,
`SPEC_G1-09_Onboarding_Data_Model.md`) does **not** mean any of these
phases are complete or partially complete — design and implementation are
different phases with different evidence requirements, per instruction.

## What NOT to do while blocked

- Do not write `.gs` code based on the inferred function names/behavior
  above — they are a best guess from log messages, not verified signatures.
- Do not treat the Google Form's `Logs` evidence as validating anything
  about the not-yet-built `doPost` endpoint.
- Do not mark G1-12, or PM OS `04_Gates` items 3–4, as Completed or
  partially complete because this checklist or `ADD_G1-06D`'s design
  exists — they remain Blocked/Not Started until each phase above is
  independently done and evidenced.
