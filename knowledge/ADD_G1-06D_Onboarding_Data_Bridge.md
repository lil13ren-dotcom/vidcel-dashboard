# Architecture Decision Document — Production Onboarding Data Bridge

- **Task ID:** G1-06D
- **Date:** 2026-07-25
- **Status:** Proposed (not implemented — this document is the deliverable;
  building the bridge is separate, future, Task-ID-gated work)
- **Decides:** how the Vidcel Onboarding Page delivers customer data into
  the existing `店舗IT担当_オンボーディング管理_v1` spreadsheet, without
  modifying Stripe, the onboarding Apps Script, or any production workflow.

## 1. Context

G1-06C finalized the entry point: **Stripe Payment Link → Vidcel Onboarding
Page** (replacing the native Google Form), while the backend — Google
Sheets + the existing Apps Script — was confirmed to stay unchanged. That
left an explicit gap: *how* does the onboarding page's data reach the same
spreadsheet the Apps Script already watches? This document is that
decision.

### The constraint that shapes every option

The existing automation's customer-registration logic (`handleFormSubmit`:
dedup by email/phone, `Customers` row creation, `generateInitialTasks`,
`sendApplicationReceivedEmail`) is wired to an **installable `onFormSubmit`
trigger** (confirmed in the Apps Script's own `Logs` sheet:
`installTriggers` → "トリガーを設定しました（フォーム送信時 / 編集時 /
毎日7時）"). `onFormSubmit` is a Google Forms–specific event. It does
**not** fire for rows added by the Sheets API, nor for rows added by an
Apps Script Web App unless that Web App is itself part of a real Form
submission. **No option below can make a non-Form data source "trigger"
`onFormSubmit` — that event is not obtainable outside a real Form
response.** This rules out any design that assumes the existing trigger
can be reused as-is; every option instead needs `handleFormSubmit`'s
*registration logic* invoked directly, decoupled from the Form-submission
event that currently is its only caller. That decoupling is itself a small,
identified Apps Script change — not made in this task, but named explicitly
in every option below as the shared prerequisite.

## 2. Decision drivers

Per this task's evaluation criteria: low maintenance, low operational cost,
simple deployment, minimal vendor lock-in, scalability, and compatibility
with the existing Apps Script automation (dedup, task generation,
confirmation emails).

## 3. Options considered

### Option A — Vidcel Onboarding → Apps Script Web App → Google Sheets → existing Apps Script workflow

The onboarding page POSTs JSON to a `doPost(e)` endpoint added to the
*same* Apps Script project already bound to the spreadsheet. That handler
calls the registration logic directly (the decoupled function described
above) — no simulated Form event needed, no Sheets API credentials needed,
because the code already runs inside the spreadsheet's own script context.

- **Pros:** Reuses 100% of existing logic (dedup, task generation, emails)
  with zero duplication — it's the same functions, called a different way.
  No new vendor, no new hosting, no new secrets beyond a shared
  request-signing token. Free within Apps Script quotas. Stays entirely
  inside the Google Workspace boundary already trusted for this data.
- **Cons:** Apps Script Web Apps have real operational quirks: deployment
  versioning (a new "deployment" is needed to publish URL changes, easy to
  get wrong), execution identity choice ("Execute as: me" vs. "as the user
  accessing") has security implications, no built-in schema validation, and
  debugging/observability are weaker than a typical backend framework.
- **Complexity:** Low–medium. Conceptually simple (one HTTP endpoint
  wrapping existing functions); the friction is entirely in Apps Script's
  deployment/permissions model, not in the logic itself.
- **Risks:** A Web App deployed with "Anyone" access is publicly reachable
  with no inherent trust boundary — **must** validate the caller (e.g. a
  shared secret or signature the onboarding page includes in every
  request) or the endpoint becomes an open, unauthenticated way to inject
  fake customer rows. Consumer Apps Script execution has a 6-minute/
  execution ceiling and daily quota limits — unlikely to matter at this
  volume, but worth knowing.
- **Migration effort:** Low. Add one `doPost` handler + one small refactor
  (extract the registration logic so it's callable from both `onFormSubmit`
  and `doPost`) to the *existing* script project; no new infrastructure to
  provision.

### Option B — Vidcel Onboarding → Google Sheets API (direct)

The onboarding page's own backend (it would need one — this can't be called
safely from browser JS without exposing credentials) calls the Google
Sheets API directly with a service account to append a row.

- **Pros:** Standard, well-documented Google API; not tied to Apps Script's
  deployment model; usable from any server-side runtime.
- **Cons:** Does not solve the trigger problem — appending a row via the
  Sheets API still does not invoke `handleFormSubmit`'s logic, so
  duplication would be required *unless* this is combined with Option A
  anyway (call the Sheets API to write the row, then separately call an
  Apps Script Web App to run the registration logic — at which point Option
  A alone is simpler). Requires provisioning and protecting a Google Cloud
  service account (a new credential/secret class this system doesn't
  currently have).
- **Complexity:** Medium. New credential management, new server-side code
  path in the onboarding page.
- **Risks:** Credential leakage if the service account key is mishandled;
  namespace/quota management on a Google Cloud project that doesn't
  currently exist for this purpose.
- **Migration effort:** Medium–high, and doesn't fully replace the need for
  Option A's logic-invocation anyway — this is the weakest option unless
  paired with A, in which case A alone is preferable.

### Option C — Vidcel Onboarding → Cloudflare Worker → Google Sheets

A Cloudflare Worker acts as a thin proxy: receives the onboarding page's
data, authenticates to the Google Sheets API (service account, same as
Option B), writes the row.

- **Pros:** Matches the deployment pattern already used by `vidcel-web`'s
  other apps (`wrangler.jsonc` + OpenNext), if the onboarding page ends up
  hosted there. Good edge performance.
- **Cons:** **Directly reintroduces a custom Cloudflare Worker — the exact
  component PM-003 explicitly decided was not required for the initial
  release and moved to `07_Parking`.** Doesn't solve the trigger problem
  any better than Option B (still needs a way to invoke the registration
  logic, most naturally by also calling an Apps Script Web App — i.e., this
  option is Option A plus an unnecessary extra hop). Adds Cloudflare
  Secrets management for the same service account credential as Option B.
- **Complexity:** Highest of the three. New deployment target, new secret
  management, still doesn't avoid needing Option A's Apps Script changes.
- **Risks:** Same credential risk as B, plus reopens a decision the project
  owner already made once (see `Decision_Log.md`, PM-003 and the G1-06
  conflict entry — this is the third time Worker/Resend-style infra has
  resurfaced after being deferred).
- **Migration effort:** Highest — new infra, new secrets, and the
  trigger-invocation problem still isn't solved by this layer alone.

### Option D — Alternative not listed above: embed/redirect to the real Google Form

Considered as a lower-effort fallback, not the primary recommendation: the
Vidcel Onboarding Page could embed the actual Google Form (iframe) or
redirect to a prefilled Form URL after Stripe payment, rather than building
any new data bridge at all.

- **Pros:** Zero new integration code — `onFormSubmit` keeps firing exactly
  as it does today, because it *is* still a real Form submission. No Apps
  Script changes needed at all.
- **Cons:** Likely defeats the business reason for building a custom
  onboarding page in the first place (branded UX, controlled flow) — an
  embedded/redirected native Google Form looks and behaves like a Google
  Form, not a "Vidcel" page. Doesn't scale well if the onboarding page is
  meant to grow richer (e.g. multi-step, dynamic pricing display).
- **Complexity:** Lowest.
- **Risks:** Low technical risk, but a real risk of not meeting the
  original intent behind replacing the Form.
- **Migration effort:** Lowest — but only defers the real integration work
  rather than doing it.

## 4. Recommendation

**Recommend Option A** (Vidcel Onboarding → Apps Script Web App → existing
registration logic).

**Reasoning:** It is the only option that satisfies every decision driver
simultaneously — no new vendor (Cloudflare, a Google Cloud service account)
and no new hosting; it reuses the existing, already-proven registration
logic by direct function call rather than by duplicating it or trying to
simulate an event that can't be simulated; and it keeps the entire customer
data path inside the Google Workspace boundary the business already trusts
and pays for. Option B doesn't solve the core problem on its own. Option C
reopens a decision (custom Worker) the owner already made twice before.
Option D is viable only if the custom-UX goal is dropped, which is a
product decision, not an architecture one.

**Migration path:** (1) extract `handleFormSubmit`'s registration logic
into a function callable independent of the Form-submit event; (2) add a
`doPost` handler to the same Apps Script project that validates a shared
secret/signature and calls that function with the onboarding page's
payload; (3) deploy as a Web App; (4) onboarding page POSTs to that URL
after Stripe payment confirmation. Each step is independently testable
before the old Form is retired.

**Backward compatibility:** Full — the native Google Form can keep working
unmodified in parallel during migration (both paths call the same
underlying function), giving a safe rollback if the new page has issues.

**Operational complexity:** Low ongoing burden — one Apps Script project to
maintain (same as today), no new service to monitor, no new bill.

**Future scalability:** Apps Script consumer quotas (execution time,
triggers/day) are generous relative to this business's current and
near-term volume (tens–low hundreds of customers). If volume eventually
exceeds Apps Script's ceiling, this design doesn't block a later migration
to a real backend — the decoupled registration-logic function from step (1)
above would still exist as the reference implementation to port.

## 5. Evidence status — explicit statement per instruction

**No existing Google Form validation evidence is inherited by this
decision or by the future Option-A implementation.** The Google Form's
proven behavior (required fields, legal consent capture, duplicate
prevention, correct delivery to the spreadsheet — see PM OS `04_Gates`
items 3–4, reset to Not Started by G1-06C) was evidence for the Form
specifically. Whatever replaces it — a `doPost` Web App per this
recommendation — is a new integration and requires its own independent
end-to-end validation once built: request signing/validation actually
rejects unauthorized calls, required-field and consent enforcement is
reproduced (not just visually present, but actually blocking submission
without them), duplicate-customer detection still fires, and a real test
submission reaches the spreadsheet and triggers task generation and the
confirmation email — all under the new path, not assumed from the old one.

## 6. Required future implementation tasks (not started, no Task ID assigned yet)

1. Extract `handleFormSubmit`'s registration logic into a directly-callable
   function (Apps Script change — requires its own Task ID and explicit
   authorization; not covered by this ADD).
2. Add and secure a `doPost` Web App endpoint (shared-secret or signature
   validation; decide execution identity).
3. Build/confirm the Vidcel Onboarding Page itself (location currently
   unknown — see `Backlog.md`).
4. Wire the onboarding page to POST to the new endpoint after Stripe
   payment confirmation.
5. Independent E2E validation of the new path (per §5 above) — this is
   what would actually move PM OS `04_Gates` items 3–4 back to Completed,
   with new evidence, not the old Form's.
6. Decide and implement the Stripe → onboarding-page redirect itself
   (still open per G1-06/G1-09 in the PM OS).

## 7. Open questions

- Where will the Vidcel Onboarding Page be hosted/built? Not found in any
  of the 7 repos this session has inventoried (see `Architecture.md`).
- Does the onboarding page use Resend for anything of its own (e.g., an
  immediate branded confirmation distinct from the Apps Script's existing
  email)? Still unconfirmed either way (see `Backlog.md`).
- Who owns writing the `doPost` handler and the shared-secret scheme —
  Claude Code (once authorized with a Task ID) or the project owner
  directly, given it touches the production Apps Script?
