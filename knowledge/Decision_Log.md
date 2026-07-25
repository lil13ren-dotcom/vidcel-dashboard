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

## 2026-07-25 — G1-06: partial evidence received; redirect assumption corrected; **conflicts with PM-003**

Project owner supplied partial evidence for G1-06 and, in the same message,
corrected the assumed post-payment redirect target:

- **Confirmed by owner:** a Japan Stripe Payment Link exists; a US Stripe
  Payment Link exists.
- **Still not evidenced:** active status, exact product names, exact
  recurring prices, live vs. test mode, the actual Payment Link URLs,
  post-payment redirect configuration, whether the production LP's CTA
  matches the Stripe Payment Link URL, and end-to-end payment→onboarding
  completion.
- **Architecture correction:** the intended flow is no longer "Stripe
  Payment Link → Google Form." It is **"Stripe Payment Link → Vidcel
  onboarding page → Resend workflow."** The Resend onboarding flow is
  explicitly confirmed **incomplete** by the owner, so the redirect and
  full E2E cannot yet be validated either way.

G1-06 recorded as **部分完了/証跡待ち (PARTIALLY COMPLETE / EVIDENCE
PENDING)** — a new status value, distinct from Completed/Blocked/Not
Started, added to `03_MasterTask` and `02_Gantt`'s dropdowns. `04_Gates`
Gate 1 checklist item 2's wording changed from "...reaches the correct
Google Form" to "...reaches the correct destination" (no destination
assumed). Gate 1 remains **Release不可 (NO-GO)** — this correction, if
anything, adds an unresolved item (the Resend workflow) rather than
resolving one.

**⚠️ This directly conflicts with PM-003's decision (immediately above),
which explicitly moved Resend to `07_Parking` as "not required for the
initial release" on the grounds that the existing Apps Script (`GmailApp`)
already had working send evidence.** That evidence is still accurate — the
Apps Script's `Logs` sheet genuinely shows working confirmation/payment
emails — but it now appears to describe a *different* pipeline (Google
Form → Spreadsheet → Apps Script) than the one the owner says is actually
intended for production (Stripe → Vidcel onboarding page → Resend). Per
this task's explicit scope ("update the task documentation only"), this
was **not resolved** — `07_Parking`'s Resend entry and PM-003's Google-Form
framing were deliberately left as-is rather than guessed at. Two readings
are possible and need the project owner to pick one:

1. The Google Form + Apps Script system (proven working) is being replaced
   by a new Payment Link → onboarding page → Resend system (in progress,
   incomplete) — in which case PM-003's Resend-deferral reasoning no longer
   holds and should be reversed.
2. Both systems coexist for different purposes (e.g., Apps Script for
   internal task/ops tracking, Resend for the customer-facing onboarding
   sequence) — in which case PM-003's reasoning still holds for the
   Apps Script side, and this Resend work is genuinely new/additive scope.

See `Backlog.md` for this as an open item.

## 2026-07-25 — G1-06C: onboarding entry point finalized, backend preserved

Project owner finalized the architecture: **replace the Google Form entry
point with the Vidcel onboarding page; preserve Google Sheets + the existing
Apps Script as the backend workflow (unchanged).**

This resolves the PM-003/G1-06 conflict logged above **in favor of PM-003's
original reasoning** — the backend is confirmed to stay Apps Script, not
Resend. It does not resolve whether Resend plays any role *within* the new
onboarding page itself (e.g., its own confirmation email); the instruction
didn't mention Resend at all, so that stays an open item in `Backlog.md`
rather than assumed either way.

**Important consequence, not stated explicitly by the owner but necessary
for honesty:** the Google Form's proven behavior (required fields, legal
consent, delivery to the spreadsheet) was evidence *for the Google Form
specifically*. Replacing the entry point with a different page means that
evidence no longer automatically applies — a new page is a new artifact
until proven otherwise. Rather than silently carrying forward "Completed" on
`04_Gates` items 3–4 (required fields/consent; form→spreadsheet delivery),
they were reset to **Not Started**, with the original Google Form evidence
kept in the cell (not deleted) and explicitly labeled as pre-dating the
entry-point change. This is a judgment call in the spirit of "do not infer
completion without direct evidence" from prior tasks, not something the
owner asked for directly — flagging it here in case that reset is not what
was intended.

Also newly surfaced: **how** the onboarding page actually gets data into the
existing Google Sheet was never specified (embed the real Form? a new Apps
Script Web App endpoint? direct Sheets API calls?). This is real, undecided
technical scope, not paperwork — added as a new task, **G1-09**, in
`03_MasterTask`/`02_Gantt` (Not Started, blocks Gate 1 items 3–4). Nothing
was implemented; only the task and its open design question were recorded.

Gate 1 evidence count dropped from 11/15 to 9/15 Completed as a direct
result of the honest reset above — this is not new bad news, it's the same
underlying gap (the onboarding page doesn't exist yet) being counted
correctly instead of inheriting the old Form's credit.

## 2026-07-25 — G1-06D: Architecture Decision Document for the data bridge (G1-09)

Produced `ADD_G1-06D_Onboarding_Data_Bridge.md` — documentation only, no
code changed, no Stripe/Apps Script configuration touched.

**Key finding that shaped the whole document:** the existing registration
automation is wired to Google Forms' `onFormSubmit` event specifically.
That event cannot be triggered by any non-Form data source — not the
Sheets API, not a Cloudflare Worker, nothing. Every architecture option
therefore requires the same underlying fix regardless of which is chosen:
decoupling the registration logic from that trigger into a directly-callable
function. This isn't optional scope creep, it's a hard constraint the ADD
had to work around, not just recommend around.

**Options evaluated:** (A) Apps Script Web App calling the existing logic
directly, (B) direct Google Sheets API calls from the onboarding page's own
backend, (C) a Cloudflare Worker proxy, (D) embed/redirect to the real
Google Form as a lower-effort fallback.

**Recommended: Option A.** Reasoning: only option requiring no new vendor,
no new hosting, no new credential class, and it reuses the proven
registration logic by direct function call instead of duplicating it.
Option B doesn't solve the trigger problem on its own. **Option C would
reintroduce a custom Cloudflare Worker — the third time this specific
component has resurfaced after PM-003 explicitly deferred it** (see the
PM-003 entry and the G1-06 conflict entry above). Option D is viable only
if the business drops the custom-UX goal behind building the onboarding
page at all, which is a product call, not this document's to make.

**Explicitly stated in the ADD (per instruction):** none of the Google
Form's existing validation evidence transfers to whatever replaces it.
Building the Option-A Web App will need its own independent E2E validation
before PM OS `04_Gates` items 3–4 can honestly move back to Completed.

**Not done:** no code, no Apps Script changes, no Stripe changes, no PM OS
workbook changes (this task's deliverables were documentation-only and
did not include PM OS updates, unlike G1-06/G1-06C). Six concrete follow-up
implementation items are listed in the ADD's §6, none started, none
assigned a Task ID yet — including the Apps Script refactor itself, which
will need explicit authorization given it touches production automation.

## 2026-07-25 — G1-09: onboarding data model specified

Produced `SPEC_G1-09_Onboarding_Data_Model.md`. Documentation only — no
Stripe, Apps Script, or Google Sheets changes made, per instruction.

**Fields:** 18 reused (verified directly against the live Google Form
response header and `Customers` sheet schema in
`店舗IT担当_オンボーディング管理_v1` — not assumed from the task's example
list) + 6 new (Country, Preferred Language, Currency, WhatsApp, Time Zone,
a Country-conditional Legal Consent Set). The new fields are justified by
G1-06's confirmed evidence of both a JP and a US Stripe Payment Link — not
invented, per instruction.

**Most consequential finding:** the PM OS's own `00_Dashboard!B12` MRR
formula (`=契約数*2980`) hardcodes a ¥2,980 price for every customer. With a
USD Payment Link now confirmed to exist, the first US customer would
silently corrupt the MRR figure — this is a live latent bug, surfaced by
building this spec, not a hypothetical risk. Recorded as Gap 4 / build-order
item 3 in the spec; **not fixed here**, since this task is documentation
only and a formula change would need its own Task ID even though it's
small.

**Other gaps found:** legal consent checkboxes are captured in the raw Form
response log but never copied into the processed `Customers` table (a
pre-existing gap, unrelated to the multi-market question); Stripe payment
status is still customer self-attested, not verified (same gap G1-06
already flagged); no language/currency branching exists anywhere in the
Apps Script logic inspected; legal requirements for non-Japan consent are
explicitly left to legal review, not guessed at.

**Recommended build order** (10 steps, none started, none assigned Task
IDs): legal review → add the new Sheet columns → fix the MRR currency bug →
persist consent to `Customers` → build the G1-06D data-bridge Web App →
add language/currency branching → build the onboarding page UI → wire page
to endpoint → replace Stripe self-attestation with real verification →
independent E2E validation per market. Full reasoning for the ordering is
in the spec's §4.

## 2026-07-25 — G1-11: multi-currency KPI model designed

Produced `SPEC_G1-11_Multicurrency_KPI_Model.md`. Documentation only — no
formula, sheet, or PM OS workbook changes, per instruction (this task
explicitly said "do not modify formulas / spreadsheets," unlike G1-06/
G1-06C which did include PM OS updates).

**Full impact analysis, cell-by-cell (not estimated):** 12 formulas across
`00_Dashboard`, `Cost_Model`, and `05_KPI` assume a single ¥2,980 price —
not just the one MRR cell flagged in G1-09, but everything downstream of
it: gross profit, gross margin %, LTV, and CAC all inherit the error.
Additionally found a **second, distinct** currency problem: `Cost_Model`'s
fixed costs (固定費/月, AI費, メール費) are plain JPY numbers with no
currency dimension at all, so even a currency-aware revenue figure would
still be netted against costs with an implicit, unstated currency
assumption. Confirmed currency-safe: all count-based and ratio-based KPIs
(Active Contracts, reply rate, close rate, churn rate) — these need no
change.

**Model recommended:** add `Billing Amount` alongside `SPEC_G1-09`'s
already-proposed `Currency` field (Currency alone can't fix MRR; both are
needed together — this was a gap in the G1-09 spec, closed here). FX
handled via Google Sheets' native `GOOGLEFINANCE` function — deliberately
avoids introducing a new vendor, API key, or credential, matching this
project's stated low-maintenance/low-cost priority.

**Reporting recommendation:** show both separate per-currency totals
(authoritative, no FX noise, accounting-appropriate) and one clearly-
labeled converted consolidated figure (executive at-a-glance), rather than
choosing one — reasoning and trade-offs are in the spec's §3.

**Explicitly flagged, not assessed:** Stripe's fee rate may differ between
JPY and USD transactions (`Cost_Model!B6`'s 3.6% is currently assumed
uniform, unverified against Stripe); tax/accounting treatment of
multi-currency revenue needs accounting/legal input, same category as
G1-09's flagged need for legal review of non-JP consent.

**Recommended gate, independent of the rest of the onboarding-page work:**
validate the corrected model with a synthetic USD customer row *before* the
first real US customer is onboarded — this can and should happen on its
own timeline, not blocked on `ADD_G1-06D`'s data-bridge work.

## 2026-07-25 — G1-12: BLOCKED, not implemented

G1-12 asked for the actual `doPost` Web App endpoint implementation
recommended by `ADD_G1-06D`. Before writing any code, checked for the two
things that determine whether an honest implementation is even possible:

1. **The actual bound Apps Script source code.** Attempted to locate it via
   Drive search (`mimeType = 'application/vnd.google-apps.script'`,
   `fullText contains 'handleFormSubmit'`). Found two Apps Script projects
   in the account — neither is the one bound to
   `店舗IT担当_オンボーディング管理_v1`; one is a Gantt-chart backup script,
   the other a Google Places API scraper. Everything documented so far
   about the onboarding automation's actual functions
   (`handleFormSubmit`, `generateInitialTasks`, etc.) was inferred from
   `Logs` sheet message strings and sheet column headers across G1-06
   through G1-11 — never from reading real source code. This was true the
   whole time; it just hadn't mattered until an implementation task
   required it.
2. **An Apps Script deployment/execution environment.** This session has
   Drive-level tools only. No Apps Script API access exists to deploy a
   Web App, assign it a real URL, or execute code to produce genuine test
   results.

**Decision, per explicit instruction: do not implement based on inferred
behavior.** G1-12 is recorded as **BLOCKED** in the PM OS
(`03_MasterTask`, `02_Gantt`) rather than marked with any design/code
deliverable standing in for progress. `04_Gates` items 3–4 now reference
G1-12 (implementation, blocked) downstream of G1-09 (design, complete via
`ADD_G1-06D`) — the two are explicitly not conflated. The existing Google
Form's `Logs` evidence continues to **not** count as evidence for the new
endpoint, per instruction, restated here for emphasis since it would be an
easy mistake to reach for that evidence out of habit.

Produced `CHECKLIST_G1-12_Source_Access.md`: an itemized list of exactly
what's needed to unblock (the real `.gs` files, `appsscript.json`, trigger
configuration, script properties, and a decision on how deployment/testing
will actually happen — likely the owner running a manual deploy/test loop,
since no Apps Script API tool is provisioned in this session). Also
formally separates five phases — source review, implementation,
deployment, runtime testing, E2E evidence — none of which may be assumed
complete because an earlier one (or a design document) exists.

**No code was written for G1-12.** Not a partial implementation, not a
draft — nothing, per instruction.

## 2026-07-25 — PM-AUTO-01: PM automation layer built and smoke-tested

Unlike every prior task in this project, this one's deliverable *was*
implementation — local tooling, not product/production code, so the usual
"do not implement" caution didn't apply. Built `automation/` (four Python
scripts, stdlib-only, no new dependency): `generate_completion_report.py`,
`generate_review_package.py`, `generate_next_task.py`, and an orchestrator
`run_pm_pipeline.py`. Full design and usage in `automation/README.md`.

**Explicitly out of scope, by design:** writing/editing product code,
touching Stripe, the production Apps Script, or Google Sheets, deciding
PASS/FAIL/BLOCKED, or auto-approving/executing the next-task draft. The
task's own instruction ("Human approval remains mandatory... No
implementation begins until the user explicitly approves") is enforced
structurally — nothing in this layer calls out to Claude Code or any
other execution path; it only writes markdown/JSON files for a human to
act on.

**Auto Stop / Auto Continue implementation choice:** rather than
text-scanning the risks/blockers prose for the eight stop keywords
(`BLOCKED`, `EVIDENCE_MISSING`, `PRODUCTION_CHANGE`, `ARCHITECTURE_CHANGE`,
`PAYMENT_CHANGE`, `LEGAL_DECISION`, `SECRET_REQUIRED`,
`DEPLOYMENT_REQUIRED` — which would be unreliable in both directions),
`task_meta.json` requires them to be set **explicitly** in a `flags`
array. The category field (`Documentation`/`Tests`/etc.) is recorded but
doesn't itself gate anything — only `flags` does. This is a deliberate
deviation from a literal "detect these categories automatically" reading
of the instructions, in favor of an honest, explicit signal over a guessed
one — flagged here in case that trade-off should go the other way.

**Actually run, not just written:** smoke-tested twice against this repo —
once with no flags (completed all three stages, real output committed:
`automation/reports/latest_report.md`, `automation/review/review_request.md`,
`automation/tasks/NEXT_TASK_DRAFT.md`), once with `flags: ["BLOCKED"]`
(halted correctly at stage 1, exit code 2, stages 2–3 did not run). Neither
pytest, mypy, ruff, nor an npm build is configured in this repo, so the
"tool found and actually ran" code path is **not yet exercised** — only
the "not configured, correctly skipped, not silently omitted" path is.
Recorded as the suggested next task: run this pipeline against `ai-lead-os`
(which has real pytest/mypy/ruff config) to validate that path for real.

**Design choice on folder structure:** the task's "Required Folder
Structure" listed `automation/`, `reports/`, `review/`, `tasks/`,
`knowledge/` without clear nesting. Interpreted as `automation/{reports,
review,tasks}/` (matching the architecture diagram exactly) plus reuse of
the project's *existing* top-level `knowledge/` folder rather than a
duplicate `automation/knowledge/` — the task's own final instruction
("update **the** knowledge folder") refers to a single, already-existing
folder throughout this project. Flagged here in case a separate
`automation/knowledge/` (e.g. for automation-run logs) was actually
intended.

## 2026-07-25 — PM-AUTO-02: automation validated against real ai-lead-os tooling

Directly closes the gap PM-AUTO-01 left open: the "tool found and actually
ran" code path (as opposed to "not configured, correctly skipped") had
never been exercised against a repo with real pytest/mypy/ruff/Alembic
config. `ai-lead-os` was used as the real target, read-only (no push
access in this session — nothing was ever going to be committed there).

**Ground truth established first, deliberately, before trusting the
automation's own output:** ran every real command from `ai-lead-os`'s
`CONTRIBUTING.md` by hand — `uv run ruff check .`, `uv run ruff format
--check .`, `uv run mypy src`, `uv run alembic upgrade head` +
`uv run alembic check`, `uv run pytest --cov=ai_lead_os
--cov-report=term-missing` — before running the automation once. All
clean: ruff/ruff-format/mypy pass, Alembic reports no drift, 1006 tests
pass, 91.07% coverage (≥90% threshold in `pyproject.toml`).

**`generate_review_package.py` rewritten** to make this validation
possible at all: the PM-AUTO-01 version hardcoded generic `pytest`/
`mypy .`/`ruff check .` invocations against this repo (`vidcel-dashboard`)
only, with no way to point it at another repo's tooling. Added:
- `--root <path>` so the script can run checks against an arbitrary
  target repo while still writing its own reports/review output under
  this repo's `automation/`.
- A `Runner` that detects `uv`-based invocation via `uv.lock` presence
  (`ai-lead-os` uses `uv` exclusively per its own docs) and falls back to
  a bare tool call, or `SKIPPED` with a stated reason, otherwise.
- Real config discovery via `tomllib` against the target's
  `pyproject.toml` — `[tool.ruff]`, `[tool.mypy]` (+ `strict` flag),
  `[tool.pytest.ini_options]`, `[tool.coverage.run].source` — rather than
  assuming ai-lead-os-specific commands. This was a deliberate choice:
  generic detection logic that happens to reproduce ai-lead-os's exact
  documented commands is stronger evidence than a script special-cased to
  match one repo.
- Separate Ruff-check and Ruff-format-check steps (previously conflated),
  and a new Alembic upgrade-head + check step, gated on `alembic.ini`
  being present.
- A `quality_checks.json` machine-readable output (`name`, `command`,
  `status`, `exit_code`, `reason` per check) alongside the existing
  markdown, and an explicit "Overall: PASS/FAIL (n passed, n failed, n
  skipped)" line plus a per-check status table in `review_request.md`.

**Bug fixed during this task (not a functional bug, but a real one):**
`run_pytest_with_coverage()`'s skip-guard was written as two ANDed
conditions, the first of which (`"pytest" not in
pyproject["tool"]["pytest"]["ini_options"]`) checks for the literal
string `"pytest"` as a *key inside* `ini_options`, which is structurally
meaningless — it evaluates true almost unconditionally, so the guard's
actual behavior reduced to just the second, correct clause
(`"ini_options" not in pyproject["tool"]["pytest"]`). Simplified to the
single correct condition and re-ran against `ai-lead-os` to confirm
identical (correct) behavior before and after.

**Also fixed: `run_pm_pipeline.py` didn't forward `--root`** to
`generate_review_package.py` at all — a gap from when `--root` was added
mid-session. Added `--root` as a pipeline-level argument, forwarded
alongside the existing `--base`.

**Scenario 1 (successful run, `flags: []`) — verified against real
captured output, not inference:** ran the full pipeline
(`run_pm_pipeline.py automation/reports/task_meta.json --root
/workspace/ai-lead-os`) with a `task_meta.json` written for this task.
All 6 checks (Ruff check, Ruff format check, mypy (strict), Alembic
upgrade head, Alembic check, pytest with coverage) were discovered from
`ai-lead-os`'s real config and actually executed via `uv run`; every
result matched the manual baseline byte-for-byte in substance: "All
checks passed!", "314 files already formatted", "Success: no issues
found in 195 source files", "No new upgrade operations detected.", "1006
passed in 190.87s", 91.07% coverage. `latest_report.md`/`.json`,
`review_request.md`, `quality_checks.json`, and
`tasks/NEXT_TASK_DRAFT.md` were all generated. A minimal, harmless,
doc-only change (one HTML comment appended to `ai-lead-os/README.md`) was
made beforehand so the git-diff/git-status detection had a real non-empty
diff to report on — confirmed present verbatim in `reports/git_diff.md`
and `git status --short` in `review_request.md`. No business logic in
`ai-lead-os` was touched.

**Scenario 2 (controlled failure) — verified detection, not just
absence of a crash:** added a throwaway file
(`scratch_pm_auto02_tmp/__pmauto02_ruff_violation.py`, two unused imports
+ one unused variable — a Ruff violation only, chosen as the safest of
the three suggested options since it can't affect mypy/pytest/coverage
results) inside `ai-lead-os`. Re-running `generate_review_package.py
--root /workspace/ai-lead-os` correctly reported `Overall: FAIL (5
passed, 1 failed, 0 skipped)`, script exit code 1, `Ruff check` status
`FAIL` with the real `F401`/`F841` Ruff output captured verbatim in
`test_results.md`, while the other 5 checks still correctly reported
PASS — no false PASS on the failing check, no false FAIL bleeding into
unrelated ones. `review_request.md`'s summary table and git-status
section both reflected the failure clearly.

**Restoration confirmed, not assumed:** deleted the scratch file/
directory, ran `git checkout -- README.md`, and confirmed `git status
--short` returned empty in `ai-lead-os`. Re-ran the review package once
more and got `Overall: PASS (6 passed, 0 failed, 0 skipped)` again,
confirming the repo was genuinely back to its clean, passing baseline —
not just that the working tree looked clean. `.venv/` and `data/*.db`
(created by `uv sync --frozen` / `alembic upgrade head` earlier in this
task) are properly gitignored in `ai-lead-os` and never appeared in `git
status` at any point.

**Result: PM-AUTO-01's previously-unverified code path is now verified.**
The automation correctly discovers project-specific tooling from a
target repo's own config, executes real commands, captures real output,
distinguishes PASS from FAIL from SKIPPED correctly, and does not
silently swallow or misreport a failure. No product/business code was
changed in `ai-lead-os` (read-only session access; nothing was committed
there) or in `店舗IT担当`'s Stripe/Apps Script/Sheets systems. Changed
files in this repo: `automation/generate_review_package.py`,
`automation/run_pm_pipeline.py`.

## 2026-07-25 — PM-AUTO-03: structured, deterministic PM decision package

Built a second, more structured layer on top of PM-AUTO-01/02's existing
review package: `automation/generate_decision_package.py`, producing
`review/review_summary.md`, `review/review_decision.json`, and
`review/next_task_draft.md`. Full design in `automation/DECISION_PACKAGE.md`.

**Central design constraint, taken directly from the task instructions
("Do not parse free-form text. Every field must have a fixed meaning"):**
`review_decision.json` never reads `risks`/`remaining_blockers`/`evidence`/
`suggested_next_task` prose to decide anything. Every field is either
copied verbatim from an explicit, new `task_meta.json` field (`risk`,
`next_task_id`, `status_override` — all three added to the schema this
task, documented in `task_meta.example.json`) or derived by a fixed rule
over other structured data:

- **`status`**: `status_override` if set (always wins) → else any
  auto-stop flag present → `BLOCKED` → else any `FAIL` in this cycle's
  `quality_checks.json` → `FAIL` → else `PASS`. "This cycle's" means
  `quality_checks.json`'s own `generated_at` is not older than
  `latest_report.json`'s — added `generated_at`/`overall`/`n_pass`/
  `n_fail`/`n_skip` fields to `quality_checks.json` (in
  `generate_review_package.py`) specifically to make this freshness check
  possible, so a stale leftover from an unrelated earlier run is never
  mistaken for this task's result.
- **`next_task`**: PASS → `next_task_id` verbatim or `null`. FAIL → always
  the fixed pattern `REWORK-<task_id>`, overriding whatever
  `next_task_id`/`suggested_next_task` said — a failed task's next step is
  fixing itself, not whatever was planned next. BLOCKED → always `null`.
- **`requires_human_approval`**: always `true` — fixed, per PM OS rule.
- **`risk`**: copied from `task_meta.json`, defaults to `MEDIUM` if
  omitted (a conservative default, not a guess). Does not currently gate
  anything — informational only, flagged as a limitation.

**`run_pm_pipeline.py` re-wired**, not just extended: on an auto-stop
flag, it now runs `generate_decision_package.py` *before* halting (so a
`BLOCKED` `review_decision.json` is always produced) and explicitly skips
both the quality-check stage and the freeform next-task generator — matching
the task's "no automatic continuation" requirement precisely, not just
avoiding a crash. On the non-blocked path, `generate_decision_package.py`
now runs after `generate_review_package.py` so it can see this cycle's
real check results. **Also fixed a gap for CI usability**, since the task
explicitly asked for GitHub-Actions suitability: the orchestrator's own
exit code previously stayed `0` even when the decision was `FAIL` (nothing
downstream checked `generate_review_package.py`'s own exit code). Now
`run_pm_pipeline.py` reads its own `review_decision.json` at the end and
returns exit code `3` for FAIL, `2` for BLOCKED (unchanged), `0` for PASS,
`1` for an invalid `task_meta.json` (unchanged) — a CI step can gate on
exit code alone with no output parsing.

**Deliverables, all actually produced (not just described):**
`automation/schemas/review_decision.schema.json` (JSON Schema draft-07,
one `description` per field), `automation/DECISION_PACKAGE.md` (prose:
derivation rules, field reference, usage, limitations), and three example
packages under `automation/examples/{pass,fail,blocked}/`, each containing
the `task_meta.json` fixture that produced it alongside the three real
generated output files.

**Scenario 1 (PASS)** — ran with no flags, no configured Python tooling in
this repo (all 5 quality checks correctly `SKIPPED`, `n_fail=0`) →
`status=PASS`, `next_task='PM-AUTO-04'` (from the fixture's explicit
`next_task_id`, not parsed from `suggested_next_task`), exit code 0.

**Scenario 2 (BLOCKED)** — ran with `flags: ["SECRET_REQUIRED"]` →
`status=BLOCKED`, `blocked=true`, `next_task=null`, quality-check stage
and freeform next-task generator both **did not run** (confirmed by
absence of a fresh `test_results.md`/`NEXT_TASK_DRAFT.md` write in that
run's output), `requires_human_approval=true` regardless, exit code 2.

**Scenario 3 (FAIL)** — same throwaway-Ruff-violation technique as
PM-AUTO-02: added a scratch file with 2 unused imports + 1 unused variable
to `ai-lead-os`, ran the pipeline with `--root /workspace/ai-lead-os` →
1 quality check FAILed → `status=FAIL`,
`next_task='REWORK-PM-AUTO-03-EXAMPLE-FAIL'` (the fixture's
`suggested_next_task` text was present but deliberately **not** used, per
the fixed FAIL rule), `review_summary.md`'s Recommendation section updated
to "do not proceed... rework required", exit code 3. Scratch file deleted
and `ai-lead-os`'s `git status --short` confirmed empty immediately after
capturing the example — nothing left behind.

**Validation beyond the three scenarios:** all three example
`review_decision.json` files (plus this task's own real run's output) were
validated against `schemas/review_decision.schema.json` using the
`jsonschema` Python library (`jsonschema.validate()`), not just eyeballed
against the schema prose.

**This task's own real evidence**: a `task_meta.json` was written for
PM-AUTO-03 itself (`risk: LOW`, `next_task_id: PM-AUTO-04`, no flags) and
run through the real pipeline — `status=PASS`, exit code 0 — committed
as `automation/review/review_decision.json` etc. alongside the code, same
pattern as PM-AUTO-01/02's self-referential smoke tests.

**Explicitly not done, flagged as limitations in `DECISION_PACKAGE.md`:**
`risk` doesn't gate the pipeline (informational only); no actual
`.github/workflows/*.yml` file was created (only the exit-code contract
that such a workflow could consume); `next_task_id` has no format
validation. No business logic was touched anywhere — `ai-lead-os` remains
read-only, nothing committed there; Stripe/Apps Script/Sheets untouched.
